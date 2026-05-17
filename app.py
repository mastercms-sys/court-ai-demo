import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import tempfile
import os
import time
import subprocess

# پیج کی سیٹنگ
st.set_page_config(page_title="Court Dictation AI - Deep Think", page_icon="⚖️", layout="centered")

# ==========================================
# 🔒 لاگ ان سسٹم (Monthly Subscription Lock)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔒 Court Dictation Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>براہ کرم اپنا ماہانہ پاس ورڈ درج کریں۔</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        password_input = st.text_input("پاس ورڈ (Password):", type="password")
        if st.button("لاگ ان (Login)", use_container_width=True):
            try:
                correct_password = st.secrets["APP_PASSWORD"]
                if password_input == correct_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ غلط پاس ورڈ! رسائی کے لیے ایڈمن سے رابطہ کریں۔")
            except Exception as e:
                st.error("⚠️ ایپ کے بیک اینڈ پر پاس ورڈ سیٹ نہیں ہے۔")
    st.stop()
# ==========================================

st.title("⚖️ Auto Court Dictation Pro")
st.markdown("**(🧠 Deep Think / Pro Model Enabled)**")
st.write("اپنی ڈکٹیشن کی آڈیو یا ویڈیو فائل اپلوڈ کریں۔ سسٹم گہرائی سے سوچ کر Word فائل بنا دے گا۔")

# API Key
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ ایپ کے بیک اینڈ پر API Key موجود نہیں ہے۔")
    st.stop()

allowed_formats = ["mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "aac", "ogg"]
uploaded_file = st.file_uploader("فائل اپلوڈ کریں", type=allowed_formats)

if uploaded_file is not None:
    if st.button("Generate Court Document"):
        
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        temp_media = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_media.write(uploaded_file.getbuffer())
        temp_media.close()
        temp_media_path = temp_media.name
        
        clean_audio_path = None
        
        try:
            with st.spinner("1️⃣ سسٹم آپ کی فائل کو آٹو فکس کر رہا ہے (بیک گراؤنڈ پروسیسنگ)..."):
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

            with st.spinner("2️⃣ فائل گوگل کے سرور پر اپلوڈ ہو رہی ہے..."):
                gemini_media = genai.upload_file(path=clean_audio_path, mime_type="audio/mp3")
            
            with st.spinner("3️⃣ AI سرور آواز کو سمجھ رہا ہے، براہ کرم انتظار کریں..."):
                while gemini_media.state.name == 'PROCESSING':
                    time.sleep(5)
                    gemini_media = genai.get_file(gemini_media.name) 
                    
                if gemini_media.state.name == 'FAILED':
                    st.error("❌ گوگل AI نے اس فائل کو ریجیکٹ کر دیا ہے۔")
                    genai.delete_file(gemini_media.name)
                    st.stop()
            
            with st.spinner("4️⃣ 🧠 DEEP THINK: سرور بہترین ماڈل تلاش کر کے فیصلہ ٹائپ کر رہا ہے..."):
                
                # 🔴 100% بلٹ پروف آٹو ماڈل ڈیٹیکٹر (اب 404 ایرر ناممکن ہے)
                available_models = []
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                except Exception as e:
                    pass
                
                target_model = None
                
                # 1. سب سے پہلے "Pro" (Deep Think) ڈھونڈے گا
                pro_models = [m for m in available_models if '1.5-pro' in m.lower()]
                
                if pro_models:
                    target_model = pro_models[0] # گوگل کا اصلی Pro ماڈل
                else:
                    # 2. اگر Pro نہیں ملا تو "Flash" ڈھونڈے گا
                    flash_models = [m for m in available_models if '1.5-flash' in m.lower()]
                    
                    if flash_models:
                        target_model = flash_models[0] # گوگل کا اصلی Flash ماڈل
                        
                # 3. اگر دونوں نہ ملے تو جو بھی لیٹسٹ ماڈل لسٹ میں ہو وہ اٹھا لے گا
                if not target_model and available_models:
                    target_model = available_models[0]
                    
                if not target_model:
                    st.error("❌ آپ کی API Key پر کوئی AI ماڈل کام نہیں کر رہا۔ براہ کرم نئی API Key استعمال کریں۔")
                    st.stop()
                    
                # یوزر کو سکرین پر دکھائیں گے کہ کون سا اصلی ماڈل ملا ہے
                st.info(f"💡 سمارٹ ڈیٹیکٹر نے یہ ماڈل استعمال کیا ہے: **{target_model}**")
                
                model = genai.GenerativeModel(target_model)
                
                prompt = """Act as an Expert Legal Assistant and Senior Court Stenographer in a Pakistani District and Sessions Court.

I will provide you with an audio dictation of court proceedings. Your task is to process, edit, and format this audio into a flawless, highly professional Court Order or Judgment.

Please strictly follow these instructions:

1. CLEAN UP THE TEXT: Remove all hesitations, stutters, false starts, filler sounds (e.g., 'umm', 'uh'), and informal conversational words (e.g., 'yar', 'acha', 'theek').
2. PERFECT GRAMMAR & TONE: Correct all English grammar, sentence structures, and punctuation perfectly. Maintain a highly formal, objective, and judicial tone.
3. PRESERVE PAKISTANI LEGAL CONTEXT: Retain, correctly spell, and properly capitalize Pakistani legal and local terms (e.g., FIR, PPC, CrPC, IO, SHO, ADPP, Plaint, Nikahnama, Iddat, Panchayat, OPP, OPD, PW, DW). DO NOT change any core facts, dates, names, or amounts.
4. PROFESSIONAL FORMATTING:
   - Separate multiple cases clearly.
   - Use proper paragraph breaks for readability.
   - Use BOLD and ALL CAPS for main headings (e.g., **ORDER**, **JUDGMENT**).
   - For criminal cases, neatly format the header (e.g., **TITLE:**, **FIR NO.:**, **OFFENCES:**, **POLICE STATION:**).
   - For civil/family cases, boldly format the issues (e.g., **ISSUE NO. 1 (OPP):**, **ISSUE NO. 2 (OPD):**).
5. STRICT OUTPUT CONSTRAINT: Output ONLY the final, clean, formatted English legal document. Do not include any conversational AI filler, greetings, introductory remarks, or concluding statements.
6. NO EXTRA HEADERS/FOOTERS: DO NOT add "In the Court of", Judge names, Dates, Signatures, or Stamps at the top or bottom UNLESS explicitly spoken in the audio dictation.

Here is the audio file for you to process:"""
                
                response = model.generate_content([prompt, gemini_media])
                
                st.success("✅ ڈکٹیشن 100% درستگی (Deep Think) کے ساتھ تیار ہو گئی!")
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
                    file_name="Court_Order_DeepThink.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
            genai.delete_file(gemini_media.name)
            
        except Exception as e:
            st.error(f"کوئی مسئلہ پیش آیا: {e}")
            with st.expander("تکنیکی خرابی کی تفصیل (ایرر آئے تو یہ دیکھیں)"):
                st.write(e)
                if 'available_models' in locals():
                    st.write("آپ کی API Key پر گوگل کی طرف سے دستیاب ماڈلز کی مکمل لسٹ:", available_models)
            
        finally:
            if os.path.exists(temp_media_path):
                os.remove(temp_media_path)
            if clean_audio_path and os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
