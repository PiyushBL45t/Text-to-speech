"""
Image -> OCR -> Speech  (Streamlit UI)

Run locally:
    streamlit run app.py

Dependencies:
    pip install streamlit pytesseract pillow numpy gtts edge-tts pyttsx3 opencv-python-headless

Deploy on Streamlit Cloud:
    - requirements.txt (Python deps listed above)
    - packages.txt (system deps: tesseract-ocr + language packs)
"""

import asyncio
import io
import os
import tempfile

import numpy as np
import pytesseract
import streamlit as st
from PIL import Image, ImageOps

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# Windows only: uncomment and set this if Tesseract isn't on your PATH
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ----------------------------------------------------------------------------
# Configuration
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
# Mobile responsiveness (stack columns, bigger touch targets)
# ----------------------------------------------------------------------------
st.markdown("""
<style>
@media (max-width: 768px) {
    .stMainBlockContainer {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
    }
    .stButton > button {
        min-height: 48px;
        font-size: 16px;
    }
    .stTextArea textarea {
        font-size: 16px !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Preprocessing
# ----------------------------------------------------------------------------
def preprocess(img, grayscale, autocontrast, upscale, threshold,
               adaptive=False, block_size=31, c_const=10, denoise=True):
    img = ImageOps.exif_transpose(img)

    if upscale != 1.0:
        w, h = img.size
        img = img.resize((int(w * upscale), int(h * upscale)), Image.LANCZOS)

    if grayscale or autocontrast or threshold > 0 or adaptive:
        img = img.convert("L")

    if adaptive and _CV2_AVAILABLE:
        arr = np.array(img)
        if denoise:
            arr = cv2.medianBlur(arr, 3)
        bs = block_size if block_size % 2 == 1 else block_size + 1
        arr = cv2.adaptiveThreshold(
            arr, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=bs,
            C=c_const,
        )
        return Image.fromarray(arr)

    if autocontrast:
        img = ImageOps.autocontrast(img)
    if threshold > 0:
        img = img.point(lambda p: 255 if p > threshold else 0)
    return img


@st.cache_data(show_spinner=False)
def run_ocr(image_bytes, lang, psm, grayscale, autocontrast, upscale, threshold,
            adaptive, block_size, c_const, denoise):
    img = Image.open(io.BytesIO(image_bytes))
    processed = preprocess(img, grayscale, autocontrast, upscale, threshold,
                           adaptive, block_size, c_const, denoise)
    config = f"--psm {psm} --oem 1"
    text = pytesseract.image_to_string(processed, lang=lang, config=config)
    return " ".join(text.split()), processed


# ----------------------------------------------------------------------------
# Text to speech
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
# Sidebar
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

        if _CV2_AVAILABLE:
            adaptive = st.checkbox(
                "Adaptive thresholding (handles uneven lighting)",
                value=False,
                help="Best for phone photos and scans with shadows/gradients.",
            )
        else:
            adaptive = False
            st.caption("Install `opencv-python-headless` to enable adaptive thresholding.")

        if adaptive:
            denoise = st.checkbox("Denoise (median blur)", value=True)
            block_size = st.slider("Adaptive block size", 11, 101, 31, 2,
                                   help="Larger = tolerates big lighting gradients.")
            c_const = st.slider("Adaptive C", 2, 30, 10, 1,
                                help="Higher = more aggressive binarization.")
            threshold = 0
        else:
            denoise = False
            block_size = 31
            c_const = 10
            threshold = st.slider("Black & white threshold", 0, 255, 0,
                                  help="0 = off. Try 120-160 for noisy backgrounds.")

    st.subheader("Speech")
    engine_label = st.selectbox("Engine", list(TTS_ENGINES))
    engine = TTS_ENGINES[engine_label]

    if engine == "gtts":
        slow = st.checkbox("Speak slowly")
    elif engine == "edge":
        voice = st.text_input("Voice", value=edge_voice,
                              help="Any edge-tts voice, e.g. en-US-AriaNeural")
        rate_pct = st.slider("Speed", -50, 50, 0, 5, format="%d%%")
    else:
        rate_wpm = st.slider("Speed (words per minute)", 80, 300, 170, 10)
        st.caption("Offline voices only support system-installed languages.")

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
st.write("Upload or snap an image, check the detected text, then listen to it.")

# --- Input: tabs for file upload vs camera capture ---
tab_upload, tab_cam = st.tabs(["📁 Upload Image", "📷 Take Photo"])

with tab_upload:
    uploaded_file = st.file_uploader(
        "Drag and drop an image here",
        type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        key="file_uploader",
    )

with tab_cam:
    uploaded_cam = st.camera_input("Take a photo", key="camera_input")

uploaded = uploaded_file if uploaded_file is not None else uploaded_cam

if uploaded is None:
    st.info("Upload an image or take a photo to get started.")
    st.stop()

image_bytes = uploaded.getvalue()

try:
    with st.spinner("Reading text from image..."):
        text, processed = run_ocr(
            image_bytes, ocr_lang, PSM_MODES[psm_label],
            grayscale, autocontrast, upscale, threshold,
            adaptive, block_size, c_const, denoise,
        )
except pytesseract.TesseractNotFoundError:
    st.error("Tesseract isn't installed or isn't on your PATH.")
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
        st.warning("No text detected. Try adjusting the sidebar settings.")
    edited = st.text_area(
        "You can fix mistakes before generating speech",
        value=text,
        height=300,
        key=f"text_{hash((uploaded.file_id, ocr_lang, psm_label, grayscale, autocontrast, upscale, threshold, adaptive, block_size, c_const, denoise))}",
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