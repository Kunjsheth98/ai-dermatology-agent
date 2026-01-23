import streamlit as st
import sqlite3
import uuid
import os
import random
from PIL import Image

# ================== CONFIG ==================
MOCK_MODE = True              # 🔴 CHANGE TO False WHEN CARD WORKS
ENABLE_SECOND_BRAIN = True
STORE_IMAGES = True

IMAGE_DIR = "stored_images"
DB_PATH = "ai_dermatology.db"

os.makedirs(IMAGE_DIR, exist_ok=True)

st.set_page_config(page_title="AI Dermatology Agent", layout="centered")
st.title("AI Dermatology Agent")
st.caption("AI-powered skin insights. This is not medical advice.")

# ================== DATABASE ==================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS cases (
    session_id TEXT PRIMARY KEY,
    skin_type TEXT,
    issues TEXT,
    confidence INTEGER,
    doctor_flag INTEGER,
    brain_used TEXT,
    notes TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    session_id TEXT,
    helpful TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS images (
    session_id TEXT,
    image_path TEXT
)
""")

conn.commit()

# ================== IMAGE STORAGE ==================
def save_image(image, session_id):
    path = os.path.join(IMAGE_DIR, f"{session_id}.jpg")
    image.save(path)
    return path

# ================== BRAIN 1 (OPENAI MOCK) ==================
def brain_openai_mock():
    return {
        "skin_type": random.choice(["Oily", "Dry", "Combination", "Normal", "Sensitive"]),
        "issues": random.sample(
            ["Mild acne", "Open pores", "Pigmentation", "Uneven tone", "Dullness"],
            k=2
        ),
        "confidence": random.randint(65, 85),
        "doctor_flag": 0,
        "notes": "Primary AI visual analysis."
    }

# ================== BRAIN 2 (GEMINI MOCK) ==================
def brain_gemini_mock():
    return {
        "skin_type": random.choice(["Oily", "Combination", "Normal"]),
        "issues": random.sample(
            ["Oil imbalance", "Texture irregularity", "Redness", "Dry patches"],
            k=2
        ),
        "confidence": random.randint(60, 80),
        "doctor_flag": 0,
        "notes": "Secondary AI cross-check analysis."
    }

# ================== CONSENSUS ENGINE ==================
def consensus(a, b):
    same_skin = a["skin_type"] == b["skin_type"]
    avg_conf = int((a["confidence"] + b["confidence"]) / 2)
    issues = list(set(a["issues"] + b["issues"]))
    doctor_flag = 1 if (a["doctor_flag"] or b["doctor_flag"]) else 0

    if not same_skin:
        avg_conf -= 10

    return {
        "skin_type": a["skin_type"] if same_skin else "Uncertain",
        "issues": issues,
        "confidence": max(avg_conf, 50),
        "doctor_flag": doctor_flag,
        "notes": "Consensus from multiple AI models."
    }

# ================== ROUTINE ENGINE ==================
def generate_routine(skin_type, issues):
    routine = {
        "Morning": [
            "Cleanse face gently with lukewarm water",
            "Use a mild, non-stripping cleanser",
            "Apply lightweight hydration",
            "Apply broad-spectrum sun protection",
        ],
        "Night": [
            "Cleanse face to remove dirt and oil",
            "Apply calming hydration",
            "Use barrier-repair moisturizer",
        ],
        "Weekly": [
            "Exfoliate gently once or twice a week",
            "Use a soothing mask if skin feels irritated",
        ],
        "Avoid": [
            "Over-washing the face",
            "Harsh scrubs or strong chemicals",
            "Touching or picking skin frequently",
        ]
    }

    if "Mild acne" in issues:
        routine["Night"].append("Focus on keeping pores clean and unclogged")

    if "Dry patches" in issues:
        routine["Morning"].append("Prioritize deep hydration")
        routine["Night"].append("Apply richer moisturizer")

    if skin_type == "Oily":
        routine["Avoid"].append("Heavy or greasy products")

    return routine

# ================== UI ==================
consent = st.checkbox(
    "I agree my image may be stored anonymously to improve the AI. This is not medical advice."
)

uploaded = st.file_uploader(
    "Upload a clear, front-facing face photo (natural light, no filters)",
    type=["jpg", "jpeg", "png"]
)

# ================== MAIN FLOW ==================
if consent and uploaded:
    session_id = str(uuid.uuid4())
    image = Image.open(uploaded).convert("RGB")

    st.image(image, caption="Uploaded Image", use_column_width=True)
    st.info("Analyzing skin…")

    if STORE_IMAGES:
        image_path = save_image(image, session_id)
        c.execute("INSERT OR IGNORE INTO images VALUES (?,?)", (session_id, image_path))
        conn.commit()

    # ---------- AI LOGIC ----------
    if MOCK_MODE:
        a = brain_openai_mock()
        if ENABLE_SECOND_BRAIN:
            b = brain_gemini_mock()
            final = consensus(a, b)
            brain_used = "openai + gemini (mock)"
        else:
            final = a
            brain_used = "openai (mock)"
    else:
        # 🔥 LIVE MODE (WILL BE FILLED LATER)
        final = {
            "skin_type": "Pending",
            "issues": [],
            "confidence": 0,
            "doctor_flag": 0,
            "notes": "Live AI mode enabled."
        }
        brain_used = "live"

    # ---------- ROUTINE ----------
    routine = generate_routine(final["skin_type"], final["issues"])

    # ---------- DISPLAY ----------
    st.subheader("AI Skin Analysis")
    st.write(f"**Skin Type:** {final['skin_type']}")
    st.write(f"**Issues:** {', '.join(final['issues']) if final['issues'] else 'None'}")
    st.write(f"**Confidence:** {final['confidence']}%")

    if final["doctor_flag"]:
        st.warning("Consider consulting a dermatologist for further evaluation.")

    st.caption(final["notes"])

    st.subheader("Personalized Skincare Routine")
    for section, steps in routine.items():
        st.markdown(f"**{section}**")
        for step in steps:
            st.markdown(f"- {step}")

    # ---------- STORE CASE ----------
    c.execute(
        "INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?)",
        (
            session_id,
            final["skin_type"],
            ", ".join(final["issues"]),
            final["confidence"],
            final["doctor_flag"],
            brain_used,
            final["notes"]
        )
    )
    conn.commit()

    # ---------- FEEDBACK ----------
    feedback = st.radio("Did this help you?", ["", "Yes", "No"])
    if feedback:
        c.execute("INSERT INTO feedback VALUES (?,?)", (session_id, feedback))
        conn.commit()
        st.success("Thanks. This helps the AI learn.")
