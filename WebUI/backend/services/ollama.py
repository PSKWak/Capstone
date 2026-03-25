"""
Ollama service — calls local llama3 (or any model) to generate
a structured JSON travel itinerary, then geocodes every stop.
"""
import json
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import httpx

from backend.config import OLLAMA_BASE, OLLAMA_MODEL, OLLAMA_TIMEOUT
from backend.services.geocoding import geocode


# ── Time helpers ───────────────────────────────────────────────

SLOT_WINDOWS = {
    "Morning":   ("08:00", "12:00"),
    "Lunch":     ("12:15", "13:30"),
    "Afternoon": ("13:45", "17:30"),
    "Evening":   ("18:00", "20:00"),
    "Dinner":    ("20:00", "21:30"),
}
SLOT_ORDER = ["Morning", "Lunch", "Afternoon", "Evening", "Dinner"]


def _parse(s: str) -> datetime:
    return datetime.strptime(s, "%H:%M")


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _reschedule(stops: List[Dict], start_str: str = "08:00") -> List[Dict]:
    """Recompute planned_start / planned_end after reordering, keeping durations."""
    t = _parse(start_str)
    for s in stops:
        s["planned_start"] = _fmt(t)
        end = t + timedelta(minutes=s.get("duration_min", 60))
        s["planned_end"] = _fmt(end)
        t = end + timedelta(minutes=12)   # 12-min travel buffer
    return stops


# ── Ollama call ────────────────────────────────────────────────

async def check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


def _extract_json(text: str) -> Optional[str]:
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return m.group(1)
    start = text.find("{")
    if start == -1:
        return None
    return text[start:]


async def generate_itinerary(
    destination: str,
    days: int,
    interests: List[str],
    manual_places: List[str],
) -> Dict[str, Any]:
    """
    Call Ollama → parse JSON → geocode stops → return structured plan dict.
    """
    interest_str = ", ".join(interests) if interests else "General sightseeing"
    manual_block = ""
    if manual_places:
        mp_lines = "\n".join(f"  - {p}" for p in manual_places if p.strip())
        manual_block = f"""
MANDATORY USER-REQUESTED PLACES (must appear, distribute naturally across days):
{mp_lines}
"""

    schema = {
        "overview": "2 sentences about the trip strategy",
        "days": [
            {
                "day": 1,
                "day_theme": "One evocative theme for the day",
                "slots": [
                    {
                        "slot": "Morning",
                        "start": "08:00",
                        "end": "12:00",
                        "stops": [
                            {
                                "name": "Real place name",
                                "category": "Landmark",
                                "duration_min": 90,
                                "description": "Why it's unmissable in one sentence.",
                                "priority": 5,
                                "rating": 4.8,
                            }
                        ],
                    }
                ],
            }
        ],
    }

    prompt = f"""You are an expert local travel curator for {destination}.
Create a premium, realistic {days}-day itinerary.

RULES:
1. Exactly {days} days.
2. Include the most iconic landmarks of {destination} — do not skip them.
3. Group geographically close places in the same slot (minimise travel).
4. Prioritise interests: {interest_str}.
5. No repeated places across days.
6. Every "name" must be a REAL, geocodable place in {destination}.
7. duration_min: realistic visit time (museum=90-120, viewpoint=30-45, meal=60-75).
{manual_block}
TIME SLOTS:
- Morning: 08:00–12:00
- Lunch: 12:15–13:30
- Afternoon: 13:45–17:30
- Evening: 18:00–20:00
- Dinner: 20:00–21:30

OUTPUT: ONLY valid JSON matching this schema exactly, no markdown, no commentary:
{json.dumps(schema, indent=2)}"""

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        r = await client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        r.raise_for_status()
        raw = r.json().get("response", "")

    json_str = _extract_json(raw)
    if not json_str:
        raise ValueError("Ollama returned no JSON. Try regenerating.")

    try:
        plan = json.loads(json_str)
    except json.JSONDecodeError:
        # trim to last valid brace
        cut = max(json_str.rfind("}"), json_str.rfind("]"))
        if cut != -1:
            plan = json.loads(json_str[: cut + 1])
        else:
            raise

    return await _build_stop_list(plan, destination, days, manual_places)


# ── Convert LLM JSON → structured stop list ────────────────────

