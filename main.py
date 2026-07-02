"""
main.py — Entry point Auto Clipper.

Cara pakai:
    python main.py --url "https://youtu.be/xxxx"
    python main.py --file /path/to/video.mp4
    python main.py --url "..." --type podcast --max-clips 3
"""

import argparse
import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import config
from downloader import YouTubeDownloader, LocalVideoLoader
from transcriber import WhisperTranscriber, SRTGenerator
from analyzer import HighlightFinder
from editor import FaceTracker, ClipCutter, CaptionRenderer, WatermarkAdder

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="🎬 Auto Clipper — Buat klip viral dari video panjang secara otomatis"
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url",  type=str, help="URL video YouTube")
    source.add_argument("--file", type=str, help="Path ke video lokal")

    parser.add_argument(
        "--type",
        type=str,
        default="general",
        choices=["general", "educational", "podcast", "gaming"],
        help="Tipe konten video (default: general)",
    )
    parser.add_argument(
        "--max-clips",
        type=int,
        default=config.MAX_HIGHLIGHTS,
        help=f"Maksimal jumlah klip output (default: {config.MAX_HIGHLIGHTS})",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=config.WHISPER_LANGUAGE,
        help='Bahasa video: "id", "en", atau None untuk auto-detect',
    )
    parser.add_argument(
        "--no-face-track",
        action="store_true",
        help="Nonaktifkan face tracking (gunakan crop tengah saja)",
    )
    parser.add_argument(
        "--skip-transcribe",
        type=str,
        default=None,
        metavar="TRANSCRIPT_JSON",
        help="Skip transkripsi, pakai file JSON yang sudah ada",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(config.OUTPUT_DIR),
        help=f"Folder output klip (default: {config.OUTPUT_DIR})",
    )
    return parser.parse_args()


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🎬 AUTO CLIPPER[/bold cyan]\n"
        "[dim]YouTube / Local Video → Viral Short Clips[/dim]",
        border_style="cyan",
    ))


def print_summary(highlights, clip_paths: list[Path]):
    table = Table(title="✅ Hasil Klip", show_lines=True)
    table.add_column("ID",    style="dim",    width=4)
    table.add_column("Judul", style="bold",   min_width=30)
    table.add_column("Durasi",               width=10)
    table.add_column("File",  style="green")

    for h, p in zip(highlights, clip_paths):
        table.add_row(
            str(h.id),
            h.title,
            f"{h.duration:.1f}s",
            p.name if p.exists() else "[red]GAGAL[/red]",
        )

    console.print(table)
    console.print(f"\n[bold]📁 Output folder:[/bold] {config.OUTPUT_DIR.resolve()}")


