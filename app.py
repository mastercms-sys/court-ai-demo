import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import tempfile
import os
import time
import subprocess

# پیج کی سیٹنگ
st.set_page_config(page_title="Court Dictation AI", page_icon="⚖️", layout="centered")
st.title("⚖️ Auto Court Dictation Pro")
st.write("اپنی ڈکٹیشن کی آڈیو یا ویڈیو فائل اپلوڈ کریں۔ سسٹم خود اسے ٹھیک کر کے Word فائل بنا دے گا۔")

# API Key کو خفیہ خانے سے لانا
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ ایپ کے بیک اینڈ پر API Key موجود نہیں ہے۔")
    st.stop()

# یوزر کے لیے 2 آپشنز کا بٹن (ریڈیو بٹن)
st.markdown("### ⚙️ ڈکٹیشن کا انداز منتخب کریں:")
processing_mode = st.radio(
    "",
    ["1️⃣ بالکل اصل الفاظ (Original Text - صرف گرامر اور سپیلنگ درست کرے گا)", 
     "2️⃣ بہتر قانونی مسودہ (Improved Text - پیراگراف اور ہیڈنگز کے ساتھ فارمیٹ کرے گا)"]
)

allowed_formats = ["mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "aac", "ogg"]
st.markdown("### 📁 فائل اپلوڈ کریں:")
uploaded_file = st.file_uploader("", type=allowed_formats)

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
            # 1. ڈائریکٹ سرور کمانڈ کے ذریعے آٹو کنورٹر 
            with st.spinner("1️⃣ سسٹم آپ کی فائل کو آٹو فکس کر کے MP3 بنا رہا ہے..."):
                clean_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                clean_audio.close()
                clean_audio_path = clean_audio.name
                
                try:
                    command = [
                        "ffmpeg", "-y", "-i", temp_media_path, 
                        "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k", 
                        clean_audio_path
                    ]
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    st.error("❌ فائل کنورٹ نہیں ہو سکی۔ یہ فائل مکمل کرپٹ ہے۔")
                    st.stop()

            # 2. صاف MP3 فائل گوگل کو بھیجیں گے
            with st.spinner("2️⃣ صاف کی گئی فائل سرور پر اپلوڈ ہو رہی ہے..."):
                gemini_media = genai.upload_file(path=clean_audio_path, mime_type="audio/mp3")
            
            # 3. پکا انتظار
            with st.spinner("3️⃣ AI سرور آواز کو سمجھ رہا ہے، براہ کرم انتظار کریں..."):
                while gemini_media.state.name == 'PROCESSING':
                    time.sleep(5)
                    gemini_media = genai.get_file(gemini_media.name) 
                    
                if gemini_media.state.name == 'FAILED':
                    st.error("❌ گوگل AI نے اس فائل کو ریجیکٹ کر دیا ہے۔")
                    genai.delete_file(gemini_media.name)
                    st.stop()
            
            # 4. قانونی ہدایت اور آٹو ماڈل سلیکشن
            with st.spinner("4️⃣ سرور عدالتی فیصلہ ٹائپ کر رہا ہے..."):
                
                target_model = None
                available_models = []
                
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                except Exception:
                    pass
                        
                for m_name in available_models:
                    if '1.5-flash' in m_name:
                        target_model = m_name
                        break
                        
                if not target_model:
                    for m_name in available_models:
                        if '1.5-pro' in m_name:
                            target_model = m_name
                            break
                            
                if not target_model and available_models:
                    target_model = available_models[0]
                    
                if not target_model:
                    st.error("❌ آپ کی API Key پر کوئی بھی AI ماڈل دستیاب نہیں ہے۔")
                    st.stop()
                
                model = genai.GenerativeModel(target_model)
                
                # 🔴 یوزر کی پسند کے مطابق AI کو سخت ہدایات (Prompts) دینا
                if "Original Text" in processing_mode:
                    prompt = """
                    You are an expert Stenographer. Listen to this audio dictation carefully.
                    Transcribe the text EXACTLY as dictated, keeping the original sentence structure and wording.
                    Only correct spelling mistakes and basic grammar. Remove hesitations like 'umm' or 'yar'.
                    
                    IMPORTANT STRICT RULES:
                    1. DO NOT add "In the Court of" or any court names at the top.
                    2. DO NOT add any signature lines, stamps, judge's name, or dates at the bottom.
                    3. Do not rephrase sentences or add extra legal formatting unless it was spoken in the audio.
                    
                    Output ONLY the transcribed clean English text.
                    """
                else:
                    prompt = """
                    You are an expert Legal Assistant and Stenographer in a Pakistani Court.
                    Listen to this audio dictation carefully.
                    Remove all hesitations, 'umm', 'yar', and informal words.
                    Correct the English grammar perfectly and format the text into a professional Court Order or Judgment.
                    Use proper paragraphs and format legal headings (like Plaintiff, Defendant, Issues, OPP, OPD, Relief) properly if they are in the audio.
                    
                    IMPORTANT STRICT RULES:
                    1. DO NOT add "In the Court of" or any court headings at the top unless explicitly dictated in the audio.
                    2. DO NOT add any signature lines, stamps, judge's name, or dates at the bottom unless explicitly dictated in the audio.
                    
                    Output ONLY the clean English legal text, nothing else.
                    """
                
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