async def _build_stop_list(
    plan: Dict,
    destination: str,
    days: int,
    manual_places: List[str],
) -> Dict[str, Any]:
    from backend.services.geocoding import jitter as _jitter
    dest_coord = await geocode(destination)
    if not dest_coord:
        city = destination.split(",")[0].strip()
        dest_coord = await geocode(city)
    if not dest_coord:
        raise ValueError(f"Could not geocode destination '{destination}'. Check the spelling.")
    dest_lat, dest_lon = dest_coord

    days_out: List[Dict] = []
    stop_id   = 1
    days_list = sorted(plan.get("days", []), key=lambda d: int(d.get("day", 0)))

    for d in range(1, days + 1):
        day_obj = next((x for x in days_list if int(x.get("day", 0)) == d), None)
        if not day_obj:
            days_out.append({"day": d, "stops": [], "total_duration_min": 0, "overview": ""})
            continue

        stops: List[Dict] = []
        order = 1

        for slot_name in SLOT_ORDER:
            slot_map = {s["slot"]: s for s in day_obj.get("slots", []) if isinstance(s, dict)}
            slot = slot_map.get(slot_name, {})
            win_start, win_end = SLOT_WINDOWS[slot_name]
            t          = _parse(slot.get("start", win_start))
            window_end = _parse(slot.get("end",   win_end))

            for raw_stop in slot.get("stops", []):
                if not isinstance(raw_stop, dict):
                    continue
                name = (raw_stop.get("name") or "").strip()
                if not name:
                    continue

                dur = raw_stop.get("duration_min", 75)
                try:
                    dur = int(dur)
                except Exception:
                    dur = 75

                planned_start  = _fmt(t)
                end_dt         = t + timedelta(minutes=dur)
                if end_dt > window_end:
                    dur    = max(15, int((window_end - t).total_seconds() // 60))
                    end_dt = t + timedelta(minutes=dur)

                coords = await geocode(f"{name}, {destination}")
                if coords:
                    lat, lon = coords[0], coords[1]
                else:
                    lat, lon = _jitter(dest_lat, dest_lon, stop_id)

                stops.append({
                    "id":            f"stop_{stop_id}",
                    "name":          name,
                    "lat":           lat,
                    "lon":           lon,
                    "category":      (raw_stop.get("category") or "Sightseeing").strip(),
                    "description":   (raw_stop.get("description") or "").strip(),
                    "duration_min":  dur,
                    "planned_start": planned_start,
                    "planned_end":   _fmt(end_dt),
                    "day":           d,
                    "visit_order":   order,
                    "priority":      int(raw_stop.get("priority", 4)),
                    "rating":        float(raw_stop.get("rating", 4.5)),
                    "is_manual":     False,
                    "status":        "pending",
                    "checked_in":    False,
                })
                stop_id += 1
                order   += 1
                t        = end_dt + timedelta(minutes=12)
                if t >= window_end:
                    break

        # Inject manual places on day 1 if not already present
        if d == 1 and manual_places:
            existing = {s["name"].lower() for s in stops}
            for mp in manual_places:
                mp = mp.strip()
                if not mp or mp.lower() in existing:
                    continue
                coords = await geocode(f"{mp}, {destination}")
                if coords:
                    lat, lon = coords[0], coords[1]
                else:
                    lat, lon = _jitter(dest_lat, dest_lon, stop_id)
                stops.append({
                    "id":            f"stop_{stop_id}",
                    "name":          mp,
                    "lat":           lat,
                    "lon":           lon,
                    "category":      "Your Pick",
                    "description":   "Hand-picked by you — must visit!",
                    "duration_min":  60,
                    "planned_start": "17:30",
                    "planned_end":   "18:30",
                    "day":           1,
                    "visit_order":   order,
                    "priority":      5,
                    "rating":        5.0,
                    "is_manual":     True,
                    "status":        "pending",
                    "checked_in":    False,
                })
                stop_id += 1
                order   += 1

        total = sum(s["duration_min"] for s in stops)
        days_out.append({
            "day":               d,
            "day_theme":         day_obj.get("day_theme", f"Day {d}"),
            "stops":             stops,
            "total_duration_min": total,
            "overview":          day_obj.get("day_theme", ""),
        })

    return {
        "destination": destination,
        "days":        days,
        "overview":    plan.get("overview", ""),
        "plan":        days_out,
        "generated_at": datetime.utcnow().isoformat(),
        "cached":      False,
    }
