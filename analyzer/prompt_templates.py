"""
prompt_templates.py — Kumpulan prompt untuk menemukan highlight video.
Tambahkan template baru sesuai jenis konten yang kamu proses.
"""


class PromptTemplates:
    """Koleksi prompt siap pakai untuk berbagai genre konten."""

    SYSTEM = """Kamu adalah AI editor video profesional yang ahli memilih momen terbaik \
dari sebuah video untuk dijadikan konten viral di TikTok, Instagram Reels, dan YouTube Shorts.

Tugas kamu:
1. Analisis transkrip video yang diberikan.
2. Pilih {max_highlights} momen terbaik yang akan menarik perhatian penonton.
3. Setiap momen harus berdurasi antara {min_dur}–{max_dur} detik.
4. Kembalikan HANYA JSON valid, tanpa teks lain, tanpa markdown code block.

Format JSON yang harus dikembalikan:
{{
  "highlights": [
    {{
      "id": 1,
      "title": "Judul singkat klip (maks 60 karakter)",
      "start": 12.5,
      "end": 45.0,
      "reason": "Mengapa ini momen terbaik (1–2 kalimat)",
      "hook": "Kalimat pembuka yang bikin penonton penasaran",
      "tags": ["#tag1", "#tag2", "#tag3"]
    }}
  ]
}}"""

    @staticmethod
    def general(transcript_text: str, max_highlights: int, min_dur: int, max_dur: int) -> str:
        """Prompt umum untuk video apapun."""
        return f"""Berikut transkrip video dengan format [detik] teks:

{transcript_text}

Pilih {max_highlights} momen paling menarik, informatif, atau menghibur. \
Prioritaskan bagian yang mengandung:
- Insight mengejutkan atau fakta menarik
- Momen emosional atau lucu
- Puncak cerita / climax
- Nasihat / tips yang actionable
- Pertanyaan retoris yang engaging"""

    @staticmethod
    def educational(transcript_text: str, max_highlights: int, min_dur: int, max_dur: int) -> str:
        """Prompt untuk video edukasi / tutorial."""
        return f"""Transkrip video edukasi:

{transcript_text}

Pilih {max_highlights} momen yang mengandung:
- Penjelasan konsep paling penting
- Tips atau trik yang langsung bisa diaplikasikan
- Jawaban dari pertanyaan yang sering ditanyakan
- Momen "aha!" atau insight terbesar dalam video"""

    @staticmethod
    def podcast(transcript_text: str, max_highlights: int, min_dur: int, max_dur: int) -> str:
        """Prompt untuk podcast / interview."""
        return f"""Transkrip podcast/interview:

{transcript_text}

Pilih {max_highlights} momen terbaik yang mengandung:
- Pernyataan kontroversial atau mengejutkan
- Kisah personal yang relatable
- Kutipan inspiratif atau thought-provoking
- Argumen kuat yang bisa memancing diskusi
- Humor atau momen candid"""

    @staticmethod
    def gaming(transcript_text: str, max_highlights: int, min_dur: int, max_dur: int) -> str:
        """Prompt untuk video gaming / streaming."""
        return f"""Transkrip video gaming:

{transcript_text}

Pilih {max_highlights} momen yang mengandung:
- Momen epik atau comeback yang mengagumkan
- Reaksi ekstrem (kemenangan besar / kekalahan tragis)
- Aksi atau skill yang mengesankan
- Momen lucu atau fail yang menghibur
- Teori atau pembahasan lore menarik"""
