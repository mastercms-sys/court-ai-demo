import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import tempfile
import os

# پیج کی سیٹنگ
st.set_page_config(page_title="Court Dictation AI", page_icon="⚖️", layout="centered")
st.title("⚖️ Auto Court Dictation Pro")
st.write("اپنی ڈکٹیشن آڈیو اپلوڈ کریں اور پروفیشنل Word فائل حاصل کریں۔ (Zero Storage Policy: آپ کا ڈیٹا کہیں محفوظ نہیں ہوتا)")

# 1. پروفیشنل طریقہ: API Key کو خفیہ خانے (Streamlit Secrets) سے خود بخود لانا
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ ایپ کے بیک اینڈ پر API Key موجود نہیں ہے۔ براہ کرم ایڈمن سے رابطہ کریں یا Streamlit Secrets میں Key سیٹ کریں۔")
    st.stop()

# 2. آڈیو فائل اپلوڈ کرنے کا آپشن
uploaded_file = st.file_uploader("آڈیو فائل اپلوڈ کریں (MP3, WAV, M4A)", type=["mp3", "wav", "m4a"])

if uploaded_file is not None:
    if st.button("Generate Court Document"):
        st.info("فائل پراسیس ہو رہی ہے، براہ کرم 1 یا 2 منٹ انتظار کریں...")
        
        # آڈیو کو صرف کمپیوٹر کی عارضی میموری (RAM) میں رکھنا
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(uploaded_file.read())
            temp_audio_path = temp_audio.name
            
        try:
            # آڈیو براہ راست AI کو بھیجنا
            gemini_audio = genai.upload_file(path=temp_audio_path)
            
            # AI کو سخت ہدایت
            prompt = """
            You are an expert Legal Assistant and Stenographer in a Pakistani Court.
            Listen to this audio dictation carefully.
            Remove all hesitations, 'umm', 'yar', and informal words.
            Correct the English grammar perfectly.
            Format the text into a professional Court Order or Judgment.
            Use proper paragraphs and format legal headings (like Plaintiff, Defendant, Issues, OPP, OPD, Relief) properly.
            Output ONLY the clean English legal text, nothing else.
            """
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, gemini_audio])
            
            generated_text = response.text
            
            st.success("ڈکٹیشن کامیابی سے تیار ہو گئی!")
            st.write(generated_text)
            
            # Word Document (.docx) بنانا (ہارڈ ڈسک میں سیو کیے بغیر)
            doc = Document()
            doc.add_paragraph(generated_text)
            
            doc_buffer = io.BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            st.download_button(
                label="📥 Word File (.docx) ڈاؤنلوڈ کریں",
                data=doc_buffer,
                file_name="Court_Order.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # زیرو سٹوریج: گوگل سرور سے فائل فوراً ڈیلیٹ کرنا
            genai.delete_file(gemini_audio.name)
            
        except Exception as e:
            st.error(f"کوئی مسئلہ پیش آیا: {e}")
            
        finally:
            # زیرو سٹوریج: اپنے لوکل سرور سے بھی آڈیو ڈیلیٹ کرنا
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
