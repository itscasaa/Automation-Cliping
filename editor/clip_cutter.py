"""
clip_cutter.py — Potong video berdasarkan list highlight menggunakan ffmpeg.
"""

import subprocess
from pathlib import Path

from rich.console import Console

from config import (
    TEMP_DIR, OUTPUT_DIR, OUTPUT_FPS,
    OUTPUT_CODEC, OUTPUT_AUDIO_CODEC, OUTPUT_BITRATE, OUTPUT_PRESET,
    OUTPUT_RESOLUTION,
)

console = Console()
TARGET_W, TARGET_H = OUTPUT_RESOLUTION


class ClipCutter:
    """Potong video per highlight dan resize ke 9:16."""

    def __init__(self):
        self._check_ffmpeg()

    def cut(
        self,
        video_path: Path,
        highlight,
        crop_filter: str,
        subtitle_path: Path = None,
        output_dir: Path = OUTPUT_DIR,
    ) -> Path:
        """
        Potong satu highlight dari video sumber.

        Args:
            video_path: Path video sumber (dari temp/).
            highlight: Objek Highlight dengan start/end/title.
            crop_filter: String ffmpeg filter dari FaceTracker.
            subtitle_path: Path ke file .ass (opsional).
            output_dir: Folder output.

        Returns:
            Path ke file klip yang sudah jadi.
        """
        safe_title = self._safe_filename(highlight.title)
        output_path = output_dir / f"clip_{highlight.id:02d}_{safe_title}.mp4"

        duration = highlight.end - highlight.start

        # Build filter chain
        vf_parts = [crop_filter]

        if subtitle_path and subtitle_path.exists():
            # Escape path untuk ffmpeg (khususnya Windows)
            sub_str = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
            vf_parts.append(f"ass='{sub_str}'")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(highlight.start),
            "-i", str(video_path),
            "-t", str(duration),
            "-vf", vf,
            "-r", str(OUTPUT_FPS),
            "-c:v", OUTPUT_CODEC,
            "-preset", OUTPUT_PRESET,
            "-b:v", OUTPUT_BITRATE,
            "-c:a", OUTPUT_AUDIO_CODEC,
            "-movflags", "+faststart",
            str(output_path),
        ]

        console.print(
            f"[cyan]✂  Memotong klip {highlight.id}:[/cyan] "
            f"{highlight.start:.1f}s – {highlight.end:.1f}s "
            f"({duration:.1f}s)"
        )

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg error saat memotong klip {highlight.id}:\n{result.stderr}"
            )

        size_mb = output_path.stat().st_size / (1024 * 1024)
        console.print(
            f"[green]✓  Klip {highlight.id} selesai:[/green] "
            f"{output_path.name} ({size_mb:.1f} MB)"
        )
        return output_path

    def cut_all(
        self,
        video_path: Path,
        highlights: list,
        crop_windows_per_highlight: dict,
        subtitle_path: Path = None,
        output_dir: Path = OUTPUT_DIR,
    ) -> list[Path]:
        """
        Potong semua highlight sekaligus.

        Args:
            video_path: Video sumber.
            highlights: List objek Highlight.
            crop_windows_per_highlight: Dict {highlight_id: crop_filter_str}.
            subtitle_path: Path subtitle .ass global.
            output_dir: Folder output.

        Returns:
            List path klip yang berhasil dipotong.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[Path] = []

        for h in highlights:
            crop = crop_windows_per_highlight.get(h.id, f"scale={TARGET_W}:{TARGET_H}")
            try:
                path = self.cut(video_path, h, crop, subtitle_path, output_dir)
                results.append(path)
            except RuntimeError as e:
                console.print(f"[red]✗  Klip {h.id} gagal:[/red] {e}")

        console.print(
            f"\n[bold green]🎬 {len(results)}/{len(highlights)} klip berhasil dibuat![/bold green]"
        )
        return results

    @staticmethod
    def _safe_filename(title: str) -> str:
        """Hapus karakter yang tidak valid untuk nama file."""
        invalid = r'\/:*?"<>|'
        clean = "".join(c if c not in invalid else "_" for c in title)
        return clean[:50].strip()

    @staticmethod
    def _check_ffmpeg() -> None:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(
                "ffmpeg tidak ditemukan! Install dulu: https://ffmpeg.org/download.html"
            )
