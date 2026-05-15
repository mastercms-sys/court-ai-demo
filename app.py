import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import tempfile
import os
import time

# پیج کی سیٹنگ
st.set_page_config(page_title="Court Dictation AI", page_icon="⚖️", layout="centered")
st.title("⚖️ Auto Court Dictation Pro")
st.write("اپنی ڈکٹیشن کی آڈیو یا ویڈیو فائل اپلوڈ کریں۔ AI خود آواز سن کر Word فائل بنا دے گا۔ (Zero Storage Policy)")

# 1. API Key کو خفیہ خانے (Streamlit Secrets) سے لانا
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ ایپ کے بیک اینڈ پر API Key موجود نہیں ہے۔ براہ کرم Streamlit Secrets میں Key سیٹ کریں۔")
    st.stop()

# 2. ہر قسم کی آڈیو/ویڈیو فائل اپلوڈ کرنے کا آپشن
allowed_formats = ["mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "aac"]
uploaded_file = st.file_uploader("آڈیو یا ویڈیو فائل اپلوڈ کریں (MP3, MP4, WAV وغیرہ)", type=allowed_formats)

if uploaded_file is not None:
    if st.button("Generate Court Document"):
        st.info("فائل پراسیس ہو رہی ہے۔ سائز کے حساب سے 1 سے 2 منٹ لگ سکتے ہیں...")
        
        # 3. جو بھی فائل ہو (mp4 ہو یا mp3) اس کی ایکسٹینشن (Extension) خود بخود نکالنا
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        # فائل کو کمپیوٹر کی عارضی میموری میں اس کی اصلی ایکسٹینشن کے ساتھ محفوظ کرنا
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_media:
            temp_media.write(uploaded_file.read())
            temp_media_path = temp_media.name
            
        try:
            # 4. فائل (آڈیو/ویڈیو) براہ راست AI کے سرور کو بھیجنا
            gemini_media = genai.upload_file(path=temp_media_path)
            
            # 5. آڈیو/ویڈیو کے تیار ہونے کا انتظار کرنا
            with st.spinner("AI سرور آپ کی فائل سن رہا ہے، براہِ کرم انتظار کریں..."):
                while gemini_media.state.name == 'PROCESSING':
                    time.sleep(3) # 3 سیکنڈ انتظار کریں
                    gemini_media = genai.get_file(gemini_media.name) # دوبارہ چیک کریں
                    
                if gemini_media.state.name == 'FAILED':
                    st.error("پراسیسنگ میں کوئی مسئلہ آیا ہے۔ براہ کرم فائل چیک کریں۔")
                    st.stop()
            
            # 6. AI کو سخت ہدایت (Prompt) جس میں آڈیو/ویڈیو دونوں شامل ہیں
            prompt = """
            You are an expert Legal Assistant and Stenographer in a Pakistani Court.
            Listen to this audio/video dictation carefully.
            Remove all hesitations, 'umm', 'yar', and informal words.
            Correct the English grammar perfectly.
            Format the text into a professional Court Order or Judgment.
            Use proper paragraphs and format legal headings (like Plaintiff, Defendant, Issues, OPP, OPD, Relief) properly.
            Output ONLY the clean English legal text, nothing else.
            """
            
            # ماڈل کی سیٹنگ
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, gemini_media])
            
            generated_text = response.text
            
            st.success("ڈکٹیشن کامیابی سے تیار ہو گئی!")
            st.write(generated_text)
            
            # 7. Word Document (.docx) بنانا
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
            
            # 8. زیرو سٹوریج: گوگل سرور سے فائل فوراً ڈیلیٹ کرنا
            genai.delete_file(gemini_media.name)
            
        except Exception as e:
            st.error(f"کوئی مسئلہ پیش آیا: {e}")
            
        finally:
            # 9. زیرو سٹوریج: اپنے لوکل سرور سے بھی فائل ڈیلیٹ کرنا
            if os.path.exists(temp_media_path):
                os.remove(temp_media_path)
