# MOCK MODE FINAL VERSION – FORCE COMMIT

import streamlit as st
import sqlite3
import uuid
import io
import os
import random
from PIL import Image

# ================= CONFIG =================
MOCK_MODE = True              # 🔴 Change to False when billing works
ENABLE_SECOND_BRAIN = True
STORE_IMAGES = True

IMAGE_DIR = "stored_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

st.set_page_config(page_title="AI Dermatology Agent", layout="centered")
st.title("AI Dermatology Agent")
st.caption("AI-powered skin analysis. Not medical advice.")

# ================= DATABASE =================
conn = sqlite3.connect("ai_dermatology.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS cases (
    session_id TEXT,
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

# ================= IMAGE STORAGE =================
def save_image(image, session_id):
    path = f"{IMAGE_DIR}/{session_id}.jpg"
    image.save(path)
    return path

# ================= AI BRAINS (MOCK) =================
def brain_openai_mock():
    return {
        "skin_type": random.choice(["Oily", "Dry", "Combination", "Normal", "Sensitive"]),
        "issues": random.sample(
            ["Mild acne", "Open pores", "Pigmentation", "Uneven tone", "Dullness"],
            k=2
        ),
        "confidence": random.randint(65, 85),
        "doctor_flag": 0,
        "notes": "Primary AI analysis based on visible skin features."
    }

def brain_gemini_mock():
    return {
        "skin_type": random.choice(["Oily", "Combination", "Normal"]),
        "issues": random.sample(
            ["Oil imbalance", "Texture irregularity", "Redness", "Dry patches"],
            k=2
        ),
        "confidence": random.randint(60, 80),
        "doctor_flag": 0,
        "notes": "Secondary AI analysis for cross-verification."
    }

# ================= CONSENSUS ENGINE =================
def consensus(brain_a, brain_b):
    same_skin = brain_a["skin_type"] == brain_b["skin_type"]
    avg_conf = int((brain_a["confidence"] + brain_b["confidence"]) / 2)

    issues = list(set(brain_a["issues"] + brain_b["issues"]))
    doctor_flag = 1 if (brain_a["doctor_flag"] or brain_b["doctor_flag"]) else 0

    if not same_skin:
        avg_conf -= 10

    return {
        "skin_type": brain_a["skin_type"] if same_skin else "Uncertain",
        "issues": issues,
        "confidence": max(avg_conf, 50),
        "doctor_flag": doctor_flag,
        "notes": "Consensus result from multiple AI models."
    }

# ================= UI =================
consent = st.checkbox(
    "I agree that my image may be stored anonymously to improve the AI. "
    "This is not medical advice."
)

uploaded = st.file_uploader(
    "Upload a clear, front-facing face photo (no filters, natural light)",
    type=["jpg", "jpeg", "png"]
)

# ================= MAIN FLOW =================
if consent and uploaded:
    session_id = str(uuid.uuid4())
    image = Image.open(uploaded).convert("RGB")

    st.image(image, caption="Uploaded Image", use_column_width=True)
    st.info("Analyzing skin...")

    if STORE_IMAGES:
        image_path = save_image(image, session_id)
        c.execute("INSERT INTO images VALUES (?,?)", (session_id, image_path))
        conn.commit()

    # -------- AI LOGIC --------
    if MOCK_MODE:
        brain_a = brain_openai_mock()

        if ENABLE_SECOND_BRAIN:
            brain_b = brain_gemini_mock()
            final = consensus(brain_a, brain_b)
            brain_used = "openai + gemini"
        else:
            final = brain_a
            brain_used = "openai"
    else:
        final = {}  # 🔥 Real AI will replace this later
        brain_used = "live"

    # -------- DISPLAY --------
    st.subheader("AI Skin Analysis")
    st.json(final)

    if final["doctor_flag"] == 1:
        st.warning("We recommend consulting a dermatologist for further evaluation.")

    # -------- STORE CASE --------
    c.execute(
        "INSERT INTO cases VALUES (?,?,?,?,?,?,?)",
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

    # -------- FEEDBACK --------
    feedback = st.radio("Did this analysis help you?", ["", "Yes", "No"])
    if feedback:
        c.execute(
            "INSERT INTO feedback VALUES (?,?)",
            (session_id, feedback)
        )
        conn.commit()
        st.success("Thank you. This helps the AI learn.")
