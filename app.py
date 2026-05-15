import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import tempfile
import os
import time
import sys

# پائتھن کے نئے ورژن کا مسئلہ حل کرنے کے لیے سمارٹ ٹرک (اس سے ایرر ختم ہو جائے گا)
try:
    import audioop
except ImportError:
    import pyaudioop as audioop
    sys.modules['audioop'] = audioop

from pydub import AudioSegment

# پیج کی سیٹنگ
st.set_page_config(page_title="Court Dictation AI", page_icon="⚖️", layout="centered")
st.title("⚖️ Auto Court Dictation Pro")
st.write("اپنی ڈکٹیشن کی آڈیو، ویڈیو یا واٹس ایپ فائل اپلوڈ کریں۔ سسٹم خود اسے ٹھیک کر کے Word فائل بنا دے گا۔")

# API Key کو خفیہ خانے (Streamlit Secrets) سے لانا
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ ایپ کے بیک اینڈ پر API Key موجود نہیں ہے۔")
    st.stop()

# ہر قسم کی آڈیو/ویڈیو فائل اپلوڈ کرنے کا آپشن
allowed_formats = ["mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "aac", "ogg"]
uploaded_file = st.file_uploader("فائل اپلوڈ کریں", type=allowed_formats)

if uploaded_file is not None:
    if st.button("Generate Court Document"):
        
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        # اصلی اپلوڈ شدہ فائل محفوظ کریں
        temp_media = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_media.write(uploaded_file.getbuffer())
        temp_media.close()
        temp_media_path = temp_media.name
        
        clean_audio_path = None
        
        try:
            # 1. آٹو کنورٹر (خراب آڈیو/ویڈیو کو صاف ستھری MP3 میں بدلنا)
            with st.spinner("1️⃣ سسٹم آپ کی فائل کو آٹو فکس کر کے MP3 بنا رہا ہے..."):
                try:
                    audio = AudioSegment.from_file(temp_media_path)
                    
                    clean_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    clean_audio.close()
                    clean_audio_path = clean_audio.name
                    
                    audio.export(clean_audio_path, format="mp3")
                except Exception as e:
                    st.error(f"❌ آپ کی فائل کنورٹ نہیں ہو سکی۔ ایرر: {e}")
                    st.stop()

            # 2. اب صاف MP3 فائل گوگل کو بھیجیں گے
            with st.spinner("2️⃣ صاف کی گئی فائل سرور پر اپلوڈ ہو رہی ہے..."):
                gemini_media = genai.upload_file(path=clean_audio_path, mime_type="audio/mp3")
            
            # 3. پکا انتظار
            with st.spinner("3️⃣ AI سرور آواز کو سمجھ رہا ہے، براہ کرم انتظار کریں..."):
                while gemini_media.state.name == 'PROCESSING':
                    time.sleep(5)
                    gemini_media = genai.get_file(gemini_media.name) 
                    
                if gemini_media.state.name == 'FAILED':
                    st.error(f"❌ گوگل AI نے اب بھی اس فائل کو ریجیکٹ کر دیا ہے۔ ایرر: {gemini_media.error.message if hasattr(gemini_media, 'error') else 'Unknown Error'}")
                    genai.delete_file(gemini_media.name)
                    st.stop()
            
            # 4. قانونی ہدایت
            with st.spinner("4️⃣ سرور عدالتی فیصلہ ٹائپ کر رہا ہے..."):
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
                response = model.generate_content([prompt, gemini_media])
                
                st.success("✅ ڈکٹیشن کامیابی سے تیار ہو گئی!")
                st.write(response.text)
                
                # 5. Word Document بنانا
                doc = Document()
                doc.add_paragraph(response.text)
                doc_buffer = io.BytesIO()
                doc.save(doc_buffer)
                doc_buffer.seek(0)
                
                st.download_button(
                    label="📥 Word File (.docx) ڈاؤنلوڈ کریں",
                    data=doc_buffer,
                    file_name="Court_Order.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
            # زیرو سٹوریج: گوگل سرور سے آڈیو ڈیلیٹ کرنا
            genai.delete_file(gemini_media.name)
            
        except Exception as e:
            st.error(f"کوئی مسئلہ پیش آیا: {e}")
            
        finally:
            # زیرو سٹوریج: اپنے لوکل سرور سے دونوں عارضی فائلیں ڈیلیٹ کرنا
            if os.path.exists(temp_media_path):
                os.remove(temp_media_path)
            if clean_audio_path and os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
