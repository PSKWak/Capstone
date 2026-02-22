import streamlit as st
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3:latest"

# ----------------------------
# Session State Initialization
# ----------------------------
if "user_inputs" not in st.session_state:
    st.session_state.user_inputs = {
        "destination": "",
        "days": 3,
        "interests": []
    }

if "workflow_stage" not in st.session_state:
    st.session_state.workflow_stage = "input"

if "itinerary" not in st.session_state:
    st.session_state.itinerary = ""

if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = DEFAULT_MODEL


# ----------------------------
# Ollama Availability Check
# ----------------------------
def ollama_available(model):
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = [m["name"] for m in response.json()["models"]]
            return model in models
        return False
    except:
        return False
# ----------------------------
# Generate Itinerary
# ----------------------------
def generate_itinerary(destination, days, interests):
    interest_text = ", ".join(interests)

    prompt = f"""
    You are a local travel plannar and have extensive experience when it comes to curate a clean and detailed travel itenary for {days}- .Include the most visites places at {destination}.
    Keep in mind that you focus on these interests: {interest_text}. Make sure you are creating one of the best itenaries. Keep the itenary realistic and minimalist such that tourist experience and enjoy there time. Do not repeat attractios for another day and it it very important that when creating itenary you include the places in nearby locations such that tourist should not waste their time in travel. Next day you can cover another area.

    For each day include:
    - Morning activity
    - Afternoon activity
    - Evening activity
    
    Keep it structured and practical.
    """

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": st.session_state.ollama_model,
            "prompt": prompt,
            "stream": False
        }
    )

    if response.status_code == 200:
        return response.json()["response"]
    else:
        return "Could not generate AI itinerary."


# ----------------------------
# UI
# ----------------------------

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️")
st.title("✈️ AI Travel Planner with Ollama")

st.markdown("---")
st.markdown("### Step 1: Tell us about your trip")

col1, col2 = st.columns(2)

with col1:
    destination = st.text_input(
        "📍 Destination",
        value=st.session_state.user_inputs["destination"]
    )

    days = st.number_input(
        "📅 Number of Days",
        min_value=1,
        max_value=7,
        value=st.session_state.user_inputs["days"]
    )

with col2:
    interests = st.multiselect(
        "🎯 Your Interests",
        ["Culture & History", "Nature & Outdoors", "Food & Drink",
         "Shopping", "City Highlights", "Museums",
         "Relaxation & Wellness", "Adventure & Activities"],
        default=st.session_state.user_inputs["interests"],
    )

st.markdown("---")

if not ollama_available(st.session_state.ollama_model):
    st.warning(
        f"⚠️ Ollama is not running or model "
        f"**{st.session_state.ollama_model}** is not pulled.\n\n"
        "Run:\n"
        "`ollama serve`\n"
        "`ollama pull llama3`"
    )

if st.button("✨ Generate AI Itinerary with Ollama",
             use_container_width=True,
             type="primary"):

    # Save user inputs into session state
    st.session_state.user_inputs = {
        "destination": destination,
        "days": days,
        "interests": interests
    }

    st.session_state.workflow_stage = "generating"
    st.rerun()


# ----------------------------
# Workflow Logic
# ----------------------------

if st.session_state.workflow_stage == "generating":
    with st.spinner("Generating your itinerary..."):
        st.session_state.itinerary = generate_itinerary(
            st.session_state.user_inputs["destination"],
            st.session_state.user_inputs["days"],
            st.session_state.user_inputs["interests"]
        )

    st.session_state.workflow_stage = "complete"
    st.rerun()


if st.session_state.workflow_stage == "complete":
    st.markdown("## 🧳 Your AI Travel Plan")
    st.write(st.session_state.itinerary)

    if st.button("🔄 Plan Another Trip"):
        st.session_state.workflow_stage = "input"
        st.session_state.itinerary = ""
        st.rerun()