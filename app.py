import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict
import json
import math

# Page configuration
st.set_page_config(
    page_title="🌍 AI Travel Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Improved Readability
st.markdown("""
    <style>
    .main {
        background: #0b1220;
    }
    .stApp {
        background: #020617;
    }

    /* Workflow Step Cards */
    .workflow-step {
        background: #020617;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.9);
        margin: 15px 0;
        border-left: 6px solid #38bdf8;
        color: #e5e7eb;
    }

    /* Location Cards - High Contrast */
    .location-card {
        background: #020617;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 3px 8px rgba(15, 23, 42, 0.85);
        margin: 12px 0;
        border-left: 5px solid #38bdf8;
        transition: all 0.3s ease;
        color: #e5e7eb;
    }
    .location-card:hover {
        transform: translateX(5px);
        box-shadow: 0 5px 15px rgba(15, 23, 42, 0.95);
    }
    .location-card h4 {
        color: #f9fafb;
        margin-bottom: 10px;
        font-size: 1.1em;
    }
    .location-card p {
        color: #cbd5f5;
        margin: 5px 0;
        font-size: 0.95em;
    }

    /* Day Headers */
    .day-header {
        background: linear-gradient(135deg, #38bdf8 0%, #22c55e 100%);
        color: #0b1120;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0 10px 0;
        text-align: center;
        font-size: 1.5em;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(56, 189, 248, 0.5);
    }

    /* Status Badges - High Contrast */
    .status-badge {
        padding: 8px 18px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
        font-size: 0.9em;
        box-shadow: 0 2px 5px rgba(15, 23, 42, 0.9);
    }
    .status-completed {
        background: #22c55e;
        color: #022c22;
    }
    .status-current {
        background: #38bdf8;
        color: #020617;
        animation: pulse 2s infinite;
    }
    .status-pending {
        background: #eab308;
        color: #1f2937;
    }
    .status-skipped {
        background: #ef4444;
        color: #fef2f2;
    }
    .status-approaching {
        background: #f97316;
        color: #111827;
        animation: blink 1.5s infinite;
    }
    .status-checkedin {
        background: #6366f1;
        color: #e5e7eb;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* Check-in Notification - Dark Background */
    .checkin-notification {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: #022c22;
        padding: 25px;
        border-radius: 12px;
        margin: 15px 0;
        box-shadow: 0 4px 15px rgba(34, 197, 94, 0.7);
        animation: slideIn 0.5s ease;
    }
    .checkin-notification h3 {
        color: #022c22;
        margin-top: 0;
        font-size: 1.3em;
    }
    .checkin-notification p {
        color: #022c22;
        margin: 8px 0;
        font-size: 1em;
    }

    @keyframes slideIn {
        from {
            transform: translateY(-20px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }

    /* Distance Indicator - Better Contrast */
    .distance-indicator {
        background: #0ea5e9;
        color: #0b1120;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 8px 0;
        font-size: 0.95em;
        font-weight: 600;
    }

    /* Metric Cards */
    .metric-card {
        background: #020617;
        padding: 20px;
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
        letter-spacing: 0.5px;
    }
    .metric-card h2 {
        color: #f9fafb;
        margin: 10px 0;
    }
    .metric-card p {
        color: #9ca3af;
        font-size: 0.9em;
    }

    /* Progress Container */
    .progress-container {
        background: #020617;
        border-radius: 10px;
        height: 28px;
        overflow: hidden;
        margin-top: 10px;
        border: 1px solid #1f2937;
    }
    .progress-fill {
        background: linear-gradient(90deg, #38bdf8 0%, #22c55e 100%);
        height: 100%;
        transition: width 0.5s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #020617;
        font-weight: bold;
        font-size: 0.9em;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #38bdf8 0%, #22c55e 100%);
        color: #020617;
        border: none;
        border-radius: 10px;
        padding: 12px 28px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(56, 189, 248, 0.7);
    }

    /* Replan Alert - Better Contrast */
    .replan-alert {
        background: #0f172a;
        border-left: 5px solid #eab308;
        padding: 25px;
        border-radius: 10px;
        margin: 15px 0;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.9);
    }
    .replan-alert h3 {
        color: #eab308;
        margin-top: 0;
        font-size: 1.3em;
    }
    .replan-alert p {
        color: #e5e7eb;
        font-size: 1em;
        margin: 10px 0;
    }

    /* Route Info - Darker Background */
    .route-info {
        background: #020617;
        color: #e5e7eb;
        border-left: 5px solid #38bdf8;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.9);
    }
    .route-info h4 {
        color: #f9fafb;
        margin-top: 0;
        font-size: 1.2em;
    }
    .route-info p {
        color: #cbd5f5;
        margin: 8px 0;
        font-size: 0.95em;
    }

    /* Headers */
    h1, h2, h3 {
        color: #f9fafb !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #020617;
    }
    [data-testid="stSidebar"] .element-container {
        color: #e5e7eb;
    }

    /* Tab styling for better contrast */
    .stTabs [data-baseweb="tab-list"] {
        background: #020617;
        border-bottom: 2px solid #1f2937;
    }
    .stTabs [data-baseweb="tab"] {
        color: #9ca3af;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #38bdf8;
        border-bottom-color: #38bdf8;
    }

    /* Info boxes */
    .element-container .stInfo {
        background: #0f172a;
        color: #38bdf8;
        border-left: 4px solid #38bdf8;
    }
    .element-container .stSuccess {
        background: #022c22;
        color: #22c55e;
        border-left: 4px solid #22c55e;
    }
    .element-container .stWarning {
        background: #451a03;
        color: #facc15;
        border-left: 4px solid #fbbf24;
    }
    </style>
""", unsafe_allow_html=True)


# Data classes
@dataclass
class Location:
    id: int
    name: str
    lat: float
    lon: float
    category: str
    planned_duration: int  # minutes
    planned_start: str
    planned_end: str
    priority: int  # 1-5
    description: str
    rating: float
    day: int
    actual_start: str = None
    actual_end: str = None
    status: str = "pending"  # pending, approaching, checked-in, in-progress, completed, skipped
    visit_order: int = 0
    checked_in: bool = False
    check_in_time: str = None
    distance_from_user: float = None  # in meters

    def get_actual_duration(self):
        if self.actual_start and self.actual_end:
            start = datetime.strptime(self.actual_start, "%H:%M")
            end = datetime.strptime(self.actual_end, "%H:%M")
            return int((end - start).total_seconds() / 60)
        return 0


@dataclass
class DayItinerary:
    day_number: int
    locations: List[Location] = field(default_factory=list)
    total_planned_time: int = 0
    status: str = "pending"  # pending, in-progress, completed


# Helper functions for distance and proximity
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula
    Returns distance in meters
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def check_proximity_and_auto_checkin(user_lat, user_lon, check_in_radius=100):
    """
    Check if user is within check-in radius of any pending location
    Returns tuple: (checked_in_location, all_distances)
    """
    current_day = st.session_state.current_day
    locations = st.session_state.itinerary[current_day].locations

    checked_in_location = None
    all_distances = {}

    for loc in locations:
        # Calculate distance from user to this location
        distance = calculate_distance(user_lat, user_lon, loc.lat, loc.lon)
        loc.distance_from_user = distance
        all_distances[loc.id] = distance

        # Auto check-in logic
        if distance <= check_in_radius and not loc.checked_in and loc.status in ["pending", "approaching"]:
            # Auto check-in!
            loc.checked_in = True
            loc.check_in_time = datetime.now().strftime("%H:%M")
            loc.status = "checked-in"
            checked_in_location = loc

            # Show notification
            st.session_state.last_checkin = {
                'location': loc.name,
                'time': loc.check_in_time,
                'distance': distance
            }

        # Update approaching status
        elif distance <= check_in_radius * 2 and loc.status == "pending":
            loc.status = "approaching"

    return checked_in_location, all_distances


def simulate_user_movement_to_location(location):
    """Simulate user moving to a specific location (for demo purposes)"""
    # Add some random offset to make it realistic (within 10-50 meters)
    offset_lat = random.uniform(-0.0005, 0.0005)
    offset_lon = random.uniform(-0.0005, 0.0005)

    new_position = (location.lat + offset_lat, location.lon + offset_lon)
    st.session_state.user_position = new_position

    # Trigger proximity check
    checked_in_loc, distances = check_proximity_and_auto_checkin(new_position[0], new_position[1])

    return checked_in_loc


# Initialize session state
def initialize_session_state():
    if 'workflow_stage' not in st.session_state:
        st.session_state.workflow_stage = 'input'  # input, generating, itinerary_review, tracking, mid_trip_replan

    if 'user_inputs' not in st.session_state:
        st.session_state.user_inputs = {
            'days': 2,
            'destination': 'Washington DC',
            'interests': ['City Highlights', 'Museums']
        }

    if 'itinerary' not in st.session_state:
        # Sample 2-day Washington DC itinerary
        st.session_state.itinerary = {
            1: DayItinerary(
                day_number=1,
                locations=[
                    Location(1, "National Mall", 38.8893, -77.0502, "Monument", 60, "09:00", "10:00", 5,
                             "Start at the iconic National Mall", 4.8, 1, visit_order=1),
                    Location(2, "Lincoln Memorial", 38.8893, -77.0502, "Monument", 45, "10:15", "11:00", 5,
                             "Visit the majestic Lincoln Memorial", 4.9, 1, visit_order=2),
                    Location(3, "World War II Memorial", 38.8894, -77.0405, "Monument", 30, "11:15", "11:45", 4,
                             "Pay respects at WWII Memorial", 4.7, 1, visit_order=3),
                    Location(4, "Washington Monument", 38.8895, -77.0353, "Monument", 45, "12:00", "12:45", 5,
                             "Iconic obelisk on the National Mall", 4.8, 1, visit_order=4),
                    Location(5, "White House (Outside)", 38.8977, -77.0365, "Landmark", 30, "13:30", "14:00", 4,
                             "Midday - Walk toward the White House (outside views)", 4.6, 1, visit_order=5),
                    Location(6, "Penn Quarter", 38.8991, -77.0229, "District", 60, "14:30", "15:30", 3,
                             "Lunch near Penn Quarter or Capitol Hill", 4.5, 1, visit_order=6),
                    Location(7, "U.S. Capitol", 38.8899, -77.0091, "Government", 90, "16:00", "17:30", 5,
                             "Afternoon - U.S. Capitol (guided tour if booked)", 4.9, 1, visit_order=7),
                    Location(8, "Library of Congress", 38.8886, -77.0047, "Library", 60, "17:45", "18:45", 4,
                             "Library of Congress", 4.8, 1, visit_order=8),
                    Location(9, "Tidal Basin", 38.8814, -77.0365, "Nature", 45, "19:00", "19:45", 4,
                             "Evening - Relax around the Tidal Basin (especially beautiful at sunset)", 4.7, 1,
                             visit_order=9),
                    Location(10, "The Wharf", 38.8804, -77.0177, "Waterfront", 90, "20:00", "21:30", 3,
                             "Dinner at The Wharf or Georgetown", 4.6, 1, visit_order=10),
                ],
                status="pending"
            ),
            2: DayItinerary(
                day_number=2,
                locations=[
                    Location(11, "National Air and Space Museum", 38.8882, -77.0199, "Museum", 120, "09:00", "11:00", 5,
                             "Morning - National Air and Space Museum", 4.9, 2, visit_order=1),
                    Location(12, "National Museum of American History", 38.8913, -77.0300, "Museum", 120, "11:30",
                             "13:30", 5,
                             "National Museum of American History", 4.8, 2, visit_order=2),
                    Location(13, "Lunch Break", 38.8913, -77.0300, "Food & Drink", 60, "13:30", "14:30", 3,
                             "Lunch - Similar for day 2", 4.5, 2, visit_order=3),
                    Location(14, "Afternoon Activities", 38.8913, -77.0300, "Activity", 120, "14:30", "16:30", 3,
                             "Afternoon - Similar for day 2", 4.6, 2, visit_order=4),
                    Location(15, "Evening Dining", 38.8913, -77.0300, "Food & Drink", 90, "18:00", "19:30", 3,
                             "Evening - Similar for day 2", 4.5, 2, visit_order=5),
                ],
                status="pending"
            )
        }

    if 'current_day' not in st.session_state:
        st.session_state.current_day = 1

    if 'current_location_idx' not in st.session_state:
        st.session_state.current_location_idx = 0

    if 'user_position' not in st.session_state:
        st.session_state.user_position = (38.8893, -77.0502)

    if 'tracking_active' not in st.session_state:
        st.session_state.tracking_active = False

    if 'time_variance' not in st.session_state:
        st.session_state.time_variance = 0

    if 'show_replan_modal' not in st.session_state:
        st.session_state.show_replan_modal = False

    if 'auto_checkin_enabled' not in st.session_state:
        st.session_state.auto_checkin_enabled = True

    if 'checkin_radius' not in st.session_state:
        st.session_state.checkin_radius = 100  # meters

    if 'last_checkin' not in st.session_state:
        st.session_state.last_checkin = None


# Helper functions
def create_route_map(day_number):
    """Create route map for specific day"""
    day_itinerary = st.session_state.itinerary[day_number]

    if not day_itinerary.locations:
        return None

    # Center on first location
    first_loc = day_itinerary.locations[0]
    m = folium.Map(location=[first_loc.lat, first_loc.lon], zoom_start=13)

    # Color mapping
    colors = {
        "completed": "green",
        "in-progress": "blue",
        "checked-in": "purple",
        "approaching": "orange",
        "pending": "lightgray",
        "skipped": "red"
    }

    # Add markers
    for i, loc in enumerate(day_itinerary.locations):
        icon_color = colors.get(loc.status, "gray")

        # Build check-in info
        checkin_info = ""
        if loc.checked_in:
            checkin_info = f"<p><b>✅ Checked In:</b> {loc.check_in_time}</p>"
        if loc.distance_from_user is not None:
            distance_m = int(loc.distance_from_user)
            if distance_m < 1000:
                dist_str = f"{distance_m}m away"
            else:
                dist_str = f"{distance_m / 1000:.1f}km away"
            checkin_info += f"<p><b>📍 Distance:</b> {dist_str}</p>"

        popup_html = f"""
            <div style="width: 220px;">
                <h4>{loc.visit_order}. {loc.name}</h4>
                <p><b>Status:</b> {loc.status}</p>
                <p><b>Time:</b> {loc.planned_start} - {loc.planned_end}</p>
                <p><b>Duration:</b> {loc.planned_duration} min</p>
                <p><b>Category:</b> {loc.category}</p>
                <p><b>Rating:</b> {'⭐' * int(loc.rating)}</p>
                {checkin_info}
            </div>
        """

        folium.Marker(
            location=[loc.lat, loc.lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{loc.visit_order}. {loc.name}",
            icon=folium.Icon(color=icon_color, icon="info-sign", prefix='glyphicon')
        ).add_to(m)

        # Add number label
        folium.Marker(
            location=[loc.lat, loc.lon],
            icon=folium.DivIcon(html=f"""
                <div style="font-size: 14pt; color: white; font-weight: bold; 
                background-color: {icon_color}; border-radius: 50%; 
                width: 30px; height: 30px; display: flex; 
                align-items: center; justify-content: center; 
                border: 2px solid white;">
                    {loc.visit_order}
                </div>
            """)
        ).add_to(m)

    # Draw route
    route_coords = [[loc.lat, loc.lon] for loc in day_itinerary.locations]
    folium.PolyLine(
        route_coords,
        color="blue",
        weight=4,
        opacity=0.7,
        dash_array="10, 5"
    ).add_to(m)

    # Add check-in radius circles for pending/approaching locations
    if st.session_state.tracking_active and st.session_state.auto_checkin_enabled:
        for loc in day_itinerary.locations:
            if loc.status in ["pending", "approaching"]:
                folium.Circle(
                    location=[loc.lat, loc.lon],
                    radius=st.session_state.checkin_radius,
                    color="#3b82f6",
                    fill=True,
                    fillColor="#3b82f6",
                    fillOpacity=0.1,
                    weight=1,
                    dashArray='5, 5',
                    popup=f"Auto Check-in Zone ({st.session_state.checkin_radius}m)"
                ).add_to(m)

    # Add user position if tracking
    if st.session_state.tracking_active:
        folium.Marker(
            location=st.session_state.user_position,
            popup="📍 Your Current Location",
            tooltip="You are here",
            icon=folium.Icon(color="red", icon="user", prefix='fa')
        ).add_to(m)

        # Add accuracy circle around user
        folium.Circle(
            location=st.session_state.user_position,
            radius=20,  # 20m accuracy
            color="red",
            fill=True,
            fillColor="red",
            fillOpacity=0.2,
            weight=1
        ).add_to(m)

    return m


def get_current_location():
    """Get current location being visited"""
    day = st.session_state.current_day
    locations = st.session_state.itinerary[day].locations

    for loc in locations:
        if loc.status == "in-progress":
            return loc
    return None


def simulate_visit_completion(location, time_variance_minutes=0):
    """Simulate completing a location visit"""
    now = datetime.now()
    location.actual_start = now.strftime("%H:%M")

    actual_duration = location.planned_duration + time_variance_minutes
    end_time = now + timedelta(minutes=actual_duration)
    location.actual_end = end_time.strftime("%H:%M")
    location.status = "completed"

    # Update time variance
    st.session_state.time_variance += time_variance_minutes

    # Move to next location
    day = st.session_state.current_day
    current_locations = st.session_state.itinerary[day].locations
    current_idx = next((i for i, loc in enumerate(current_locations) if loc.id == location.id), -1)

    if current_idx < len(current_locations) - 1:
        current_locations[current_idx + 1].status = "in-progress"
        st.session_state.current_location_idx = current_idx + 1
    else:
        # Day completed
        if day < max(st.session_state.itinerary.keys()):
            st.session_state.current_day += 1
            st.session_state.itinerary[st.session_state.current_day].status = "in-progress"
            st.session_state.itinerary[st.session_state.current_day].locations[0].status = "in-progress"
            st.session_state.current_location_idx = 0


def trigger_mid_trip_replan():
    """Trigger mid-trip replanning"""
    st.session_state.workflow_stage = 'mid_trip_replan'
    st.session_state.show_replan_modal = True


# Initialize
initialize_session_state()

# Sidebar
with st.sidebar:
    st.title("🤖 AI Travel Planner")
    st.markdown("### Workflow Progress")

    stages = {
        'input': '1️⃣ User Input',
        'generating': '2️⃣ AI Generating',
        'itinerary_review': '3️⃣ Review Itinerary',
        'tracking': '4️⃣ Live Tracking',
        'mid_trip_replan': '5️⃣ Mid-Trip Replan'
    }

    for key, label in stages.items():
        if key == st.session_state.workflow_stage:
            st.markdown(f"**✅ {label}** ← Current")
        else:
            st.markdown(f"⚪ {label}")

    st.markdown("---")

    # Quick navigation
    st.markdown("### 🎯 Quick Actions")

    if st.button("🏠 Start Over", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    if st.session_state.workflow_stage == 'tracking':
        if st.button("🔄 Trigger Mid-Trip Replan", use_container_width=True):
            trigger_mid_trip_replan()
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Trip Overview")

    if st.session_state.workflow_stage in ['itinerary_review', 'tracking', 'mid_trip_replan']:
        st.metric("Days", len(st.session_state.itinerary))
        st.metric("Destination", st.session_state.user_inputs['destination'])

        total_locations = sum(len(day.locations) for day in st.session_state.itinerary.values())
        st.metric("Total Locations", total_locations)

# Main content based on workflow stage
if st.session_state.workflow_stage == 'input':
    st.title("🌍 Plan Your Perfect Trip")
    st.markdown("### Step 1: Tell us about your trip")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📅 Trip Duration")
        days = st.number_input("Number of Days", min_value=1, max_value=14, value=2)

        st.markdown("#### 📍 Destination")
        destination = st.text_input("Where are you going?", value="Washington DC")

    with col2:
        st.markdown("#### 🎯 What You Like")
        interests = st.multiselect(
            "Choose your interests",
            ["Culture & History", "Nature & Outdoors", "Entertainment & Science",
             "Food & Drink", "Shopping", "City Highlights", "Museums",
             "Relaxation & Wellness", "Adventure & Activities", "Events & Local Life"],
            default=["City Highlights", "Museums"]
        )

    st.markdown("---")

    if st.button("✨ Generate My Itinerary", use_container_width=True, type="primary"):
        st.session_state.user_inputs = {
            'days': days,
            'destination': destination,
            'interests': interests
        }
        st.session_state.workflow_stage = 'generating'
        st.rerun()

elif st.session_state.workflow_stage == 'generating':
    st.title("🤖 AI is Crafting Your Perfect Itinerary...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = [
        ("Analyzing your preferences...", 20),
        ("Finding top-rated attractions...", 40),
        ("Calculating optimal routes...", 60),
        ("Scheduling activities...", 80),
        ("Finalizing your itinerary...", 100)
    ]

    for step, progress in steps:
        status_text.markdown(f"### {step}")
        progress_bar.progress(progress)
        time.sleep(0.8)

    st.success("✅ Your itinerary is ready!")
    time.sleep(1)

    st.session_state.workflow_stage = 'itinerary_review'
    st.rerun()

elif st.session_state.workflow_stage == 'itinerary_review':
    st.title("📋 Review Your Itinerary")
    st.markdown(f"### {st.session_state.user_inputs['days']}-Day Trip to {st.session_state.user_inputs['destination']}")

    # Display each day
    for day_num, day_itinerary in st.session_state.itinerary.items():
        st.markdown(f'<div class="day-header">Day {day_num}: {day_itinerary.locations[0].category.title()} Day</div>',
                    unsafe_allow_html=True)

        # Create map for this day
        day_map = create_route_map(day_num)
        if day_map:
            st_folium(day_map, width=1200, height=400, key=f"review_map_{day_num}")

        # Show locations
        for loc in day_itinerary.locations:
            st.markdown(f"""
                <div class="location-card">
                    <h4>{loc.visit_order}. {loc.name} <span class="status-badge status-pending">Planned</span></h4>
                    <p><b>📍 Category:</b> {loc.category} | <b>⭐ Rating:</b> {loc.rating}/5.0</p>
                    <p><b>🕒 Time:</b> {loc.planned_start} - {loc.planned_end} ({loc.planned_duration} min)</p>
                    <p><b>💡 Priority:</b> {'⭐' * loc.priority}</p>
                    <p style="font-size: 0.95em; color: #6b7280;">{loc.description}</p>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ Not Satisfied - Regenerate", use_container_width=True):
            st.session_state.workflow_stage = 'generating'
            st.rerun()

    with col2:
        if st.button("✅ Looks Good - Start Trip!", use_container_width=True, type="primary"):
            st.session_state.workflow_stage = 'tracking'
            st.session_state.itinerary[1].status = "in-progress"
            st.session_state.itinerary[1].locations[0].status = "in-progress"
            st.balloons()
            st.rerun()

elif st.session_state.workflow_stage == 'tracking':
    st.title("🗺️ Live Trip Tracking")

    current_day = st.session_state.current_day

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_locations = len(st.session_state.itinerary[current_day].locations)
        completed = sum(1 for loc in st.session_state.itinerary[current_day].locations
                        if loc.status == "completed")
        progress = (completed / total_locations) * 100

        st.markdown(f"""
            <div class="metric-card">
                <h3>Day {current_day} Progress</h3>
                <div class="progress-container">
                    <div class="progress-fill" style="width: {progress}%">{progress:.0f}%</div>
                </div>
                <p style="margin-top: 10px;">{completed}/{total_locations} Locations</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        status = "On Time"
        if st.session_state.time_variance > 15:
            status = f"{st.session_state.time_variance} min Behind"
            badge_class = "status-skipped"
        elif st.session_state.time_variance < -15:
            status = f"{abs(st.session_state.time_variance)} min Ahead"
            badge_class = "status-current"
        else:
            badge_class = "status-completed"

        st.markdown(f"""
            <div class="metric-card">
                <h3>Schedule Status</h3>
                <span class="status-badge {badge_class}">{status}</span>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        current_time = datetime.now().strftime("%H:%M")
        st.markdown(f"""
            <div class="metric-card">
                <h3>Current Time</h3>
                <h2>{current_time}</h2>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        tracking_status = "🟢 Active" if st.session_state.tracking_active else "🔴 Paused"
        st.markdown(f"""
            <div class="metric-card">
                <h3>Tracking Status</h3>
                <h2>{tracking_status}</h2>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Map and itinerary
    col_map, col_itinerary = st.columns([1.3, 1])

    with col_map:
        st.markdown(f"### 🗺️ Day {current_day} Route Map")

        # Map controls
        map_col1, map_col2, map_col3 = st.columns(3)

        with map_col1:
            if st.button("📍 Start Tracking", use_container_width=True):
                st.session_state.tracking_active = True
                # Auto check proximity when tracking starts
                if st.session_state.auto_checkin_enabled:
                    check_proximity_and_auto_checkin(
                        st.session_state.user_position[0],
                        st.session_state.user_position[1],
                        st.session_state.checkin_radius
                    )
                st.success("Location tracking activated!")
                st.rerun()

        with map_col2:
            if st.button("⏸️ Pause", use_container_width=True):
                st.session_state.tracking_active = False
                st.rerun()

        with map_col3:
            if st.button("🔄 Refresh", use_container_width=True):
                # Re-check proximity on refresh
                if st.session_state.tracking_active and st.session_state.auto_checkin_enabled:
                    check_proximity_and_auto_checkin(
                        st.session_state.user_position[0],
                        st.session_state.user_position[1],
                        st.session_state.checkin_radius
                    )
                st.rerun()

        # Auto check-in settings
        st.markdown("##### ⚙️ Auto Check-in Settings")
        auto_col1, auto_col2 = st.columns(2)

        with auto_col1:
            auto_enabled = st.checkbox(
                "Enable Auto Check-in",
                value=st.session_state.auto_checkin_enabled,
                key="auto_checkin_toggle"
            )
            if auto_enabled != st.session_state.auto_checkin_enabled:
                st.session_state.auto_checkin_enabled = auto_enabled
                st.rerun()

        with auto_col2:
            radius = st.selectbox(
                "Check-in Radius",
                options=[50, 100, 150, 200],
                index=1,
                format_func=lambda x: f"{x}m",
                key="radius_select"
            )
            if radius != st.session_state.checkin_radius:
                st.session_state.checkin_radius = radius
                st.rerun()

        # Simulation controls for testing
        st.markdown("##### 🎮 Demo: Simulate Movement")
        next_pending = next((loc for loc in st.session_state.itinerary[current_day].locations
                             if loc.status in ["pending", "approaching"]), None)

        if next_pending:
            sim_col1, sim_col2 = st.columns(2)

            with sim_col1:
                if st.button(f"🚶 Move to {next_pending.name[:20]}...", use_container_width=True):
                    checked_in = simulate_user_movement_to_location(next_pending)
                    if checked_in:
                        st.success(f"✅ Auto-checked in to {checked_in.name}!")
                    st.rerun()

            with sim_col2:
                # Calculate current distance to next location
                if st.session_state.tracking_active:
                    dist = calculate_distance(
                        st.session_state.user_position[0],
                        st.session_state.user_position[1],
                        next_pending.lat,
                        next_pending.lon
                    )
                    st.info(f"📏 {int(dist)}m away")

        # Check-in notification
        if st.session_state.last_checkin:
            checkin = st.session_state.last_checkin
            st.markdown(f"""
                <div class="checkin-notification">
                    <h3>✅ Auto Check-in Successful!</h3>
                    <p><b>Location:</b> {checkin['location']}</p>
                    <p><b>Time:</b> {checkin['time']}</p>
                    <p><b>Distance:</b> {int(checkin['distance'])}m from location</p>
                    <p style="margin-top: 10px; font-size: 0.9em;">You are now checked in. Start your visit!</p>
                </div>
            """, unsafe_allow_html=True)

            # Clear notification after showing
            if st.button("✓ Dismiss", key="dismiss_checkin"):
                st.session_state.last_checkin = None
                st.rerun()

        # Display map
        day_map = create_route_map(current_day)
        if day_map:
            st_folium(day_map, width=800, height=600, key=f"tracking_map_{current_day}")

        # Route info
        current_loc = get_current_location()
        next_loc = next((loc for loc in st.session_state.itinerary[current_day].locations
                         if loc.status in ["pending", "approaching"]), None)

        if next_loc:
            st.markdown(f"""
                <div class="route-info">
                    <h4>📍 Next: {next_loc.name}</h4>
                    <p><b>Planned arrival:</b> {next_loc.planned_start}</p>
                    <p><b>Duration:</b> {next_loc.planned_duration} minutes</p>
                    <p>Auto check-in will activate when you're within {st.session_state.checkin_radius}m</p>
                </div>
            """, unsafe_allow_html=True)
        elif current_loc:
            st.markdown(f"""
                <div class="route-info">
                    <h4>🔵 Currently at: {current_loc.name}</h4>
                    <p><b>Started:</b> {current_loc.actual_start}</p>
                    <p><b>Planned duration:</b> {current_loc.planned_duration} minutes</p>
                </div>
            """, unsafe_allow_html=True)

    with col_itinerary:
        st.markdown(f"### 📋 Day {current_day} Itinerary")

        for loc in st.session_state.itinerary[current_day].locations:
            status_badges = {
                "completed": ("status-completed", "✅ Completed"),
                "in-progress": ("status-current", "🔵 In Progress"),
                "checked-in": ("status-checkedin", "✅ Checked In"),
                "approaching": ("status-approaching", "🟠 Approaching"),
                "pending": ("status-pending", "⏳ Pending"),
                "skipped": ("status-skipped", "⏭️ Skipped")
            }

            badge_class, badge_text = status_badges.get(loc.status, ("", ""))

            # Show distance if available
            distance_info = ""
            if loc.distance_from_user is not None and st.session_state.tracking_active:
                dist_m = int(loc.distance_from_user)
                if dist_m < 1000:
                    distance_info = f'<div class="distance-indicator">📏 {dist_m}m away</div>'
                else:
                    distance_info = f'<div class="distance-indicator">📏 {dist_m / 1000:.1f}km away</div>'

            # Show check-in info if checked in
            checkin_info = ""
            if loc.checked_in:
                checkin_info = f'<p style="color: #22c55e; font-weight: bold;">✅ Checked in at {loc.check_in_time}</p>'

            st.markdown(f"""
                <div class="location-card">
                    <h4>{loc.visit_order}. {loc.name}</h4>
                    <span class="status-badge {badge_class}">{badge_text}</span>
                    {distance_info}
                    <p><b>🕒 Planned:</b> {loc.planned_start} - {loc.planned_end}</p>
                    <p><b>⏱️ Duration:</b> {loc.planned_duration} min</p>
                    {checkin_info}
                </div>
            """, unsafe_allow_html=True)

            # Action buttons for checked-in or current location
            if loc.status == "checked-in":
                # Show "Start Visit" button for checked-in locations
                if st.button(f"▶️ Start Visit", key=f"start_{loc.id}", use_container_width=True):
                    loc.status = "in-progress"
                    loc.actual_start = datetime.now().strftime("%H:%M")
                    st.rerun()

            elif loc.status == "in-progress":
                btn_col1, btn_col2, btn_col3 = st.columns(3)

                with btn_col1:
                    if st.button("✅ On Time", key=f"ontime_{loc.id}", use_container_width=True):
                        simulate_visit_completion(loc, 0)
                        st.rerun()

                with btn_col2:
                    if st.button("⏱️ Overstay +30m", key=f"over_{loc.id}", use_container_width=True):
                        simulate_visit_completion(loc, 30)
                        trigger_mid_trip_replan()
                        st.rerun()

                with btn_col3:
                    if st.button("⚡ Early -20m", key=f"early_{loc.id}", use_container_width=True):
                        simulate_visit_completion(loc, -20)
                        st.rerun()

            elif loc.status == "approaching":
                st.info(f"🚶 Approaching... Move closer to auto check-in (within {st.session_state.checkin_radius}m)")

elif st.session_state.workflow_stage == 'mid_trip_replan':
    st.title("🔄 Mid-Trip Replanning")

    st.markdown(f"""
        <div class="replan-alert">
            <h3>⚠️ Schedule Adjustment Needed</h3>
            <p>You're currently <b>{abs(st.session_state.time_variance)} minutes</b> 
            {'behind' if st.session_state.time_variance > 0 else 'ahead of'} schedule.</p>
        </div>
    """, unsafe_allow_html=True)

    current_day = st.session_state.current_day
    remaining_locations = [loc for loc in st.session_state.itinerary[current_day].locations
                           if loc.status == "pending"]

    st.markdown("### 💡 Replanning Options")

    tab1, tab2, tab3 = st.tabs(["📊 Same Itinerary", "✨ New Itinerary", "🎯 Replan Remaining"])

    with tab1:
        st.markdown("#### Keep Same Locations, Adjust Timing")

        if st.session_state.time_variance > 0:
            compression_per_loc = st.session_state.time_variance // len(
                remaining_locations) if remaining_locations else 0

            st.markdown(f"""
                <div style="background: #0f172a; border-left: 5px solid #38bdf8; padding: 20px; border-radius: 8px; margin: 15px 0;">
                    <h4 style="color: #38bdf8; margin-top: 0;">Strategy: Compress Schedule</h4>
                    <ul style="color: #e5e7eb; margin: 10px 0; line-height: 1.8;">
                        <li>Reduce time at <b>{len(remaining_locations)} remaining locations</b></li>
                        <li>Each location: <b>-{compression_per_loc} minutes</b></li>
                        <li>All planned stops retained</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("**Adjusted Schedule:**")
            for loc in remaining_locations:
                new_duration = max(15, loc.planned_duration - compression_per_loc)
                st.markdown(f"""
                    <div style="background: #020617; border: 1px solid #1f2937; padding: 12px; border-radius: 6px; margin: 8px 0;">
                        <span style="color: #e5e7eb; font-weight: 600;">• {loc.name}:</span> 
                        <span style="color: #9ca3af;">{loc.planned_duration}min</span> 
                        <span style="color: #ef4444;">→</span> 
                        <span style="color: #22c55e; font-weight: 700;">{new_duration}min</span>
                    </div>
                """, unsafe_allow_html=True)

            if st.button("✅ Apply Compression", key="compress", use_container_width=True):
                for loc in remaining_locations:
                    loc.planned_duration = max(15, loc.planned_duration - compression_per_loc)
                st.session_state.time_variance = 0
                st.session_state.workflow_stage = 'tracking'
                st.success("Schedule compressed successfully!")
                time.sleep(1)
                st.rerun()
        else:
            st.markdown("""
                <div style="background: #022c22; border-left: 5px solid #22c55e; padding: 20px; border-radius: 8px;">
                    <h4 style="color: #bbf7d0; margin-top: 0;">✅ You're ahead of schedule!</h4>
                    <ul style="color: #86efac; line-height: 1.8;">
                        <li>Consider extending time at remaining locations</li>
                        <li>Add buffer for unexpected discoveries</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.markdown("#### Generate Completely New Itinerary for Remaining Day")

        st.markdown("##### 🎯 Choose What You Like to Visit")

        new_interests = st.multiselect(
            "Select new preferences",
            ["Culture & History", "Nature & Outdoors", "Entertainment & Science",
             "Food & Drink", "Shopping", "Relaxation"],
            default=["Culture & History"]
        )

        if st.button("✨ Generate New Itinerary", key="new_itinerary", use_container_width=True):
            with st.spinner("AI is creating a new plan for the rest of your day..."):
                time.sleep(2)
                st.success("✅ New itinerary generated!")
                st.session_state.workflow_stage = 'tracking'
                st.rerun()

    with tab3:
        st.markdown("#### Replan Remaining Locations")

        st.markdown("##### Remaining locations to optimize:")

        for loc in remaining_locations:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{loc.name}** - {loc.planned_duration} min (Priority: {'⭐' * loc.priority})")
            with col2:
                skip = st.checkbox("Skip", key=f"skip_{loc.id}")
                if skip:
                    loc.status = "skipped"

        active_remaining = [loc for loc in remaining_locations if loc.status != "skipped"]

        if active_remaining:
            st.markdown(f"**Replanned itinerary:** {len(active_remaining)} locations")

            for i, loc in enumerate(active_remaining, 1):
                st.markdown(f"{i}. {loc.name} ({loc.planned_duration} min)")

        if st.button("✅ Apply Replan", key="replan", use_container_width=True):
            st.session_state.workflow_stage = 'tracking'
            st.success("Itinerary updated!")
            time.sleep(1)
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #9ca3af; padding: 20px;">
        <p><b>🌍 AI Travel Planner</b> | Real-time Tracking & Dynamic Replanning</p>
        <p>Powered by Agentic AI & Location Intelligence</p>
    </div>
""", unsafe_allow_html=True)