def main():
    print_banner()
    args = parse_args()

    # Validasi API key di awal sebelum memproses video
    if not config.GEMINI_API_KEY:
        console.print(
            "[bold red]✗ Error: GEMINI_API_KEY tidak ditemukan![/bold red]\n"
            "[yellow]Pastikan Anda telah membuat file .env di root folder dan mengisi:\n"
            "GEMINI_API_KEY=AIzaSy...[/yellow]"
        )
        sys.exit(1)

    # Update config dari argumen
    config.MAX_HIGHLIGHTS = args.max_clips
    config.WHISPER_LANGUAGE = args.lang if args.lang != "None" else None
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ─── Step 1: Download / Load Video ───────────────────────────────────────
    console.rule("[bold cyan]STEP 1 — Input Video[/bold cyan]")

    if args.url:
        downloader = YouTubeDownloader()
        video_path = downloader.download(args.url)
    else:
        loader = LocalVideoLoader()
        video_path = loader.load(args.file)

    # ─── Step 2: Transkripsi ──────────────────────────────────────────────────
    console.rule("[bold cyan]STEP 2 — Transkripsi[/bold cyan]")

    if args.skip_transcribe:
        console.print(f"[yellow]⚡ Skip transkripsi, memuat:[/yellow] {args.skip_transcribe}")
        segments = WhisperTranscriber.load_json(Path(args.skip_transcribe))
    else:
        transcriber = WhisperTranscriber()
        segments = transcriber.transcribe(video_path, language=args.lang)

    # Generate file subtitle (akan dipakai saat cutting)
    srt_gen = SRTGenerator()
    subtitle_path = srt_gen.generate_ass(segments)

    # ─── Step 3: Analisis Highlight ───────────────────────────────────────────
    console.rule("[bold cyan]STEP 3 — AI Highlight Finder[/bold cyan]")

    finder = HighlightFinder()
    video_duration = segments[-1].end if segments else None
    highlights = finder.find_highlights(
        segments,
        content_type=args.type,
        video_duration=video_duration,
    )

    if not highlights:
        console.print("[red]✗  Tidak ada highlight yang ditemukan. Coba ubah --type.[/red]")
        sys.exit(1)

    # ─── Step 4: Face Tracking ────────────────────────────────────────────────
    console.rule("[bold cyan]STEP 4 — Face Tracking & Crop[/bold cyan]")

    crop_per_highlight: dict[int, str] = {}
    caption_renderer = CaptionRenderer()

    if args.no_face_track:
        console.print("[yellow]⚠  Face tracking dinonaktifkan — menggunakan crop tengah.[/yellow]")
        default_crop = (
            f"crop={config.OUTPUT_RESOLUTION[0]}:{config.OUTPUT_RESOLUTION[1]},"
            f"scale={config.OUTPUT_RESOLUTION[0]}:{config.OUTPUT_RESOLUTION[1]}"
        )
        for h in highlights:
            crop_per_highlight[h.id] = default_crop
    else:
        tracker = FaceTracker()
        # Analisis satu kali untuk seluruh video, lalu assign per highlight
        windows = tracker.analyze(video_path)
        for h in highlights:
            crop_per_highlight[h.id] = tracker.get_ffmpeg_crop_filter(
                windows, start_time=h.start, end_time=h.end
            )

    # ─── Step 5: Potong & Render Klip ─────────────────────────────────────────
    console.rule("[bold cyan]STEP 5 — Cutting & Rendering[/bold cyan]")

    cutter = ClipCutter()

    # Buat subtitle per klip (timestamp offset)
    clip_subtitle_paths: dict[int, Path] = {}
    for h in highlights:
        sub_out = config.TEMP_DIR / f"sub_clip_{h.id:02d}.ass"
        path = caption_renderer.trim_subtitle_for_clip(
            segments, h.start, h.end, sub_out, mode="ass"
        )
        clip_subtitle_paths[h.id] = path

    clip_paths: list[Path] = []
    for h in highlights:
        try:
            p = cutter.cut(
                video_path=video_path,
                highlight=h,
                crop_filter=crop_per_highlight[h.id],
                subtitle_path=clip_subtitle_paths.get(h.id),
                output_dir=output_dir,
            )
            clip_paths.append(p)
        except Exception as e:
            console.print(f"[red]✗  Klip {h.id} gagal:[/red] {e}")

    # ─── Step 6: Watermark (opsional) ────────────────────────────────────────
    if config.WATERMARK_ENABLED:
        console.rule("[bold cyan]STEP 6 — Watermark[/bold cyan]")
        wm = WatermarkAdder()
        clip_paths = wm.add_to_all(clip_paths)

    # ─── Cleanup Temp ─────────────────────────────────────────────────────────
    if config.CLEANUP_TEMP:
        console.print("[dim]🧹 Membersihkan file temp...[/dim]")
        for f in config.TEMP_DIR.iterdir():
            if f.is_file():
                f.unlink()

    # ─── Summary ──────────────────────────────────────────────────────────────
    console.rule("[bold green]SELESAI![/bold green]")
    print_summary(highlights, clip_paths)


if __name__ == "__main__":
    main()
