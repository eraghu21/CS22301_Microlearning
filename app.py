import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import io
import base64
from datetime import datetime
from fpdf import FPDF

# =================== CONFIG ===================
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

try:
    AES_FILE = st.secrets["aes"]["file"]
    AES_PASSWORD = st.secrets["aes"]["password"]
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
except Exception as e:
    st.error("Missing secrets: Please configure [aes] and [admin] in Streamlit secrets.")
    st.stop()

VIDEO_URL = st.secrets.get("video", {}).get("url", "https://www.youtube.com/watch?v=eLxQMPkDmAo")
VIDEO_DURATION = int(st.secrets.get("video", {}).get("duration", 600))  # seconds
SUBJECT = st.secrets.get("video", {}).get("subject", "CS22301 Microlearning")
CERT_IMAGE = st.secrets.get("certificate", {}).get("image_path", None)  # optional certificate background image path

# =================== DECRYPT & LOAD STUDENT FILE ===================
def load_student_file():
    try:
        if not os.path.exists(AES_FILE):
            st.error(f"Encrypted file not found: {AES_FILE}")
            return None

        decrypted_bytes = io.BytesIO()
        with open(AES_FILE, "rb") as f_in:
            pyAesCrypt.decryptStream(f_in, decrypted_bytes, AES_PASSWORD, BUFFER_SIZE)
        
        decrypted_bytes.seek(0)
        df = pd.read_excel(decrypted_bytes)

        if df.empty:
            st.error("Decrypted file is empty. Check AES password.")
            return None

        st.success("✅ Student list loaded successfully.")
        return df
    except Exception as e:
        st.error(f"❌ Failed to decrypt student file: {e}")
        return None

# =================== FIND STUDENT ===================
def find_student(df, reg_no):
    reg_no = str(reg_no).strip().lower()
    for col in df.columns:
        series = df[col].astype(str).str.strip().str.lower()
        match = df[series == reg_no]
        if not match.empty:
            return match.iloc[0].to_dict()
    return None

# =================== CERTIFICATE GENERATION ===================
def create_certificate(name, reg_no, subject):
    pdf = FPDF("L", "mm", "A4")
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # Add background image if provided
    if CERT_IMAGE and os.path.exists(CERT_IMAGE):
        pdf.image(CERT_IMAGE, x=0, y=0, w=297, h=210)  # A4 landscape

    # Overlay text
    pdf.set_font("Arial", "B", 30)
    pdf.set_y(40)
    pdf.cell(0, 10, "Certificate of Completion", align="C", ln=1)

    pdf.set_font("Arial", "", 18)
    pdf.cell(0, 10, "This certifies that", align="C", ln=1)

    pdf.set_font("Arial", "B", 26)
    pdf.cell(0, 15, name, align="C", ln=1)

    pdf.set_font("Arial", "", 16)
    pdf.cell(0, 10, f"Reg. No: {reg_no}", align="C", ln=1)
    pdf.ln(5)
    pdf.multi_cell(0, 10,
        f"has successfully completed the microlearning session on '{subject}' "
        f"on {datetime.now().strftime('%d-%m-%Y')}.",
        align="C")
    pdf.ln(15)
    pdf.set_font("Arial", "", 14)
    pdf.cell(0, 10, "Authorized by: Course Coordinator", align="R")

    filename = f"{reg_no}_{subject.replace(' ', '_')}.pdf"
    path = os.path.join(CERT_DIR, filename)
    pdf.output(path)
    return path

def get_pdf_download_link(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    name = os.path.basename(path)
    return f'<a href="data:application/pdf;base64,{b64}" download="{name}">📥 Download Certificate</a>'

# =================== MAIN APP ===================
st.set_page_config(page_title="CS22301 Microlearning", layout="centered")
st.title("🎓 CS22301 Microlearning Portal")

# Load student file once
if "df" not in st.session_state:
    st.session_state.df = load_student_file()

df = st.session_state.df
if df is None:
    st.stop()

# ----------------- LOGIN -----------------
reg_no = st.text_input("Enter your Registration Number")
if st.button("Login") and reg_no:
    student = find_student(df, reg_no)
    if student is None:
        st.error("Registration number not found in the student list.")
    else:
        st.session_state.student = student
        st.session_state.login_time = datetime.now()
        st.session_state.timer_started = True
        st.session_state.video_done = False
        st.session_state.certificate_ready = False
        st.success(f"Welcome, {student.get('Name', 'Student')}!")

# ----------------- VIDEO + TIMER + WATCHED BUTTON -----------------
if st.session_state.get("timer_started", False):
    student = st.session_state.student
    name = student.get("Name", "Student")
    reg = student.get("Reg_No", reg_no)

    st.subheader(f"Subject: {SUBJECT}")

    # Timer on top
    if "video_done" not in st.session_state:
        st.session_state.video_done = False

    elapsed = (datetime.now() - st.session_state.login_time).total_seconds()
    remaining = VIDEO_DURATION - elapsed

    if remaining > 0:
        st.info(f"⏱ Time remaining: {int(remaining)} seconds. Please keep watching...")
        st.progress(int((elapsed / VIDEO_DURATION) * 100))
    else:
        st.session_state.video_done = True
        st.success("✅ Video time completed!")

    # Video embed
    embed_url = VIDEO_URL.replace("watch?v=", "embed/")
    st.video(embed_url)

    # "I have watched the video" button always visible
    if "certificate_ready" not in st.session_state:
        st.session_state.certificate_ready = False

    if st.button("🎥 I have watched the video"):
        if st.session_state.video_done:
            path = create_certificate(student.get("Name", "Student"), reg, SUBJECT)
            st.session_state.certificate_path = path
            st.session_state.certificate_ready = True
            st.success("✅ Certificate generated successfully!")
        else:
            st.warning(f"⏱ You need to finish watching the video before downloading the certificate. Remaining: {int(remaining)} sec")

    # Download link below button
    if st.session_state.certificate_ready:
        st.markdown(get_pdf_download_link(st.session_state.certificate_path), unsafe_allow_html=True)

# ----------------- ADMIN -----------------
st.markdown("---")
if st.checkbox("Admin Login"):
    pw = st.text_input("Password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Admin access granted.")
        if st.button("Reload Student File"):
            st.session_state.df = load_student_file()
