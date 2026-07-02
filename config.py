"""
config.py — Konfigurasi global untuk Auto Clipper.
Ubah nilai di sini sesuai kebutuhan project kamu.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
TEMP_DIR    = BASE_DIR / "temp"
OUTPUT_DIR  = BASE_DIR / "output"
ASSETS_DIR  = BASE_DIR / "assets"
FONTS_DIR   = ASSETS_DIR / "fonts"
MUSIC_DIR   = ASSETS_DIR / "music"
LOGOS_DIR   = ASSETS_DIR / "logos"

for _dir in [TEMP_DIR, OUTPUT_DIR]:
    _dir.mkdir(exist_ok=True)

# ─── Download ─────────────────────────────────────────────────────────────────
DOWNLOAD_QUALITY = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
DOWNLOAD_FORMAT  = "mp4"

# ─── Transcription ────────────────────────────────────────────────────────────
WHISPER_MODEL    = "base"          # tiny | base | small | medium | large-v3
WHISPER_LANGUAGE = "id"              # "id" = Bahasa Indonesia, "en" = English, None = auto-detect
WHISPER_DEVICE   = "cpu"             # "cpu" | "cuda" (GPU)
WHISPER_COMPUTE  = "int8"            # "int8" | "float16" | "float32"

# ─── Analyzer ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY", "")
DISCORD_BOT_TOKEN     = os.getenv("DISCORD_BOT_TOKEN", "")
GEMINI_MODEL          = "gemini-1.5-flash"
MAX_HIGHLIGHTS        = 5            # Maksimal jumlah klip yang diambil
MIN_CLIP_DURATION     = 30           # detik — klip minimal
MAX_CLIP_DURATION     = 90           # detik — klip maksimal
HIGHLIGHT_CONTEXT_SEC = 5            # detik padding sebelum/sesudah highlight

# ─── Video Output ─────────────────────────────────────────────────────────────
OUTPUT_RESOLUTION   = (1080, 1920)   # (width, height) → 9:16 portrait
OUTPUT_FPS          = 30
OUTPUT_CODEC        = "libx264"
OUTPUT_AUDIO_CODEC  = "aac"
OUTPUT_BITRATE      = "8M"
OUTPUT_PRESET       = "fast"         # ultrafast | fast | medium | slow

# ─── Face Tracking ────────────────────────────────────────────────────────────
FACE_DETECTION_SCALE   = 1.1
FACE_DETECTION_NEIGHBORS = 5
FACE_SMOOTH_FRAMES     = 15          # Frame smoothing untuk mengurangi jitter
FACE_PADDING           = 0.3         # Padding di sekitar wajah (30%)

# ─── Subtitle ─────────────────────────────────────────────────────────────────
SUBTITLE_FONT         = str(FONTS_DIR / "Montserrat-Bold.ttf")
SUBTITLE_FONT_SIZE    = 56
SUBTITLE_COLOR        = "&H00FFFFFF"  # ASS format — putih
SUBTITLE_OUTLINE      = "&H00000000"  # ASS format — hitam
SUBTITLE_OUTLINE_SIZE = 3
SUBTITLE_POSITION     = "bottom"      # "top" | "center" | "bottom"
SUBTITLE_MAX_CHARS    = 40            # Maksimal karakter per baris

# ─── Watermark (opsional) ─────────────────────────────────────────────────────
WATERMARK_ENABLED  = False
WATERMARK_PATH     = str(LOGOS_DIR / "logo.png")
WATERMARK_POSITION = "top-right"     # "top-left" | "top-right" | "bottom-left" | "bottom-right"
WATERMARK_OPACITY  = 0.8
WATERMARK_SCALE    = 0.1             # 10% dari lebar video

# ─── Background Music (opsional) ──────────────────────────────────────────────
MUSIC_ENABLED  = False
MUSIC_PATH     = str(MUSIC_DIR / "background.mp3")
MUSIC_VOLUME   = 0.15                # 0.0 – 1.0

# ─── Misc ─────────────────────────────────────────────────────────────────────
CLEANUP_TEMP   = True                # Hapus file temp setelah selesai
LOG_LEVEL      = "INFO"              # DEBUG | INFO | WARNING | ERROR
