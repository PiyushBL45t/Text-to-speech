# 🔊 Image to Speech

An OCR + Text-to-Speech web app built with Streamlit. Drop in an image or snap a photo with your phone's camera, extract the text with Tesseract, review it, and turn it into speech — in six languages, using three TTS engines.

Deployable to Streamlit Community Cloud and packageable as an Android APK via a lightweight WebView wrapper, so the same codebase works on desktop and mobile.

---

## ✨ Features

- **Two input modes** — file upload *or* camera capture (`st.camera_input`)
- **Six languages** — English, Hindi, Marathi, Spanish, French, German
- **Mixed-language detection** — combine multiple Tesseract language packs on a single image
- **Tesseract LSTM engine** (`--oem 1`) with optional `tessdata_best` models for higher accuracy
- **Advanced preprocessing**
  - Grayscale and auto-contrast
  - Upscaling (1.0× – 3.0×) for small or low-resolution images
  - Global black-and-white threshold
  - **Adaptive thresholding** (OpenCV) for uneven lighting, shadows, and phone photos
  - **Median-blur denoising** to remove salt-and-pepper noise without eroding text edges
- **Live preview** — toggle "What the OCR sees" to inspect the exact image Tesseract receives
- **Editable OCR output** — fix any residual errors before generating speech
- **Three TTS engines**
  - **gTTS** — simple, online, MP3
  - **edge-tts** — natural neural voices, per-voice and speed control
  - **pyttsx3** — offline, uses system voices, WAV
- **Downloadable audio** (MP3 or WAV)
- **Mobile-responsive UI** — columns stack vertically on phones; large touch targets
- **Cached OCR** — re-running with identical inputs is instant

---

## 📸 How it works

```
┌──────────────┐   ┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│ Image input  │ → │ Preprocessing │ → │ OCR (Tess.)  │ → │ TTS engine   │
│ (upload/cam) │   │ (grayscale,   │   │ --psm, --oem │   │ (gTTS/edge/  │
│              │   │  adaptive,    │   │  + lang pack │   │  pyttsx3)    │
│              │   │  denoise)     │   │              │   │              │
└──────────────┘   └───────────────┘   └──────────────┘   └──────────────┘
                                              ↓
                                     Editable text area
```

1. Image arrives via upload or camera
2. Preprocessing normalizes lighting, contrast, and noise
3. Tesseract extracts the text (`--oem 1` = LSTM engine, best with `tessdata_best`)
4. The user reviews/edits the detected text
5. The chosen TTS engine generates audio
6. Audio plays in the browser and can be downloaded

---

## 🚀 Quick start (local)

### 1. Install Tesseract

**Windows** — download the installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki), then either add it to `PATH` or uncomment this line in `app.py`:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

**macOS**:
```bash
brew install tesseract
brew install tesseract-lang   # all language packs
```

**Ubuntu / Debian**:
```bash
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-hin tesseract-ocr-mar \
                 tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-deu
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
streamlit run app.py
```

Open the printed URL (usually `http://localhost:8501`).

---

## ☁️ Deploy to Streamlit Community Cloud

### Files to add to your repo

**`requirements.txt`**:
```
streamlit
pytesseract
pillow
numpy
opencv-python-headless
gtts
edge-tts
pyttsx3
```

**`packages.txt`** (system dependencies — Tesseract binary + language packs):
```
tesseract-ocr
tesseract-ocr-eng
tesseract-ocr-hin
tesseract-ocr-mar
tesseract-ocr-spa
tesseract-ocr-fra
tesseract-ocr-deu
```

Streamlit Cloud installs `packages.txt` via `apt`, so the Tesseract binary is available at runtime without any manual setup. Drop language packs you don't need to shorten the build.

### Deploy steps

1. Push `app.py`, `requirements.txt`, `packages.txt` to a **public** GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub
3. Click **Create app** → **Deploy a public app from GitHub**
4. Pick your repo, branch, and set **Main file path** = `app.py`
5. Open **Advanced settings** → choose **Python 3.12**
6. Click **Deploy** and wait for the build

The resulting URL (`https://<app-name>.streamlit.app`) works on desktop and mobile. Test camera capture on your phone before packaging.

