"""
services/camera_service.py
CameraService managing webcam video capture with automated fallback
to synthetic test media when hardware video capture is unavailable.
"""

import os
import cv2
import time
import logging
from typing import Tuple, Optional, Generator
import numpy as np

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, camera_id: int = 0, video_path: Optional[str] = None):
        """
        Initializes the CameraService.
        
        Args:
            camera_id: System camera index (default 0).
            video_path: Optional path to fallback test video file.
        """
        self.camera_id = camera_id
        default_test_video = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_media",
            "test_classroom.mp4"
        )
        self.video_path = video_path if (video_path and os.path.exists(video_path)) else default_test_video
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running: bool = False
        self.using_fallback: bool = False
        self.fps: float = 30.0
        self.width: int = 640
        self.height: int = 480

    def start(self) -> bool:
        """
        Attempts to open hardware camera. If unavailable or unauthorized,
        falls back to test video file.
        """
        # Try hardware camera first
        logger.info(f"Attempting to open camera index {self.camera_id}...")
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.is_running = True
                self.using_fallback = False
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
                logger.info(f"Hardware camera {self.camera_id} active: {self.width}x{self.height} @ {self.fps}fps")
                return True
            else:
                self.cap.release()

        # Fallback to synthetic test video
        if os.path.exists(self.video_path):
            logger.info(f"Hardware camera unavailable. Falling back to test video: {self.video_path}")
            self.cap = cv2.VideoCapture(self.video_path)
            if self.cap.isOpened():
                self.is_running = True
                self.using_fallback = True
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 20.0
                logger.info(f"Fallback test video loaded: {self.width}x{self.height} @ {self.fps}fps")
                return True

        self.is_running = False
        logger.error("Unable to open hardware camera or fallback video.")
        return False

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Reads the next video frame. If playing test video and end is reached,
        it automatically loops from the beginning.
        """
        if not self.is_running or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            if self.using_fallback:
                # Loop test video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    return True, frame
            return False, None

        return True, frame

    def generate_jpeg_stream(self) -> Generator[bytes, None, None]:
        """
        Yields multipart JPEG frames for HTTP streaming (e.g., FastAPI / MJPEG).
        """
        delay = 1.0 / max(self.fps, 1.0)
        while self.is_running:
            ret, frame = self.get_frame()
            if not ret or frame is None:
                time.sleep(delay)
                continue
            
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(delay)

    def stop(self):
        """Releases the video capture device."""
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("CameraService stopped.")
