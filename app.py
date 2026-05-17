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
st.write("اپنی ڈکٹیشن کی آڈیو، ویڈیو یا واٹس ایپ فائل اپلوڈ کریں۔ سسٹم خود اسے ٹھیک کر کے  فائل بنا دے گا۔")

# API Key کو خفیہ خانے سے لانا
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
                
                # 🔴 آپ کا دیا گیا بہترین اور پروفیشنل پرامپٹ (تھوڑی سی موڈیفکیشن کے ساتھ)
                prompt = """Act as an Expert Legal Drafter and Senior Court Stenographer in a Pakistani District and Sessions Court. 

I will provide you with a raw audio transcript or rough dictation of court proceedings. Your task is to process, edit, and highly format this text into a flawless, ready-to-print Court Order or Judgment. 

You MUST strictly adhere to the following 5 rules:

1. CURRENCY & NUMBER FORMATTING (CRITICAL): 
   - Never write amounts in words (e.g., "Rupees 55 Lakh", "Rupees 10000"). 
   - Always convert amounts to the standard Pakistani legal numeric format with commas and a trailing dash. Example: "Rs. 5,500,000/-", "Rs. 10,000/-", "Rs. 500,000/-".

2. ELIMINATE DICTATION ARTIFACTS: 
   - Remove all hesitations, stutters, and informal words (e.g., 'umm', 'uh', 'yar', 'acha').
   - STRICTLY remove the repetitive use of the word "That" at the beginning of every sentence or paragraph (a common dictation habit). Start sentences directly to ensure a natural, professional flow.

3. CORRECT LEGAL CONTEXT & TITLES: 
   - Correctly translate local terms if used as parties: change "Sarkar" to "THE STATE".
   - Do not mistake application types for party names. If the dictation says "Imam Bakhsh vs Execution", infer the context and format the title properly as "TITLE: IMAM BAKHSH VS. JUDGMENT DEBTOR" and add "NATURE: EXECUTION PETITION" below it.
   - Retain and properly capitalize Pakistani land and legal terms (e.g., Khata, Killa, Marla, Kanal, Patwari Halqa, FIR, PPC, CrPC, IO, SHO, ADPP, OPP, OPD, PW, DW).

4. PERFECT GRAMMAR & TENSES: 
   - Fix mixed tenses within a single sentence. (e.g., Change "Patwari Halqa is present and submitted" to "The Patwari Halqa is present in Court and submits"). Ensure a highly formal, objective, and judicial tone.

5. PROFESSIONAL LAYOUT & HEADINGS:
   - Separate multiple cases clearly using a divider `***`.
   - Use bold and uppercase for main headers. Follow this exact structure for every case:
     **CASE NO. [Number]**
     **TITLE:** [Party A] VS. [Party B]
     **ORDER** (or **JUDGMENT**)
     [Body of the order in well-structured paragraphs]
     **ISSUE NO. 1 (OPP):** [Text]
     **RELIEF:** [Text]

STRICT OUTPUT CONSTRAINT: 
Output ONLY the final, clean, formatted English legal document. Do not include any conversational AI filler, greetings, or concluding statements.

Here is the raw text to process:
{{RAW_TEXT}}"""
                
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
            with st.expander("تکنیکی خرابی کی تفصیل (ایرر آئے تو یہ دیکھیں)"):
                st.write(e)
            
        finally:
            # زیرو سٹوریج: اپنے لوکل سرور سے دونوں عارضی فائلیں ڈیلیٹ کرنا
            if os.path.exists(temp_media_path):
                os.remove(temp_media_path)
            if clean_audio_path and os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
