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

# API Key کو خفیہ خانے (Streamlit Secrets) سے لانا
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ ایپ کے بیک اینڈ پر API Key موجود نہیں ہے۔ براہ کرم Streamlit Secrets میں Key سیٹ کریں۔")
    st.stop()

# ہر قسم کی آڈیو/ویڈیو فائل اپلوڈ کرنے کا آپشن
allowed_formats = ["mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "aac", "ogg"]
uploaded_file = st.file_uploader("آڈیو یا ویڈیو فائل اپلوڈ کریں", type=allowed_formats)

if uploaded_file is not None:
    if st.button("Generate Court Document"):
        
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        # 1. سب سے اہم فکس: فائل کو 100% محفوظ طریقے سے ڈسک پر لکھ کر 'Close' کرنا
        # تاکہ کوئی نامکمل یا خالی فائل گوگل کو نہ جائے
        temp_media = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_media.write(uploaded_file.getbuffer()) # getbuffer() سب سے محفوظ طریقہ ہے
        temp_media.close() # یہاں فائل کو کلوز کرنا لازمی ہے
        temp_media_path = temp_media.name
            
        try:
            # 2. اب مکمل فائل گوگل AI کو بھیجیں گے
            with st.spinner("1️⃣ فائل سرور پر اپلوڈ ہو رہی ہے..."):
                gemini_media = genai.upload_file(path=temp_media_path)
            
            # 3. پکا انتظار (جب تک گوگل فائل تیار نہ کر لے، یہ یہیں رکا رہے گا)
            with st.spinner("2️⃣ AI سرور آپ کی فائل پڑھ رہا ہے، جب تک رزلٹ نہیں آتا یہ انتظار کرے گا..."):
                while gemini_media.state.name == 'PROCESSING':
                    time.sleep(5) # 5 سیکنڈ بعد دوبارہ سرور کا سٹیٹس چیک کرے گا
                    gemini_media = genai.get_file(gemini_media.name) 
                    
                # اگر واقعی فائل میں کوئی مسئلہ ہو تو ایرر بتائے گا
                if gemini_media.state.name == 'FAILED':
                    st.error("❌ گوگل AI نے اس فائل کو ریجیکٹ کر دیا ہے۔ (ممکنہ وجہ: یہ واٹس ایپ کی کرپٹ فائل ہے یا نام زبردستی بدلا گیا ہے)")
                    genai.delete_file(gemini_media.name)
                    st.stop()
            
            # 4. AI کو سخت قانونی ہدایت
            with st.spinner("3️⃣ سرور آواز سن کر عدالتی فیصلہ ٹائپ کر رہا ہے، بس تھوڑا سا انتظار کریں..."):
                prompt = """
                You are an expert Legal Assistant and Stenographer in a Pakistani Court.
                Listen to this audio/video dictation carefully.
                Remove all hesitations, 'umm', 'yar', and informal words.
                Correct the English grammar perfectly.
                Format the text into a professional Court Order or Judgment.
                Use proper paragraphs and format legal headings (like Plaintiff, Defendant, Issues, OPP, OPD, Relief) properly.
                Output ONLY the clean English legal text, nothing else.
                """
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([prompt, gemini_media])
                
                generated_text = response.text
                
                st.success("✅ ڈکٹیشن کامیابی سے تیار ہو گئی!")
                st.write(generated_text)
                
                # 5. Word Document (.docx) بنانا
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
            
            # 6. زیرو سٹوریج: گوگل سرور سے فائل فوراً ڈیلیٹ کرنا
            genai.delete_file(gemini_media.name)
            
        except Exception as e:
            st.error(f"کوئی مسئلہ پیش آیا: {e}")
            
        finally:
            # 7. زیرو سٹوریج: اپنے لوکل سرور سے بھی فائل ڈیلیٹ کرنا
            if os.path.exists(temp_media_path):
                os.remove(temp_media_path)
