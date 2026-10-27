"""
Image -> OCR -> Speech  (Streamlit UI)

Run:
    streamlit run app.py
"""

import asyncio
import io
import os
import tempfile

import pytesseract
import streamlit as st
from PIL import Image, ImageOps

# Windows only: uncomment and set this if Tesseract isn't on your PATH
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ----------------------------------------------------------------------------
# Configuration: add a language here and it shows up in the UI automatically.
# name -> (tesseract code, gTTS code, edge-tts voice)
# ----------------------------------------------------------------------------
LANGUAGES = {
    "English": ("eng", "en", "en-IN-NeerjaNeural"),
    "Hindi": ("hin", "hi", "hi-IN-SwaraNeural"),
    "Marathi": ("mar", "mr", "mr-IN-AarohiNeural"),
    "Spanish": ("spa", "es", "es-ES-ElviraNeural"),
    "French": ("fra", "fr", "fr-FR-DeniseNeural"),
    "German": ("deu", "de", "de-DE-KatjaNeural"),
}

TTS_ENGINES = {
    "gTTS (online, simple)": "gtts",
    "edge-tts (online, natural voices)": "edge",
    "pyttsx3 (offline, system voices)": "pyttsx3",
}

PSM_MODES = {
    "Auto (default)": 3,
    "Single block of text": 6,
    "Single line": 7,
    "Sparse text": 11,
}

st.set_page_config(page_title="Image to Speech", page_icon="🔊", layout="wide")


# ----------------------------------------------------------------------------
# OCR
# ----------------------------------------------------------------------------
def preprocess(img, grayscale, autocontrast, upscale, threshold):
    img = ImageOps.exif_transpose(img)
    if upscale != 1.0:
        w, h = img.size
        img = img.resize((int(w * upscale), int(h * upscale)), Image.LANCZOS)
    if grayscale or autocontrast or threshold > 0:
        img = img.convert("L")
    if autocontrast:
        img = ImageOps.autocontrast(img)
    if threshold > 0:
        img = img.point(lambda p: 255 if p > threshold else 0)
    return img


@st.cache_data(show_spinner=False)
def run_ocr(image_bytes, lang, psm, grayscale, autocontrast, upscale, threshold):
    img = Image.open(io.BytesIO(image_bytes))
    processed = preprocess(img, grayscale, autocontrast, upscale, threshold)
    text = pytesseract.image_to_string(processed, lang=lang, config=f"--psm {psm}")
    return " ".join(text.split()), processed


# ----------------------------------------------------------------------------
# Text to speech: every engine returns (audio_bytes, mime_type)
# ----------------------------------------------------------------------------
def tts_gtts(text, lang_code, slow):
    from gtts import gTTS

    buf = io.BytesIO()
    gTTS(text=text, lang=lang_code, slow=slow).write_to_fp(buf)
    return buf.getvalue(), "audio/mp3"


def tts_edge(text, voice, rate_pct):
    import edge_tts

    async def _run():
        chunks = []
        comm = edge_tts.Communicate(text, voice, rate=f"{rate_pct:+d}%")
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    return asyncio.run(_run()), "audio/mp3"


def tts_pyttsx3(text, rate_wpm):
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", rate_wpm)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "speech.wav")
        engine.save_to_file(text, path)
        engine.runAndWait()
        with open(path, "rb") as f:
            return f.read(), "audio/wav"


# ----------------------------------------------------------------------------
# Sidebar settings
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("Text detection")
    lang_name = st.selectbox("Language in the image", list(LANGUAGES))
    tess_lang, gtts_lang, edge_voice = LANGUAGES[lang_name]
    extra_langs = st.multiselect(
        "Also detect (mixed-language images)",
        [n for n in LANGUAGES if n != lang_name],
    )
    ocr_lang = "+".join([tess_lang] + [LANGUAGES[n][0] for n in extra_langs])
    psm_label = st.selectbox("Layout", list(PSM_MODES))

    with st.expander("Image preprocessing"):
        grayscale = st.checkbox("Grayscale", value=True)
        autocontrast = st.checkbox("Auto contrast", value=True)
        upscale = st.slider("Upscale", 1.0, 3.0, 1.0, 0.25,
                            help="Enlarging small images can improve accuracy.")
        threshold = st.slider("Black & white threshold", 0, 255, 0,
                              help="0 = off. Try 120-160 for noisy backgrounds.")

    st.subheader("Speech")
    engine_label = st.selectbox("Engine", list(TTS_ENGINES))
    engine = TTS_ENGINES[engine_label]

    if engine == "gtts":
        slow = st.checkbox("Speak slowly")
    elif engine == "edge":
        voice = st.text_input("Voice", value=edge_voice,
                              help="Any edge-tts voice name, e.g. en-US-AriaNeural")
        rate_pct = st.slider("Speed", -50, 50, 0, 5, format="%d%%")
    else:
        rate_wpm = st.slider("Speed (words per minute)", 80, 300, 170, 10)
        st.caption("Offline voices only support languages installed on your system.")

    try:
        installed = set(pytesseract.get_languages())
        missing = [c for c in ocr_lang.split("+") if c not in installed]
        if missing:
            st.warning(f"Tesseract language data missing: {', '.join(missing)}")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Main page
# ----------------------------------------------------------------------------
st.title("🔊 Image to Speech")
st.write("Drop an image, check the detected text, then listen to it.")

uploaded = st.file_uploader(
    "Drag and drop an image here",
    type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
)

if uploaded is None:
    st.info("Upload an image to get started.")
    st.stop()

image_bytes = uploaded.getvalue()

try:
    with st.spinner("Reading text from image..."):
        text, processed = run_ocr(
            image_bytes, ocr_lang, PSM_MODES[psm_label],
            grayscale, autocontrast, upscale, threshold,
        )
except pytesseract.TesseractNotFoundError:
    st.error("Tesseract isn't installed or isn't on your PATH. See the install notes.")
    st.stop()
except Exception as e:
    st.error(f"Couldn't process the image: {e}")
    st.stop()

col_img, col_text = st.columns(2)

with col_img:
    st.subheader("Image")
    tab_orig, tab_proc = st.tabs(["Original", "What the OCR sees"])
    with tab_orig:
        st.image(image_bytes, use_container_width=True)
    with tab_proc:
        st.image(processed, use_container_width=True)

with col_text:
    st.subheader("Detected text")
    if not text:
        st.warning("No text detected. Try adjusting the settings in the sidebar.")
    # The key changes whenever the OCR result changes, so the box refreshes
    edited = st.text_area(
        "You can fix mistakes before generating speech",
        value=text,
        height=300,
        key=f"text_{hash((uploaded.file_id, ocr_lang, psm_label, grayscale, autocontrast, upscale, threshold))}",
    )
    st.caption(f"{len(edited.split())} words")

    if st.button("🎧 Generate speech", type="primary", disabled=not edited.strip()):
        try:
            with st.spinner("Generating audio..."):
                if engine == "gtts":
                    audio, mime = tts_gtts(edited, gtts_lang, slow)
                elif engine == "edge":
                    audio, mime = tts_edge(edited, voice, rate_pct)
                else:
                    audio, mime = tts_pyttsx3(edited, rate_wpm)
            st.session_state["audio"] = (audio, mime)
        except Exception as e:
            st.session_state.pop("audio", None)
            st.error(f"Speech generation failed: {e}")

    if "audio" in st.session_state:
        audio, mime = st.session_state["audio"]
        st.audio(audio, format=mime)
        ext = "mp3" if mime == "audio/mp3" else "wav"
        st.download_button("⬇️ Download audio", audio, file_name=f"speech.{ext}", mime=mime)