import streamlit as st
import sqlite3
import uuid
import os
import random
from PIL import Image
from datetime import datetime
import cv2
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ================== CONFIG ==================
MOCK_MODE = True   # change to False when OpenAI/Gemini live
IMAGE_DIR = "stored_images"
DB_PATH = "ai_dermatology.db"
PDF_DIR = "reports"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

st.set_page_config(page_title="AI Dermatology Agent", layout="centered")
st.title("AI Dermatology Agent")
st.caption("AI-powered skin analysis. Not medical advice.")

# ================== DATABASE ==================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS cases (
    session_id TEXT PRIMARY KEY,
    created_at TEXT,
    skin_type TEXT,
    issues TEXT,
    confidence INTEGER
)
""")
conn.commit()

# ================== FACE CHECK ==================
def is_real_face(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return len(faces) == 1

# ================== CHAT MEMORY ==================
if "chat" not in st.session_state:
    st.session_state.chat = [
        {
            "role": "assistant",
            "text": "Hi 👋 I’m your AI Dermatology Assistant. Upload a **real, clear face photo** or ask skin-related questions."
        }
    ]

def show_chat():
    for m in st.session_state.chat:
        if m["role"] == "user":
            st.markdown(f"**You:** {m['text']}")
        else:
            st.markdown(f"**AI:** {m['text']}")

show_chat()

user_msg = st.text_input("Ask a skin-related question")

if user_msg:
    st.session_state.chat.append({"role": "user", "text": user_msg})
    st.session_state.chat.append({
        "role": "assistant",
        "text": "Thanks! Upload a face photo for visual analysis, or continue asking skin-related questions."
    })
    st.rerun()

# ================== IMAGE UPLOAD ==================
uploaded = st.file_uploader(
    "Upload a clear, front-facing **REAL PERSON** face photo",
    type=["jpg", "jpeg", "png"]
)

# ================== MOCK ANALYSIS ==================
def analyze_skin_mock():
    skin_type = random.choice(["Oily", "Dry", "Combination", "Normal"])
    issues = random.sample(
        ["Acne-prone", "Pigmentation", "Redness", "Uneven texture", "Dehydration"], 3
    )
    confidence = random.randint(70, 88)
    return skin_type, issues, confidence

def generate_routine(skin_type, issues):
    routine = {
        "Morning": [
            "Cleanse gently with a mild cleanser",
            "Apply hydrating layer while skin is damp",
            "Use sunscreen (SPF 30+), even indoors"
        ],
        "Night": [
            "Cleanse to remove oil and pollution",
            "Apply calming hydration",
            "Use barrier-repair moisturizer"
        ],
        "Weekly": [
            "Gentle exfoliation once or twice weekly",
            "Soothing mask if skin feels stressed"
        ],
        "Avoid": [
            "Harsh scrubs",
            "Over-washing",
            "Picking or touching skin frequently"
        ]
    }

    if "Acne-prone" in issues:
        routine["Night"].append("Keep pores unclogged, avoid heavy products")

    if "Dehydration" in issues:
        routine["Morning"].append("Layer hydration, avoid stripping cleansers")

    if skin_type == "Oily":
        routine["Avoid"].append("Greasy or heavy products")

    return routine

# ================== PDF ==================
def generate_pdf(session_id, skin_type, issues, routine):
    path = os.path.join(PDF_DIR, f"{session_id}.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    text = c.beginText(40, 800)

    text.textLine("AI Dermatology Report")
    text.textLine("")
    text.textLine(f"Skin Type: {skin_type}")
    text.textLine(f"Issues: {', '.join(issues)}")
    text.textLine("")

    for section, steps in routine.items():
        text.textLine(section)
        for s in steps:
            text.textLine(f"- {s}")
        text.textLine("")

    c.drawText(text)
    c.save()
    return path

# ================== MAIN FLOW ==================
if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="Uploaded image")

    if not is_real_face(image):
        st.error("❌ This does not appear to be a real, clear human face. Please upload a proper face photo.")
    else:
        st.info("Analyzing skin…")

        session_id = str(uuid.uuid4())

        skin_type, issues, confidence = analyze_skin_mock()

        c.execute(
            "INSERT INTO cases VALUES (?,?,?,?,?)",
            (
                session_id,
                datetime.now().isoformat(),
                skin_type,
                ", ".join(issues),
                confidence
            )
        )
        conn.commit()

        routine = generate_routine(skin_type, issues)

        # ===== DISPLAY =====
        st.subheader("Skin Analysis")
        st.write(f"**Skin Type:** {skin_type}")
        st.write(f"**Key Issues:** {', '.join(issues)}")
        st.write(f"**Confidence:** {confidence}%")

        st.subheader("Personalized Routine")
        for k, v in routine.items():
            st.markdown(f"**{k}**")
            for i in v:
                st.markdown(f"- {i}")

        st.subheader("Quick Questions")
        st.markdown("- Do you experience breakouts frequently?")
        st.markdown("- Does your skin feel tight after washing?")
        st.markdown("- Any recent changes in skincare or lifestyle?")

        if st.button("Generate PDF Report"):
            pdf_path = generate_pdf(session_id, skin_type, issues, routine)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download Report",
                    f,
                    file_name="skin_report.pdf"
                )

        st.success("Analysis complete. You may return anytime for comparison.")
