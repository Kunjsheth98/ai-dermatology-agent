import streamlit as st
import sqlite3
import uuid
import os
import random
from PIL import Image
from datetime import datetime

# ================== CONFIG ==================
MOCK_MODE = True            # 🔴 Set False when OpenAI/Gemini billing works
STORE_IMAGES = True

IMAGE_DIR = "stored_images"
DB_PATH = "ai_dermatology.db"

os.makedirs(IMAGE_DIR, exist_ok=True)

st.set_page_config(page_title="AI Dermatology Agent", layout="centered")
st.title("AI Dermatology Agent")
st.caption("AI-powered skin insights. This is NOT medical advice.")

# ================== SESSION ==================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "chat" not in st.session_state:
    st.session_state.chat = [
        {
            "role": "assistant",
            "content": (
                "Hi 👋 I’m your AI Dermatology Assistant.\n\n"
                "You can:\n"
                "• Ask skin or hair questions\n"
                "• Upload a clear face photo for deeper analysis"
            )
        }
    ]

if "followup_step" not in st.session_state:
    st.session_state.followup_step = 0

# ================== DATABASE ==================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS cases (
    session_id TEXT,
    created_at TEXT,
    skin_type TEXT,
    issues TEXT,
    confidence INTEGER,
    notes TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS images (
    session_id TEXT,
    image_path TEXT
)
""")

conn.commit()

# ================== HELPERS ==================
def save_image(image, session_id):
    path = os.path.join(IMAGE_DIR, f"{session_id}.jpg")
    image.save(path)
    return path

def is_valid_face_image(image: Image.Image) -> bool:
    # 🚨 STRICT VALIDATION GATE (MOCK VERSION)
    width, height = image.size
    if width < 200 or height < 200:
        return False
    return True

# ================== MOCK AI BRAINS ==================
def mock_analysis():
    return {
        "skin_type": random.choice(["Oily", "Dry", "Combination", "Normal", "Sensitive"]),
        "issues": random.sample(
            ["Acne tendency", "Pigmentation", "Redness", "Uneven texture", "Dry patches"],
            k=2
        ),
        "confidence": random.randint(70, 88),
        "notes": "Visual skin pattern analysis based on image + responses."
    }

def generate_routine(skin_type, issues):
    routine = {
        "Morning": [
            "Cleanse gently with lukewarm water",
            "Use a mild non-foaming cleanser",
            "Apply lightweight hydration",
            "Apply broad-spectrum sun protection"
        ],
        "Night": [
            "Cleanse to remove oil and dirt",
            "Use calming hydration",
            "Apply barrier-repair moisturizer"
        ],
        "Weekly": [
            "Gentle exfoliation once or twice weekly",
            "Use a soothing mask if skin feels stressed"
        ],
        "Avoid": [
            "Harsh scrubs",
            "Over-washing",
            "Picking or touching skin frequently"
        ]
    }

    if "Acne tendency" in issues:
        routine["Night"].append("Focus on keeping pores unclogged")

    if "Dry patches" in issues:
        routine["Morning"].append("Prioritize deeper hydration")
        routine["Night"].append("Use richer moisturizer")

    if skin_type == "Oily":
        routine["Avoid"].append("Heavy or greasy products")

    return routine

# ================== CHAT DISPLAY ==================
st.subheader("Chat")

for msg in st.session_state.chat:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**AI:** {msg['content']}")

# ================== CHAT INPUT ==================
user_input = st.text_input("Type your message and press Enter")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})

    # Follow-up questioning logic
    if st.session_state.followup_step == 0:
        reply = "Thanks. Do you experience oiliness or dryness more often?"
        st.session_state.followup_step = 1
    elif st.session_state.followup_step == 1:
        reply = "Got it. Any frequent breakouts, redness, or pigmentation?"
        st.session_state.followup_step = 2
    elif st.session_state.followup_step == 2:
        reply = "Thanks. You can now upload a clear front-facing face photo for full analysis."
        st.session_state.followup_step = 3
    else:
        reply = "I’m ready when you upload a photo."

    st.session_state.chat.append({"role": "assistant", "content": reply})
    st.rerun()

# ================== IMAGE UPLOAD ==================
uploaded = st.file_uploader(
    "Upload a clear, front-facing face photo (real person, natural light)",
    type=["jpg", "jpeg", "png"]
)

# ================== MAIN ANALYSIS ==================
if uploaded:
    image = Image.open(uploaded).convert("RGB")

    if not is_valid_face_image(image):
        st.error(
            "❌ This does not appear to be a clear real human face.\n\n"
            "Please upload a clear, front-facing photo of a real person in natural light."
        )
        st.stop()

    st.image(image, caption="Uploaded Image", width=300)
    st.info("Analyzing skin…")

    if STORE_IMAGES:
        path = save_image(image, st.session_state.session_id)
        c.execute("INSERT INTO images VALUES (?,?)", (st.session_state.session_id, path))
        conn.commit()

    # AI ANALYSIS
    final = mock_analysis() if MOCK_MODE else mock_analysis()

    routine = generate_routine(final["skin_type"], final["issues"])

    # STORE CASE
    c.execute(
        "INSERT INTO cases VALUES (?,?,?,?,?,?)",
        (
            st.session_state.session_id,
            datetime.now().isoformat(),
            final["skin_type"],
            ", ".join(final["issues"]),
            final["confidence"],
            final["notes"]
        )
    )
    conn.commit()

    # DISPLAY RESULTS
    st.subheader("Skin Analysis")
    st.write(f"**Skin Type:** {final['skin_type']}")
    st.write(f"**Key Observations:** {', '.join(final['issues'])}")
    st.write(f"**Confidence:** {final['confidence']}%")
    st.caption(final["notes"])

    st.subheader("Personalized Skincare Routine")
    for section, steps in routine.items():
        st.markdown(f"**{section}**")
        for step in steps:
            st.markdown(f"- {step}")

    st.success("Analysis complete. You may return anytime for comparison.")
