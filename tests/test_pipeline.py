"""
test_pipeline.py — Unit test untuk setiap modul Auto Clipper.
Jalankan dengan: python -m pytest tests/ -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Tambahkan root ke path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock modul besar agar unit test bisa jalan tanpa perlu instalasi lengkap
from unittest.mock import MagicMock
sys.modules['yt_dlp'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['faster_whisper'] = MagicMock()

# Mock numpy dan mean function-nya serta dummy class bool_
mock_np = MagicMock()
mock_np.mean = lambda x: sum(x) / len(x) if x else 0.0
class MockNumpyBool:
    pass
mock_np.bool_ = MockNumpyBool
sys.modules['numpy'] = mock_np

# Mock namespace google dan google.genai
mock_google = MagicMock()
sys.modules['google'] = mock_google
sys.modules['google.genai'] = mock_google


# ─── Transcriber ──────────────────────────────────────────────────────────────

class TestSRTGenerator:
    """Test pembuatan file subtitle."""

    def _make_segments(self):
        from transcriber.whisper_stt import Segment
        return [
            Segment(id=0, start=0.0, end=5.5, text="Halo semuanya, selamat datang!", words=[]),
            Segment(id=1, start=5.5, end=12.0, text="Hari ini kita akan belajar tentang Python.", words=[]),
            Segment(id=2, start=12.0, end=18.3, text="Python adalah bahasa pemrograman yang sangat populer.", words=[]),
        ]

    def test_generate_srt(self, tmp_path):
        from transcriber.srt_generator import SRTGenerator
        gen = SRTGenerator()
        segments = self._make_segments()
        out = gen.generate_srt(segments, tmp_path / "test.srt")
        content = out.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:05,500" in content
        assert "Halo semuanya" in content

    def test_generate_ass(self, tmp_path):
        from transcriber.srt_generator import SRTGenerator
        gen = SRTGenerator()
        segments = self._make_segments()
        out = gen.generate_ass(segments, tmp_path / "test.ass")
        content = out.read_text(encoding="utf-8")
        assert "[V4+ Styles]" in content
        assert "Dialogue:" in content
        assert "Halo semuanya" in content

    def test_empty_segments(self, tmp_path):
        from transcriber.srt_generator import SRTGenerator
        gen = SRTGenerator()
        out = gen.generate_srt([], tmp_path / "empty.srt")
        assert out.read_text(encoding="utf-8").strip() == ""


# ─── Analyzer ─────────────────────────────────────────────────────────────────

class TestHighlightFinder:
    """Test parsing respons LLM."""

    def test_parse_valid_json(self, tmp_path):
        from analyzer.highlight_finder import HighlightFinder

        finder = HighlightFinder.__new__(HighlightFinder)  # skip __init__

        raw = json.dumps({
            "highlights": [
                {
                    "id": 1,
                    "title": "Momen seru pertama",
                    "start": 10.0,
                    "end": 50.0,
                    "reason": "Ini bagian terbaik.",
                    "hook": "Kamu tidak akan percaya ini!",
                    "tags": ["#viral", "#python"],
                }
            ]
        })

        highlights = finder._parse_response(raw, video_duration=300.0)
        assert len(highlights) == 1
        assert highlights[0].title == "Momen seru pertama"
        # start harus ter-offset oleh HIGHLIGHT_CONTEXT_SEC
        assert highlights[0].start < 10.0

    def test_parse_json_with_fence(self):
        from analyzer.highlight_finder import HighlightFinder

        finder = HighlightFinder.__new__(HighlightFinder)

        raw = "```json\n" + json.dumps({
            "highlights": [
                {
                    "id": 1, "title": "Test", "start": 30.0, "end": 60.0,
                    "reason": "ok", "hook": "hook", "tags": [],
                }
            ]
        }) + "\n```"

        highlights = finder._parse_response(raw, video_duration=None)
        assert len(highlights) == 1

    def test_format_transcript(self):
        from analyzer.highlight_finder import HighlightFinder
        from transcriber.whisper_stt import Segment

        segs = [
            Segment(id=0, start=0.0, end=5.0, text="Hello", words=[]),
            Segment(id=1, start=65.0, end=70.0, text="World", words=[]),
        ]
        text = HighlightFinder._format_transcript(segs)
        assert "[00:00]" in text
        assert "[01:05]" in text


# ─── Downloader ───────────────────────────────────────────────────────────────

class TestLocalVideoLoader:
    """Test validasi file lokal."""

    def test_unsupported_format(self, tmp_path):
        from downloader.local import LocalVideoLoader
        dummy = tmp_path / "video.xyz"
        dummy.write_bytes(b"fake")
        loader = LocalVideoLoader(output_dir=tmp_path)
        with pytest.raises(ValueError, match="Format tidak didukung"):
            loader.load(str(dummy))

    def test_file_not_found(self, tmp_path):
        from downloader.local import LocalVideoLoader
        loader = LocalVideoLoader(output_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load("/tidak/ada/file.mp4")

    def test_list_videos(self, tmp_path):
        from downloader.local import LocalVideoLoader
        (tmp_path / "a.mp4").write_bytes(b"")
        (tmp_path / "b.mkv").write_bytes(b"")
        (tmp_path / "c.txt").write_bytes(b"")
        videos = LocalVideoLoader.list_videos(str(tmp_path))
        assert len(videos) == 2
        assert all(v.suffix in {".mp4", ".mkv"} for v in videos)


# ─── Editor ───────────────────────────────────────────────────────────────────

class TestClipCutter:
    def test_safe_filename(self):
        from editor.clip_cutter import ClipCutter
        assert ClipCutter._safe_filename('Hello: World? "Test"') == "Hello_ World_ _Test_"

    def test_safe_filename_truncation(self):
        from editor.clip_cutter import ClipCutter
        long_name = "A" * 100
        assert len(ClipCutter._safe_filename(long_name)) <= 50


class TestFaceTracker:
    def test_smooth_empty(self):
        from editor.face_tracker import FaceTracker
        result = FaceTracker._smooth([], window=5)
        assert result == []

    def test_smooth_values(self):
        from editor.face_tracker import FaceTracker
        values = [100, 200, 100, 200, 100]
        smoothed = FaceTracker._smooth(values, window=3)
        # Nilai tengah harus lebih mendekati rata-rata
        assert smoothed[2] == pytest.approx(166, abs=5)

    def test_get_ffmpeg_crop_filter(self):
        from editor.face_tracker import FaceTracker, CropWindow
        tracker = FaceTracker.__new__(FaceTracker)
        windows = [
            CropWindow(x=10, y=20, w=100, h=100),  # 0.0s - index 0
            CropWindow(x=20, y=30, w=100, h=100),  # 0.2s - index 1
            CropWindow(x=30, y=40, w=100, h=100),  # 0.4s - index 2
            CropWindow(x=40, y=50, w=100, h=100),  # 0.6s - index 3
            CropWindow(x=50, y=60, w=100, h=100),  # 0.8s - index 4
        ]
        # Slice dari 0.2s sampai 0.6s -> index 1 ke 3 -> index 1 & 2
        crop_filter = tracker.get_ffmpeg_crop_filter(windows, start_time=0.2, end_time=0.6, sample_fps=5)
        # avg_x = (20 + 30) // 2 = 25
        # avg_y = (30 + 40) // 2 = 35
        assert "crop=100:100:25:35" in crop_filter


# ─── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    def test_dirs_exist(self):
        import config
        assert config.TEMP_DIR.exists()
        assert config.OUTPUT_DIR.exists()

    def test_resolution_portrait(self):
        import config
        w, h = config.OUTPUT_RESOLUTION
        assert h > w  # 9:16 = portrait


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
