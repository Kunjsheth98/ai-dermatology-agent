import streamlit as st
import sqlite3
import uuid
import os
import random
from PIL import Image
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ================== CONFIG ==================
MOCK_MODE = True
IMAGE_DIR = "stored_images"
DB_PATH = "ai_dermatology.db"
PDF_DIR = "reports"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

st.set_page_config(page_title="AI Dermatology Agent", layout="centered")
st.title("AI Dermatology Agent")
st.caption("AI-powered skin insights. This is not medical advice.")

# ================== DATABASE ==================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS chat (
    user_id TEXT,
    role TEXT,
    message TEXT,
    time TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS cases (
    user_id TEXT,
    created_at TEXT,
    skin_type TEXT,
    issues TEXT,
    confidence INTEGER
)
""")

conn.commit()

# ================== USER ID ==================
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

# ================== CHAT MEMORY ==================
if "chat_messages" not in st.session_state:
    c.execute(
        "SELECT role, message, time FROM chat WHERE user_id=?",
        (user_id,)
    )
    rows = c.fetchall()

    if rows:
        st.session_state.chat_messages = [
            {"role": r[0], "content": r[1], "time": r[2]} for r in rows
        ]
    else:
        welcome = {
            "role": "assistant",
            "content": (
                "Hi 👋 I’m your AI Dermatology Assistant.\n\n"
                "You can ask skin or hair questions, "
                "or upload a face photo for deeper analysis."
            ),
            "time": datetime.now().strftime("%H:%M")
        }
        st.session_state.chat_messages = [welcome]
        c.execute(
            "INSERT INTO chat VALUES (?,?,?,?)",
            (user_id, "assistant", welcome["content"], welcome["time"])
        )
        conn.commit()

# ================== CHAT DISPLAY ==================
st.subheader("Chat")

for msg in st.session_state.chat_messages:
    label = "You" if msg["role"] == "user" else "AI"
    st.markdown(f"**{label} ({msg['time']}):** {msg['content']}")

# ================== CHAT INPUT ==================
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message")
    submitted = st.form_submit_button("Send")

if submitted and user_input.strip():
    time_now = datetime.now().strftime("%H:%M")

    user_msg = {
        "role": "user",
        "content": user_input,
        "time": time_now
    }
    st.session_state.chat_messages.append(user_msg)
    c.execute(
        "INSERT INTO chat VALUES (?,?,?,?)",
        (user_id, "user", user_input, time_now)
    )

    ai_reply = (
        "Thanks for sharing. I can help only with skin, hair, or scalp concerns. "
        "You can also upload a face photo for deeper analysis."
    )

    ai_msg = {
        "role": "assistant",
        "content": ai_reply,
        "time": time_now
    }
    st.session_state.chat_messages.append(ai_msg)
    c.execute(
        "INSERT INTO chat VALUES (?,?,?,?)",
        (user_id, "assistant", ai_reply, time_now)
    )

    conn.commit()

# ================== IMAGE UPLOAD ==================
uploaded = st.file_uploader(
    "Upload a clear face photo (natural light, no filters)",
    type=["jpg", "jpeg", "png"]
)

def analyze_mock():
    return (
        random.choice(["Oily", "Dry", "Combination", "Normal", "Sensitive"]),
        random.sample(
            ["Mild acne", "Pigmentation", "Redness", "Uneven tone", "Dry patches"], 2
        ),
        random.randint(65, 85)
    )

analysis_result = None
previous_case = None

if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="Uploaded Image", width=400)

    skin, issues, confidence = analyze_mock()
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute(
        "SELECT created_at, skin_type, issues FROM cases WHERE user_id=? ORDER BY created_at ASC",
        (user_id,)
    )
    history = c.fetchall()

    if history:
        previous_case = history[0]

    c.execute(
        "INSERT INTO cases VALUES (?,?,?,?,?)",
        (user_id, today, skin, ", ".join(issues), confidence)
    )
    conn.commit()

    analysis_result = (skin, issues, confidence)

# ================== DISPLAY ==================
if analysis_result:
    skin, issues, confidence = analysis_result

    st.subheader("Skin Analysis")
    st.write(f"**Skin Type:** {skin}")
    st.write(f"**Issues:** {', '.join(issues)}")
    st.write(f"**Confidence:** {confidence}%")

    if previous_case:
        st.subheader("Progress Comparison")
        st.write(f"Earlier skin type: {previous_case[1]}")
        st.write(f"Earlier issues: {previous_case[2]}")

# ================== PDF ==================
def generate_pdf():
    path = os.path.join(PDF_DIR, f"{user_id}.pdf")
    cpdf = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    cpdf.setFont("Helvetica", 12)
    cpdf.drawString(40, h - 40, "AI Dermatology Report")
    cpdf.drawString(40, h - 80, f"Skin Type: {skin}")
    cpdf.drawString(40, h - 110, f"Issues: {', '.join(issues)}")
    cpdf.drawString(40, h - 140, f"Confidence: {confidence}%")

    if previous_case:
        cpdf.drawString(40, h - 180, "Progress Summary:")
        cpdf.drawString(40, h - 210, f"Earlier Issues: {previous_case[2]}")

    cpdf.drawString(40, h - 260, "Disclaimer: Not medical advice.")
    cpdf.save()
    return path

if analysis_result and st.button("Generate PDF Report"):
    pdf = generate_pdf()
    with open(pdf, "rb") as f:
        st.download_button("Download Report", f, file_name="skin_report.pdf")
