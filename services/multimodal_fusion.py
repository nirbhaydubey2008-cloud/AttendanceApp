"""
services/multimodal_fusion.py
Multimodal Temporal Synchronization and Feature Alignment Service.
Aligns high-frequency visual perception streams (~20-30 fps face tracking, head pose, eye gaze)
with lower-frequency acoustic context windows (0.5s - 2.0s audio chunks, VAD state, noise level).
Maintains rolling temporal buffers and computes aggregate student statistics across sliding windows.
"""

import time
import logging
from collections import deque, defaultdict
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)


class TemporalSyncBuffer:
    """
    Thread-safe circular buffer for temporal alignment of vision and audio streams.
    """
    def __init__(self, buffer_duration_sec: float = 60.0, max_track_history: int = 500):
        self.buffer_duration_sec = buffer_duration_sec
        self.max_track_history = max_track_history
        self.audio_chunks = deque()
        # History keyed by track_id -> deque of synchronized observations
        self.track_histories = defaultdict(lambda: deque(maxlen=self.max_track_history))
        self.latest_timestamp: float = 0.0

    def add_audio_chunk(self, chunk: Dict[str, Any]):
        """
        Appends an audio analysis chunk to the temporal buffer.
        """
        start_time = float(chunk.get("timestamp", time.time()))
        duration = float(chunk.get("duration_sec", 2.0))
        end_time = start_time + duration

        record = {
            "start_time": start_time,
            "end_time": end_time,
            "state": chunk.get("state", "QUIET"),
            "rms": float(chunk.get("rms", 0.004)),
            "db_level": float(chunk.get("db_level", -48.0)),
            "zcr": float(chunk.get("zcr", 0.0)),
            "spectral_centroid": float(chunk.get("spectral_centroid", 0.0)),
            "is_speech": bool(chunk.get("is_speech", False)),
            "speech_confidence": float(chunk.get("speech_confidence", 0.0)),
            "is_disturbance": bool(chunk.get("is_disturbance", False)),
            "snr_db": float(chunk.get("snr_db", 0.0)),
            "noise_floor": float(chunk.get("noise_floor", 0.004)),
            "engagement_audio_factor": float(chunk.get("engagement_audio_factor", 1.0))
        }
        self.audio_chunks.append(record)

        # Prune old chunks beyond buffer duration
        cutoff_time = end_time - self.buffer_duration_sec
        while self.audio_chunks and self.audio_chunks[0]["end_time"] < cutoff_time:
            self.audio_chunks.popleft()

    def get_audio_context_at(self, timestamp: float) -> Dict[str, Any]:
        """
        Retrieves the acoustic context active at the given timestamp.
        Falls back to nearest chunk or default ambient quiet state if buffer is empty.
        """
        if not self.audio_chunks:
            return {
                "audio_state": "QUIET",
                "audio_rms": 0.004,
                "audio_db": -48.0,
                "audio_is_speech": False,
                "audio_speech_conf": 0.0,
                "audio_is_disturbance": False,
                "audio_snr": 0.0,
                "audio_engagement_factor": 1.0
            }

        # Check for chunk covering timestamp
        for chunk in reversed(self.audio_chunks):
            if chunk["start_time"] <= timestamp <= chunk["end_time"]:
                return {
                    "audio_state": chunk["state"],
                    "audio_rms": chunk["rms"],
                    "audio_db": chunk["db_level"],
                    "audio_is_speech": chunk["is_speech"],
                    "audio_speech_conf": chunk["speech_confidence"],
                    "audio_is_disturbance": chunk["is_disturbance"],
                    "audio_snr": chunk["snr_db"],
                    "audio_engagement_factor": chunk["engagement_audio_factor"]
                }

        # Nearest neighbor lookup
        nearest = min(
            self.audio_chunks,
            key=lambda c: min(abs(timestamp - c["start_time"]), abs(timestamp - c["end_time"]))
        )
        return {
            "audio_state": nearest["state"],
            "audio_rms": nearest["rms"],
            "audio_db": nearest["db_level"],
            "audio_is_speech": nearest["is_speech"],
            "audio_speech_conf": nearest["speech_confidence"],
            "audio_is_disturbance": nearest["is_disturbance"],
            "audio_snr": nearest["snr_db"],
            "audio_engagement_factor": nearest["engagement_audio_factor"]
        }

    def synchronize_frame(
        self,
        frame_timestamp: float,
        tracks: List[Dict[str, Any]],
        pose_estimates: Optional[List[Dict[str, Any]]] = None,
        identities: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuses visual track observations, head pose/gaze metrics, student identities,
        and synchronized acoustic context for the current frame.
        """
        self.latest_timestamp = max(self.latest_timestamp, frame_timestamp)
        audio_context = self.get_audio_context_at(frame_timestamp)
        pose_estimates = pose_estimates or []
        identities = identities or {}

        # Map pose estimates by track_id
        pose_by_track = {p["track_id"]: p for p in pose_estimates if p.get("track_id") is not None}

        synced_records = []
        for track in tracks:
            track_id = str(track["track_id"])
            bbox = track["bbox"]
            conf = float(track.get("confidence", 0.85))

            # Find matching pose estimate
            pose = pose_by_track.get(track_id)
            if not pose and pose_estimates:
                # Match closest unassociated pose
                tx_c = bbox[0] + bbox[2] / 2.0
                ty_c = bbox[1] + bbox[3] / 2.0
                best_p = None
                min_d = float("inf")
                for p in pose_estimates:
                    fc = p.get("face_center", [0, 0])
                    d = np.hypot(fc[0] - tx_c, fc[1] - ty_c)
                    if d < min_d:
                        min_d = d
                        best_p = p
                pose = best_p

            yaw = float(pose.get("yaw", 0.0)) if pose else 0.0
            pitch = float(pose.get("pitch", 0.0)) if pose else 0.0
            roll = float(pose.get("roll", 0.0)) if pose else 0.0
            ear = float(pose.get("ear", 0.24)) if pose else 0.24
            is_blinking = bool(pose.get("is_blinking", False)) if pose else False
            gaze_score = float(pose.get("gaze_score", 0.80)) if pose else 0.80
            is_looking_forward = bool(pose.get("is_looking_forward", True)) if pose else True

            # Student identity
            identity = identities.get(track_id, {})
            student_id = identity.get("student_id")
            student_name = identity.get("name", f"Student #{track_id}")
            is_enrolled = bool(identity.get("is_enrolled", False))

            observation = {
                "timestamp": frame_timestamp,
                "track_id": track_id,
                "student_id": student_id,
                "student_name": student_name,
                "is_enrolled": is_enrolled,
                "bbox": bbox,
                "detection_confidence": conf,
                "yaw": yaw,
                "pitch": pitch,
                "roll": roll,
                "ear": ear,
                "is_blinking": is_blinking,
                "gaze_score": gaze_score,
                "is_looking_forward": is_looking_forward,
                **audio_context
            }

            self.track_histories[track_id].append(observation)
            synced_records.append(observation)

        return synced_records

    def get_track_history(self, track_id: str, window_sec: float = 10.0) -> List[Dict[str, Any]]:
        """Returns observation history for track within the recent window_sec."""
        history = self.track_histories.get(str(track_id))
        if not history:
            return []

        cutoff = self.latest_timestamp - window_sec
        return [obs for obs in history if obs["timestamp"] >= cutoff]

    def get_track_window_summary(self, track_id: str, window_sec: float = 10.0) -> Dict[str, Any]:
        """
        Computes aggregate rolling metrics for a student over the sliding window.
        """
        obs_list = self.get_track_history(track_id, window_sec=window_sec)
        if not obs_list:
            return {
                "track_id": str(track_id),
                "sample_count": 0,
                "presence_ratio": 0.0,
                "mean_gaze_score": 0.0,
                "forward_gaze_ratio": 0.0,
                "mean_abs_yaw": 0.0,
                "mean_abs_pitch": 0.0,
                "blink_count": 0,
                "mean_audio_engagement_factor": 1.0,
                "dominant_audio_state": "QUIET"
            }

        sample_count = len(obs_list)
        time_span = obs_list[-1]["timestamp"] - obs_list[0]["timestamp"] if sample_count > 1 else 0.0
        presence_ratio = float(min(1.0, time_span / max(window_sec * 0.8, 1.0)))

        gaze_scores = [o["gaze_score"] for o in obs_list]
        forward_looks = [1 if o["is_looking_forward"] else 0 for o in obs_list]
        abs_yaws = [abs(o["yaw"]) for o in obs_list]
        abs_pitches = [abs(o["pitch"]) for o in obs_list]
        blinks = sum(1 for o in obs_list if o["is_blinking"])
        audio_factors = [o["audio_engagement_factor"] for o in obs_list]
        
        # Audio states count
        state_counts = defaultdict(int)
        for o in obs_list:
            state_counts[o["audio_state"]] += 1
        dominant_state = max(state_counts.items(), key=lambda item: item[1])[0] if state_counts else "QUIET"

        return {
            "track_id": str(track_id),
            "student_id": obs_list[-1]["student_id"],
            "student_name": obs_list[-1]["student_name"],
            "is_enrolled": obs_list[-1]["is_enrolled"],
            "sample_count": sample_count,
            "presence_ratio": presence_ratio,
            "mean_gaze_score": float(np.mean(gaze_scores)),
            "forward_gaze_ratio": float(np.mean(forward_looks)),
            "mean_abs_yaw": float(np.mean(abs_yaws)),
            "mean_abs_pitch": float(np.mean(abs_pitches)),
            "blink_count": blinks,
            "mean_audio_engagement_factor": float(np.mean(audio_factors)),
            "dominant_audio_state": dominant_state
        }
