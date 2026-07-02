"""
face_tracker.py — Deteksi wajah dengan OpenCV dan hitung crop 9:16 yang optimal.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from rich.console import Console

from config import (
    FACE_DETECTION_SCALE, FACE_DETECTION_NEIGHBORS,
    FACE_SMOOTH_FRAMES, FACE_PADDING, OUTPUT_RESOLUTION,
)

console = Console()

TARGET_W, TARGET_H = OUTPUT_RESOLUTION  # 1080 x 1920


@dataclass
class CropWindow:
    """Koordinat crop untuk satu frame."""
    x: int
    y: int
    w: int
    h: int


class FaceTracker:
    """
    Analisis video frame-by-frame untuk menemukan posisi wajah,
    lalu hitung koordinat crop 9:16 yang smooth.
    """

    def __init__(self):
        # Cascade classifier bawaan OpenCV
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise RuntimeError("Gagal memuat haarcascade_frontalface_default.xml")

    def analyze(
        self,
        video_path: Path,
        sample_fps: int = 5,
    ) -> list[CropWindow]:
        """
        Analisis video dan kembalikan list crop window per detik.

        Args:
            video_path: Path ke file video.
            sample_fps: Berapa frame per detik yang di-sample (lebih rendah = lebih cepat).

        Returns:
            List CropWindow yang sudah di-smooth.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Tidak bisa membuka video: {video_path}")

        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        src_fps = cap.get(cv2.CAP_PROP_FPS)
        interval = max(1, int(src_fps / sample_fps))

        # Hitung dimensi crop 9:16 yang pas di dalam source video
        crop_h = src_h
        crop_w = int(crop_h * TARGET_W / TARGET_H)
        if crop_w > src_w:
            crop_w = src_w
            crop_h = int(crop_w * TARGET_H / TARGET_W)

        console.print(
            f"[cyan]👁  Face tracking:[/cyan] {src_w}x{src_h} → crop {crop_w}x{crop_h} (9:16)"
        )

        raw_cx: list[int] = []   # center X per frame yang dianalisis
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % interval == 0:
                cx = self._detect_face_center_x(frame, src_w)
                raw_cx.append(cx)

            frame_idx += 1

        cap.release()

        # Smooth dengan rolling average
        smooth_cx = self._smooth(raw_cx, FACE_SMOOTH_FRAMES)

        # Konversi ke CropWindow
        windows: list[CropWindow] = []
        for cx in smooth_cx:
            x = cx - crop_w // 2
            x = max(0, min(x, src_w - crop_w))
            y = (src_h - crop_h) // 2  # vertikal center
            windows.append(CropWindow(x=x, y=y, w=crop_w, h=crop_h))

        console.print(f"[green]✓  Face tracking selesai:[/green] {len(windows)} sample")
        return windows

    def get_ffmpeg_crop_filter(
        self,
        windows: list[CropWindow],
        start_time: float,
        end_time: float,
        sample_fps: int = 5,
    ) -> str:
        """
        Buat ffmpeg filter string untuk crop dinamis.
        Gunakan ini di ClipCutter.

        Saring windows berdasarkan start_time dan end_time untuk klip ini,
        kemudian ambil rata-rata posisi crop agar stabil selama klip berlangsung.
        """
        if not windows:
            return f"crop={TARGET_W}:{TARGET_H}"

        start_idx = int(start_time * sample_fps)
        end_idx = int(end_time * sample_fps)
        sub_windows = windows[start_idx:end_idx]

        if not sub_windows:
            sub_windows = windows

        avg_x = int(np.mean([w.x for w in sub_windows]))
        avg_y = int(np.mean([w.y for w in sub_windows]))
        avg_w = sub_windows[0].w
        avg_h = sub_windows[0].h

        return f"crop={avg_w}:{avg_h}:{avg_x}:{avg_y},scale={TARGET_W}:{TARGET_H}"

    def _detect_face_center_x(self, frame: np.ndarray, src_w: int) -> int:
        """Deteksi wajah dan kembalikan center X. Fallback ke tengah frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=FACE_DETECTION_SCALE,
            minNeighbors=FACE_DETECTION_NEIGHBORS,
            minSize=(80, 80),
        )

        if len(faces) == 0:
            return src_w // 2  # fallback: tengah

        # Ambil wajah terbesar
        largest = max(faces, key=lambda f: f[2] * f[3])
        fx, fy, fw, fh = largest
        return fx + fw // 2

    @staticmethod
    def _smooth(values: list[int], window: int) -> list[int]:
        """Rolling average untuk mengurangi jitter."""
        if not values:
            return values
        result = []
        half = window // 2
        for i in range(len(values)):
            lo = max(0, i - half)
            hi = min(len(values), i + half + 1)
            result.append(int(np.mean(values[lo:hi])))
        return result
