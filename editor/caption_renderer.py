"""
caption_renderer.py — Render subtitle .ass ke dalam video klip.
Subtitle sudah di-embed saat ClipCutter memotong, tapi modul ini
menyediakan method tambahan untuk post-processing atau preview.
"""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from config import OUTPUT_CODEC, OUTPUT_AUDIO_CODEC, OUTPUT_BITRATE, OUTPUT_PRESET, TEMP_DIR

console = Console()


class CaptionRenderer:
    """
    Burn subtitle ke dalam video menggunakan ffmpeg ASS filter.
    Jika ClipCutter sudah menghandel subtitle, kelas ini berguna
    untuk burn-in subtitle ke klip yang sudah dipotong (post-process).
    """

    def burn_subtitles(
        self,
        clip_path: Path,
        subtitle_path: Path,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Burn subtitle .ass/.srt ke dalam video.

        Args:
            clip_path: Video input (klip yang sudah dipotong).
            subtitle_path: File .ass atau .srt.
            output_path: Nama output. Default: menimpa input (via temp).

        Returns:
            Path ke video dengan subtitle ter-burn.
        """
        if output_path is None:
            temp_out = TEMP_DIR / f"_tmp_{clip_path.name}"
        else:
            temp_out = output_path

        ext = subtitle_path.suffix.lower()
        sub_str = str(subtitle_path).replace("\\", "/").replace(":", "\\:")

        if ext == ".ass":
            vf = f"ass='{sub_str}'"
        elif ext == ".srt":
            vf = f"subtitles='{sub_str}'"
        else:
            raise ValueError(f"Format subtitle tidak didukung: {ext}")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-vf", vf,
            "-c:v", OUTPUT_CODEC,
            "-preset", OUTPUT_PRESET,
            "-b:v", OUTPUT_BITRATE,
            "-c:a", OUTPUT_AUDIO_CODEC,
            str(temp_out),
        ]

        console.print(f"[cyan]📝 Burning subtitle:[/cyan] {clip_path.name}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Gagal burn subtitle:\n{result.stderr}")

        # Replace asli jika tidak ada output_path
        if output_path is None:
            clip_path.unlink()
            temp_out.rename(clip_path)
            console.print(f"[green]✓  Subtitle burned:[/green] {clip_path.name}")
            return clip_path

        console.print(f"[green]✓  Subtitle burned:[/green] {output_path.name}")
        return output_path

    def trim_subtitle_for_clip(
        self,
        segments,
        clip_start: float,
        clip_end: float,
        output_path: Path,
        mode: str = "ass",
    ) -> Path:
        """
        Buat file subtitle yang sudah di-offset untuk sebuah klip.
        (Timestamps disesuaikan agar mulai dari 0 untuk klip tersebut.)

        Args:
            segments: List Segment dari WhisperTranscriber.
            clip_start: Waktu mulai klip (detik) dari video asli.
            clip_end: Waktu selesai klip (detik) dari video asli.
            output_path: Path untuk menyimpan file subtitle klip.
            mode: "ass" atau "srt".

        Returns:
            Path ke file subtitle yang sudah di-trim.
        """
        from transcriber.whisper_stt import Segment
        from transcriber.srt_generator import SRTGenerator

        # Filter dan offset segmen
        clipped = []
        for seg in segments:
            if seg.end < clip_start or seg.start > clip_end:
                continue
            from dataclasses import replace
            clipped.append(
                Segment(
                    id=seg.id,
                    start=max(0.0, seg.start - clip_start),
                    end=min(clip_end - clip_start, seg.end - clip_start),
                    text=seg.text,
                    words=seg.words,
                )
            )

        gen = SRTGenerator()
        if mode == "ass":
            return gen.generate_ass(clipped, output_path)
        else:
            return gen.generate_srt(clipped, output_path)
