# 🎬 Auto Clipper

Ubah video YouTube atau video lokal panjang menjadi **klip viral 9:16** secara otomatis — siap upload ke TikTok, Reels, dan YouTube Shorts.

## Fitur

- **Download otomatis** dari YouTube via `yt-dlp`
- **Transkripsi lokal** (offline) dengan `faster-whisper`
- **AI Highlight Finder** — Claude memilih momen terbaik dari transkrip
- **Face Tracking** — auto-crop 9:16 mengikuti wajah speaker dengan OpenCV
- **Subtitle animasi** — render caption `.ass` ke dalam klip
- **Watermark opsional** — tambahkan logo ke semua klip

---

## Struktur Folder

```
auto-clipper/
├── main.py              ← Entry point
├── config.py            ← Semua konfigurasi
├── requirements.txt
├── downloader/          ← YouTube & lokal
├── transcriber/         ← Whisper STT + SRT/ASS generator
├── analyzer/            ← Claude AI highlight finder
├── editor/              ← Crop, cut, subtitle, watermark
├── assets/              ← Font, musik, logo
├── output/              ← Klip hasil jadi
└── temp/                ← File sementara (auto-cleanup)
```

---

## Instalasi

### 1. Clone & masuk ke folder
```bash
git clone <repo-url>
cd auto-clipper
```

### 2. Buat virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Install ffmpeg
- **Mac:** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **Windows:** Download dari https://ffmpeg.org/download.html dan tambahkan ke PATH

### 5. Setup API Key
Buat file `.env` di root folder:
```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### 6. (Opsional) Tambahkan font
Letakkan `Montserrat-Bold.ttf` di folder `assets/fonts/`. Download gratis di [Google Fonts](https://fonts.google.com/specimen/Montserrat).

---

## Cara Pakai

### Dari YouTube URL
```bash
python main.py --url "https://youtu.be/VIDEO_ID"
```

### Dari file lokal
```bash
python main.py --file /path/to/video.mp4
```

### Dengan opsi tambahan
```bash
# Tipe konten podcast, maksimal 3 klip, bahasa Indonesia
python main.py --url "https://youtu.be/VIDEO_ID" \
               --type podcast \
               --max-clips 3 \
               --lang id

# Skip transkripsi (gunakan file JSON yang sudah ada)
python main.py --file video.mp4 --skip-transcribe temp/transcript.json

# Nonaktifkan face tracking (crop tengah saja)
python main.py --file video.mp4 --no-face-track
```

### Semua opsi
| Opsi | Default | Keterangan |
|------|---------|------------|
| `--url` | — | URL YouTube |
| `--file` | — | Path video lokal |
| `--type` | `general` | Tipe konten: `general`, `educational`, `podcast`, `gaming` |
| `--max-clips` | 5 | Maksimal jumlah klip |
| `--lang` | `id` | Bahasa: `id`, `en`, atau `None` (auto-detect) |
| `--no-face-track` | — | Nonaktifkan face tracking |
| `--skip-transcribe` | — | Path ke `transcript.json` yang sudah ada |
| `--output-dir` | `output/` | Folder output klip |

---

## Konfigurasi

Edit `config.py` untuk menyesuaikan:

```python
# Model Whisper (lebih besar = lebih akurat, lebih lambat)
WHISPER_MODEL = "medium"   # tiny | base | small | medium | large-v3

# Durasi klip
MIN_CLIP_DURATION = 30     # detik
MAX_CLIP_DURATION = 90     # detik

# Resolusi output
OUTPUT_RESOLUTION = (1080, 1920)   # 9:16 portrait

# Aktifkan watermark
WATERMARK_ENABLED = True
WATERMARK_PATH = "assets/logos/logo.png"

# Aktifkan background music
MUSIC_ENABLED = True
MUSIC_PATH = "assets/music/background.mp3"
```

---

## Alur Pipeline

```
Input (URL / file lokal)
    ↓
downloader/     →  video asli (.mp4)
    ↓
transcriber/    →  teks + timestamp (.json + .ass)
    ↓
analyzer/       →  list highlight (start, end, judul) via Claude AI
    ↓
editor/         →  crop 9:16 + potong + subtitle
    ↓
output/         →  klip siap upload 🎬
```

---

## Menjalankan Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Tips Performa

| Kebutuhan | Rekomendasi |
|-----------|-------------|
| Video pendek (<1 jam) | `WHISPER_MODEL = "medium"` |
| Video panjang (>1 jam) | `WHISPER_MODEL = "small"` |
| Punya GPU NVIDIA | `WHISPER_DEVICE = "cuda"`, `WHISPER_COMPUTE = "float16"` |
| Ingin lebih cepat | `WHISPER_MODEL = "base"`, `OUTPUT_PRESET = "ultrafast"` |
| Kualitas terbaik | `WHISPER_MODEL = "large-v3"`, `OUTPUT_PRESET = "slow"` |

---

## Troubleshooting

**`ANTHROPIC_API_KEY tidak ditemukan`**
→ Pastikan file `.env` ada dan berisi `ANTHROPIC_API_KEY=sk-ant-...`

**`ffmpeg tidak ditemukan`**
→ Install ffmpeg dan pastikan sudah ada di PATH

**Transkripsi terlalu lambat**
→ Gunakan model lebih kecil: `WHISPER_MODEL = "small"` di `config.py`

**Subtitle tidak muncul di output**
→ Pastikan font `Montserrat-Bold.ttf` ada di `assets/fonts/`

**Face tracking tidak akurat**
→ Coba `--no-face-track` untuk crop tengah, atau adjust `FACE_PADDING` di `config.py`

---

## Lisensi

MIT License — bebas digunakan dan dimodifikasi.
