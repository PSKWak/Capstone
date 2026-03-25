import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit.components.v1 import html
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
import re
import requests

# ============================================================
# CONFIG
# ============================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_MODEL = "llama3:latest"
OLLAMA_TIMEOUT_SEC = 600

CACHE_DIR = Path("itinerary_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_JSONL = CACHE_DIR / "ollama_itineraries.jsonl"
REPLAN_CACHE_JSONL = CACHE_DIR / "replanned_itineraries.jsonl"

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="🌍 AI Travel Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
.main { background: #0b1220; }
.stApp { background: #020617; }

label, .stMarkdown, .stText, .stCaption, p, span, div {
    color: #e5e7eb;
}

.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stMultiSelect label,
.stTextArea label,
.stSlider label,
.stCheckbox label {
    color: #f8fafc !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    color: #111827 !important;
    background-color: #f3f4f6 !important;
}

.stSelectbox div[data-baseweb="select"] *,
.stMultiSelect div[data-baseweb="select"] * {
    color: #111827 !important;
    fill: #111827 !important;
    opacity: 1 !important;
}

[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #cbd5f5 !important;
    border-radius: 8px !important;
}

[data-baseweb="select"] > div * {
    color: #111827 !important;
    fill: #111827 !important;
    opacity: 1 !important;
}

[data-baseweb="select"] input {
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}

[data-baseweb="select"] input::placeholder {
    color: #6b7280 !important;
    -webkit-text-fill-color: #6b7280 !important;
    opacity: 1 !important;
}

div[data-baseweb="popover"] {
    background: transparent !important;
}

div[data-baseweb="popover"] ul {
    background: #ffffff !important;
    color: #111827 !important;
    border-radius: 8px !important;
}

div[data-baseweb="popover"] li,
div[role="listbox"] > div,
div[role="option"] {
    background: #ffffff !important;
    color: #111827 !important;
    opacity: 1 !important;
    font-weight: 500 !important;
}

div[data-baseweb="popover"] li *,
div[role="listbox"] > div *,
div[role="option"] * {
    color: #111827 !important;
    fill: #111827 !important;
    opacity: 1 !important;
}

div[data-baseweb="popover"] li:hover,
div[role="option"]:hover {
    background: #e5e7eb !important;
    color: #111827 !important;
}

div[data-baseweb="popover"] li[aria-selected="true"],
div[role="option"][aria-selected="true"] {
    background: #dbeafe !important;
    color: #111827 !important;
}

input::placeholder,
textarea::placeholder {
    color: #6b7280 !important;
    opacity: 1 !important;
}

.location-card {
    background: #020617;
    padding: 18px;
    border-radius: 12px;
    box-shadow: 0 3px 8px rgba(15, 23, 42, 0.85);
    margin: 10px 0;
    border-left: 5px solid #38bdf8;
    color: #e5e7eb;
}

.location-card h4 {
    color: #f9fafb;
    margin-bottom: 8px;
    font-size: 1.05em;
}

.location-card p {
    color: #cbd5f5;
    margin: 5px 0;
    font-size: 0.94em;
}

.day-header {
    background: linear-gradient(135deg, #38bdf8 0%, #22c55e 100%);
    color: #0b1120;
    padding: 18px;
    border-radius: 10px;
    margin: 20px 0 10px 0;
    text-align: center;
    font-size: 1.4em;
    font-weight: bold;
    box-shadow: 0 4px 10px rgba(56, 189, 248, 0.5);
}

.status-badge {
    padding: 7px 15px;
    border-radius: 20px;
    font-weight: bold;
    display: inline-block;
    margin: 5px 0;
    font-size: 0.86em;
}

.status-completed { background: #22c55e; color: #022c22; }
.status-current { background: #38bdf8; color: #020617; }
.status-pending { background: #eab308; color: #1f2937; }
.status-skipped { background: #ef4444; color: #fef2f2; }

.metric-card {
    background: #020617;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 3px 8px rgba(15, 23, 42, 0.9);
    border: 1px solid #1f2937;
}

.metric-card h3 {
    color: #e5e7eb;
    font-size: 0.9em;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

.metric-card h2 { color:#f9fafb; margin:10px 0; }
.metric-card p { color:#9ca3af; font-size:0.9em; }

.info-box {
    background:#0f172a;
    border-left:5px solid #38bdf8;
    padding:16px;
    border-radius:10px;
    margin:10px 0;
    color:#e5e7eb;
}

.replan-box {
    background:#0f172a;
    border-left:5px solid #eab308;
    padding:18px;
    border-radius:10px;
    margin:10px 0;
    color:#e5e7eb;
}

.success-box {
    background:#052e16;
    border-left:5px solid #22c55e;
    padding:16px;
    border-radius:10px;
    margin:10px 0;
    color:#dcfce7;
}

.stButton>button {
    background: linear-gradient(135deg, #38bdf8 0%, #22c55e 100%);
    color:#020617;
    border:none;
    border-radius:10px;
    padding:10px 20px;
    font-weight:bold;
}

.stButton>button:hover {
    transform: translateY(-1px);
}

/* 🔥 Increase expander title size (Day 1, Day 2, etc.) */
/* 🔥 Increase expander title size (Day 1, Day 2, etc.) */
div[data-testid="stExpander"] summary {
    padding: 14px 0 !important;
}

div[data-testid="stExpander"] summary p {
    font-size: 38px !important;
    font-weight: 800 !important;
    color: #f9fafb !important;
    margin: 0 !important;
}

div[data-testid="stExpander"] summary span {
    font-size: 38px !important;
    font-weight: 800 !important;
    color: #f9fafb !important;
}


h1, h2, h3, h4 { color:#f9fafb !important; }
[data-testid="stSidebar"] { background:#020617; }
[data-testid="stSidebar"] .element-container { color:#e5e7eb; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA CLASSES
# ============================================================
@dataclass
class Location:
    id: int
    name: str
    lat: float
    lon: float
    category: str
    planned_duration: int
    planned_start: str
    planned_end: str
    priority: int
    description: str
    rating: float
    day: int
    status: str = "pending"
    visit_order: int = 0
    approximate_location: bool = False


@dataclass
class DayItinerary:
    day_number: int
    locations: List[Location] = field(default_factory=list)
    total_planned_time: int = 0
    status: str = "pending"


# ============================================================
# SESSION STATE
# ============================================================
def initialize_session_state():
    defaults = {
        "stage": "input",
        "user_inputs": {
            "days": 2,
            "destination": "Washington DC",
            "interests": ["City Highlights", "Museums"],
            "pace": "Balanced",
            "must_visit_locations": [],
            "base_location_text": ""
        },
        "itinerary": {},
        "current_day": 1,
        "live_active_day": 1,
        "ollama_model": DEFAULT_MODEL,
        "llama_raw_output": "",
        "llama_pretty_text": "",
        "llama_cache_hit": False,
        "llama_saved_ok": False,
        "base_location": None,
        "sim_speed_mps": 35.0,

        # replan state
        "replan_results": None,
        "replan_request_text": "",
        "replan_selected_day": 1,
        "replan_selected_anchor_id": None,
        "replan_action_mode": "Insert after selected stop",
        "replan_selected_suggestions": [],
        "replan_checkbox_states": {},
        "replan_cache_hit": False,
        "replan_saved_ok": False,
        # review edit state
        "review_edit_open_loc_id": None,
        "review_replace_mode_by_loc": {},
        "review_custom_place_by_loc": {},
        "review_ai_replace_results_by_loc": {},
        "review_ai_replace_selected_by_loc": {},
        "review_add_open_day": None,
        "review_add_open_loc_id": None,



        # dashboard refresh after patch
        "replan_pending_refresh": False,
        "replan_success_message": "",
        "replan_applied_day": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


initialize_session_state()

# Sync live_active_day from query param if live page is open
if st.session_state.get("stage") == "live_trip":
    params = st.query_params
    if "active_day" in params:
        try:
            qp_day = int(params["active_day"])
            if st.session_state.itinerary and qp_day in st.session_state.itinerary:
                st.session_state.live_active_day = qp_day
        except (ValueError, TypeError):
            pass

PACE_SETTINGS = {
    "Relaxed": {"duration_multiplier": 1.20},
    "Balanced": {"duration_multiplier": 1.00},
    "Fast-paced": {"duration_multiplier": 0.85},
}

SLOT_ORDER = ["Morning", "Lunch", "Afternoon", "Evening", "Dinner"]

DEFAULT_SLOT_WINDOWS = {
    "Morning": ("08:30", "12:00"),
    "Lunch": ("12:30", "13:30"),
    "Afternoon": ("13:45", "17:30"),
    "Evening": ("18:00", "20:00"),
    "Dinner": ("20:00", "21:30"),
}


# ============================================================
# HELPERS
# ============================================================
def parse_hhmm(s: str) -> datetime:
    return datetime.strptime(s, "%H:%M")


def fmt_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def safe_hhmm(s: str, fallback: str) -> str:
    if isinstance(s, str) and re.match(r"^\d{2}:\d{2}$", s):
        return s
    return fallback


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def estimate_travel_buffer_minutes(lat1, lon1, lat2, lon2):
    dist_m = calculate_distance(lat1, lon1, lat2, lon2)
    if dist_m < 1000:
        return 10
    if dist_m < 3000:
        return 15
    if dist_m < 7000:
        return 20
    return 30


def get_total_locations() -> int:
    return sum(len(d.locations) for d in st.session_state.itinerary.values()) if st.session_state.itinerary else 0


def find_location_by_id(day_num: int, location_id: int) -> Optional[Location]:
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return None
    for loc in day_itin.locations:
        if loc.id == location_id:
            return loc
    return None


def get_live_active_day() -> int:
    if "live_active_day" not in st.session_state:
        st.session_state.live_active_day = 1
    available_days = sorted(list(st.session_state.itinerary.keys())) if st.session_state.itinerary else [1]
    if st.session_state.live_active_day not in available_days:
        st.session_state.live_active_day = available_days[0]
    return st.session_state.live_active_day


def get_next_location_id() -> int:
    max_id = 0
    for day in st.session_state.itinerary.values():
        for loc in day.locations:
            max_id = max(max_id, loc.id)
    return max_id + 1


def get_anchor_and_remaining(day_num: int, anchor_loc_id: int):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return None, []
    anchor = None
    remaining = []
    found = False
    for loc in day_itin.locations:
        if loc.id == anchor_loc_id:
            anchor = loc
            found = True
            continue
        if found:
            remaining.append(loc)
    return anchor, remaining


def recompute_visit_orders(day_num: int):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return
    for idx, loc in enumerate(day_itin.locations, start=1):
        loc.visit_order = idx


def reschedule_day_from_index(day_num: int, start_idx: int):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin or not day_itin.locations:
        return

    locs = day_itin.locations
    recompute_visit_orders(day_num)

    if start_idx <= 0:
        first_start = locs[0].planned_start if locs[0].planned_start else DEFAULT_SLOT_WINDOWS["Morning"][0]
        current_time = parse_hhmm(first_start)
        prev_lat = st.session_state.base_location["lat"] if st.session_state.base_location else locs[0].lat
        prev_lon = st.session_state.base_location["lon"] if st.session_state.base_location else locs[0].lon
        idx_range = range(0, len(locs))
    else:
        prev = locs[start_idx - 1]
        current_time = parse_hhmm(prev.planned_end)
        prev_lat, prev_lon = prev.lat, prev.lon
        idx_range = range(start_idx, len(locs))

    for idx in idx_range:
        loc = locs[idx]
        if idx > 0 or start_idx > 0:
            buffer_min = estimate_travel_buffer_minutes(prev_lat, prev_lon, loc.lat, loc.lon)
            current_time = current_time + timedelta(minutes=buffer_min)

        loc.planned_start = fmt_hhmm(current_time)
        end_time = current_time + timedelta(minutes=loc.planned_duration)
        loc.planned_end = fmt_hhmm(end_time)

        current_time = end_time
        prev_lat, prev_lon = loc.lat, loc.lon

    day_itin.total_planned_time = sum(x.planned_duration for x in locs)


def detect_replan_intent(user_request: str) -> str:
    req = (user_request or "").lower().strip()

    if any(word in req for word in ["shop", "shopping", "mall", "market", "boutique", "souvenir", "retail", "store"]):
        return "shopping"
    if any(word in req for word in
           ["food", "eat", "restaurant", "cafe", "coffee", "lunch", "dinner", "dessert", "bakery"]):
        return "food"
    if any(word in req for word in ["museum", "history", "art", "gallery", "culture", "cultural", "landmark"]):
        return "culture"
    if any(word in req for word in ["park", "nature", "garden", "outdoor", "walk", "trail", "waterfront"]):
        return "outdoor"

    return "general"


def filter_replan_suggestions_by_intent(suggestions: list, intent: str) -> list:
    allowed = {
        "shopping": ["shopping", "market", "mall", "boutique", "retail", "souvenir", "shopping district"],
        "food": ["food", "restaurant", "cafe", "dessert", "street food", "bakery", "eatery"],
        "culture": ["museum", "history", "cultural", "landmark", "gallery", "art", "heritage"],
        "outdoor": ["park", "garden", "outdoor", "trail", "waterfront", "nature", "plaza"],
        "general": []
    }

    blocked = {
        "shopping": ["dessert", "bakery", "cupcake", "cafe", "restaurant", "food", "sweet treat"],
        "food": [],
        "culture": ["restaurant", "bakery", "shopping mall"],
        "outdoor": ["bakery", "dessert"],
        "general": []
    }

    if intent == "general":
        return suggestions

    filtered = []
    allowed_words = allowed[intent]
    blocked_words = blocked[intent]

    for s in suggestions:
        category = str(s.get("category", "")).lower()
        name = str(s.get("name", "")).lower()
        desc = str(s.get("description", "")).lower()
        text = f"{category} {name} {desc}"

        has_allowed = any(word in text for word in allowed_words)
        has_blocked = any(word in text for word in blocked_words)

        if has_allowed and not has_blocked:
            filtered.append(s)

    return filtered


# ============================================================
# CACHE HELPERS
# ============================================================
def _normalize_interests(interests: List[str]) -> List[str]:
    return sorted([i.strip() for i in interests if i and i.strip()])


def _normalize_locations(locations: List[str]) -> List[str]:
    return sorted([x.strip().lower() for x in locations if x and x.strip()])


def make_cache_key(destination: str, days: int, interests: List[str], model: str, pace: str,
                   must_visit_locations: List[str]) -> str:
    base = {
        "destination": destination.strip().lower(),
        "days": int(days),
        "interests": _normalize_interests(interests),
        "model": model.strip().lower(),
        "pace": pace.strip().lower(),
        "must_visit_locations": _normalize_locations(must_visit_locations),
        "schema_version": 4
    }
    s = json.dumps(base, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def load_cached_record(cache_key: str) -> Optional[dict]:
    if not CACHE_JSONL.exists():
        return None
    try:
        with open(CACHE_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("cache_key") == cache_key:
                    return rec
    except Exception:
        return None
    return None


def append_cache_record(record: dict) -> None:
    try:
        with open(CACHE_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def make_replan_cache_key(
        destination: str,
        day_num: int,
        anchor_name: str,
        interests: List[str],
        pace: str,
        remaining_stops: List[Location],
        user_request: str,
        model_name: str,
        n: int = 5
) -> str:
    base = {
        "destination": normalize_replan_text(destination),
        "day_num": int(day_num),
        "anchor_name": normalize_replan_text(anchor_name),
        "interests": _normalize_interests(interests),
        "pace": normalize_replan_text(pace),
        "user_request": normalize_replan_text(user_request),
        "model": normalize_replan_text(model_name),
        "n": int(n),
        "schema_version": 2
    }
    s = json.dumps(base, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def load_replan_cached_record(cache_key: str) -> Optional[dict]:
    if not REPLAN_CACHE_JSONL.exists():
        return None
    try:
        with open(REPLAN_CACHE_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("cache_key") == cache_key:
                    return rec
    except Exception:
        return None
    return None


def append_replan_cache_record(record: dict) -> None:
    try:
        with open(REPLAN_CACHE_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ============================================================
# GEOCODING / OLLAMA
# ============================================================
@lru_cache(maxsize=256)
def geocode_destination(destination: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": destination, "format": "json", "limit": 1}
    headers = {"User-Agent": "ai-travel-planner-streamlit/6.0"}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


@lru_cache(maxsize=4096)
def geocode_place(place_query: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_query, "format": "json", "limit": 1}
    headers = {"User-Agent": "ai-travel-planner-streamlit/6.0"}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def ollama_available(model_name: str) -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=10)
        if r.status_code != 200:
            return False
        models = [m.get("name") for m in r.json().get("models", [])]
        return model_name in models
    except Exception:
        return False


def call_ollama(prompt: str, model_name: str) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={"model": model_name, "prompt": prompt, "stream": False},
        timeout=OLLAMA_TIMEOUT_SEC
    )
    if r.status_code != 200:
        raise RuntimeError(f"Ollama error: {r.status_code} - {r.text}")
    return r.json().get("response", "")


def _extract_json_block(text: str) -> Optional[str]:
    if not text:
        return None

    m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, flags=re.S)
    if m:
        return m.group(1)

    first_brace = text.find("{")
    first_bracket = text.find("[")
    if first_brace == -1 and first_bracket == -1:
        return None

    start = first_brace if first_bracket == -1 else (
        first_bracket if first_brace == -1 else min(first_brace, first_bracket)
    )
    candidate = text[start:].strip()
    last_curly = candidate.rfind("}")
    last_square = candidate.rfind("]")
    cut = max(last_curly, last_square)
    if cut != -1:
        candidate = candidate[:cut + 1]
    return candidate.strip()


# ============================================================
# VALIDATION
# ============================================================
def validate_and_normalize_itinerary_json(plan: dict, requested_days: int) -> dict:
    normalized = {"overview": "", "days": []}
    if not isinstance(plan, dict):
        raise ValueError("Plan is not a dictionary.")

    overview = plan.get("overview", "")
    normalized["overview"] = overview if isinstance(overview, str) else ""

    days_list = plan.get("days", [])
    if not isinstance(days_list, list):
        raise ValueError("Plan 'days' must be a list.")

    day_map = {}
    for day_obj in days_list:
        if not isinstance(day_obj, dict):
            continue

        try:
            day_num = int(day_obj.get("day"))
        except Exception:
            continue

        if day_num < 1 or day_num > requested_days:
            continue

        slots = day_obj.get("slots", [])
        if not isinstance(slots, list):
            slots = []

        normalized_slots = []
        seen_names = set()

        for slot in slots:
            if not isinstance(slot, dict):
                continue

            slot_name = slot.get("slot", "Morning")
            if slot_name not in SLOT_ORDER:
                slot_name = "Morning"

            default_start, default_end = DEFAULT_SLOT_WINDOWS[slot_name]
            start = safe_hhmm(slot.get("start"), default_start)
            end = safe_hhmm(slot.get("end"), default_end)

            stops = slot.get("stops", [])
            if not isinstance(stops, list):
                stops = []

            cleaned_stops = []
            for s in stops:
                if not isinstance(s, dict):
                    continue

                name = str(s.get("name", "")).strip()
                if not name or name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())

                category = str(s.get("category", "City Highlights")).strip() or "City Highlights"
                description = str(s.get("description", "")).strip()
                dur = s.get("duration_min", 60)
                try:
                    dur = int(dur)
                except Exception:
                    dur = 60
                dur = max(15, min(dur, 240))

                cleaned_stops.append({
                    "name": name,
                    "category": category,
                    "duration_min": dur,
                    "description": description
                })

            normalized_slots.append({
                "slot": slot_name,
                "start": start,
                "end": end,
                "stops": cleaned_stops
            })

        slot_map = {s["slot"]: s for s in normalized_slots}
        ordered_slots = [slot_map[s] for s in SLOT_ORDER if s in slot_map]
        day_map[day_num] = {"day": day_num, "slots": ordered_slots}

    for d in range(1, requested_days + 1):
        normalized["days"].append(day_map.get(d, {"day": d, "slots": []}))

    return normalized


def parse_and_validate_json_from_llm(raw_text: str, requested_days: int) -> dict:
    json_text = _extract_json_block(raw_text)
    if not json_text:
        raise ValueError("LLM did not return JSON.")
    plan = json.loads(json_text)
    return validate_and_normalize_itinerary_json(plan, requested_days)


# ============================================================
# ITINERARY MARKDOWN
# ============================================================
def pretty_itinerary_markdown_from_plan(plan: dict) -> str:
    if not isinstance(plan, dict):
        return ""

    lines = []
    overview = plan.get("overview")
    if isinstance(overview, str) and overview.strip():
        lines.append(f"**Overview:** {overview.strip()}")
        lines.append("")

    for day_obj in plan.get("days", []):
        day_num = day_obj.get("day", "")
        lines.append(f"## Day {day_num}")
        lines.append("")

        for slot in day_obj.get("slots", []):
            slot_name = slot.get("slot", "Slot")
            start = slot.get("start", "")
            end = slot.get("end", "")
            time_txt = f"({start} – {end})" if start and end else ""
            lines.append(f"### {slot_name} {time_txt}".strip())
            lines.append("")

            stops = slot.get("stops", [])
            if not stops:
                lines.append("_No stops listed._")
                lines.append("")
                continue

            for i, stop in enumerate(stops, start=1):
                name = stop.get("name", "")
                desc = stop.get("description", "")
                dur = stop.get("duration_min", None)
                bullet = f"{i}. **{name}**"
                if dur is not None:
                    bullet += f" ({dur} min)"
                if desc:
                    bullet += f" — {desc}"
                lines.append(bullet)
            lines.append("")

    return "\n".join(lines).strip()


# ============================================================
# ITINERARY GENERATION
# ============================================================
def generate_itinerary_json_with_ollama(
        destination: str,
        days: int,
        interests: List[str],
        model_name: str,
        pace: str,
        must_visit_locations: List[str]
) -> dict:
    cache_key = make_cache_key(destination, days, interests, model_name, pace, must_visit_locations)
    cached = load_cached_record(cache_key)
    if cached:
        st.session_state.llama_raw_output = cached.get("llama_raw_output", "")
        st.session_state.llama_pretty_text = cached.get("llama_pretty_text", "")
        st.session_state.llama_cache_hit = True
        st.session_state.llama_saved_ok = True
        return cached["itinerary_json"]

    st.session_state.llama_cache_hit = False
    st.session_state.llama_saved_ok = False

    interest_text = ", ".join(interests) if interests else "General sightseeing"
    must_visit_text = ", ".join(must_visit_locations) if must_visit_locations else "None"

    schema_example = {
        "overview": "1-2 sentences about geographic clustering, pacing, and priorities",
        "days": [
            {
                "day": 1,
                "slots": [
                    {
                        "slot": "Morning",
                        "start": "08:30",
                        "end": "12:00",
                        "stops": [
                            {
                                "name": "Place name",
                                "category": "City Highlights",
                                "duration_min": 90,
                                "description": "Why this stop fits the traveler"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    prompt = f"""
You are an expert local travel planner for {destination}.

Create a realistic, high-quality itinerary.

USER PROFILE
- Destination: {destination}
- Days: {days}
- Interests: {interest_text}
- Pace: {pace}
- Specific locations the user wants included: {must_visit_text}

MANDATORY RULES
1) Generate EXACTLY {days} days.
2) Use real places likely to exist in {destination}.
3) Do NOT repeat attractions.
4) Group nearby places together to reduce travel time.
5) Respect the pace:
   - Relaxed = fewer stops, longer visits
   - Balanced = moderate number of stops
   - Fast-paced = more stops, shorter visits
6) Include iconic landmarks early unless clearly irrelevant.
7) Strongly prioritize all user-requested specific locations if provided.
8) If a user-requested location seems valid, include it whenever geographically and logically feasible.
9) Lunch and dinner should be realistic food areas or restaurants.

TIME STRUCTURE
- Morning: 08:30–12:00
- Lunch: 12:30–13:30
- Afternoon: 13:45–17:30
- Evening: 18:00–20:00
- Dinner: 20:00–21:30

OUTPUT
- Return ONLY valid JSON
- No markdown
- No explanation
- Follow this schema exactly:
{json.dumps(schema_example, indent=2)}
""".strip()

    raw = call_ollama(prompt, model_name)
    st.session_state.llama_raw_output = raw

    try:
        itinerary_json = parse_and_validate_json_from_llm(raw, days)
    except Exception:
        repair_prompt = f"""
Return ONLY valid JSON.
No markdown.
No explanation.

Fix this travel itinerary into exactly {days} days and this schema:
{json.dumps(schema_example, indent=2)}

Input:
{raw}
""".strip()
        repaired_raw = call_ollama(repair_prompt, model_name)
        st.session_state.llama_raw_output = repaired_raw
        itinerary_json = parse_and_validate_json_from_llm(repaired_raw, days)

    pretty_text = pretty_itinerary_markdown_from_plan(itinerary_json)
    st.session_state.llama_pretty_text = pretty_text

    record = {
        "cache_key": cache_key,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "destination": destination,
        "days": int(days),
        "interests": _normalize_interests(interests),
        "pace": pace,
        "must_visit_locations": must_visit_locations,
        "model": model_name,
        "llama_raw_output": st.session_state.llama_raw_output,
        "llama_pretty_text": pretty_text,
        "itinerary_json": itinerary_json,
    }
    append_cache_record(record)
    st.session_state.llama_saved_ok = True
    return itinerary_json


def build_itinerary_from_ollama(
        destination: str,
        days: int,
        interests: List[str],
        pace: str,
        must_visit_locations: List[str]
) -> Dict[int, DayItinerary]:
    model_name = st.session_state.get("ollama_model", DEFAULT_MODEL)

    center = geocode_destination(destination)
    if not center:
        raise ValueError("Could not find that destination. Try a more specific name.")

    dest_lat, dest_lon = center
    pace_cfg = PACE_SETTINGS.get(pace, PACE_SETTINGS["Balanced"])
    duration_multiplier = pace_cfg["duration_multiplier"]

    plan = generate_itinerary_json_with_ollama(
        destination,
        days,
        interests,
        model_name,
        pace,
        must_visit_locations
    )

    itinerary: Dict[int, DayItinerary] = {}
    loc_id = 1
    days_list = sorted(plan.get("days", []), key=lambda d: int(d.get("day", 0)))

    for d in range(1, days + 1):
        day_obj = next((x for x in days_list if int(x.get("day", -1)) == d), None)
        if not day_obj:
            itinerary[d] = DayItinerary(day_number=d, locations=[], status="pending")
            continue

        slots = day_obj.get("slots", [])
        slot_map = {s.get("slot"): s for s in slots if isinstance(s, dict) and s.get("slot")}
        day_locs: List[Location] = []
        visit_order = 1
        prev_lat, prev_lon = dest_lat, dest_lon

        for slot_name in SLOT_ORDER:
            slot = slot_map.get(slot_name, {})
            if not slot:
                continue

            start_s = safe_hhmm(slot.get("start"), DEFAULT_SLOT_WINDOWS[slot_name][0])
            end_s = safe_hhmm(slot.get("end"), DEFAULT_SLOT_WINDOWS[slot_name][1])
            t = parse_hhmm(start_s)
            window_end = parse_hhmm(end_s)

            stops = slot.get("stops", [])
            if not isinstance(stops, list):
                stops = []

            for stop in stops:
                name = (stop.get("name") or "").strip()
                if not name:
                    continue

                category = (stop.get("category") or "City Highlights").strip()
                desc = (stop.get("description") or "").strip()
                dur = stop.get("duration_min", 60)

                try:
                    dur = int(dur)
                except Exception:
                    dur = 60

                dur = max(15, int(round(dur * duration_multiplier)))

                coords = None
                approximate = False
                try:
                    coords = geocode_place(f"{name}, {destination}")
                except Exception:
                    coords = None

                if not coords:
                    plat, plon = dest_lat, dest_lon
                    approximate = True
                else:
                    plat, plon = coords

                if day_locs:
                    travel_buffer = estimate_travel_buffer_minutes(prev_lat, prev_lon, plat, plon)
                    t = t + timedelta(minutes=travel_buffer)

                planned_start = fmt_hhmm(t)
                planned_end_dt = t + timedelta(minutes=dur)

                if planned_end_dt > window_end:
                    remaining = int((window_end - t).total_seconds() // 60)
                    if remaining < 15:
                        break
                    dur = max(15, remaining)
                    planned_end_dt = t + timedelta(minutes=dur)

                planned_end = fmt_hhmm(planned_end_dt)

                priority = 5 if slot_name in ["Morning", "Afternoon"] else 4
                if slot_name in ["Lunch", "Dinner"]:
                    priority = 3

                rating = 4.7 if slot_name not in ["Lunch", "Dinner"] else 4.6

                day_locs.append(Location(
                    id=loc_id,
                    name=name,
                    lat=float(plat),
                    lon=float(plon),
                    category=category,
                    planned_duration=dur,
                    planned_start=planned_start,
                    planned_end=planned_end,
                    priority=priority,
                    description=desc if desc else f"Planned for your interests: {', '.join(interests)}",
                    rating=rating,
                    day=d,
                    visit_order=visit_order,
                    approximate_location=approximate
                ))
                loc_id += 1
                visit_order += 1
                t = planned_end_dt
                prev_lat, prev_lon = plat, plon

        total_time = sum(x.planned_duration for x in day_locs)
        itinerary[d] = DayItinerary(
            day_number=d,
            locations=day_locs,
            total_planned_time=total_time,
            status="pending"
        )

    return itinerary


# ============================================================
# BASE LOCATION RESOLUTION
# ============================================================
def choose_demo_hotel(destination: str):
    options = [
        f"Hilton {destination}",
        f"Hilton Garden Inn {destination}",
        f"Marriott {destination}",
        f"Hyatt {destination}",
    ]

    for q in options:
        try:
            coords = geocode_place(q)
            if coords:
                return {"name": q, "lat": coords[0], "lon": coords[1]}
        except Exception:
            continue

    center = geocode_destination(destination)
    if center:
        lat, lon = center
        return {"name": f"Hotel near {destination}", "lat": lat + 0.01, "lon": lon + 0.01}
    return {"name": f"Hotel near {destination}", "lat": 0.0, "lon": 0.0}


def resolve_base_location(base_location_text: str, destination: str):
    base_location_text = (base_location_text or "").strip()

    if base_location_text:
        queries = [base_location_text, f"{base_location_text}, {destination}"]
        for q in queries:
            try:
                coords = geocode_place(q)
                if coords:
                    return {"name": base_location_text, "lat": coords[0], "lon": coords[1]}
            except Exception:
                continue

    return choose_demo_hotel(destination)


# ============================================================
# MID-TRIP REPLAN
# ============================================================
def normalize_replan_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def ollama_midtrip_replan_options(
        destination: str,
        day_num: int,
        anchor_name: str,
        interests: List[str],
        pace: str,
        remaining_stops: List[Location],
        user_request: str,
        model_name: str,
        n: int = 5
) -> dict:
    schema = {
        "anchor": anchor_name,
        "request_summary": "short summary",
        "suggestions": [
            {
                "name": "Place name",
                "category": "Category label",
                "estimated_duration_min": 60,
                "description": "Why this is a good fit right now"
            }
        ]
    }

    user_request = normalize_replan_text(user_request)
    remaining_names = [x.name for x in remaining_stops] if remaining_stops else []
    remaining_text = ", ".join(remaining_names) if remaining_names else "No remaining planned stops."
    intent = detect_replan_intent(user_request)

    replan_cache_key = make_replan_cache_key(
        destination=destination,
        day_num=day_num,
        anchor_name=anchor_name,
        interests=interests,
        pace=pace,
        remaining_stops=remaining_stops,
        user_request=user_request,
        model_name=model_name,
        n=n
    )

    cached = load_replan_cached_record(replan_cache_key)
    if cached:
        st.session_state.replan_cache_hit = True
        st.session_state.replan_saved_ok = True
        return cached["replan_result"]

    st.session_state.replan_cache_hit = False
    st.session_state.replan_saved_ok = False

    strict_rules = {
        "shopping": """
- If the user asks for shopping, return ONLY shopping-related places.
- Do NOT return dessert shops, cupcake shops, cafes, restaurants, or food places.
- Valid shopping categories: Shopping, Retail, Market, Mall, Boutique, Shopping District, Souvenir Shopping.
""",
        "food": """
- If the user asks for food, return ONLY food/drink places.
- Valid food categories: Food, Restaurant, Cafe, Dessert, Bakery, Street Food.
""",
        "culture": """
- If the user asks for culture/history/art, return ONLY museums, galleries, landmarks, and cultural sites.
""",
        "outdoor": """
- If the user asks for outdoor/nature, return ONLY parks, gardens, waterfronts, trails, and outdoor places.
""",
        "general": """
- Match the request as closely as possible.
"""
    }[intent]

    prompt = f"""
You are a smart travel replanning assistant for {destination}.

Current context:
- Day: {day_num}
- Traveler interests: {", ".join(interests) if interests else "General sightseeing"}
- Pace: {pace}
- Current / anchor stop: {anchor_name}
- Remaining planned stops today: {remaining_text}
- User request: {user_request}

Task:
Suggest {n} strong options for the rest of today.

STRICT RULES:
1) Suggest real places likely to exist in or near {destination}
2) Suggestions should fit naturally with today's remaining plan
3) Avoid repeating the current anchor stop
4) Favor literal relevance to the user request
5) Keep options realistic for the same day
6) {strict_rules}
7) Return ONLY valid JSON with this schema:
{json.dumps(schema, indent=2)}
""".strip()

    raw = call_ollama(prompt, model_name)
    json_text = _extract_json_block(raw)
    if not json_text:
        raise ValueError("No valid JSON from mid-trip replanning step.")

    data = json.loads(json_text)
    suggestions = data.get("suggestions", [])
    filtered = filter_replan_suggestions_by_intent(suggestions, intent)
    data["suggestions"] = filtered

    if not data.get("request_summary"):
        data["request_summary"] = f"Detected request type: {intent}"

    if intent != "general" and not filtered:
        data["request_summary"] = f"No strong {intent}-only suggestions found. Try a slightly broader request."

    record = {
        "cache_key": replan_cache_key,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "destination": destination,
        "day_num": int(day_num),
        "anchor_name": anchor_name,
        "interests": _normalize_interests(interests),
        "pace": pace,
        "remaining_stops": remaining_names,
        "user_request": user_request,
        "model": model_name,
        "n": int(n),
        "replan_result": data
    }

    append_replan_cache_record(record)
    st.session_state.replan_saved_ok = True
    return data


def resolve_new_location_from_place(new_place: dict, destination: str, day_num: int) -> Location:
    name = (new_place.get("name") or "").strip()
    if not name:
        raise ValueError("Suggestion has no place name.")

    category = (new_place.get("category") or "Suggestion").strip()
    description = (new_place.get("description") or "Suggested during mid-trip replanning").strip()

    try:
        dur = int(new_place.get("estimated_duration_min", 60))
    except Exception:
        dur = 60
    dur = max(15, dur)

    coords = None
    approximate = False
    try:
        coords = geocode_place(f"{name}, {destination}")
    except Exception:
        coords = None

    if coords:
        lat, lon = float(coords[0]), float(coords[1])
    else:
        center = geocode_destination(destination)
        if center:
            lat, lon = float(center[0]), float(center[1])
        else:
            lat, lon = 0.0, 0.0
        approximate = True

    return Location(
        id=get_next_location_id(),
        name=name,
        lat=lat,
        lon=lon,
        category=category,
        planned_duration=dur,
        planned_start="08:30",
        planned_end="09:30",
        priority=4,
        description=description,
        rating=4.6,
        day=day_num,
        visit_order=1,
        approximate_location=approximate
    )


def insert_stop_after(day_num: int, after_loc_id: int, new_place: dict, destination: str):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return

    new_loc = resolve_new_location_from_place(new_place, destination, day_num)

    insert_idx = None
    for idx, loc in enumerate(day_itin.locations):
        if loc.id == after_loc_id:
            insert_idx = idx + 1
            break

    if insert_idx is None:
        return

    day_itin.locations.insert(insert_idx, new_loc)
    recompute_visit_orders(day_num)
    reschedule_day_from_index(day_num, max(0, insert_idx - 1))


def replace_stop(day_num: int, target_loc_id: int, new_place: dict, destination: str):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return

    replacement = resolve_new_location_from_place(new_place, destination, day_num)

    replace_idx = None
    for idx, loc in enumerate(day_itin.locations):
        if loc.id == target_loc_id:
            replace_idx = idx
            break

    if replace_idx is None:
        return

    replacement.id = day_itin.locations[replace_idx].id
    replacement.visit_order = day_itin.locations[replace_idx].visit_order
    day_itin.locations[replace_idx] = replacement
    recompute_visit_orders(day_num)
    reschedule_day_from_index(day_num, max(0, replace_idx))


def append_stop_to_day(day_num: int, new_place: dict, destination: str):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return

    new_loc = resolve_new_location_from_place(new_place, destination, day_num)
    day_itin.locations.append(new_loc)
    recompute_visit_orders(day_num)
    reschedule_day_from_index(day_num, max(0, len(day_itin.locations) - 2))


def insert_multiple_stops_after(day_num: int, after_loc_id: int, new_places: List[dict], destination: str):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin or not new_places:
        return

    insert_idx = None
    for idx, loc in enumerate(day_itin.locations):
        if loc.id == after_loc_id:
            insert_idx = idx + 1
            break

    if insert_idx is None:
        return

    new_locations = []
    for place in new_places:
        new_locations.append(resolve_new_location_from_place(place, destination, day_num))

    for offset, loc in enumerate(new_locations):
        day_itin.locations.insert(insert_idx + offset, loc)

    recompute_visit_orders(day_num)
    reschedule_day_from_index(day_num, max(0, insert_idx - 1))


def append_multiple_stops_to_day(day_num: int, new_places: List[dict], destination: str):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin or not new_places:
        return

    for place in new_places:
        day_itin.locations.append(resolve_new_location_from_place(place, destination, day_num))

    recompute_visit_orders(day_num)
    reschedule_day_from_index(day_num, max(0, len(day_itin.locations) - len(new_places) - 1))

# ============================================================
# REVIEW PAGE EDIT HELPERS
# ============================================================
def remove_stop(day_num: int, target_loc_id: int):
    day_itin = st.session_state.itinerary.get(day_num)
    if not day_itin:
        return

    remove_idx = None
    for idx, loc in enumerate(day_itin.locations):
        if loc.id == target_loc_id:
            remove_idx = idx
            break

    if remove_idx is None:
        return

    day_itin.locations.pop(remove_idx)
    recompute_visit_orders(day_num)

    if day_itin.locations:
        reschedule_day_from_index(day_num, max(0, remove_idx - 1))
    else:
        day_itin.total_planned_time = 0


def replace_stop_with_custom_place(day_num: int, target_loc_id: int, place_name: str, destination: str):
    place_name = (place_name or "").strip()
    if not place_name:
        raise ValueError("Please enter a replacement location.")

    new_place = {
        "name": place_name,
        "category": "Custom Place",
        "estimated_duration_min": 60,
        "description": f"Custom replacement selected by the user: {place_name}"
    }
    replace_stop(day_num, target_loc_id, new_place, destination)

def add_custom_stop_to_day(day_num: int, place_name: str, destination: str):
    place_name = (place_name or "").strip()
    if not place_name:
        raise ValueError("Please enter a location to add.")

    new_place = {
        "name": place_name,
        "category": "Custom Place",
        "estimated_duration_min": 60,
        "description": f"Custom stop added by the user: {place_name}"
    }
    append_stop_to_day(day_num, new_place, destination)

def ollama_review_replace_options(
    destination: str,
    day_num: int,
    current_stop: Location,
    interests: List[str],
    pace: str,
    user_request: str,
    model_name: str,
    n: int = 5
) -> dict:
    schema = {
        "target_stop": current_stop.name,
        "request_summary": "short summary of what the user wants instead",
        "suggestions": [
            {
                "name": "Place name",
                "category": "Category label",
                "estimated_duration_min": 60,
                "description": "Why this is a good alternative"
            }
        ]
    }

    user_request = (user_request or "").strip()

    prompt = f"""
You are helping replace one travel stop in an itinerary.

Context:
- Destination: {destination}
- Day: {day_num}
- Current stop to replace: {current_stop.name}
- Current stop category: {current_stop.category}
- Traveler interests: {", ".join(interests) if interests else "General sightseeing"}
- Pace: {pace}
- What the user wants instead: {user_request if user_request else "A suitable alternative"}

Task:
Suggest {n} strong replacement options for this stop.

Rules:
1) Suggest real places likely to exist in or near {destination}
2) Suggestions must match what the user wants instead
3) Do not repeat the same place as the current stop
4) Keep the options realistic for the same day and same trip style
5) Return ONLY valid JSON using this schema:
{json.dumps(schema, indent=2)}
""".strip()

    raw = call_ollama(prompt, model_name)
    json_text = _extract_json_block(raw)
    if not json_text:
        raise ValueError("No valid JSON returned for replacement suggestions.")

    data = json.loads(json_text)
    if "suggestions" not in data or not isinstance(data["suggestions"], list):
        data["suggestions"] = []

    if "request_summary" not in data:
        data["request_summary"] = user_request if user_request else "A suitable alternative"

    filtered = []
    seen = set()
    for s in data["suggestions"]:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name", "")).strip()
        if not name:
            continue
        if name.lower() == current_stop.name.strip().lower():
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        filtered.append({
            "name": name,
            "category": str(s.get("category", "Suggestion")).strip() or "Suggestion",
            "estimated_duration_min": int(s.get("estimated_duration_min", 60) or 60),
            "description": str(s.get("description", "Suggested replacement")).strip() or "Suggested replacement"
        })

    data["suggestions"] = filtered[:n]
    return data
# ============================================================
# REVIEW MAP HELPER
# ============================================================
def create_review_day_map(day_num: int, day_itinerary: DayItinerary, base_location: Optional[dict] = None):
    if not day_itinerary.locations:
        return None

    first_loc = day_itinerary.locations[0]
    m = folium.Map(location=[first_loc.lat, first_loc.lon], zoom_start=13)
    coords = []

    if base_location:
        base_lat = base_location["lat"]
        base_lon = base_location["lon"]

        folium.Marker(
            [base_lat, base_lon],
            tooltip="Start / End Base Location",
            popup=f"Start / End: {base_location['name']}",
            icon=folium.Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)

        coords.append([base_lat, base_lon])

    for loc in day_itinerary.locations:
        coords.append([loc.lat, loc.lon])

        popup_html = f"""
            <div style="width: 220px;">
                <h4>{loc.visit_order}. {loc.name}</h4>
                <p><b>Category:</b> {loc.category}</p>
                <p><b>Time:</b> {loc.planned_start} - {loc.planned_end}</p>
                <p><b>Duration:</b> {loc.planned_duration} min</p>
                <p>{loc.description}</p>
            </div>
        """

        folium.Marker(
            location=[loc.lat, loc.lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{loc.visit_order}. {loc.name}",
            icon=folium.Icon(color="blue", icon="info-sign", prefix="glyphicon")
        ).add_to(m)

        folium.Marker(
            location=[loc.lat, loc.lon],
            icon=folium.DivIcon(html=f"""
                <div style="
                    font-size: 13pt;
                    color: white;
                    font-weight: bold;
                    background-color: #7c3aed;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: 2px solid white;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
                ">
                    {loc.visit_order}
                </div>
            """)
        ).add_to(m)

    if base_location:
        coords.append([base_location["lat"], base_location["lon"]])

    if len(coords) >= 2:
        folium.PolyLine(coords, color="blue", weight=4, opacity=0.8).add_to(m)

    return m


# ============================================================
# LIVE DASHBOARD
# JS stores a compact animation snapshot in ?anim=...
# Python reads it on rerun and restores the dashboard state.
# ============================================================
def build_live_trip_component_all_days(
        itinerary: Dict[int, DayItinerary],
        base_location: dict,
        speed_mps: float,
        active_day: int = 1,
        restore_state: Optional[dict] = None
):
    if not itinerary:
        return

    all_days = []
    for day_num in sorted(itinerary.keys()):
        day_itinerary = itinerary[day_num]
        if not day_itinerary.locations:
            continue

        stops = []
        for loc in day_itinerary.locations:
            stops.append({
                "id": loc.id,
                "name": loc.name,
                "lat": float(loc.lat),
                "lon": float(loc.lon),
                "planned_start": loc.planned_start,
                "planned_end": loc.planned_end,
                "dur": int(loc.planned_duration),
                "category": loc.category,
                "description": loc.description,
                "visit_order": loc.visit_order,
            })

        all_days.append({"day": day_num, "stops": stops})

    if not all_days:
        st.warning("No itinerary days found for live trip.")
        return

    start_point = {
        "name": base_location["name"],
        "lat": float(base_location["lat"]),
        "lon": float(base_location["lon"])
    }

    resume_day_index = 0
    for i, d in enumerate(all_days):
        if d["day"] == active_day:
            resume_day_index = i
            break

    # Only restore when the saved state points to the same active day
    safe_restore_state = None
    if restore_state and isinstance(restore_state, dict) and "dayIndex" in restore_state:
        try:
            saved_idx = int(restore_state["dayIndex"])
            if 0 <= saved_idx < len(all_days):
                saved_day = all_days[saved_idx]["day"]
                if saved_day == active_day:
                    safe_restore_state = restore_state
        except Exception:
            safe_restore_state = None

    restore_state_json = json.dumps(safe_restore_state) if safe_restore_state else "null"

    html_content = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body {{
      margin:0; padding:0; height:100%; background:#020617;
      color:#e5e7eb; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    }}
    .wrap {{
      display:flex; gap:14px; padding:10px; box-sizing:border-box; height:760px; background:#020617;
    }}
    #map {{
      flex: 1.5; border-radius:14px; overflow:hidden;
    }}
    .panel {{
      flex: 1; background:#0b1220; border:1px solid #1f2937;
      border-radius:14px; padding:14px; overflow:auto;
    }}
    .topbar {{
      display:flex; gap:8px; margin-bottom:12px;
    }}
    .btn {{
      background: linear-gradient(135deg, #38bdf8 0%, #22c55e 100%);
      color:#020617; border:none; padding:10px 12px; border-radius:10px;
      font-weight:800; cursor:pointer; flex:1;
    }}
    .btn.secondary {{
      background:#111827; color:#e5e7eb; border:1px solid #1f2937;
    }}
    .stat {{
      margin: 10px 0; padding:12px; border-radius:12px;
      background:#020617; border:1px solid #1f2937;
    }}
    .section-title {{
      font-size: 28px; font-weight: 800; margin: 0 0 10px 0; color:#f8fafc;
    }}
    .sub-title {{
      font-size: 14px; color:#94a3b8; margin-bottom: 12px;
    }}
    .pill {{
      display:inline-block; padding:4px 10px; border-radius:999px;
      font-weight:800; font-size:12px;
    }}
    .done {{ background:#22c55e; color:#022c22; }}
    .current {{ background:#38bdf8; color:#020617; }}
    .pending {{ background:#eab308; color:#111827; }}
    .atstop {{ background:#38bdf8; color:#020617; }}
    .moving {{ background:#38bdf8; color:#020617; }}
    .completed-day {{
      background:#052e16; color:#dcfce7; border-left:4px solid #22c55e;
      padding:10px 12px; border-radius:10px; margin:10px 0;
    }}
    .row {{
      padding:12px; border-radius:12px; background:#020617;
      border:1px solid #1f2937; margin-bottom:10px;
    }}
    .row h4 {{ margin:0 0 6px 0; font-size:15px; color:#f8fafc; }}
    .row p {{ margin:4px 0; color:#cbd5e1; font-size:12px; }}
    .small {{
      color:#94a3b8; font-size:12px;
    }}
    .trip-complete {{
      background:#052e16; border:1px solid #22c55e; color:#dcfce7;
      padding:16px; border-radius:12px; margin-top:12px; font-weight:700;
    }}
    .replan-banner {{
      background:#1e3a5f; border:1px solid #38bdf8; color:#e5e7eb;
      padding:10px 14px; border-radius:10px; margin-bottom:10px; font-size:13px; display:none;
    }}
    display: flex;
    gap: 8px;
    justify-content: flex-start;
    margin-top: 8px;
    margin-bottom: 8px;
}}
  </style>
</head>
<body>
  <div class="wrap">
    <div id="map"></div>
    <div class="panel">
      <div id="replanBanner" class="replan-banner"></div>
      <div class="section-title" id="liveDayTitle">🧭 Day 1 Live Dashboard</div>
      <div class="sub-title">Each day starts and ends at your base location.</div>

      <div class="topbar">
        <button id="startBtn" class="btn">▶ Start Tracking</button>
        <button id="pauseBtn" class="btn secondary">⏸ Pause</button>
      </div>

      <div class="stat">
        <div><b>Day:</b> <span id="dayText">1</span></div>
        <div style="margin-top:6px;"><b>Status:</b> <span id="statusText">Ready</span></div>
        <div style="margin-top:6px;"><b>Current:</b> <span id="currentStop">{start_point["name"]}</span></div>
        <div style="margin-top:6px;"><b>Next:</b> <span id="nextStop">—</span></div>
        <div style="margin-top:6px;"><b>Schedule Offset:</b> <span id="offsetText">0</span> min</div>
      </div>

      <div class="stat">
        <div><b>Base Location:</b> {start_point["name"]}</div>
        <div class="small" style="margin-top:6px;">The route starts here, visits your itinerary stops, and returns here before the next day begins.</div>
      </div>

      <div style="margin:10px 0;">
        <label><b>Speed:</b> <span id="speedVal"></span> m/s</label>
        <input id="speed" type="range" min="5" max="120" step="5" value="{float(speed_mps)}" style="width:100%;">
      </div>

      <div id="completedDays"></div>
      <div id="itineraryList"></div>
      <div id="tripCompleteBox"></div>
    </div>
  </div>

<script>
  const startPoint = {json.dumps(start_point)};
  let itineraryDays = {json.dumps(all_days)};
  let speedMps = {float(speed_mps)};
  let initialDayIndex = {resume_day_index};
  let activeDayNumber = {active_day};
  const restoreState = {restore_state_json};

  document.getElementById("speedVal").innerText = speedMps;

  function parseHHMM(s) {{
    const [h,m] = s.split(":").map(Number);
    return h*60 + m;
  }}

  function fmtHHMM(mins) {{
    mins = (mins + 24*60) % (24*60);
    return String(Math.floor(mins/60)).padStart(2,"0") + ":" + String(mins%60).padStart(2,"0");
  }}

  function haversine(lat1, lon1, lat2, lon2) {{
    const R = 6371000;
    const toRad = x => x * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  }}

  function lerp(a, b, t) {{
    return a + (b-a)*t;
  }}

  let running = false;
  let phase = "idle";
  let pausedFromPhase = null;

  let dayIndex = 0;
  let stopIndex = -1;
  let targetIndex = -1;
  let completedDayNumbers = [];
  let currentDay = null;
  let stops = [];
  let completedStops = [];
  let actualTimes = [];
  let offsetMin = 0;

  let from = null, to = null, segmentStart = null, segmentDist = 0;
  let segmentElapsedBeforePause = 0, stayStart = null, stayElapsedBeforePause = 0;
  let current = {{lat:startPoint.lat, lon:startPoint.lon}};
  let map = null, traveler = null;

  let _saveTimer = null;

  function scheduleStateSave() {{
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(pushStateToUrl, 350);
  }}

  function pushStateToUrl() {{
    try {{
    const state = {{
      dayIndex,
      phase,
      pausedFromPhase,
      stopIndex,
      targetIndex,
      offsetMin,
      completedStops: Array.from(completedStops),
      completedStopIds: stops
        .filter((s, i) => completedStops[i])
        .map(s => s.id),
      currentStopId:
        (stopIndex >= 0 && stopIndex < stops.length) ? stops[stopIndex].id : null,
      targetStopId:
        (targetIndex >= 0 && targetIndex < stops.length) ? stops[targetIndex].id : null,
      completedDayNumbers: Array.from(completedDayNumbers),
      currentLat: current.lat,
      currentLon: current.lon
    }};

      const url = new URL(window.parent.location.href);
      url.searchParams.set("anim", JSON.stringify(state));
      url.searchParams.set("active_day", currentDay ? currentDay.day : activeDayNumber);
      window.parent.history.replaceState({{}}, "", url);
    }} catch(e) {{
      try {{
        const state = {{
          dayIndex,
          phase,
          pausedFromPhase,
          stopIndex,
          targetIndex,
          offsetMin,
          completedStops: Array.from(completedStops),
      completedStopIds: stops
        .filter((s, i) => completedStops[i])
        .map(s => s.id),
      currentStopId:
        (stopIndex >= 0 && stopIndex < stops.length) ? stops[stopIndex].id : null,
      targetStopId:
        (targetIndex >= 0 && targetIndex < stops.length) ? stops[targetIndex].id : null,
      completedDayNumbers: Array.from(completedDayNumbers),
      currentLat: current.lat,
      currentLon: current.lon
        }};
        window.parent.sessionStorage.setItem("anim_state", JSON.stringify(state));
      }} catch(e2) {{}}
    }}
  }}

  function updateStartButtonLabel() {{
    const btn = document.getElementById("startBtn");
    if (phase === "idle") btn.innerText = "▶ Start Tracking";
    else if (phase === "paused") btn.innerText = "▶ Resume Tracking";
    else if (phase === "done") btn.innerText = "✅ Trip Completed";
    else btn.innerText = "▶ Start Tracking";
  }}

  function buildActualTimesForDay(dayStops) {{
    return dayStops.map(s => ({{
      plannedStart: parseHHMM(s.planned_start),
      plannedEnd: parseHHMM(s.planned_end),
      actualStart: null,
      actualEnd: null
    }}));
  }}

  function autoStayDuration(plannedDur) {{
    return Math.max(15, plannedDur + Math.floor(Math.random()*31) - 15);
  }}

  function renderCompletedDays() {{
    const wrap = document.getElementById("completedDays");
    wrap.innerHTML = "";
    completedDayNumbers.forEach(d => {{
      const div = document.createElement("div");
      div.className = "completed-day";
      div.innerHTML = `✅ Day ${{d}} completed`;
      wrap.appendChild(div);
    }});
  }}

  function getStopBadge(i) {{
    if (completedStops[i]) return {{cls:"done", label:"✅ Completed"}};
    if (phase === "travel" && targetIndex === i) return {{cls:"moving", label:"🚶 Moving Towards"}};
    if (phase === "stay" && stopIndex === i) return {{cls:"atstop", label:"📍 Currently At"}};
    if ((phase === "idle" || phase === "paused") && i === 0 && stopIndex === -1) return {{cls:"pending", label:"⏳ Planned"}};

    const nextPending = completedStops.findIndex(v => !v);
    if (nextPending === i && phase !== "travel" && phase !== "stay") return {{cls:"current", label:"➡ Next"}};
    if (nextPending === i && phase === "paused" && targetIndex === i) return {{cls:"current", label:"➡ Next"}};

    return {{cls:"pending", label:"⏳ Planned"}};
  }}

  function renderItineraryList() {{
    const list = document.getElementById("itineraryList");
    list.innerHTML = `<div class="section-title" style="font-size:24px;">📋 Day ${{currentDay.day}} Itinerary</div>`;

    stops.forEach((s, i) => {{
      const badge = getStopBadge(i);
      const at = actualTimes[i];
      const startMin = at && at.actualStart !== null ? at.actualStart : (at ? at.plannedStart + offsetMin : 0);
      const endMin = at && at.actualEnd !== null ? at.actualEnd : (at ? at.plannedEnd + offsetMin : 0);
      const shown = `${{fmtHHMM(startMin)}}-${{fmtHHMM(endMin)}}`;

      const div = document.createElement("div");
      div.className = "row";
      div.innerHTML = `
        <h4>${{s.visit_order}}. ${{s.name}} <span class="pill ${{badge.cls}}">${{badge.label}}</span></h4>
        <p><b>Time:</b> ${{shown}}</p>
        <p><b>Duration:</b> ${{s.dur}} min</p>
        <p><b>Category:</b> ${{s.category}}</p>
        <p>${{s.description}}</p>
      `;
      list.appendChild(div);
    }});
  }}

  function setStatus(text, curr, next) {{
    document.getElementById("dayText").innerText = currentDay.day;
    document.getElementById("statusText").innerText = text;
    document.getElementById("currentStop").innerText = curr || "—";
    document.getElementById("nextStop").innerText = next || "—";
    document.getElementById("offsetText").innerText = offsetMin;
  }}

  function initMapForCurrentDay() {{
    if (map) map.remove();
    map = L.map('map');

    const fc = stops.length ? [stops[0].lat, stops[0].lon] : [startPoint.lat, startPoint.lon];
    map.setView(fc, 13);

    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }}).addTo(map);

    const routeLL = [[startPoint.lat, startPoint.lon], ...stops.map(s => [s.lat, s.lon]), [startPoint.lat, startPoint.lon]];
    const poly = L.polyline(routeLL, {{color:"#2563eb", weight:5, opacity:0.8}}).addTo(map);
    map.fitBounds(poly.getBounds().pad(0.2));

    L.marker([startPoint.lat, startPoint.lon]).addTo(map).bindPopup(`<b>Base:</b> ${{startPoint.name}}`);

    stops.forEach((s, i) => {{
      L.circleMarker([s.lat, s.lon], {{
        radius: 8, color: "#6b7280", weight: 2, fillColor: "#38bdf8", fillOpacity: 0.9
      }}).addTo(map).bindPopup(`<b>${{i+1}}. ${{s.name}}</b>`);

      L.marker([s.lat, s.lon], {{
        icon: L.divIcon({{
          className: "custom-num",
          html: `<div style="background:#7c3aed;color:white;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-weight:700;border:2px solid white;">${{i+1}}</div>`,
          iconSize: [30,30],
          iconAnchor: [15,15]
        }})
      }}).addTo(map);
    }});

    traveler = L.circleMarker([current.lat, current.lon], {{
      radius: 9, color:"#ef4444", weight:2, fillColor:"#ef4444", fillOpacity:0.95
    }}).addTo(map);
  }}

  function loadDay(newDayIndex) {{
  dayIndex = newDayIndex;
  currentDay = itineraryDays[dayIndex];
  stops = currentDay.stops;
  completedStops = new Array(stops.length).fill(false);
  actualTimes = buildActualTimesForDay(stops);
  offsetMin = 0;
  stopIndex = -1;
  targetIndex = -1;
  from = null;
  to = null;
  segmentStart = null;
  segmentDist = 0;
  segmentElapsedBeforePause = 0;
  stayStart = null;
  stayElapsedBeforePause = 0;
  pausedFromPhase = null;
  phase = "idle";
  current = {{lat:startPoint.lat, lon:startPoint.lon}};

    initMapForCurrentDay();
    renderCompletedDays();
    renderItineraryList();
    setStatus("Ready", startPoint.name, stops.length ? stops[0].name : "—");
    updateStartButtonLabel();
    document.getElementById("liveDayTitle").innerText = `🧭 Day ${{currentDay.day}} Live Dashboard`;
    pushStateToUrl();
  }}

  function finishTrip() {{
    running = false;
    phase = "done";
    pausedFromPhase = null;
    setStatus("Trip Completed", startPoint.name, "—");
    renderItineraryList();
    updateStartButtonLabel();
    document.getElementById("tripCompleteBox").innerHTML = `<div class="trip-complete">🎉 Trip completed successfully.</div>`;
    pushStateToUrl();
  }}

  function rolloverToNextDay() {{
    completedDayNumbers.push(currentDay.day);
    renderCompletedDays();

    if (dayIndex + 1 < itineraryDays.length) {{
      loadDay(dayIndex + 1);
      running = false;
      phase = "idle";
      setStatus("Ready", startPoint.name, stops.length ? stops[0].name : "—");
      renderItineraryList();
      updateStartButtonLabel();
    }} else {{
      finishTrip();
    }}
  }}

  function beginTravel(nextIndex) {{
    if (nextIndex >= stops.length) {{
      beginReturnToBase();
      return;
    }}

    const fp = stopIndex === -1
      ? {{lat:startPoint.lat, lon:startPoint.lon, name:startPoint.name}}
      : {{lat:stops[stopIndex].lat, lon:stops[stopIndex].lon, name:stops[stopIndex].name}};

    from = fp;
    targetIndex = nextIndex;
    to = {{
      lat: stops[nextIndex].lat,
      lon: stops[nextIndex].lon,
      name: stops[nextIndex].name,
      i: nextIndex
    }};
    segmentDist = haversine(from.lat, from.lon, to.lat, to.lon);
    segmentStart = null;
    segmentElapsedBeforePause = 0;
    phase = "travel";
    pausedFromPhase = null;
    setStatus("Moving Towards", from.name, to.name);
    renderItineraryList();
    updateStartButtonLabel();
    scheduleStateSave();
    requestAnimationFrame(frameTravel);
  }}

  function beginReturnToBase() {{
    const last = stops.length ? stops[stops.length - 1] : null;
    from = last
      ? {{lat:last.lat, lon:last.lon, name:last.name}}
      : {{lat:startPoint.lat, lon:startPoint.lon, name:startPoint.name}};

    targetIndex = -1;
    to = {{
      lat: startPoint.lat,
      lon: startPoint.lon,
      name: startPoint.name,
      i: -999
    }};
    segmentDist = haversine(from.lat, from.lon, to.lat, to.lon);
    segmentStart = null;
    segmentElapsedBeforePause = 0;
    phase = "return";
    pausedFromPhase = null;
    setStatus("Returning to Base", from.name, startPoint.name);
    renderItineraryList();
    updateStartButtonLabel();
    scheduleStateSave();
    requestAnimationFrame(frameTravel);
  }}

  function arriveAtStop(i) {{
    stopIndex = i;
    targetIndex = -1;
    current.lat = stops[i].lat;
    current.lon = stops[i].lon;
    traveler.setLatLng([current.lat, current.lon]);

    const ps = actualTimes[i].plannedStart + offsetMin;
    actualTimes[i].actualStart = ps;

    const ad = autoStayDuration(stops[i].dur);
    actualTimes[i].actualEnd = ps + ad;

    offsetMin += actualTimes[i].actualEnd - (actualTimes[i].plannedEnd + offsetMin);

    stayStart = null;
    stayElapsedBeforePause = 0;
    phase = "stay";
    pausedFromPhase = null;
    setStatus("Currently At", stops[i].name, i + 1 < stops.length ? stops[i + 1].name : "Return to Base");
    renderItineraryList();
    updateStartButtonLabel();
    pushStateToUrl();
    requestAnimationFrame(frameStay);
  }}

  function finishStop(i) {{
    completedStops[i] = true;
    pausedFromPhase = null;
    pushStateToUrl();
    renderItineraryList();

    const ni = i + 1;
    if (ni < stops.length) {{
      setStatus("Moving Towards", stops[i].name, stops[ni].name);
      beginTravel(ni);
    }} else {{
      setStatus("Returning to Base", stops[i].name, startPoint.name);
      beginReturnToBase();
    }}
  }}

  function finishReturnToBase() {{
    current.lat = startPoint.lat;
    current.lon = startPoint.lon;
    traveler.setLatLng([current.lat, current.lon]);
    pausedFromPhase = null;
    rolloverToNextDay();
  }}

  function frameTravel(ts) {{
    if (!running || (phase !== "travel" && phase !== "return")) return;
    if (segmentStart === null) segmentStart = ts;

    const elapsed = segmentElapsedBeforePause + ((ts - segmentStart) / 1000.0);
    const t = Math.min(1.0, (elapsed * speedMps) / Math.max(segmentDist, 1));

    current.lat = lerp(from.lat, to.lat, t);
    current.lon = lerp(from.lon, to.lon, t);
    traveler.setLatLng([current.lat, current.lon]);
    scheduleStateSave();

    if (t >= 1.0) {{
      segmentElapsedBeforePause = 0;
      if (phase === "return") finishReturnToBase();
      else arriveAtStop(to.i);
      return;
    }}

    requestAnimationFrame(frameTravel);
  }}

  function frameStay(ts) {{
    if (!running || phase !== "stay") return;
    if (stayStart === null) stayStart = ts;

    const i = stopIndex;
    if (i < 0 || i >= stops.length) return;

    const durMin = actualTimes[i].actualEnd - actualTimes[i].actualStart;
    const staySeconds = Math.max(2, durMin * 0.25);
    const elapsed = stayElapsedBeforePause + ((ts - stayStart) / 1000.0);
    scheduleStateSave();

    if (elapsed >= staySeconds) {{
      stayElapsedBeforePause = 0;
      finishStop(i);
      return;
    }}

    requestAnimationFrame(frameStay);
  }}

  document.getElementById("startBtn").onclick = () => {{
    if (phase === "done") return;

    if (!running) {{
      running = true;

      if (phase === "idle") {{
        beginTravel(0);
        return;
      }}

      if (phase === "paused") {{
        if (pausedFromPhase === "travel" || pausedFromPhase === "return") {{
          phase = pausedFromPhase;
          segmentStart = null;
          setStatus(
            phase === "return" ? "Returning to Base" : "Moving Towards",
            stopIndex === -1 ? startPoint.name : (stopIndex < stops.length ? stops[stopIndex].name : startPoint.name),
            to ? to.name : "—"
          );
          renderItineraryList();
          updateStartButtonLabel();
          requestAnimationFrame(frameTravel);
          return;
        }}

        if (pausedFromPhase === "stay") {{
          phase = "stay";
          stayStart = null;
          setStatus(
            "Currently At",
            stopIndex >= 0 && stopIndex < stops.length ? stops[stopIndex].name : startPoint.name,
            stopIndex + 1 < stops.length ? stops[stopIndex + 1].name : "Return to Base"
          );
          renderItineraryList();
          updateStartButtonLabel();
          requestAnimationFrame(frameStay);
          return;
        }}
      }}
    }}
  }};

  document.getElementById("pauseBtn").onclick = () => {{
    if (phase === "done") return;

    if (running) {{
      running = false;
      pausedFromPhase = phase;

      if (phase === "travel" || phase === "return") {{
        if (segmentStart !== null) segmentElapsedBeforePause += (performance.now() - segmentStart) / 1000.0;
      }} else if (phase === "stay") {{
        if (stayStart !== null) stayElapsedBeforePause += (performance.now() - stayStart) / 1000.0;
      }}

      phase = "paused";
      setStatus(
        "Paused",
        stopIndex === -1 ? startPoint.name : (stopIndex < stops.length ? stops[stopIndex].name : startPoint.name),
        to ? to.name : "—"
      );
      renderItineraryList();
      updateStartButtonLabel();
      pushStateToUrl();
    }}
  }};

  document.getElementById("speed").oninput = (e) => {{
    speedMps = Number(e.target.value);
    document.getElementById("speedVal").innerText = speedMps;
  }};

  function patchStateById(newStops) {{
    const oldActualById = {{}};
    const oldCompletedById = {{}};

    stops.forEach((s, i) => {{
      oldActualById[s.id] = actualTimes[i];
      oldCompletedById[s.id] = completedStops[i];
    }});

    const rebuiltActualTimes = newStops.map(s => {{
      if (oldActualById[s.id]) {{
        return oldActualById[s.id];
      }}
      return {{
        plannedStart: parseHHMM(s.planned_start),
        plannedEnd: parseHHMM(s.planned_end),
        actualStart: null,
        actualEnd: null
      }};
    }});

    const rebuiltCompletedStops = newStops.map(s => {{
      return !!oldCompletedById[s.id];
    }});

    actualTimes = rebuiltActualTimes;
    completedStops = rebuiltCompletedStops;
  }}

  window.addEventListener("message", function(event) {{
  const msg = event.data;
  if (!msg || msg.type !== "replan_patch") return;

  const {{ day, stops: newStops, label }} = msg;
  const dayObj = itineraryDays.find(d => d.day === day);
  if (!dayObj) return;

  dayObj.stops = newStops;

  if (!(currentDay && currentDay.day === day)) return;

  const oldActualById = {{}};
  const oldCompletedById = {{}};

  stops.forEach((s, i) => {{
    oldActualById[s.id] = actualTimes[i];
    oldCompletedById[s.id] = completedStops[i];
  }});

    const oldCurrentStopId =
    (stopIndex >= 0 && stopIndex < stops.length) ? stops[stopIndex].id : null;

  const oldTargetStopId =
    (targetIndex >= 0 && targetIndex < stops.length) ? stops[targetIndex].id : null;

  const oldStopsSnapshot = [...stops];

  // Swap in new stops
  stops = newStops;
  currentDay.stops = newStops;

  // Rebuild actualTimes by id
  actualTimes = newStops.map(s => {{
    return oldActualById[s.id] || {{
      plannedStart: parseHHMM(s.planned_start),
      plannedEnd: parseHHMM(s.planned_end),
      actualStart: null,
      actualEnd: null
    }};
  }});

  // Rebuild completion by id first
  completedStops = newStops.map(s => !!oldCompletedById[s.id]);

  // Keep all stops up to the previously completed boundary as completed
  let lastCompletedIndexOld = -1;
  for (let i = 0; i < oldStopsSnapshot.length; i++) {{
    if (oldCompletedById[oldStopsSnapshot[i].id]) {{
      lastCompletedIndexOld = i;
    }}
  }}

  const completedBoundaryStopId =
    oldCurrentStopId !== null && oldCompletedById[oldCurrentStopId]
      ? oldCurrentStopId
      : (
          lastCompletedIndexOld >= 0 && lastCompletedIndexOld < oldStopsSnapshot.length
            ? oldStopsSnapshot[lastCompletedIndexOld].id
            : null
        );

  if (completedBoundaryStopId !== null) {{
    const boundaryIndexNew = newStops.findIndex(s => s.id === completedBoundaryStopId);
    if (boundaryIndexNew >= 0) {{
      for (let i = 0; i <= boundaryIndexNew; i++) {{
        completedStops[i] = true;
      }}
    }}
  }}


  stopIndex = oldCurrentStopId !== null
  ? newStops.findIndex(s => s.id === oldCurrentStopId)
  : -1;

targetIndex = -1;
for (let i = 0; i < newStops.length; i++) {{
  if (!completedStops[i]) {{
    targetIndex = i;
    break;
  }}
}}

    const wasInMotion =
    phase === "travel" || phase === "return" || phase === "stay";

  const wasPausedMidTrip =
    phase === "paused" &&
    (pausedFromPhase === "travel" ||
     pausedFromPhase === "return" ||
     pausedFromPhase === "stay");

  running = false;

  if (wasInMotion || wasPausedMidTrip) {{
    // keep it resumable only if the day was actually in progress
    if (wasInMotion) {{
      pausedFromPhase = phase;
    }}

    phase = "paused";

    if (targetIndex >= 0 && targetIndex < newStops.length) {{
      to = {{
        lat: newStops[targetIndex].lat,
        lon: newStops[targetIndex].lon,
        name: newStops[targetIndex].name,
        i: targetIndex
      }};

      from = {{
        lat: current.lat,
        lon: current.lon,
        name: stopIndex >= 0 && stopIndex < newStops.length
          ? newStops[stopIndex].name
          : "Current Position"
      }};

      segmentDist = haversine(from.lat, from.lon, to.lat, to.lon);
      segmentStart = null;
      segmentElapsedBeforePause = 0;
    }} else if (stopIndex >= 0 && stopIndex < newStops.length) {{
      from = {{
        lat: current.lat,
        lon: current.lon,
        name: newStops[stopIndex].name
      }};
      to = null;
    }} else {{
      from = {{
        lat: current.lat,
        lon: current.lon,
        name: "Current Position"
      }};
      to = null;
    }}

    if (traveler) {{
      traveler.setLatLng([current.lat, current.lon]);
    }}

    initMapForCurrentDay();
    if (traveler) {{
      traveler.setLatLng([current.lat, current.lon]);
    }}

    renderItineraryList();

    const currentName =
      stopIndex >= 0 && stopIndex < newStops.length
        ? newStops[stopIndex].name
        : "Current Position";

    const nextName =
      targetIndex >= 0 && targetIndex < newStops.length
        ? newStops[targetIndex].name
        : (
            stopIndex + 1 < newStops.length
              ? newStops[stopIndex + 1].name
              : "Return to Base"
          );

    setStatus("Paused — itinerary updated", currentName, nextName);
    updateStartButtonLabel();
  }} else {{
    // day was not started yet -> keep fresh state
    phase = "idle";
    pausedFromPhase = null;
    stopIndex = -1;
    targetIndex = -1;
    from = null;
    to = null;
    segmentStart = null;
    segmentDist = 0;
    segmentElapsedBeforePause = 0;
    stayStart = null;
    stayElapsedBeforePause = 0;
    current = {{lat: startPoint.lat, lon: startPoint.lon }};

    initMapForCurrentDay();
    if (traveler) {{
      traveler.setLatLng([current.lat, current.lon]);
    }}

    renderItineraryList();
    setStatus("Ready", startPoint.name, newStops.length ? newStops[0].name : "—");
    updateStartButtonLabel();
  }}

  const banner = document.getElementById("replanBanner");
  banner.innerText = "✅ Itinerary updated: " + (label || "Replan applied");
  banner.style.display = "block";
  setTimeout(() => {{ banner.style.display = "none"; }}, 4000);

  pushStateToUrl();
}});

  if (restoreState && typeof restoreState.dayIndex === "number") {{
    dayIndex = restoreState.dayIndex;
    currentDay = itineraryDays[dayIndex] || itineraryDays[initialDayIndex];
    stops = currentDay.stops;
    completedDayNumbers = restoreState.completedDayNumbers || [];
    actualTimes = buildActualTimesForDay(stops);
offsetMin = restoreState.offsetMin || 0;

// Restore completed stops by ID if available
if (Array.isArray(restoreState.completedStopIds)) {{
  const completedIdSet = new Set(restoreState.completedStopIds);
  completedStops = stops.map(s => completedIdSet.has(s.id));
}} else if (restoreState.completedStops && restoreState.completedStops.length === stops.length) {{
  completedStops = restoreState.completedStops;
}} else {{
  completedStops = new Array(stops.length).fill(false);
}}

// Restore current/target by ID if available
if (restoreState.currentStopId !== undefined && restoreState.currentStopId !== null) {{
  stopIndex = stops.findIndex(s => s.id === restoreState.currentStopId);
}} else {{
  stopIndex = typeof restoreState.stopIndex === "number" ? restoreState.stopIndex : -1;
}}

if (restoreState.targetStopId !== undefined && restoreState.targetStopId !== null) {{
  targetIndex = stops.findIndex(s => s.id === restoreState.targetStopId);
}} else {{
  targetIndex = typeof restoreState.targetIndex === "number" ? restoreState.targetIndex : -1;
}}

    current = {{
      lat: typeof restoreState.currentLat === "number" ? restoreState.currentLat : startPoint.lat,
      lon: typeof restoreState.currentLon === "number" ? restoreState.currentLon : startPoint.lon
    }};

        const restoreWasPausedMidTrip =
      restoreState.phase === "paused" &&
      (restoreState.pausedFromPhase === "travel" ||
       restoreState.pausedFromPhase === "return" ||
       restoreState.pausedFromPhase === "stay");

    const restoreWasInMotion =
      restoreState.phase === "travel" ||
      restoreState.phase === "return" ||
      restoreState.phase === "stay";

    if (restoreWasPausedMidTrip || restoreWasInMotion) {{
      phase = "paused";
      pausedFromPhase = restoreWasInMotion
        ? restoreState.phase
        : restoreState.pausedFromPhase;
    }} else {{
      phase = "idle";
      pausedFromPhase = null;
    }}

    if (pausedFromPhase === "travel" && targetIndex >= 0 && targetIndex < stops.length) {{
      to = {{
        lat: stops[targetIndex].lat,
        lon: stops[targetIndex].lon,
        name: stops[targetIndex].name,
        i: targetIndex
      }};
      from = stopIndex >= 0 && stopIndex < stops.length
        ? {{lat:stops[stopIndex].lat, lon:stops[stopIndex].lon, name:stops[stopIndex].name}}
        : {{lat:startPoint.lat, lon:startPoint.lon, name:startPoint.name}};
      segmentDist = haversine(from.lat, from.lon, to.lat, to.lon);
    }} else if (pausedFromPhase === "return") {{
      const last = stops.length ? stops[stops.length - 1] : null;
      from = last
        ? {{lat:last.lat, lon:last.lon, name:last.name}}
        : {{lat:startPoint.lat, lon:startPoint.lon, name:startPoint.name}};
      to = {{lat:startPoint.lat, lon:startPoint.lon, name:startPoint.name, i:-999}};
      segmentDist = haversine(from.lat, from.lon, to.lat, to.lon);
    }} else if (pausedFromPhase === "stay" && stopIndex >= 0 && stopIndex < stops.length) {{
      from = {{lat:stops[stopIndex].lat, lon:stops[stopIndex].lon, name:stops[stopIndex].name}};
      to = null;
    }}

    initMapForCurrentDay();
    if (traveler) traveler.setLatLng([current.lat, current.lon]);
    renderCompletedDays();
    renderItineraryList();

        const cName = stopIndex >= 0 && stopIndex < stops.length ? stops[stopIndex].name : startPoint.name;
    const nName = to ? to.name : (stops.length ? stops[0].name : "—");

    if (phase === "paused") {{
      setStatus("Paused — tap Resume to continue", cName, nName);
    }} else {{
      setStatus("Ready", startPoint.name, stops.length ? stops[0].name : "—");
    }}
    updateStartButtonLabel();
    document.getElementById("liveDayTitle").innerText = `🧭 Day ${{currentDay.day}} Live Dashboard`;
  }} else {{
    loadDay(initialDayIndex);
  }}
</script>
</body>
</html>
"""
    html(html_content, height=780, scrolling=False)


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("🤖 AI Travel Planner")
    st.markdown("### Workflow")

    stage_labels = {
        "input": "1️⃣ Plan Trip",
        "review": "2️⃣ Review Itinerary",
        "live_trip": "3️⃣ Live Trip Dashboard"
    }

    for key, label in stage_labels.items():
        if key == st.session_state.stage:
            st.markdown(f"**✅ {label}** ← Current")
        else:
            st.markdown(f"⚪ {label}")

    st.markdown("---")
    st.markdown("### 🧠 Model")
    st.session_state.ollama_model = st.text_input("Ollama model name", value=st.session_state.ollama_model)

    if ollama_available(st.session_state.ollama_model):
        st.success(f"✅ Ollama ready: {st.session_state.ollama_model}")
    else:
        st.warning(
            f"⚠️ Ollama not ready or model not pulled: **{st.session_state.ollama_model}**\n\n"
            "Run:\n"
            "`ollama serve`\n"
            f"`ollama pull {st.session_state.ollama_model.split(':')[0]}`"
        )

    st.markdown("---")

    if st.button("🏠 Start Over", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.query_params.clear()
        st.rerun()

    if st.button("🧹 Clear itinerary cache", use_container_width=True):
        if CACHE_JSONL.exists():
            CACHE_JSONL.unlink()
        st.success("Cache cleared.")
        st.rerun()

    if st.button("🧹 Clear replan cache", use_container_width=True):
        if REPLAN_CACHE_JSONL.exists():
            REPLAN_CACHE_JSONL.unlink()
        st.success("Replan cache cleared.")
        st.rerun()

    st.markdown("---")
    st.metric("Destination", st.session_state.user_inputs.get("destination", "—"))
    st.metric("Days",
              len(st.session_state.itinerary) if st.session_state.itinerary else st.session_state.user_inputs.get(
                  "days", 0))
    st.metric("Stops", get_total_locations())

# ============================================================
# PAGE 1: INPUT
# ============================================================
if st.session_state.stage == "input":
    st.title("🌍 Plan Your Trip")
    st.markdown("### Generate your itinerary, review it once, then run the trip on one live dashboard")

    col1, col2 = st.columns(2)
    with col1:
        destination = st.text_input(
            "Where are you going?",
            value=st.session_state.user_inputs.get("destination", "Washington DC")
        )
        days = st.number_input(
            "Number of Days",
            min_value=1,
            max_value=14,
            value=int(st.session_state.user_inputs.get("days", 2))
        )

    with col2:
        interests = st.multiselect(
            "Choose your interests",
            [
                "Culture & History", "Nature & Outdoors", "Entertainment & Science",
                "Food & Drink", "Shopping", "City Highlights", "Museums",
                "Relaxation & Wellness", "Adventure & Activities", "Events & Local Life"
            ],
            default=st.session_state.user_inputs.get("interests", ["City Highlights", "Museums"])
        )
        pace = st.selectbox(
            "Trip pace",
            ["Relaxed", "Balanced", "Fast-paced"],
            index=["Relaxed", "Balanced", "Fast-paced"].index(st.session_state.user_inputs.get("pace", "Balanced"))
        )

    base_location_text = st.text_input(
        "Where will you start and end each day from? (optional)",
        value=st.session_state.user_inputs.get("base_location_text", ""),
        placeholder="Example: Hilton Washington DC, Airbnb near Dupont Circle, My apartment"
    )

    specific_locations_text = st.text_area(
        "Do you have any specific location in mind to visit? I can add that to your itinerary.",
        value="\n".join(st.session_state.user_inputs.get("must_visit_locations", [])),
        placeholder="Example:\nEiffel Tower\nLouvre Museum\nSeine River Cruise"
    )

    st.markdown("""
    <div class="info-box">
        <b>Cleaner final flow:</b><br>
        1. Generate itinerary<br>
        2. Review it once<br>
        3. Start each day from your chosen base location<br>
        4. Visit the planned stops<br>
        5. Return to the same base location at the end of the day
    </div>
    """, unsafe_allow_html=True)

    if st.button("✨ Generate My Itinerary", use_container_width=True, type="primary"):
        must_visit_locations = [line.strip() for line in specific_locations_text.splitlines() if line.strip()]

        st.session_state.user_inputs = {
            "days": int(days),
            "destination": destination,
            "interests": interests,
            "pace": pace,
            "must_visit_locations": must_visit_locations,
            "base_location_text": base_location_text
        }

        try:
            with st.spinner("Generating itinerary and geocoding locations..."):
                st.session_state.itinerary = build_itinerary_from_ollama(
                    destination,
                    int(days),
                    interests,
                    pace,
                    must_visit_locations
                )
                st.session_state.base_location = resolve_base_location(base_location_text, destination)

            st.session_state.current_day = 1
            st.session_state.replan_results = None
            st.session_state.stage = "review"
            st.rerun()

        except Exception as e:
            st.error(f"Failed to generate itinerary: {e}")

# ============================================================
# PAGE 2: REVIEW
# ============================================================
elif st.session_state.stage == "review":
    st.title("📋 Review Itinerary")
    st.markdown(f"### {st.session_state.user_inputs['days']}-Day Trip to {st.session_state.user_inputs['destination']}")

    # ---------------------------
    # Top Metrics
    # ---------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f'<div class="metric-card"><h3>Destination</h3><h2>{st.session_state.user_inputs["destination"]}</h2></div>',
        unsafe_allow_html=True
    )
    c2.markdown(
        f'<div class="metric-card"><h3>Days</h3><h2>{st.session_state.user_inputs["days"]}</h2></div>',
        unsafe_allow_html=True
    )
    c3.markdown(
        f'<div class="metric-card"><h3>Pace</h3><h2>{st.session_state.user_inputs["pace"]}</h2></div>',
        unsafe_allow_html=True
    )
    c4.markdown(
        f'<div class="metric-card"><h3>Stops</h3><h2>{get_total_locations()}</h2></div>',
        unsafe_allow_html=True
    )

    # ---------------------------
    # Short AI Summary instead of full repeated itinerary text
    # ---------------------------
    # ---------------------------
    # Combined Trip Summary
    # ---------------------------
    overview_text = ""
    raw_pretty = st.session_state.get("llama_pretty_text", "").strip()

    if raw_pretty:
        first_line = raw_pretty.split("\n")[0].strip()
        if first_line.lower().startswith("**overview:**"):
            overview_text = first_line.replace("**Overview:**", "").strip()

    if not overview_text:
        overview_text = (
            f"This itinerary was generated based on your selected interests, pace, and destination "
            f"to keep the trip organized, readable, and geographically practical."
        )

    specific_locations = st.session_state.user_inputs.get("must_visit_locations", [])
    specific_locations_html = "<br>".join([f"• {loc}" for loc in specific_locations]) if specific_locations else "None"

    base_location_name = (
        st.session_state.base_location["name"]
        if st.session_state.base_location else "Not specified"
    )

    st.markdown("""
    <h2 style="
        font-size: 40px;
        font-weight: 800;
        color: #f9fafb;
        margin-top: 10px;
        margin-bottom: 12px;
    ">
    Trip Summary
    </h2>
    """, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="info-box">
            <p><b>Overview:</b> {overview_text}</p>
            <p><b>Specific locations you asked to include:</b><br>{specific_locations_html}</p>
            <p><b>Daily base location:</b> {base_location_name}<br>
            Each day will start here and return here at the end.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("""
    <h2 style="
        font-size: 42px;
        font-weight: 800;
        color: #f9fafb;
        margin-top: 18px;
        margin-bottom: 10px;
    ">
    🗓️ Day-by-Day Plan
    </h2>
    """, unsafe_allow_html=True)

    # ---------------------------
    # Day sections
    # ---------------------------
    for day_num, day_itinerary in st.session_state.itinerary.items():
        if not day_itinerary.locations:
            continue

        total_day_minutes = sum(loc.planned_duration for loc in day_itinerary.locations)
        total_day_hours = round(total_day_minutes / 60, 1)
        stop_count = len(day_itinerary.locations)

        route_flow = " → ".join([loc.name for loc in day_itinerary.locations[:6]])
        if len(day_itinerary.locations) > 6:
            route_flow += " → ..."

        with st.expander(f"📍 Day {day_num}", expanded=(day_num == 1)):

            summary_col1, summary_col2, summary_col3 = st.columns(3)
            summary_col1.markdown(
                f'<div class="metric-card"><h3>Stops</h3><h2>{stop_count}</h2></div>',
                unsafe_allow_html=True
            )
            summary_col2.markdown(
                f'<div class="metric-card"><h3>Total Time</h3><h2>{total_day_hours} hrs</h2></div>',
                unsafe_allow_html=True
            )
            summary_col3.markdown(
                f'<div class="metric-card"><h3>Day Type</h3><h2>{st.session_state.user_inputs["pace"]}</h2></div>',
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div class="info-box">
                    <b>Planned route flow:</b> {route_flow}
                </div>
                """,
                unsafe_allow_html=True
            )

            review_map = create_review_day_map(
                day_num=day_num,
                day_itinerary=day_itinerary,
                base_location=st.session_state.base_location
            )
            if review_map:
                st_folium(review_map, width=1200, height=400, key=f"review_map_{day_num}")

            st.markdown("### Stops")

            must_visit_set = {x.strip().lower() for x in st.session_state.user_inputs.get("must_visit_locations", [])}

            for loc in day_itinerary.locations:
                is_must_visit = loc.name.strip().lower() in must_visit_set

                badge_html = '<span class="status-badge status-current">⭐ Must Visit</span>' if is_must_visit else \
                    '<span class="status-badge status-pending">Planned</span>'

                approx_note = ""
                if getattr(loc, "approximate_location", False):
                    approx_note = "<p><i>Note: map location is approximate.</i></p>"

                st.markdown(f"""
                    <div class="location-card">
                        <h4>{loc.visit_order}. {loc.name} {badge_html}</h4>
                        <p><b>📍 Category:</b> {loc.category} | <b>⭐ Rating:</b> {loc.rating}/5.0</p>
                        <p><b>🕒 Time:</b> {loc.planned_start} - {loc.planned_end} ({loc.planned_duration} min)</p>
                        <p>{loc.description}</p>
                        {approx_note}
                    </div>
                """, unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1.3, 4.7])

                with btn_col1:
                    if st.button("🔁 Replace", key=f"review_replace_open_{day_num}_{loc.id}"):
                        st.session_state.review_edit_open_loc_id = loc.id
                        st.session_state.review_add_open_loc_id = None
                        st.session_state.review_ai_replace_results_by_loc[loc.id] = None
                        st.rerun()

                with btn_col2:
                    if st.button("🗑 Remove", key=f"review_remove_{day_num}_{loc.id}"):
                        remove_stop(day_num, loc.id)
                        if st.session_state.review_edit_open_loc_id == loc.id:
                            st.session_state.review_edit_open_loc_id = None
                        if st.session_state.review_add_open_loc_id == loc.id:
                            st.session_state.review_add_open_loc_id = None
                        st.success(f"Removed {loc.name}")
                        st.rerun()

                with btn_col3:
                    if st.button("➕ Add After", key=f"review_add_after_{day_num}_{loc.id}"):
                        st.session_state.review_add_open_loc_id = loc.id
                        st.session_state.review_edit_open_loc_id = None
                        st.rerun()

                if st.session_state.get("review_add_open_loc_id") == loc.id:
                    st.markdown("#### Add a new stop after this location")

                    add_place = st.text_input(
                        "Enter location to add",
                        key=f"review_add_after_place_{day_num}_{loc.id}",
                        placeholder="Example: Georgetown Waterfront"
                    )

                    add_c1, add_c2, add_c3 = st.columns([1.2, 1.2, 5.6])

                    with add_c1:
                        if st.button("✅ Add Here", key=f"review_add_after_confirm_{day_num}_{loc.id}"):
                            try:
                                insert_stop_after(
                                    day_num=day_num,
                                    after_loc_id=loc.id,
                                    new_place={
                                        "name": add_place,
                                        "category": "Custom Place",
                                        "estimated_duration_min": 60,
                                        "description": f"Custom stop added after {loc.name}: {add_place}"
                                    },
                                    destination=st.session_state.user_inputs["destination"]
                                )
                                st.session_state.review_add_open_loc_id = None
                                st.success(f"Added {add_place} after {loc.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Add failed: {e}")

                    with add_c2:
                        if st.button("Cancel", key=f"review_add_after_cancel_{day_num}_{loc.id}"):
                            st.session_state.review_add_open_loc_id = None
                            st.rerun()

                if st.session_state.get("review_edit_open_loc_id") == loc.id:
                    st.markdown("#### Replace this stop")

                    replace_mode = st.radio(
                        "Choose replacement method",
                        options=["My own location", "AI suggestions"],
                        key=f"review_replace_mode_{day_num}_{loc.id}",
                        horizontal=True
                    )

                    if replace_mode == "My own location":
                        custom_place = st.text_input(
                            "Enter replacement location",
                            key=f"review_custom_place_{day_num}_{loc.id}",
                            placeholder="Example: Lincoln Memorial"
                        )

                        rc1, rc2, rc3 = st.columns([1.2, 1.2, 5.6])

                        with rc1:
                            if st.button("✅ Confirm", key=f"review_confirm_custom_{day_num}_{loc.id}"):
                                try:
                                    replace_stop_with_custom_place(
                                        day_num=day_num,
                                        target_loc_id=loc.id,
                                        place_name=custom_place,
                                        destination=st.session_state.user_inputs["destination"]
                                    )
                                    st.session_state.review_edit_open_loc_id = None
                                    st.success(f"Replaced {loc.name}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Replacement failed: {e}")

                        with rc2:
                            if st.button("Cancel", key=f"review_cancel_custom_{day_num}_{loc.id}"):
                                st.session_state.review_edit_open_loc_id = None
                                st.rerun()

                    else:
                        ai_request = st.text_input(
                            "What would you like instead?",
                            key=f"review_ai_request_{day_num}_{loc.id}",
                            placeholder="Example: food place, shopping, museum, dessert, nature, relaxing place"
                        )

                        ai_c1, ai_c2, ai_c3 = st.columns([1.6, 1.2, 5.2])

                        with ai_c1:
                            if st.button("✨ Get AI Suggestions", key=f"review_ai_suggest_{day_num}_{loc.id}"):
                                if not ai_request.strip():
                                    st.error("Please tell AI what you want instead, like food, shopping, museum, dessert, or nature.")
                                else:
                                    try:
                                        with st.spinner("Getting AI replacement suggestions..."):
                                            ai_result = ollama_review_replace_options(
                                                destination=st.session_state.user_inputs["destination"],
                                                day_num=day_num,
                                                current_stop=loc,
                                                interests=st.session_state.user_inputs["interests"],
                                                pace=st.session_state.user_inputs["pace"],
                                                user_request=ai_request,
                                                model_name=st.session_state.ollama_model,
                                                n=5
                                            )
                                        st.session_state.review_ai_replace_results_by_loc[loc.id] = ai_result
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"AI suggestions failed: {e}")

                        with ai_c2:
                            if st.button("Cancel", key=f"review_cancel_ai_{day_num}_{loc.id}"):
                                st.session_state.review_edit_open_loc_id = None
                                st.session_state.review_ai_replace_results_by_loc[loc.id] = None
                                st.rerun()

                        ai_pack = st.session_state.review_ai_replace_results_by_loc.get(loc.id)
                        if ai_pack and ai_pack.get("suggestions"):
                            suggestion_labels = [
                                f"{i+1}. {s['name']} — {s['category']}"
                                for i, s in enumerate(ai_pack["suggestions"])
                            ]

                            selected_label = st.radio(
                                "Select one suggestion",
                                options=suggestion_labels,
                                key=f"review_ai_pick_{day_num}_{loc.id}"
                            )

                            selected_index = suggestion_labels.index(selected_label)
                            selected_suggestion = ai_pack["suggestions"][selected_index]

                            st.markdown(f"""
                                <div class="info-box">
                                    <b>{selected_suggestion['name']}</b><br>
                                    Category: {selected_suggestion['category']}<br>
                                    Suggested Duration: {selected_suggestion['estimated_duration_min']} min<br>
                                    {selected_suggestion['description']}
                                </div>
                            """, unsafe_allow_html=True)

                            if st.button("✅ Replace with Selected AI Suggestion", key=f"review_ai_apply_{day_num}_{loc.id}", use_container_width=True):
                                try:
                                    replace_stop(
                                        day_num=day_num,
                                        target_loc_id=loc.id,
                                        new_place=selected_suggestion,
                                        destination=st.session_state.user_inputs["destination"]
                                    )
                                    st.session_state.review_edit_open_loc_id = None
                                    st.session_state.review_ai_replace_results_by_loc[loc.id] = None
                                    st.session_state.review_ai_replace_selected_by_loc[loc.id] = None
                                    st.success(f"Replaced {loc.name}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"AI replacement failed: {e}")

                    if st.button("Cancel", key=f"review_cancel_replace_{day_num}_{loc.id}", use_container_width=True):
                        st.session_state.review_edit_open_loc_id = None
                        st.session_state.review_ai_replace_results_by_loc[loc.id] = None
                        st.session_state.review_ai_replace_selected_by_loc[loc.id] = None
                        st.rerun()

    # ---------------------------
    # Cache message
    # ---------------------------
    if st.session_state.llama_saved_ok:
        if st.session_state.llama_cache_hit:
            st.success("✅ Itinerary loaded from cache.")
        else:
            st.success("✅ Itinerary saved in background for reuse.")

    # ---------------------------
    # Bottom actions
    # ---------------------------
    a, b = st.columns(2)
    with a:
        if st.button("❌ Regenerate", use_container_width=True):
            st.session_state.stage = "input"
            st.rerun()

    with b:
        if st.button("✅ Start Live Trip Dashboard", use_container_width=True, type="primary"):
            st.session_state.stage = "live_trip"
            st.session_state.live_active_day = 1
            st.query_params["active_day"] = "1"
            if "anim" in st.query_params:
                del st.query_params["anim"]
            st.rerun()

# ============================================================
# PAGE 3: LIVE DASHBOARD
# ============================================================
elif st.session_state.stage == "live_trip":
    st.title("🗺️ Live Trip Dashboard")
    st.markdown(
        "### Each day starts from your base location, visits the itinerary stops, and returns to the same base location")

    if not st.session_state.itinerary:
        st.warning("No itinerary available.")
        if st.button("⬅️ Back to Planning", use_container_width=True):
            st.session_state.stage = "input"
            st.rerun()
        st.stop()

    total_days = len(st.session_state.itinerary)
    total_stops = sum(len(day.locations) for day in st.session_state.itinerary.values())

    top1, top2, top3, top4 = st.columns(4)
    top1.markdown(f'<div class="metric-card"><h3>Total Days</h3><h2>{total_days}</h2></div>', unsafe_allow_html=True)
    top2.markdown(
        f'<div class="metric-card"><h3>Base Location</h3><h2>{st.session_state.base_location["name"] if st.session_state.base_location else "Base"}</h2></div>',
        unsafe_allow_html=True)
    top3.markdown(f'<div class="metric-card"><h3>Pace</h3><h2>{st.session_state.user_inputs["pace"]}</h2></div>',
                  unsafe_allow_html=True)
    top4.markdown(f'<div class="metric-card"><h3>Total Stops</h3><h2>{total_stops}</h2></div>', unsafe_allow_html=True)

    st.markdown("### Controls")
    c1, c2 = st.columns([2, 1])

    with c1:
        st.info(
            "The live map animation runs in the browser. Use the replan panel below to update stops — the animation will pause and resume from where you left off.")
    with c2:
        st.session_state.sim_speed_mps = st.slider(
            "Simulation speed (m/s)",
            min_value=5,
            max_value=120,
            value=int(st.session_state.sim_speed_mps),
            step=5
        )

    active_day = get_live_active_day()
    st.query_params["active_day"] = str(active_day)

    st.markdown("### Active Dashboard Day")
    day_nav1, day_nav2, day_nav3 = st.columns([1, 1, 2])

    with day_nav1:
        if st.button("⬅ Previous Day", use_container_width=True):
            days_sorted = sorted(st.session_state.itinerary.keys())
            idx = days_sorted.index(active_day)
            if idx > 0:
                new_day = days_sorted[idx - 1]
                st.session_state.live_active_day = new_day
                st.session_state.replan_results = None
                st.query_params["active_day"] = str(new_day)
                if "anim" in st.query_params:
                    del st.query_params["anim"]
                st.rerun()

    with day_nav2:
        if st.button("Next Day ➡", use_container_width=True):
            days_sorted = sorted(st.session_state.itinerary.keys())
            idx = days_sorted.index(active_day)
            if idx < len(days_sorted) - 1:
                new_day = days_sorted[idx + 1]
                st.session_state.live_active_day = new_day
                st.session_state.replan_results = None
                st.query_params["active_day"] = str(new_day)
                if "anim" in st.query_params:
                    del st.query_params["anim"]
                st.rerun()

    with day_nav3:
        st.markdown(
            f'<div class="info-box"><b>Dashboard replan target:</b> Day {st.session_state.live_active_day}</div>',
            unsafe_allow_html=True)

    st.markdown("---")

    restore_state = None
    if "anim" in st.query_params:
        try:
            raw_anim = st.query_params["anim"]
            if raw_anim and raw_anim != "null":
                parsed = json.loads(raw_anim)
                if isinstance(parsed, dict) and "dayIndex" in parsed:
                    restore_state = parsed
        except Exception:
            restore_state = None

    build_live_trip_component_all_days(
        itinerary=st.session_state.itinerary,
        base_location=st.session_state.base_location or {"name": "Base", "lat": 0.0, "lon": 0.0},
        speed_mps=st.session_state.sim_speed_mps,
        active_day=active_day,
        restore_state=restore_state
    )

    if st.session_state.get("replan_pending_refresh"):
        replan_day = st.session_state.get("replan_applied_day", active_day)
        replan_label = st.session_state.get("replan_success_message", "Itinerary updated")
        day_itin = st.session_state.itinerary.get(replan_day)

        if day_itin:
            stops_payload = []
            for loc in day_itin.locations:
                stops_payload.append({
                    "id": loc.id,
                    "name": loc.name,
                    "lat": float(loc.lat),
                    "lon": float(loc.lon),
                    "planned_start": loc.planned_start,
                    "planned_end": loc.planned_end,
                    "dur": int(loc.planned_duration),
                    "category": loc.category,
                    "description": loc.description,
                    "visit_order": loc.visit_order,
                })

            patch_msg = {
                "type": "replan_patch",
                "day": replan_day,
                "stops": stops_payload,
                "label": replan_label
            }

            st.components.v1.html(f"""<script>
(function() {{
  var msg = {json.dumps(patch_msg)};
  var iframes = window.parent.document.querySelectorAll("iframe");
  iframes.forEach(function(f) {{
    try {{ f.contentWindow.postMessage(msg, "*"); }} catch(e) {{}}
  }});
}})();
</script>""", height=0)

        st.session_state.replan_pending_refresh = False
        st.session_state.replan_applied_day = None

    st.markdown("---")
    st.markdown("## 🔄 Mid-Trip Replanning")

    if st.session_state.get("replan_success_message"):
        st.markdown(
            f'<div class="success-box">✅ {st.session_state.replan_success_message} — Dashboard updated in place.</div>',
            unsafe_allow_html=True
        )
        st.session_state.replan_success_message = ""

    replan_col1, replan_col2 = st.columns([1.1, 1])

    with replan_col1:
        available_days = sorted(st.session_state.itinerary.keys())

        default_replan_day = st.session_state.get("replan_selected_day", get_live_active_day())
        if default_replan_day not in available_days:
            default_replan_day = available_days[0]

        selected_day = st.selectbox(
            "Replan for Day",
            options=available_days,
            index=available_days.index(default_replan_day),
            format_func=lambda d: f"Day {d}"
        )

        if st.session_state.replan_selected_day != selected_day:
            st.session_state.replan_selected_day = selected_day
            st.session_state.live_active_day = selected_day  # keep dashboard and replan on same day
            st.session_state.replan_selected_anchor_id = None
            st.session_state.replan_results = None
            st.session_state.replan_checkbox_states = {}

            st.query_params["active_day"] = str(selected_day)

            # IMPORTANT:
            # do NOT clear "anim" here, otherwise the live trip progress resets
            st.rerun()

        day_locs = st.session_state.itinerary[selected_day].locations
        anchor_options = [f"{loc.id} — {loc.visit_order}. {loc.name}" for loc in day_locs]

        if anchor_options:
            default_anchor_index = 0
            if st.session_state.replan_selected_anchor_id is not None:
                for i, text in enumerate(anchor_options):
                    if text.startswith(f"{st.session_state.replan_selected_anchor_id} —"):
                        default_anchor_index = i
                        break

            anchor_choice = st.selectbox(
                "Current Stop",
                options=anchor_options,
                index=default_anchor_index,
                format_func=lambda x: x.split(" — ")[1] if " — " in x else x
            )
            anchor_id = int(anchor_choice.split(" — ")[0])
            st.session_state.replan_selected_anchor_id = anchor_id
        else:
            anchor_id = None
            st.warning("No stops available for this day.")

        st.session_state.replan_request_text = st.text_area(
            "What would you like to explore?",
            value=st.session_state.replan_request_text,
            placeholder="Example:\nWhat nearby places can I still cover today?\nAdd a shopping stop\nSuggest a food place nearby"
        )

        st.session_state.replan_action_mode = st.selectbox(
            "How should the selected suggestion be applied?",
            options=["Insert after selected stop", "Replace selected stop", "Add to end of day"],
            index=["Insert after selected stop", "Replace selected stop", "Add to end of day"].index(
                st.session_state.replan_action_mode
            )
        )

        if st.button("✨ Get AI Replan Suggestions", use_container_width=True, type="primary"):
            if not anchor_id:
                st.error("Please select an anchor stop.")
            elif not st.session_state.replan_request_text.strip():
                st.error("Please describe what the traveler wants to change.")
            else:
                st.session_state.replan_cache_hit = False
                st.session_state.replan_saved_ok = False
                anchor_loc, remaining = get_anchor_and_remaining(selected_day, anchor_id)

                try:
                    with st.spinner("Asking AI for replanning options..."):
                        result = ollama_midtrip_replan_options(
                            destination=st.session_state.user_inputs["destination"],
                            day_num=selected_day,
                            anchor_name=anchor_loc.name if anchor_loc else "current location",
                            interests=st.session_state.user_inputs["interests"],
                            pace=st.session_state.user_inputs["pace"],
                            remaining_stops=remaining,
                            user_request=st.session_state.replan_request_text,
                            model_name=st.session_state.ollama_model,
                            n=5
                        )

                    st.session_state.replan_results = {
                        "day": selected_day,
                        "anchor_id": anchor_id,
                        "data": result
                    }
                    st.session_state.replan_selected_suggestions = []
                    st.session_state.replan_checkbox_states = {}
                    st.rerun()

                except Exception as e:
                    st.error(f"Replanning failed: {e}")

    with replan_col2:
        results_pack = st.session_state.replan_results
        if results_pack:
            replan_day = results_pack["day"]
            replan_anchor_id = results_pack["anchor_id"]
            suggestions = results_pack["data"].get("suggestions", [])
            summary = results_pack["data"].get("request_summary", "")

            if st.session_state.replan_cache_hit:
                st.success("✅ Replan suggestions loaded from replan cache.")
            elif st.session_state.replan_saved_ok:
                st.success("✅ Replan suggestions generated and saved for reuse.")

            if summary:
                st.markdown(f'<div class="info-box"><b>AI understanding:</b> {summary}</div>', unsafe_allow_html=True)

            if suggestions:
                st.markdown("### Select one or more suggestions")
                selected_items = []

                for i, s in enumerate(suggestions, start=1):
                    checkbox_key = f"replan_pick_{replan_day}_{replan_anchor_id}_{i}"

                    st.markdown(f"""
                        <div class="location-card">
                            <h4>{i}. {s.get('name', '')}</h4>
                            <p><b>📍 Category:</b> {s.get('category', 'Suggestion')}</p>
                            <p><b>⏱ Suggested Duration:</b> {s.get('estimated_duration_min', 60)} min</p>
                            <p>{s.get('description', '')}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    checked = st.checkbox(
                        f"Select Suggestion {i}",
                        key=checkbox_key,
                        value=st.session_state.replan_checkbox_states.get(checkbox_key, False)
                    )

                    st.session_state.replan_checkbox_states[checkbox_key] = checked
                    if checked:
                        selected_items.append(s)

                st.markdown("---")

                if st.button("✅ Apply Selected Suggestions", use_container_width=True):
                    if not selected_items:
                        st.error("Please select at least one suggestion.")
                    else:
                        mode = st.session_state.replan_action_mode
                        try:
                            if mode == "Replace selected stop":
                                if len(selected_items) > 1:
                                    st.error("Replace mode supports only one suggestion.")
                                else:
                                    replace_stop(
                                        replan_day,
                                        replan_anchor_id,
                                        selected_items[0],
                                        st.session_state.user_inputs["destination"]
                                    )
                                    msg = f"Replaced stop with {selected_items[0].get('name', '')}"

                            elif mode == "Insert after selected stop":
                                insert_multiple_stops_after(
                                    replan_day,
                                    replan_anchor_id,
                                    selected_items,
                                    st.session_state.user_inputs["destination"]
                                )
                                msg = f"Inserted {len(selected_items)} stop(s) after current anchor"

                            else:
                                append_multiple_stops_to_day(
                                    replan_day,
                                    selected_items,
                                    st.session_state.user_inputs["destination"]
                                )
                                msg = f"Added {len(selected_items)} stop(s) to end of day"

                            st.session_state.replan_results = None
                            st.session_state.replan_checkbox_states = {}
                            st.session_state.replan_cache_hit = False
                            st.session_state.replan_saved_ok = False
                            st.session_state.replan_pending_refresh = True
                            st.session_state.replan_applied_day = replan_day
                            st.session_state.replan_success_message = msg

                            st.session_state.live_active_day = replan_day
                            st.query_params["active_day"] = str(replan_day)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Failed to apply suggestions: {e}")

                if st.button("🗑 Clear Suggestions", use_container_width=True):
                    st.session_state.replan_results = None
                    st.session_state.replan_checkbox_states = {}
                    st.session_state.replan_cache_hit = False
                    st.session_state.replan_saved_ok = False
                    st.rerun()
            else:
                st.info("No suggestions available yet.")
        else:
            st.info("AI replanning suggestions will appear here.")

    st.markdown("---")
    with st.expander("📋 Current Updated Itinerary Snapshot", expanded=False):
        for day_num, day_itinerary in st.session_state.itinerary.items():
            if not day_itinerary.locations:
                continue

            st.markdown(f"### Day {day_num}")
            for loc in day_itinerary.locations:
                st.markdown(f"""
                    <div class="location-card">
                        <h4>{loc.visit_order}. {loc.name}</h4>
                        <p><b>🕒 Time:</b> {loc.planned_start} - {loc.planned_end}</p>
                        <p><b>⏱ Duration:</b> {loc.planned_duration} min</p>
                        <p><b>📍 Category:</b> {loc.category}</p>
                        <p>{loc.description}</p>
                    </div>
                """, unsafe_allow_html=True)

    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("⬅ Back to Review", use_container_width=True):
            st.session_state.stage = "review"
            if "anim" in st.query_params:
                del st.query_params["anim"]
            st.rerun()

    with nav2:
        if st.button("🏁 End Trip Session", use_container_width=True):
            st.success("Trip session ended.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#9ca3af; padding:18px;">
    <p><b>🌍 AI Travel Planner</b> | One Live Dashboard for Planning, Tracking, and Replanning</p>
    <p>Powered by Ollama, Streamlit, Folium, and Location Intelligence</p>
</div>
""", unsafe_allow_html=True)