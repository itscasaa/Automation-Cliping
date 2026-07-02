"""
local.py — Ambil video dari folder lokal.
"""

import shutil
from pathlib import Path
from rich.console import Console
from config import TEMP_DIR

console = Console()

SUPPORTED_FORMATS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv"}


class LocalVideoLoader:
    """Validasi dan salin video lokal ke folder temp."""

    def __init__(self, output_dir: Path = TEMP_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load(self, path: str, filename: str = "original_video") -> Path:
        """
        Validasi dan salin video ke folder temp.

        Args:
            path: Path ke file video lokal.
            filename: Nama file output (tanpa ekstensi).

        Returns:
            Path ke file video di folder temp.
        """
        source = Path(path).resolve()

        if not source.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {source}")

        if source.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Format tidak didukung: {source.suffix}. "
                f"Format yang didukung: {', '.join(SUPPORTED_FORMATS)}"
            )

        dest = self.output_dir / f"{filename}{source.suffix}"

        if source == dest:
            console.print(f"[yellow]⚠  File sudah di temp, skip copy.[/yellow]")
            return dest

        console.print(f"[cyan]📂 Menyalin video:[/cyan] {source.name}")
        shutil.copy2(source, dest)

        size_mb = dest.stat().st_size / (1024 * 1024)
        console.print(f"[green]✓  Video siap:[/green] {dest.name} ({size_mb:.1f} MB)")
        return dest

    @staticmethod
    def list_videos(folder: str) -> list[Path]:
        """Tampilkan semua video yang tersedia di folder."""
        folder_path = Path(folder)
        videos = [
            f for f in folder_path.iterdir()
            if f.suffix.lower() in SUPPORTED_FORMATS
        ]
        return sorted(videos)
