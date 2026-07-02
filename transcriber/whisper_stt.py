"""
whisper_stt.py — Transkripsi audio menggunakan faster-whisper (lokal, offline).
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from faster_whisper import WhisperModel
from rich.console import Console
from rich.progress import track

from config import (
    TEMP_DIR, WHISPER_MODEL, WHISPER_LANGUAGE,
    WHISPER_DEVICE, WHISPER_COMPUTE,
)

console = Console()


@dataclass
class Segment:
    """Satu segmen transkrip dengan timestamp."""
    id: int
    start: float       # detik
    end: float         # detik
    text: str
    words: list        # [{"word": str, "start": float, "end": float}]

    @property
    def duration(self) -> float:
        return self.end - self.start


class WhisperTranscriber:
    """Transkripsi audio/video menggunakan faster-whisper."""

    def __init__(self):
        console.print(
            f"[cyan]🎙  Memuat Whisper model:[/cyan] [bold]{WHISPER_MODEL}[/bold] "
            f"(device={WHISPER_DEVICE}, compute={WHISPER_COMPUTE})"
        )
        self.model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
        )

    def transcribe(
        self,
        video_path: Path,
        output_json: Optional[Path] = None,
        language: Optional[str] = WHISPER_LANGUAGE,
    ) -> list[Segment]:
        """
        Transkripsi video/audio.

        Args:
            video_path: Path ke file video atau audio.
            output_json: Path untuk menyimpan hasil JSON (opsional).
            language: Kode bahasa (mis. "id", "en"). None = auto-detect.

        Returns:
            List of Segment objects.
        """
        console.print(f"[cyan]🔊 Memulai transkripsi:[/cyan] {video_path.name}")

        segments_raw, info = self.model.transcribe(
            str(video_path),
            language=language,
            word_timestamps=True,
            vad_filter=True,              # hapus bagian sunyi
            vad_parameters={"min_silence_duration_ms": 500},
        )

        console.print(
            f"[dim]  Bahasa terdeteksi: {info.language} "
            f"(confidence: {info.language_probability:.0%})[/dim]"
        )

        segments: list[Segment] = []
        for i, seg in enumerate(segments_raw):
            words = []
            if seg.words:
                words = [
                    {"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
                    for w in seg.words
                ]
            segments.append(
                Segment(
                    id=i,
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=seg.text.strip(),
                    words=words,
                )
            )

        console.print(
            f"[green]✓  Transkripsi selesai:[/green] "
            f"{len(segments)} segmen, durasi total "
            f"{segments[-1].end:.1f}s"
        )

        # Simpan ke JSON
        if output_json is None:
            output_json = TEMP_DIR / "transcript.json"

        self._save_json(segments, output_json)
        return segments

    @staticmethod
    def _save_json(segments: list[Segment], path: Path) -> None:
        data = {
            "segments": [asdict(s) for s in segments],
            "total_segments": len(segments),
            "duration": segments[-1].end if segments else 0,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[dim]  Transkrip disimpan: {path}[/dim]")

    @staticmethod
    def load_json(path: Path) -> list[Segment]:
        """Muat transkrip dari file JSON yang sudah ada."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return [Segment(**s) for s in data["segments"]]
