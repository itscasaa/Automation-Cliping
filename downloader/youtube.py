"""
youtube.py — Download video dari YouTube menggunakan yt-dlp.
"""

import yt_dlp
from pathlib import Path
from rich.console import Console
from config import TEMP_DIR, DOWNLOAD_QUALITY, DOWNLOAD_FORMAT

console = Console()


class YouTubeDownloader:
    """Download video YouTube ke folder temp."""

    def __init__(self, output_dir: Path = TEMP_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, filename: str = "original_video") -> Path:
        """
        Download video dari URL YouTube.

        Args:
            url: URL video YouTube.
            filename: Nama file output (tanpa ekstensi).

        Returns:
            Path ke file video yang sudah didownload.
        """
        output_template = str(self.output_dir / f"{filename}.%(ext)s")

        ydl_opts = {
            "format": DOWNLOAD_QUALITY,
            "outtmpl": output_template,
            "merge_output_format": DOWNLOAD_FORMAT,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": DOWNLOAD_FORMAT,
                }
            ],
        }

        console.print(f"[cyan]⬇  Downloading:[/cyan] {url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "unknown")
            duration = info.get("duration", 0)

        output_path = self.output_dir / f"{filename}.{DOWNLOAD_FORMAT}"

        console.print(
            f"[green]✓  Download selesai:[/green] [bold]{title}[/bold] "
            f"({duration // 60}m {duration % 60}s)"
        )
        return output_path

    def get_info(self, url: str) -> dict:
        """Ambil metadata video tanpa mendownload."""
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            return ydl.extract_info(url, download=False)

    @staticmethod
    def _progress_hook(d: dict) -> None:
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "?%").strip()
            speed = d.get("_speed_str", "?").strip()
            eta = d.get("_eta_str", "?").strip()
            print(f"\r  {pct}  speed: {speed}  ETA: {eta}   ", end="", flush=True)
        elif d["status"] == "finished":
            print()
