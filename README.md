# 📘 LMS App – Streamlit + YouTube + Certificate

A micro-learning LMS platform using **Streamlit** where students:

- Log in using Registration Number
- Watch an assigned YouTube video
- Mark it as watched
- Automatically download a personalized certificate

## 🔒 Security
Student details are stored in an **AES-encrypted Excel file** (`.aes`), which is decrypted at runtime using a password.

## 📁 Files

- `app.py` – Main Streamlit application
- `progress.csv` – Stores student completion records
- `requirements.txt` – All required Python packages

## 🚀 How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
