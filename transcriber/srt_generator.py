"""
srt_generator.py — Ubah transkrip menjadi file .srt atau .ass.
"""

import textwrap
from pathlib import Path
from dataclasses import dataclass

from rich.console import Console

from config import TEMP_DIR, SUBTITLE_MAX_CHARS, SUBTITLE_FONT_SIZE, SUBTITLE_COLOR, SUBTITLE_OUTLINE, SUBTITLE_OUTLINE_SIZE

console = Console()


def _seconds_to_srt_time(seconds: float) -> str:
    """00:01:23,456"""
    ms = int((seconds % 1) * 1000)
    s  = int(seconds) % 60
    m  = int(seconds) // 60 % 60
    h  = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_ass_time(seconds: float) -> str:
    """H:MM:SS.cc (centiseconds)"""
    cs = int((seconds % 1) * 100)
    s  = int(seconds) % 60
    m  = int(seconds) // 60 % 60
    h  = int(seconds) // 3600
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


class SRTGenerator:
    """Generate file subtitle .srt dan .ass dari list segmen transkrip."""

    def generate_srt(self, segments, output_path: Path = None) -> Path:
        """
        Buat file .srt standar.

        Args:
            segments: List Segment dari WhisperTranscriber.
            output_path: Path output (default: temp/subtitles.srt).

        Returns:
            Path ke file .srt.
        """
        if output_path is None:
            output_path = TEMP_DIR / "subtitles.srt"

        lines = []
        idx = 1
        for seg in segments:
            # Wrap teks panjang
            wrapped = textwrap.wrap(seg.text, SUBTITLE_MAX_CHARS) or [seg.text]
            text_block = "\n".join(wrapped)

            lines.append(str(idx))
            lines.append(
                f"{_seconds_to_srt_time(seg.start)} --> {_seconds_to_srt_time(seg.end)}"
            )
            lines.append(text_block)
            lines.append("")
            idx += 1

        output_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]✓  SRT disimpan:[/green] {output_path}")
        return output_path

    def generate_ass(self, segments, output_path: Path = None) -> Path:
        """
        Buat file .ass dengan styling animasi (untuk caption_renderer).

        Args:
            segments: List Segment.
            output_path: Path output (default: temp/subtitles.ass).

        Returns:
            Path ke file .ass.
        """
        if output_path is None:
            output_path = TEMP_DIR / "subtitles.ass"

        header = self._ass_header()
        events = []

        for seg in segments:
            wrapped = textwrap.wrap(seg.text, SUBTITLE_MAX_CHARS) or [seg.text]
            text = r"\N".join(wrapped)           # line break di ASS
            # Fade in/out effect
            effect = r"{\fad(150,150)}"
            events.append(
                f"Dialogue: 0,"
                f"{_seconds_to_ass_time(seg.start)},"
                f"{_seconds_to_ass_time(seg.end)},"
                f"Default,,0,0,0,,{effect}{text}"
            )

        content = header + "\n".join(events) + "\n"
        output_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓  ASS disimpan:[/green] {output_path}")
        return output_path

    def generate_word_level_ass(self, segments, output_path: Path = None) -> Path:
        """
        Buat .ass dengan highlight per-kata (karaoke style).
        Membutuhkan word_timestamps=True pada whisper.
        """
        if output_path is None:
            output_path = TEMP_DIR / "subtitles_word.ass"

        header = self._ass_header()
        events = []

        for seg in segments:
            if not seg.words:
                continue
            for word_data in seg.words:
                w     = word_data["word"].strip()
                start = word_data["start"]
                end   = word_data["end"]
                effect = r"{\fad(80,80)\an2}"
                events.append(
                    f"Dialogue: 0,"
                    f"{_seconds_to_ass_time(start)},"
                    f"{_seconds_to_ass_time(end)},"
                    f"Default,,0,0,0,,{effect}{w}"
                )

        content = header + "\n".join(events) + "\n"
        output_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓  Word-level ASS disimpan:[/green] {output_path}")
        return output_path

    @staticmethod
    def _ass_header() -> str:
        return f"""[Script Info]
Title: Auto Clipper Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat-Bold,{SUBTITLE_FONT_SIZE},{SUBTITLE_COLOR},&H000000FF,{SUBTITLE_OUTLINE},&H80000000,-1,0,0,0,100,100,0,0,1,{SUBTITLE_OUTLINE_SIZE},1,2,40,40,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
