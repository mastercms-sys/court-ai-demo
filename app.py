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

# یوزر سے API Key لینا (ڈیمو کے لیے)
API_KEY = st.text_input("اپنی Gemini API Key یہاں پیسٹ کریں:", type="password")

if API_KEY:
    genai.configure(api_key=API_KEY)
    
    # آڈیو فائل اپلوڈ کرنے کا آپشن
    uploaded_file = st.file_uploader("آڈیو فائل اپلوڈ کریں (MP3, WAV)", type=["mp3", "wav", "m4a"])
    
    if uploaded_file is not None:
        if st.button("Generate Court Document"):
            st.info("فائل پراسیس ہو رہی ہے، براہ کرم 1 یا 2 منٹ انتظار کریں...")
            
            # 1. آڈیو کو صرف کمپیوٹر کی عارضی میموری (RAM) میں رکھنا
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
                temp_audio.write(uploaded_file.read())
                temp_audio_path = temp_audio.name
                
            try:
                # 2. آڈیو کو براہ راست AI کو بھیجنا
                gemini_audio = genai.upload_file(path=temp_audio_path)
                
                # 3. AI کو ہماری سخت ہدایت (Prompt)
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
                
                # 4. Word Document (.docx) بنانا (بغیر ہارڈ ڈسک میں سیو کیے، صرف BytesIO میں)
                doc = Document()
                doc.add_paragraph(generated_text)
                
                doc_buffer = io.BytesIO()
                doc.save(doc_buffer)
                doc_buffer.seek(0)
                
                # 5. ڈاؤنلوڈ بٹن
                st.download_button(
                    label="📥 Word File (.docx) ڈاؤنلوڈ کریں",
                    data=doc_buffer,
                    file_name="Court_Order.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                # 6. ZERO STORAGE POLICY: پراسیسنگ کے بعد گوگل کے سرور سے بھی آڈیو ڈیلیٹ کر دیں
                genai.delete_file(gemini_audio.name)
                
            except Exception as e:
                st.error(f"کوئی مسئلہ پیش آیا: {e}")
                
            finally:
                # 7. ZERO STORAGE POLICY: مقامی عارضی آڈیو فائل بھی ڈیلیٹ کر دیں
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)