---

## 📱 Package as an Android APK

The recommended route is the open-source [`androidwrapper4streamlit`](https://github.com/luiscunhacsc/androidwrapper4streamlit) project — a small WebView shell (~5 MB) that loads your deployed Streamlit app full-screen. Supports Android 5.0+.

> ⚠️ This produces a **WebView wrapper**, not a native app. The "camera" button uses the browser camera (front camera by default), not the native Android camera app. The app requires an internet connection. For a native camera experience with full-resolution images and offline OCR, a Kotlin rewrite (ML Kit + `TextToSpeech`) is required.

### Steps

1. Clone the wrapper:
   ```bash
   git clone https://github.com/luiscunhacsc/androidwrapper4streamlit.git
   ```
2. Open the project in **Android Studio** and wait for Gradle sync
3. In `MainActivity.java`, set your deployed URL:
   ```java
   private String streamlitUrl = "https://your-app-name.streamlit.app";
   ```
4. **Change the package name** (required — `com.example` is rejected by the Play Store):
   - `app/build.gradle` → `namespace` and `applicationId`
   - `MainActivity.java` → `package` declaration
   - Rename the source folder to match
5. Update app name in `res/values/strings.xml`
6. Replace the icon via **right-click `res` → New → Image Asset** (512×512 PNG recommended)
7. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
8. Find the APK at `app/build/outputs/apk/debug/app-debug.apk`

Install on your phone with **"Install from unknown sources"** enabled, then test camera capture and playback end-to-end.

For a Play Store release, use **Build → Generate Signed Bundle / APK** and follow the signing wizard.

---

## 🎛️ OCR tuning guide

Try these adjustments when accuracy is poor:

| Symptom | Fix |
|---|---|
| Text too thin / broken up | Lower **Adaptive C** (try 5–8) |
| Text too black / merged | Raise **Adaptive C** (try 15–20) |
| Fine print being lost | Lower **Adaptive block size** (try 15–21) |
| Large lighting gradient across page | Raise **Adaptive block size** (try 51–81) |
| Salt-and-pepper noise | Keep **Denoise** on |
| Text is small / blurry | Raise **Upscale** to 1.5–2.0 |
| Slight rotation | Currently unsupported — deskew step is a planned enhancement |
| Mixed languages | Add a second language in **"Also detect"** |

Use the **"What the OCR sees"** tab to verify preprocessing visually — if the binarized image looks clean, the OCR output usually will too.

### Getting the best accuracy: switch to `tessdata_best`

The default `tessdata_fast` models are quick but less accurate. Replacing them with `tessdata_best` (paired with `--oem 1`, which this code already uses) yields a substantial accuracy improvement at the cost of 2–3× slower inference.

1. Download `*.traineddata` for your languages from the [tessdata_best repo](https://github.com/tesseract-ocr/tessdata_best)
2. Replace the same-named files in Tesseract's `tessdata` directory
3. Restart the app — no code changes needed

---

## ⚙️ Configuration

### Adding a new language

Edit the `LANGUAGES` dict at the top of `app.py`:

```python
LANGUAGES = {
    "English": ("eng", "en", "en-IN-NeerjaNeural"),
    "Hindi":   ("hin", "hi", "hi-IN-SwaraNeural"),
    "Chinese": ("chi_sim", "zh", "zh-CN-XiaoxiaoNeural"),   # ← add here
    # ...
}
```

Format: `"Display Name": (tesseract_code, gTTS_code, edge_tts_voice)`.

The new entry appears in the sidebar automatically. Remember to add the Tesseract language pack (`tesseract-ocr-chi-sim`) to `packages.txt` for cloud deployment, and install it locally (`brew install tesseract-lang` or `apt install tesseract-ocr-chi-sim`).

### Preprocessing defaults that work well for phone photos

| Setting | Value |
|---|---|
| Upscale | 1.5 – 2.0 |
| Adaptive thresholding | ✅ on |
| Denoise | ✅ on |
| Adaptive block size | 31 – 51 |
| Adaptive C | 10 – 15 |

Turn adaptive thresholding on, leave everything else at the defaults, and adjust from there using the live preview.

---

## 🐛 Troubleshooting

### `TesseractNotFoundError`

Tesseract isn't installed or isn't on `PATH`. Install it (see [Quick start](#-quick-start-local)) and either add it to `PATH` or set `pytesseract.pytesseract.tesseract_cmd` in `app.py`.

### `Tesseract language data missing: hin` (or similar)

The language pack isn't installed. Add it locally (`apt install tesseract-ocr-hin`, etc.) or to `packages.txt` for cloud deployment.

### `AttributeError: 'NoneType' object has no attribute 'getvalue'`

Two common causes:

1. **A stale Streamlit process is still running** — kill all Python/Streamlit processes and close the browser tab, then restart. This is the most likely cause.
2. **Streamlit is too old** (`st.stop()` handling changed around v1.16). Run `streamlit version` and upgrade with `pip install --upgrade streamlit`.

### `Image too large` from Tesseract

Tesseract has a hard limit of **32767 pixels** on either dimension. If your image or upscale factor pushes past that, downscale the image before uploading, or cap the upscale slider in the sidebar.

### Adaptive thresholding checkbox is missing

OpenCV isn't installed. Run `pip install opencv-python-headless` (or check that `packages.txt`/`requirements.txt` include it for cloud).

### Camera capture fails on Streamlit Cloud

Some mobile browsers block camera access on plain HTTP or without user permission. Test over HTTPS (Streamlit Cloud serves HTTPS by default) and confirm the browser is prompting for camera permission. iOS Safari in particular may need a page reload after granting permission.

---

## 📁 Project structure

```
.
├── app.py                # The whole app (UI, preprocessing, OCR, TTS)
├── requirements.txt      # Python dependencies
├── packages.txt          # System dependencies (Tesseract + language packs)
└── README.md
```

Everything lives in `app.py` deliberately — it's small enough to keep the whole pipeline readable in one file, and Streamlit's caching works cleanly against a single module.

---

## 📌 Limitations

- **One image per run.** Batch processing would require `accept_multiple_files=True` and a loop.
- **Tesseract's 32767-pixel dimension limit** applies to both original dimensions and after upscaling.
- **`st.camera_input` uses the browser camera**, not the native Android camera app. Image quality is compressed, and the front camera opens by default.
- **The APK is a WebView wrapper** — requires an internet connection and doesn't provide native navigation gestures.
- **pyttsx3 on Streamlit Cloud** usually falls back to whatever system voices are installed; on the free tier these are often limited. **gTTS** and **edge-tts** are the more reliable choices when deployed.
- **Streamlit Community Cloud free tier** has 1 GB RAM and sleeps after 7 days of inactivity (wakes on next visit, with a few seconds of latency).

---

## 🗺️ Roadmap

- [ ] **Deskew step** — auto-correct image rotation (1–5°) using OpenCV `minAreaRect` before OCR
- [ ] **LLM post-processing** — optional GPT/Claude pass to fix residual OCR errors (research shows CER dropping below 3% on Tesseract output)
- [ ] **Batch mode** — accept multiple files and zip the resulting audio
- [ ] **Native Android** — Kotlin + ML Kit + `TextToSpeech` rewrite for a true camera experience

---

## 🙏 Credits & dependencies

- **[Streamlit](https://streamlit.io)** — UI framework
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** via **[pytesseract](https://github.com/madmaze/pytesseract)** — OCR engine
- **[OpenCV](https://opencv.org)** — adaptive thresholding and denoising
- **[gTTS](https://github.com/pndurette/gTTS)** — Google Translate TTS
- **[edge-tts](https://github.com/rany2/edge-tts)** — Microsoft Edge neural voices
- **[pyttsx3](https://github.com/nateshmbhat/pyttsx3)** — offline system TTS
- **[androidwrapper4streamlit](https://github.com/luiscunhacsc/androidwrapper4streamlit)** — Android WebView shell

---

## 📄 License

Tesseract itself is Apache-2.0 and the trained data follows its own licensing — check the [tessdata_best repo](https://github.com/tesseract-ocr/tessdata_best) for details.
