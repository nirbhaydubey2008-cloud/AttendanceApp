"""
services/face_detection.py
Face Detection and Multi-Object Tracking Service using OpenCV Haar Cascades
and DeepSort with appearance-based embedding representation.
"""

import os
import cv2
import logging
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort

logger = logging.getLogger(__name__)


def extract_appearance_embedding(crop: np.ndarray, dim: int = 128) -> np.ndarray:
    """
    Extracts a normalized appearance feature vector combining HSV color distribution
    and spatial grayscale structure. Fully offline, lightweight, and fast.
    """
    if crop is None or crop.size == 0:
        return np.zeros(dim, dtype=np.float32)

    # 1. Color distribution in HSV space (64 bins: 8 Hue x 8 Saturation)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    color_hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256]).flatten()

    # 2. Structural appearance (8x8 normalized grayscale patch = 64 values)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    spatial_patch = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA).flatten().astype(np.float32) / 255.0

    # Combine into 128-dimensional feature vector
    feat = np.concatenate([color_hist, spatial_patch])
    norm = np.linalg.norm(feat)
    if norm > 1e-6:
        feat = feat / norm
    return feat.astype(np.float32)


class FaceDetector:
    """
    OpenCV Haar Cascade Face Detector.
    Configured for classroom environment detection with confidence scoring.
    """
    def __init__(self, scale_factor: float = 1.05, min_neighbors: int = 2, min_size: Tuple[int, int] = (35, 35)):
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            raise FileNotFoundError(f"Haar cascade XML not found at {cascade_path}")
        self.cascade = cv2.CascadeClassifier(cascade_path)
        if self.cascade.empty():
            raise RuntimeError("Failed to load OpenCV Haar Cascade Classifier.")

    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in a frame.
        
        Returns:
            List of dicts: [
                {
                    "bbox": [x, y, w, h],
                    "confidence": float (0.0 to 1.0),
                    "crop": np.ndarray
                }, ...
            ]
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # detectMultiScale3 yields bounding rects, rejectLevels, and weights (confidence)
        rects, _, weights = self.cascade.detectMultiScale3(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
            outputRejectLevels=True
        )

        detections = []
        for (rx, ry, rw, rh), weight in zip(rects, weights):
            x1 = max(0, int(rx))
            y1 = max(0, int(ry))
            x2 = min(w, int(rx + rw))
            y2 = min(h, int(ry + rh))
            
            crop = frame[y1:y2, x1:x2]
            # Normalize Haar weight to a calibrated [0.5, 1.0] confidence score
            conf = float(min(1.0, max(0.5, weight / 4.5)))
            
            detections.append({
                "bbox": [x1, y1, x2 - x1, y2 - y1],
                "confidence": conf,
                "crop": crop
            })

        return detections


