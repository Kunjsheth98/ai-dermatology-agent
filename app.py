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
    date TEXT,
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
    c.execute("SELECT role, message, time FROM chat WHERE user_id=?", (user_id,))
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
                "You can ask skin or hair questions, or upload a face photo."
            ),
            "time": datetime.now().strftime("%H:%M")
        }
        st.session_state.chat_messages = [welcome]
        c.execute("INSERT INTO chat VALUES (?,?,?,?)",
                  (user_id, "assistant", welcome["content"], welcome["time"]))
        conn.commit()

# ================== CHAT DISPLAY ==================
st.subheader("Chat")

for msg in st.session_state.chat_messages:
    label = "You" if msg["role"] == "user" else "AI"
    st.markdown(f"**{label} ({msg['time']}):** {msg['content']}")

# ================== CHAT INPUT ==================
user_input = st.text_input("Type your message and press Enter")

if user_input:
    t = datetime.now().strftime("%H:%M")
    user_msg = {"role": "user", "content": user_input, "time": t}
    st.session_state.chat_messages.append(user_msg)
    c.execute("INSERT INTO chat VALUES (?,?,?,?)",
              (user_id, "user", user_input, t))

    ai_reply = (
        "Thanks for sharing. I can help only with skin, hair, or scalp concerns. "
        "You may upload a face photo for deeper analysis."
    )

    ai_msg = {"role": "assistant", "content": ai_reply, "time": t}
    st.session_state.chat_messages.append(ai_msg)
    c.execute("INSERT INTO chat VALUES (?,?,?,?)",
              (user_id, "assistant", ai_reply, t))
    conn.commit()
    st.rerun()

# ================== IMAGE UPLOAD ==================
uploaded = st.file_uploader(
    "Upload a clear face photo (natural light, no filters)",
    type=["jpg", "jpeg", "png"]
)

def analyze_mock():
    skin = random.choice(["Oily", "Dry", "Combination", "Normal", "Sensitive"])
    issues = random.sample(
        ["Mild acne", "Pigmentation", "Redness", "Uneven tone", "Dry patches"], 2
    )
    confidence = random.randint(65, 85)
    return skin, issues, confidence

# ================== MAIN ANALYSIS ==================
analysis_result = None
previous_case = None

if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="Uploaded Image", use_column_width=True)

    skin, issues, confidence = analyze_mock()
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute(
        "SELECT date, skin_type, issues, confidence FROM cases WHERE user_id=? ORDER BY date ASC",
        (user_id,)
    )
    history = c.fetchall()

    if history:
        previous_case = history[0]

    c.execute("INSERT INTO cases VALUES (?,?,?,?,?)",
              (user_id, today, skin, ", ".join(issues), confidence))
    conn.commit()

    analysis_result = (skin, issues, confidence)

# ================== DISPLAY RESULT ==================
if analysis_result:
    skin, issues, confidence = analysis_result

    st.subheader("Skin Analysis")
    st.write(f"**Skin Type:** {skin}")
    st.write(f"**Issues:** {', '.join(issues)}")
    st.write(f"**Confidence:** {confidence}%")

    if previous_case:
        st.subheader("Progress Comparison")
        st.write(f"Previous Skin Type: {previous_case[1]}")
        st.write(f"Previous Issues: {previous_case[2]}")
        st.write(
            "Compared to your earlier record, your skin condition has changed."
        )

# ================== PDF GENERATION ==================
def generate_pdf():
    file_path = os.path.join(PDF_DIR, f"{user_id}.pdf")
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica", 12)
    c.drawString(40, height - 40, "AI Dermatology Report")
    c.drawString(40, height - 80, f"Skin Type: {skin}")
    c.drawString(40, height - 110, f"Issues: {', '.join(issues)}")
    c.drawString(40, height - 140, f"Confidence: {confidence}%")

    if previous_case:
        c.drawString(40, height - 180, "Progress Summary:")
        c.drawString(40, height - 210, f"Earlier Issues: {previous_case[2]}")

    c.drawString(40, height - 260, "Disclaimer: This is not medical advice.")
    c.save()
    return file_path

if analysis_result:
    if st.button("Generate PDF Report"):
        pdf_path = generate_pdf()
        with open(pdf_path, "rb") as f:
            st.download_button("Download Report", f, file_name="skin_report.pdf")
