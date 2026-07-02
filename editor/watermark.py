"""
watermark.py — Tambahkan watermark/logo ke klip (opsional).
"""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from config import (
    WATERMARK_ENABLED, WATERMARK_PATH, WATERMARK_POSITION,
    WATERMARK_OPACITY, WATERMARK_SCALE, TEMP_DIR,
    OUTPUT_CODEC, OUTPUT_AUDIO_CODEC, OUTPUT_BITRATE, OUTPUT_PRESET,
    OUTPUT_RESOLUTION,
)

console = Console()
TARGET_W, TARGET_H = OUTPUT_RESOLUTION

POSITION_MAP = {
    "top-left":     "10:10",
    "top-right":    f"W-w-10:10",
    "bottom-left":  "10:H-h-10",
    "bottom-right": "W-w-10:H-h-10",
    "center":       "(W-w)/2:(H-h)/2",
}


class WatermarkAdder:
    """Overlay logo/watermark di atas video menggunakan ffmpeg."""

    def add(
        self,
        clip_path: Path,
        logo_path: Optional[Path] = None,
        position: str = WATERMARK_POSITION,
        opacity: float = WATERMARK_OPACITY,
        scale: float = WATERMARK_SCALE,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Tambahkan watermark ke video.

        Args:
            clip_path: Video input.
            logo_path: Path ke file logo (PNG dengan transparansi).
            position: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center".
            opacity: Transparansi logo (0.0 – 1.0).
            scale: Ukuran logo relatif terhadap lebar video.
            output_path: Output path. Default: replace input.

        Returns:
            Path ke video dengan watermark.
        """
        if not WATERMARK_ENABLED:
            return clip_path

        if logo_path is None:
            logo_path = Path(WATERMARK_PATH)

        if not logo_path.exists():
            console.print(
                f"[yellow]⚠  Logo tidak ditemukan: {logo_path} — skip watermark.[/yellow]"
            )
            return clip_path

        temp_out = TEMP_DIR / f"_wm_{clip_path.name}"
        final_out = output_path or clip_path

        overlay_pos = POSITION_MAP.get(position, POSITION_MAP["bottom-right"])
        logo_w = int(TARGET_W * scale)

        # Filter:
        # 1. Scale logo ke ukuran yang ditentukan
        # 2. Atur opasitas dengan colorchannelmixer atau format+alphamerge
        # 3. Overlay di posisi yang ditentukan
        vf = (
            f"[1:v]scale={logo_w}:-1,"
            f"format=rgba,colorchannelmixer=aa={opacity}[logo];"
            f"[0:v][logo]overlay={overlay_pos}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-i", str(logo_path),
            "-filter_complex", vf,
            "-c:v", OUTPUT_CODEC,
            "-preset", OUTPUT_PRESET,
            "-b:v", OUTPUT_BITRATE,
            "-c:a", OUTPUT_AUDIO_CODEC,
            str(temp_out),
        ]

        console.print(f"[cyan]🏷  Menambahkan watermark:[/cyan] {clip_path.name}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            console.print(f"[red]✗  Watermark gagal:[/red] {result.stderr[-200:]}")
            return clip_path

        # Replace file asli
        if output_path is None:
            clip_path.unlink()
            temp_out.rename(clip_path)
            return clip_path

        temp_out.rename(final_out)
        console.print(f"[green]✓  Watermark selesai:[/green] {final_out.name}")
        return final_out

    def add_to_all(self, clip_paths: list[Path], **kwargs) -> list[Path]:
        """Tambahkan watermark ke semua klip."""
        return [self.add(p, **kwargs) for p in clip_paths]
