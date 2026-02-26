"""
WanderMind — AI Travel Itinerary Generator
==========================================
Startup MVP: Smart geo-clustered itineraries powered by open-source LLMs + OpenStreetMap

Tech Stack:
  - Streamlit        → UI framework
  - Ollama / OpenRouter → Open-source LLM (Llama 3.2, Mistral, Gemma)
  - Nominatim        → Free OSM geocoding (no API key)
  - Folium           → Interactive map (OpenStreetMap tiles)
  - Custom clustering → Groups nearby places for realistic daily routes

Install:
    pip install streamlit folium streamlit-folium requests

Run:
    streamlit run wandermind.py
"""

import json, time, re, math
import requests
import folium
from folium.plugins import AntPath, MeasureControl
import streamlit as st
from streamlit_folium import st_folium

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WanderMind · AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# DESIGN SYSTEM — warm editorial aesthetic
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Outfit:wght@300;400;500;600&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
    background-color: #0f0e0c;
    color: #f0ede6;
}

/* Main header */
.hero-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3.2rem;
    font-weight: 700;
    line-height: 1.1;
    color: #f0ede6;
    letter-spacing: -0.02em;
}
.hero-sub {
    font-size: 0.9rem;
    color: #8a7968;
    font-weight: 300;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}

/* Day card */
.day-header {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: #f0ede6;
    border-bottom: 1px solid #2a2720;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}
.day-meta {
    font-size: 0.72rem;
    color: #8a7968;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
}

/* Stop card */
.stop-card {
    background: #1a1814;
    border: 1px solid #2a2720;
    border-left: 3px solid var(--accent);
    padding: 0.9rem 1rem;
    margin-bottom: 0.6rem;
    border-radius: 0 6px 6px 0;
    transition: border-color 0.2s;
}
.stop-row {
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
}
.stop-badge {
    min-width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; font-weight: 600;
    flex-shrink: 0; margin-top: 1px;
    color: white;
}
.stop-name {
    font-weight: 600; font-size: 0.95rem;
    color: #f0ede6;
}
.stop-time {
    font-size: 0.72rem; color: #c8410a;
    letter-spacing: 0.05em; font-weight: 500;
    margin-bottom: 2px;
}
.stop-desc {
    font-size: 0.82rem; color: #a09080;
    line-height: 1.5; margin-top: 3px;
}
.stop-tip {
    font-size: 0.76rem; color: #6a8a6a;
    font-style: italic; margin-top: 6px;
    padding: 4px 8px;
    background: #1e2420;
    border-left: 2px solid #3a6a3a;
}
.stop-duration {
    font-size: 0.68rem; color: #8a7968;
    margin-top: 4px;
}
.walk-arrow {
    text-align: center; font-size: 0.7rem;
    color: #4a4238; margin: 2px 0;
    letter-spacing: 0.05em;
}

/* Stat chips */
.stat-chip {
    display: inline-block;
    background: #1a1814;
    border: 1px solid #2a2720;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    color: #8a7968;
    margin: 3px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d0c0a !important;
    border-right: 1px solid #1a1814;
}
[data-testid="stSidebar"] label {
    font-size: 0.75rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #8a7968 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #c8410a, #a33408) !important;
    color: white !important; border: none !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    width: 100% !important;
    padding: 0.75rem !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    box-shadow: 0 4px 15px rgba(200, 65, 10, 0.3) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #e04d10, #c8410a) !important;
    box-shadow: 0 6px 20px rgba(200, 65, 10, 0.5) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea textarea,
.stSlider {
    background: #1a1814 !important;
    border-color: #2a2720 !important;
    color: #f0ede6 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0d0c0a;
    border-bottom: 1px solid #2a2720;
}
.stTabs [data-baseweb="tab"] {
    color: #8a7968 !important;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
}
.stTabs [aria-selected="true"] {
    color: #f0ede6 !important;
    border-bottom-color: #c8410a !important;
}

/* Map container */
.map-wrapper {
    border: 1px solid #2a2720;
    border-radius: 8px;
    overflow: hidden;
}

/* Section divider */
.section-label {
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #4a4238;
    margin: 1rem 0 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
# Realistic time budgets per place type (minutes)
DURATION_MAP = {
    "museum": 150, "gallery": 90, "monument": 45, "memorial": 45,
    "park": 60, "garden": 60, "palace": 90, "castle": 90,
    "cathedral": 45, "church": 30, "temple": 30, "mosque": 30,
    "market": 60, "bazaar": 75, "food hall": 60,
    "viewpoint": 30, "observation deck": 45,
    "neighborhood": 60, "district": 60, "street": 30,
    "beach": 90, "waterfront": 60, "pier": 30,
    "default": 60,
}

DAY_COLORS = ["#c8410a", "#2563eb", "#16a34a", "#9333ea",
              "#ca8a04", "#0891b2", "#db2777", "#059669"]

PLACE_EMOJIS = {
    "museum": "🏛️", "gallery": "🎨", "monument": "🗽", "memorial": "🕊️",
    "park": "🌳", "garden": "🌸", "palace": "👑", "castle": "🏰",
    "cathedral": "⛪", "church": "⛪", "temple": "🛕", "mosque": "🕌",
    "market": "🛍️", "bazaar": "🧆", "food": "🍽️", "restaurant": "🍽️",
    "viewpoint": "🔭", "beach": "🏖️", "waterfront": "⚓",
    "neighborhood": "🏘️", "default": "📍",
}


# ─────────────────────────────────────────────────────────────
# GEOCODING (Nominatim / OpenStreetMap)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def geocode(place: str, city: str):
    """Geocode a place using Nominatim. Returns (lat, lon) or None."""
    for query in [f"{place}, {city}", f"{place}"]:
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": "WanderMind-App/1.0", "Accept-Language": "en"},
                timeout=8,
            )
            data = r.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        time.sleep(0.3)
    return None


def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lon points."""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def walk_time_min(meters: float) -> int:
    """Estimate walking time assuming 80m/min."""
    return max(5, int(meters / 80))


# ─────────────────────────────────────────────────────────────
# LLM CALL
# ─────────────────────────────────────────────────────────────
def call_llm(prompt: str, provider: str, config: dict) -> str:
    """Route to the correct LLM provider."""
    if provider == "ollama":
        r = requests.post(
            config["url"].rstrip("/") + "/api/chat",
            json={"model": config["model"],
                  "messages": [{"role": "user", "content": prompt}],
                  "stream": False},
            timeout=180,
        )
        r.raise_for_status()
        d = r.json()
        return d.get("message", {}).get("content") or d.get("response", "")

    elif provider == "openrouter":
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {config['key']}",
                     "Content-Type": "application/json"},
            json={"model": config["model"],
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    elif provider == "lmstudio":
        r = requests.post(
            config["url"].rstrip("/") + "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    else:  # custom
        hdrs = {"Content-Type": "application/json"}
        if config.get("key"):
            hdrs["Authorization"] = f"Bearer {config['key']}"
        r = requests.post(
            config["url"].rstrip("/") + "/chat/completions",
            headers=hdrs,
            json={"model": config.get("model", ""),
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def parse_json(raw: str) -> dict:
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("LLM did not return valid JSON. Try a more capable model.")
    return json.loads(match.group(0))


# ─────────────────────────────────────────────────────────────
# SMART PROMPT — the core product insight
# ─────────────────────────────────────────────────────────────
def build_smart_prompt(destination: str, days: int, interests: list, pace: str) -> str:
    pace_guide = {
        "Relaxed": "2-3 stops/day, longer time at each",
        "Balanced": "3-4 stops/day, mix of exploration and rest",
        "Packed": "4-5 stops/day, efficient routing",
    }[pace]

    return f"""You are an expert local travel curator for {destination}.

Create a REALISTIC {days}-day itinerary for a traveler interested in: {', '.join(interests)}.
Travel pace: {pace} ({pace_guide}).

CRITICAL RULES — these make or break the itinerary:
1. GEOGRAPHIC CLUSTERING: Each day's stops must be in the SAME neighborhood or walking distance from each other (under 2km apart ideally). Group by area, not by category.
2. TIME REALISM: Account for actual visit durations — a major museum needs 2-3 hours, a monument 30-45 min, a market 1 hour. Don't overpack.
3. LOGICAL FLOW: Order stops so the traveler walks in a sensible direction (A→B→C, not A→C→B where C is between them).
4. OPENING HOURS: Museums and sites have limited hours. Start mornings with time-sensitive venues.
5. MEAL BREAKS: Include lunch naturally between stops. Dinner near end of day.

For each stop include:
- Real, exact place name (for geocoding)
- Type (museum/monument/park/market/restaurant/neighborhood/etc.)
- Visit duration in minutes (be realistic)
- Why visit — one compelling sentence
- Local tip — practical advice a local would give
- Start time (building on previous stop's end time, starting ~9:00 AM)

Respond ONLY with this JSON — no markdown, no explanation:
{{
  "destination": "{destination}",
  "total_days": {days},
  "days": [
    {{
      "day": 1,
      "area": "Neighborhood/Area name for this day",
      "theme": "Day theme e.g. Historic Core",
      "stops": [
        {{
          "name": "Exact Place Name",
          "type": "monument",
          "start_time": "9:00 AM",
          "duration_min": 45,
          "description": "Why this place is unmissable.",
          "tip": "Go early to beat the crowds.",
          "lat_hint": null,
          "lon_hint": null
        }}
      ]
    }}
  ]
}}"""


# ─────────────────────────────────────────────────────────────
# GET EMOJI FOR PLACE TYPE
# ─────────────────────────────────────────────────────────────
def get_emoji(place_type: str) -> str:
    t = (place_type or "").lower()
    for key, emoji in PLACE_EMOJIS.items():
        if key in t:
            return emoji
    return PLACE_EMOJIS["default"]


# ─────────────────────────────────────────────────────────────
# BUILD FOLIUM MAP
# ─────────────────────────────────────────────────────────────
def build_folium_map(itinerary: dict, dest: str) -> tuple:
    """Geocode all stops, draw routes per day, return (map, geocode_results)."""
    center = geocode(dest, "") or (38.9, -77.0)
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles="CartoDB dark_matter",
    )
    # Add OSM as optional layer
    folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="Dark (default)").add_to(m)

    all_coords = []
    results = {}  # day → list of (stop, coords)

    progress = st.progress(0, text="📍 Geocoding stops via OpenStreetMap…")
    total_stops = sum(len(d["stops"]) for d in itinerary.get("days", []))
    done = 0

    for d_idx, day in enumerate(itinerary.get("days", [])):
        color = DAY_COLORS[d_idx % len(DAY_COLORS)]
        day_coords = []
        day_results = []

        fg = folium.FeatureGroup(name=f"Day {day['day']}: {day.get('theme','')}")

        for s_idx, stop in enumerate(day.get("stops", [])):
            coords = geocode(stop["name"], dest)
            done += 1
            progress.progress(done / total_stops,
                              text=f"📍 Geocoding: {stop['name']}…")
            time.sleep(0.35)  # Nominatim rate limit

            if coords:
                day_coords.append(coords)
                all_coords.append(coords)

                emoji = get_emoji(stop.get("type", ""))
                dur = stop.get("duration_min", 60)
                end_hr = stop.get("start_time", "")

                # Marker icon
                icon_html = f"""
                <div style="
                    background:{color};
                    color:white;
                    width:32px;height:32px;
                    border-radius:50%;
                    display:flex;align-items:center;justify-content:center;
                    font-size:13px;font-weight:700;
                    border:2px solid rgba(255,255,255,0.8);
                    box-shadow:0 3px 10px rgba(0,0,0,.5);
                    font-family:'Outfit',sans-serif;
                ">{s_idx+1}</div>"""

                popup_html = f"""
                <div style="font-family:'Outfit',sans-serif;min-width:220px;padding:4px">
                  <div style="font-weight:700;font-size:1rem;margin-bottom:4px">{emoji} {stop['name']}</div>
                  <div style="color:#c8410a;font-size:0.75rem;margin-bottom:6px">
                    {stop.get('start_time','')} · {dur} min
                  </div>
                  <div style="font-size:0.82rem;color:#444;margin-bottom:6px">{stop.get('description','')}</div>
                  <div style="font-size:0.76rem;color:#2d6a2d;font-style:italic;
                              background:#f0fff0;padding:4px 8px;border-left:2px solid #4caf50">
                    💡 {stop.get('tip','')}
                  </div>
                </div>"""

                folium.Marker(
                    location=coords,
                    popup=folium.Popup(popup_html, max_width=280),
                    tooltip=f"{'★' if s_idx==0 else str(s_idx+1)} {stop['name']}",
                    icon=folium.DivIcon(html=icon_html,
                                       icon_size=(32, 32),
                                       icon_anchor=(16, 16)),
                ).add_to(fg)

            day_results.append((stop, coords))

        # Draw route line for the day
        valid_coords = [c for _, c in day_results if c]
        if len(valid_coords) >= 2:
            AntPath(
                locations=valid_coords,
                color=color,
                weight=3,
                opacity=0.7,
                dash_array=[15, 20],
                delay=800,
                tooltip=f"Day {day['day']} route",
            ).add_to(fg)

        fg.add_to(m)
        results[day["day"]] = day_results

    progress.empty()
    folium.LayerControl(collapsed=False).add_to(m)
    MeasureControl().add_to(m)

    if len(all_coords) > 1:
        m.fit_bounds(all_coords, padding=(40, 40))
    elif all_coords:
        m.location = all_coords[0]

    return m, results


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'Cormorant Garamond',serif;font-size:1.8rem;
                font-weight:700;color:#f0ede6;margin-bottom:0.2rem">
    ✈️ WanderMind
    </div>
    <div style="font-size:0.65rem;letter-spacing:0.2em;text-transform:uppercase;
                color:#4a4238;margin-bottom:1.5rem">
    AI · OPEN SOURCE · FREE
    </div>
    """, unsafe_allow_html=True)

    # ── TRIP INPUTS ──
    st.markdown('<div class="section-label">📍 Where & When</div>', unsafe_allow_html=True)
    destination = st.text_input("Destination", value="Washington DC, USA",
                                placeholder="City, Country")
    days = st.slider("Number of Days", 1, 10, 2)
    pace = st.select_slider("Travel Pace", ["Relaxed", "Balanced", "Packed"], value="Balanced")

    st.markdown('<div class="section-label">🎯 Interests</div>', unsafe_allow_html=True)
    interest_options = [
        "History & Culture", "Art & Museums", "Architecture",
        "Food & Markets", "Nature & Parks", "Nightlife",
        "Photography Spots", "Hidden Gems", "Landmarks & Icons",
        "Religion & Spirituality", "Shopping", "Sports & Recreation",
    ]
    interests = st.multiselect("What do you love?", interest_options,
                               default=["History & Culture", "Landmarks & Icons"])

    custom_interests = st.text_input("Add your own interests",
                                     placeholder="e.g. street art, jazz bars…")
    if custom_interests:
        interests += [i.strip() for i in custom_interests.split(",") if i.strip()]

    # ── LLM CONFIG ──
    with st.expander("🤖 LLM Settings", expanded=False):
        provider_label = st.selectbox("Provider", [
            "Ollama (Local — Free)",
            "OpenRouter (Free models)",
            "LM Studio (Local)",
            "Custom API",
        ])
        provider_key = provider_label.split()[0].lower()

        llm_config = {}
        if provider_key == "ollama":
            llm_config["url"]   = st.text_input("URL", value="http://localhost:11434")
            llm_config["model"] = st.text_input("Model", value="llama3.2")
            st.caption("`ollama serve` · `ollama pull llama3.2`")
        elif provider_key == "openrouter":
            llm_config["key"]   = st.text_input("API Key", type="password")
            llm_config["model"] = st.selectbox("Model", [
                "meta-llama/llama-3.2-3b-instruct:free",
                "mistralai/mistral-7b-instruct:free",
                "google/gemma-2-9b-it:free",
                "qwen/qwen-2-7b-instruct:free",
            ])
            st.caption("Free at openrouter.ai")
        elif provider_key == "lm":
            provider_key = "lmstudio"
            llm_config["url"] = st.text_input("URL", value="http://localhost:1234")
        else:
            provider_key = "custom"
            llm_config["url"]   = st.text_input("Base URL")
            llm_config["key"]   = st.text_input("API Key", type="password")
            llm_config["model"] = st.text_input("Model Name")

    st.markdown("---")
    generate = st.button("✈ Plan My Trip")

    st.markdown("""
    <div style="font-size:0.65rem;color:#4a4238;margin-top:1rem;line-height:1.8">
    Powered by open-source LLMs<br/>
    Maps © OpenStreetMap contributors<br/>
    Geocoding by Nominatim (free)
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAIN AREA — HEADER
# ─────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown('<div class="hero-title">Your Perfect Trip,<br/>Planned by AI</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Geo-clustered · Realistic · Open Source</div>',
                unsafe_allow_html=True)

with col_h2:
    if st.session_state.get("itinerary"):
        itin = st.session_state.itinerary
        n_stops = sum(len(d["stops"]) for d in itin.get("days", []))
        st.markdown(f"""
        <div style="text-align:right;padding-top:0.5rem">
          <span class="stat-chip">📅 {itin.get('total_days','?')} days</span>
          <span class="stat-chip">📍 {n_stops} stops</span>
          <span class="stat-chip">🗺️ {st.session_state.get('geocoded',0)} mapped</span>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# GENERATE
# ─────────────────────────────────────────────────────────────
if generate:
    if not destination.strip():
        st.error("Please enter a destination.")
        st.stop()
    if not interests:
        st.warning("Please select at least one interest.")
        st.stop()

    with st.spinner("🤖 AI is curating your itinerary…"):
        try:
            prompt = build_smart_prompt(destination, days, interests, pace)
            raw    = call_llm(prompt, provider_key, llm_config)
            itin   = parse_json(raw)
            st.session_state.itinerary    = itin
            st.session_state.raw_response = raw
            st.session_state.fmap         = None  # reset map
            st.session_state.geo_results  = None
        except Exception as e:
            st.error(f"❌ LLM Error: {e}")
            raw = st.session_state.get("raw_response", "")
            if raw:
                with st.expander("Raw LLM output"):
                    st.code(raw)
            st.stop()

    # Geocode + build map
    itin = st.session_state.itinerary
    try:
        fmap, geo_results = build_folium_map(itin, destination)
        st.session_state.fmap        = fmap
        st.session_state.geo_results = geo_results
        geocoded = sum(1 for day_res in geo_results.values()
                       for _, c in day_res if c)
        st.session_state.geocoded = geocoded
    except Exception as e:
        st.warning(f"Map error: {e}")

    st.rerun()


# ─────────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────────
if st.session_state.get("itinerary"):
    itin        = st.session_state.itinerary
    geo_results = st.session_state.get("geo_results", {})

    tab_itin, tab_map, tab_raw = st.tabs(["📋 Itinerary", "🗺️ Map", "🔍 Raw Data"])

    # ── ITINERARY TAB ──
    with tab_itin:
        for d_idx, day in enumerate(itin.get("days", [])):
            color   = DAY_COLORS[d_idx % len(DAY_COLORS)]
            day_res = geo_results.get(day["day"], [])

            st.markdown(f"""
            <div class="day-header" style="color:{color}">
              Day {day['day']} · {day.get('theme', '')}
            </div>
            <div class="day-meta">📍 {day.get('area', '')} &nbsp;·&nbsp;
              {len(day['stops'])} stops</div>
            """, unsafe_allow_html=True)

            prev_coords = None
            for s_idx, stop in enumerate(day.get("stops", [])):
                emoji     = get_emoji(stop.get("type", ""))
                dur       = stop.get("duration_min", 60)
                coords    = None
                if s_idx < len(day_res):
                    _, coords = day_res[s_idx]

                # Walk time from previous
                if prev_coords and coords:
                    dist_m = haversine(*prev_coords, *coords)
                    walk   = walk_time_min(dist_m)
                    st.markdown(
                        f'<div class="walk-arrow">↓ ~{walk} min walk ({int(dist_m)}m)</div>',
                        unsafe_allow_html=True,
                    )

                geo_dot = "🟢" if coords else "🔴"
                st.markdown(f"""
                <div class="stop-card" style="--accent:{color}">
                  <div class="stop-row">
                    <div class="stop-badge" style="background:{color}">{s_idx+1}</div>
                    <div style="flex:1">
                      <div class="stop-time">{stop.get('start_time','')} · {dur} min {geo_dot}</div>
                      <div class="stop-name">{emoji} {stop['name']}</div>
                      <div class="stop-desc">{stop.get('description','')}</div>
                      {"<div class='stop-tip'>💡 " + stop['tip'] + "</div>" if stop.get('tip') else ""}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if coords:
                    prev_coords = coords

            st.markdown("<br/>", unsafe_allow_html=True)

        # Download
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇ Download JSON",
                data=json.dumps(itin, indent=2),
                file_name=f"itinerary_{destination.replace(' ','_')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_dl2:
            # Plain text version
            lines = [f"ITINERARY: {destination}\n{'='*40}"]
            for day in itin.get("days", []):
                lines.append(f"\nDAY {day['day']}: {day.get('theme','')}")
                lines.append(f"Area: {day.get('area','')}")
                for s in day.get("stops", []):
                    lines.append(f"  [{s.get('start_time','')}] {s['name']} ({s.get('duration_min',60)} min)")
                    lines.append(f"    → {s.get('description','')}")
                    if s.get("tip"):
                        lines.append(f"    💡 {s['tip']}")
            st.download_button(
                "⬇ Download TXT",
                data="\n".join(lines),
                file_name=f"itinerary_{destination.replace(' ','_')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    # ── MAP TAB ──
    with tab_map:
        if st.session_state.get("fmap"):
            # Legend
            st.markdown("**Day Legend**")
            leg_cols = st.columns(min(len(itin["days"]), 4))
            for i, day in enumerate(itin["days"]):
                with leg_cols[i % len(leg_cols)]:
                    color = DAY_COLORS[i % len(DAY_COLORS)]
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:6px;margin:4px 0">'
                        f'<div style="width:14px;height:14px;border-radius:50%;background:{color};flex-shrink:0"></div>'
                        f'<span style="font-size:0.78rem">Day {day["day"]}: {day.get("theme","")}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div class="map-wrapper">', unsafe_allow_html=True)
            st_folium(st.session_state.fmap, width=None, height=650,
                      use_container_width=True, returned_objects=[])
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption(f"© OpenStreetMap contributors · Geocoding by Nominatim · "
                       f"{st.session_state.get('geocoded',0)} locations mapped")
        else:
            st.info("Map will appear after generating an itinerary.")

    # ── RAW DATA TAB ──
    with tab_raw:
        with st.expander("Structured Itinerary (JSON)"):
            st.json(itin)
        with st.expander("Raw LLM Response"):
            st.code(st.session_state.get("raw_response", ""), language="json")

else:
    # Empty state — full-width placeholder map
    st.markdown("""
    <div style="text-align:center;padding:3rem 0;color:#4a4238">
      <div style="font-size:3rem;margin-bottom:1rem">🗺️</div>
      <div style="font-family:'Cormorant Garamond',serif;font-size:1.4rem;
                  color:#8a7968;margin-bottom:0.5rem">
        Your adventure starts in the sidebar
      </div>
      <div style="font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase">
        Enter destination → Select interests → Generate
      </div>
    </div>
    """, unsafe_allow_html=True)

    placeholder_map = folium.Map(
        location=[38.9, -77.0], zoom_start=13,
        tiles="CartoDB dark_matter",
    )
    st_folium(placeholder_map, width=None, height=500, use_container_width=True,
              returned_objects=[])