class FaceTracker:
    """
    Multi-Object Face Tracker wrapping DeepSort with custom offline appearance embeddings.
    Maintains persistent tracking IDs across video frames.
    """
    def __init__(self, max_age: int = 30, n_init: int = 2, max_cosine_distance: float = 0.3):
        self.tracker = DeepSort(
            embedder=None,
            max_age=max_age,
            n_init=n_init,
            max_cosine_distance=max_cosine_distance
        )

    def update(self, detections: List[Dict[str, Any]], frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Updates tracking state with new detections from current frame.

        Returns:
            List of active confirmed tracks:
            [
                {
                    "track_id": int/str,
                    "bbox": [x, y, w, h],
                    "confidence": float,
                    "is_confirmed": bool,
                    "time_since_update": int,
                    "crop": np.ndarray
                }, ...
            ]
        """
        raw_dets = []
        embeds = []
        h, w = frame.shape[:2]

        for det in detections:
            bbox = det["bbox"]
            conf = det["confidence"]
            crop = det.get("crop")
            if crop is None or crop.size == 0:
                x, y, bw, bh = bbox
                crop = frame[max(0, y):min(h, y+bh), max(0, x):min(w, x+bw)]
            
            raw_dets.append((bbox, conf, "student"))
            embeds.append(extract_appearance_embedding(crop))

        tracks = self.tracker.update_tracks(raw_dets, embeds=embeds)
        
        active_tracks = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            # DeepSort to_tlwh returns [top_left_x, top_left_y, width, height]
            tlwh = track.to_tlwh()
            tx = max(0, int(tlwh[0]))
            ty = max(0, int(tlwh[1]))
            tw = min(w - tx, max(1, int(tlwh[2])))
            th = min(h - ty, max(1, int(tlwh[3])))
            
            crop = frame[ty:ty+th, tx:tx+tw]
            det_conf = track.get_det_conf() if hasattr(track, "get_det_conf") and track.get_det_conf() else 0.85
            
            active_tracks.append({
                "track_id": str(track.track_id),
                "bbox": [tx, ty, tw, th],
                "confidence": float(det_conf),
                "is_confirmed": track.is_confirmed(),
                "time_since_update": track.time_since_update,
                "crop": crop
            })

        return active_tracks


class FaceDetectionService:
    """
    Combined Face Detection and Tracking Service.
    Processes frames, updates tracks, and generates aesthetic annotations.
    """
    def __init__(self, scale_factor: float = 1.05, min_neighbors: int = 2, max_age: int = 30, n_init: int = 2):
        self.detector = FaceDetector(scale_factor=scale_factor, min_neighbors=min_neighbors)
        self.tracker = FaceTracker(max_age=max_age, n_init=n_init)

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Runs detection and tracking on a single frame, then returns the annotated frame
        and the list of active tracked student records.
        """
        detections = self.detector.detect_faces(frame)
        tracks = self.tracker.update(detections, frame)
        annotated_frame = self.annotate_frame(frame.copy(), tracks)
        return annotated_frame, tracks

    @staticmethod
    def annotate_frame(frame: np.ndarray, tracks: List[Dict[str, Any]]) -> np.ndarray:
        """
        Renders aesthetic modern bounding boxes, track ID pill tags, and corner brackets.
        """
        accent_color = (0, 210, 130)  # Emerald green (BGR)
        corner_len = 12

        for t in tracks:
            x, y, w, h = t["bbox"]
            track_id = t["track_id"]
            conf = t["confidence"]

            # Main bounding box (semi-transparent border)
            cv2.rectangle(frame, (x, y), (x + w, y + h), accent_color, 1, cv2.LINE_AA)

            # High-tech corner brackets
            # Top-left
            cv2.line(frame, (x, y), (x + corner_len, y), accent_color, 2, cv2.LINE_AA)
            cv2.line(frame, (x, y), (x, y + corner_len), accent_color, 2, cv2.LINE_AA)
            # Top-right
            cv2.line(frame, (x + w, y), (x + w - corner_len, y), accent_color, 2, cv2.LINE_AA)
            cv2.line(frame, (x + w, y), (x + w, y + corner_len), accent_color, 2, cv2.LINE_AA)
            # Bottom-left
            cv2.line(frame, (x, y + h), (x + corner_len, y + h), accent_color, 2, cv2.LINE_AA)
            cv2.line(frame, (x, y + h), (x, y + h - corner_len), accent_color, 2, cv2.LINE_AA)
            # Bottom-right
            cv2.line(frame, (x + w, y + h), (x + w - corner_len, y + h), accent_color, 2, cv2.LINE_AA)
            cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_len), accent_color, 2, cv2.LINE_AA)

            # Pill Badge for ID and Confidence
            label = f"ID #{track_id} ({int(conf * 100)}%)"
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.45
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, scale, thickness)
            
            badge_y1 = max(0, y - text_h - 10)
            badge_y2 = y
            badge_x1 = x
            badge_x2 = x + text_w + 12

            # Badge background
            cv2.rectangle(frame, (badge_x1, badge_y1), (badge_x2, badge_y2), (25, 25, 25), -1)
            cv2.rectangle(frame, (badge_x1, badge_y1), (badge_x2, badge_y2), accent_color, 1)
            # Badge text
            cv2.putText(frame, label, (badge_x1 + 6, badge_y2 - 5), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

        return frame
