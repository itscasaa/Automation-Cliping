"""
highlight_finder.py — Gunakan Claude AI untuk menemukan highlight terbaik dari transkrip.
"""

import json
from dataclasses import dataclass
from typing import Optional
import typing_extensions as typing

from google import genai
from google.genai import types
from rich.console import Console

from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    MAX_HIGHLIGHTS, MIN_CLIP_DURATION, MAX_CLIP_DURATION,
    HIGHLIGHT_CONTEXT_SEC,
)
from .prompt_templates import PromptTemplates

console = Console()


class HighlightDict(typing.TypedDict):
    id: int
    title: str
    start: float
    end: float
    reason: str
    hook: str
    tags: list[str]


class HighlightResponse(typing.TypedDict):
    highlights: list[HighlightDict]


@dataclass
class Highlight:
    """Satu momen highlight yang dipilih AI."""
    id: int
    title: str
    start: float        # detik (sudah termasuk padding)
    end: float          # detik (sudah termasuk padding)
    reason: str
    hook: str
    tags: list[str]

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __str__(self) -> str:
        return (
            f"[{self.id}] {self.title} "
            f"({self.start:.1f}s – {self.end:.1f}s, {self.duration:.1f}s)"
        )


class HighlightFinder:
    """Analisis transkrip dengan Gemini dan return list highlight."""

    CONTENT_TYPES = {
        "general":     PromptTemplates.general,
        "educational": PromptTemplates.educational,
        "podcast":     PromptTemplates.podcast,
        "gaming":      PromptTemplates.gaming,
    }

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY tidak ditemukan! "
                "Tambahkan ke file .env: GEMINI_API_KEY=AIzaSy..."
            )
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def find_highlights(
        self,
        segments,
        content_type: str = "general",
        video_duration: Optional[float] = None,
    ) -> list[Highlight]:
        """
        Kirim transkrip ke Gemini dan dapatkan list highlight.

        Args:
            segments: List Segment dari WhisperTranscriber.
            content_type: Tipe konten ("general", "educational", "podcast", "gaming").
            video_duration: Total durasi video dalam detik.

        Returns:
            List Highlight yang sudah diurutkan berdasarkan waktu.
        """
        transcript_text = self._format_transcript(segments)

        # Pilih prompt template
        prompt_fn = self.CONTENT_TYPES.get(content_type, PromptTemplates.general)
        user_prompt = prompt_fn(
            transcript_text,
            MAX_HIGHLIGHTS,
            MIN_CLIP_DURATION,
            MAX_CLIP_DURATION,
        )

        system_prompt = PromptTemplates.SYSTEM.format(
            max_highlights=MAX_HIGHLIGHTS,
            min_dur=MIN_CLIP_DURATION,
            max_dur=MAX_CLIP_DURATION,
        )

        console.print(
            f"[cyan]🤖 Menganalisis dengan Gemini ({GEMINI_MODEL})...[/cyan]"
        )

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=HighlightResponse,
            ),
        )

        raw_json = response.text.strip()

        # Parse dan validasi
        highlights = self._parse_response(raw_json, video_duration)

        console.print(
            f"[green]✓  Ditemukan {len(highlights)} highlight:[/green]"
        )
        for h in highlights:
            console.print(f"   {h}")

        return highlights

    def _parse_response(
        self,
        raw_json: str,
        video_duration: Optional[float],
    ) -> list[Highlight]:
        """Parse JSON dari Claude dan tambahkan padding."""
        # Bersihkan jika ada markdown fence
        if "```" in raw_json:
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]

        data = json.loads(raw_json)
        max_ts = video_duration or float("inf")

        highlights = []
        for item in data.get("highlights", []):
            # Tambahkan padding konteks
            start = max(0.0, float(item["start"]) - HIGHLIGHT_CONTEXT_SEC)
            end   = min(max_ts, float(item["end"])   + HIGHLIGHT_CONTEXT_SEC)

            highlights.append(
                Highlight(
                    id=int(item["id"]),
                    title=item["title"],
                    start=round(start, 3),
                    end=round(end, 3),
                    reason=item.get("reason", ""),
                    hook=item.get("hook", ""),
                    tags=item.get("tags", []),
                )
            )

        # Urutkan berdasarkan waktu mulai
        return sorted(highlights, key=lambda h: h.start)

    @staticmethod
    def _format_transcript(segments) -> str:
        """Format transkrip menjadi teks dengan timestamp."""
        lines = []
        for seg in segments:
            m = int(seg.start) // 60
            s = int(seg.start) % 60
            lines.append(f"[{m:02d}:{s:02d}] {seg.text}")
        return "\n".join(lines)
