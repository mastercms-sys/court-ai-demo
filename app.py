import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import tempfile
import os
import time
import subprocess

# پیج کی سیٹنگ
st.set_page_config(page_title="Court Dictation AI - Elite Drafter", page_icon="⚖️", layout="centered")

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
st.markdown("**(🧠 Deep Legal Thinker & Elite Drafter Enabled)**")
st.write("اپنی ڈکٹیشن کی آڈیو، ویڈیو یا واٹس ایپ فائل اپلوڈ کریں۔ سسٹم گہرائی سے سوچ کر Word فائل بنا دے گا۔")

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
            
            with st.spinner("4️⃣ 🧠 DEEP THINK: سرور قانونی گہرائی کے ساتھ فیصلہ ڈرافٹ کر رہا ہے..."):
                
                valid_models = []
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            name_lower = m.name.lower()
                            if 'image' not in name_lower and 'vision' not in name_lower and 'exp' not in name_lower and 'learn' not in name_lower:
                                valid_models.append(m.name)
                except Exception as e:
                    pass
                
                pro_models = sorted([m for m in valid_models if 'pro' in m.lower()], reverse=True)
                flash_models = sorted([m for m in valid_models if 'flash' in m.lower()], reverse=True)
                
                primary_model_name = pro_models[0] if pro_models else (flash_models[0] if flash_models else "gemini-1.5-pro")
                backup_model_name = flash_models[0] if flash_models else "gemini-1.5-flash"
                
                # 🔴 آپ کا الٹرا لیول پرامپٹ (Deep Legal Thinking)
                prompt = """Act as an Elite Legal Drafter and Senior District & Sessions Judge in Pakistan. 

I will provide you with a raw, unedited audio recording of court dictations. Your task is to apply "Deep Legal Thinking" to listen, process, refine, logically correct, and highly format this audio into a flawless, ready-to-print Court Order or Judgment.

You MUST strictly adhere to the following 5 golden rules:

1. NO MARKDOWN OR SPECIAL CHARACTERS (CRITICAL FOR MS WORD):
   - ABSOLUTELY DO NOT use asterisks (**), hashes (#), or quotation marks ("") for bolding or formatting. 
   - Since the output will be pasted directly into MS Word as plain text, use purely ALL CAPS to emphasize headings. 
   - Example: Write exactly ORDER instead of "**ORDER**" or "ORDER". Write exactly ISSUE NO. 1 (OPP): instead of "**ISSUE NO. 1 (OPP):**".

2. LOGICAL CORRECTIONS & ELIMINATING REPETITIONS (DEEP THINK):
   - Think deeply and analyze the context. Correct obvious slips of the tongue by the dictator. (e.g., if the audio says "sons are Parda Nashin ladies", apply logic and correct it to "daughters are Parda Nashin ladies" based on context).
   - If the dictator accidentally repeats a sentence twice (e.g., "The defendants are co-sharers. The defendants are co-sharers."), deeply analyze and write it ONLY ONCE in the final text.
   - Ensure the gender of the parties (he/she/her/his) and singular/plural nouns remain logically consistent throughout the case.

3. PERFECT LEGAL GRAMMAR & FLOW:
   - Fix literal Urdu-to-English translation errors. ALWAYS change "interfere into the possession" to "interfere with the possession".
   - ALWAYS change "deprived from" to "deprived of".
   - Always use proper articles (e.g., write "The plaintiff" instead of just "Plaintiff").
   - Remove the repetitive word "That" at the start of every sentence. Merge choppy sentences to create a smooth, highly formal, and objective judicial tone.

4. EXACT NUMBERS & ISSUE FORMATTING:
   - Convert spoken amounts into legal numeric formats with commas and a dash. Do not write "Rupees 50 Lakh" or "50000". Write: "Rs. 5,000,000/-" and "Rs. 50,000/-".
   - Do NOT repeat the burden of proof tag at the end of an issue. If the heading says "ISSUE NO. 1 (OPP):", do not put "(OPP)" again at the end of the sentence.

5. EXACT LAYOUT STRUCTURE:
   - Separate different cases using a plain line of dashes: ----------------------------------------
   - Format each case exactly like this:
   
   CASE NO. [Leave Blank if not provided]
   TITLE: [Party A] VS. [Party B]
   
   ORDER 
   [Clean, logically flowing paragraphs]
   
   ISSUES:
   ISSUE NO. 1 (OPP): [Text ends with a question mark]
   ISSUE NO. 2 (OPD): [Text ends with a question mark]
   
   RELIEF: 
   To come up for preliminary arguments on [Date].

STRICT OUTPUT CONSTRAINT:
Output ONLY the final, cleanly formatted legal document. No introductory or concluding remarks from the AI. Do not output your internal thinking process.

Here is the audio file to process:"""
                
                try:
                    st.info(f"💡 Elite Drafter Engine: **{primary_model_name}**")
                    primary_model = genai.GenerativeModel(primary_model_name)
                    response = primary_model.generate_content([prompt, gemini_media])
                    st.success("✅ ڈکٹیشن 100% درستگی (Deep Legal Think) کے ساتھ تیار ہو گئی!")
                    
                except Exception as model_error:
                    error_msg = str(model_error)
                    if ("429" in error_msg or "Quota" in error_msg or "ResourceExhausted" in error_msg) and backup_model_name != primary_model_name:
                        st.warning(f"⚠️ مین سرور بزی ہے، آٹو بیک اپ سرور (**{backup_model_name}**) استعمال کیا جا رہا ہے...")
                        try:
                            backup_model = genai.GenerativeModel(backup_model_name)
                            response = backup_model.generate_content([prompt, gemini_media])
                            st.success("✅ ڈکٹیشن بیک اپ ماڈل کے ساتھ کامیابی سے تیار ہو گئی!")
                        except Exception as backup_error:
                            raise backup_error
                    else:
                        raise model_error
                
                # نیا طریقہ: سکرین پر دکھانے کے لیے Text Area کا استعمال، تاکہ مارک ڈاؤن کا مسئلہ نہ ہو اور یوزر آسانی سے کاپی کر سکے
                st.text_area("تیار شدہ عدالتی فیصلہ (یہاں سے سلیکٹ کر کے کاپی بھی کر سکتے ہیں):", response.text, height=450)
                
                # 5. Word Document بنانا
                doc = Document()
                
                # نیا طریقہ: رزلٹ کو لائن بائی لائن پڑھ کر ورڈ فائل میں ڈالنا تاکہ فارمیٹنگ بالکل پرفیکٹ آئے
                for line in response.text.split('\n'):
                    if line.strip() != "":
                        doc.add_paragraph(line)
                    else:
                        doc.add_paragraph() # خالی لائن کے لیے
                        
                doc_buffer = io.BytesIO()
                doc.save(doc_buffer)
                doc_buffer.seek(0)
                
                st.download_button(
                    label="📥 Word File (.docx) ڈاؤنلوڈ کریں",
                    data=doc_buffer,
                    file_name="Court_Order_Elite.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
            genai.delete_file(gemini_media.name)
            
        except Exception as e:
            st.error(f"کوئی مسئلہ پیش آیا: {e}")
            with st.expander("تکنیکی خرابی کی تفصیل (ایرر آئے تو یہ دیکھیں)"):
                st.write(e)
            
        finally:
            if os.path.exists(temp_media_path):
                os.remove(temp_media_path)
            if clean_audio_path and os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
