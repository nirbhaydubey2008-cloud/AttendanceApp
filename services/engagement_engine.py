"""
services/engagement_engine.py
Multimodal Engagement Scoring Engine.
Formulates the composite engagement score combining:
  - Eye Gaze Attentiveness (40%)
  - Head Pose Stability (20%)
  - Temporal Presence & Tracking Confidence (20%)
  - Acoustic Classroom Environment Context (20%)
Provides temporal Exponential Moving Average (EMA) smoothing, tier classification
(HIGH, MEDIUM, LOW), and real-time whole-classroom engagement aggregation.
"""

import time
import logging
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)


class EngagementTier(str, Enum):
    HIGH = "HIGH"        # score >= 0.70
    MEDIUM = "MEDIUM"    # 0.45 <= score < 0.70
    LOW = "LOW"          # score < 0.45


class EngagementEngine:
    """
    Multimodal Engagement Scoring Engine.
    """
    def __init__(
        self,
        weight_gaze: float = 0.40,
        weight_pose: float = 0.20,
        weight_presence: float = 0.20,
        weight_audio: float = 0.20,
        smoothing_factor: float = 0.70
    ):
        """
        Initializes EngagementEngine.
        
        Args:
            weight_gaze: Weight for eye gaze attentiveness (default 0.40).
            weight_pose: Weight for 3D head pose stability (default 0.20).
            weight_presence: Weight for visual tracking presence & confidence (default 0.20).
            weight_audio: Weight for acoustic context multiplier (default 0.20).
            smoothing_factor: Beta for Exponential Moving Average (default 0.70).
        """
        self.w_gaze = weight_gaze
        self.w_pose = weight_pose
        self.w_presence = weight_presence
        self.w_audio = weight_audio
        self.smoothing_factor = smoothing_factor
        
        # Track state caches: { track_id: { "smoothed_score": float, "last_updated": float } }
        self.student_states: Dict[str, Dict[str, Any]] = {}

    def compute_subscores(
        self,
        observation: Dict[str, Any],
        window_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Computes normalized [0.0, 1.0] subscores for gaze, head pose, presence, and audio.
        """
        # 1. Gaze Subscore (0.0 to 1.0)
        s_gaze = float(observation.get("gaze_score", 0.70))

        # 2. Pose Stability Subscore (0.0 to 1.0)
        yaw = abs(float(observation.get("yaw", 0.0)))
        pitch = abs(float(observation.get("pitch", 0.0)))
        yaw_penalty = min(1.0, max(0.0, (yaw - 5.0) / 35.0))
        pitch_penalty = min(1.0, max(0.0, (pitch - 5.0) / 25.0))
        s_pose = float(max(0.0, min(1.0, 1.0 - (0.65 * yaw_penalty + 0.35 * pitch_penalty))))

        # 3. Presence Subscore (0.0 to 1.0)
        det_conf = float(observation.get("detection_confidence", 0.85))
        if window_summary:
            presence_ratio = float(window_summary.get("presence_ratio", 1.0))
            s_presence = float(min(1.0, presence_ratio * (det_conf / 0.80)))
        else:
            s_presence = float(min(1.0, det_conf / 0.80))

        # 4. Audio Context Subscore (0.0 to 1.0)
        s_audio = float(observation.get("audio_engagement_factor", 1.0))

        return {
            "gaze_subscore": s_gaze,
            "pose_subscore": s_pose,
            "presence_subscore": s_presence,
            "audio_subscore": s_audio
        }

    def calculate_instant_score(
        self,
        observation: Dict[str, Any],
        window_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Computes raw instantaneous composite engagement score.
        """
        subscores = self.compute_subscores(observation, window_summary)
        
        raw_score = (
            self.w_gaze * subscores["gaze_subscore"] +
            self.w_pose * subscores["pose_subscore"] +
            self.w_presence * subscores["presence_subscore"] +
            self.w_audio * subscores["audio_subscore"]
        )
        instant_score = float(max(0.0, min(1.0, raw_score)))
        
        return {
            "instant_score": instant_score,
            **subscores
        }

    def update_student_engagement(
        self,
        track_id: str,
        observation: Dict[str, Any],
        window_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Updates engagement for a student with temporal EMA smoothing and tier classification.
        """
        tid = str(track_id)
        instant_data = self.calculate_instant_score(observation, window_summary)
        instant_score = instant_data["instant_score"]
        
        cached = self.student_states.get(tid)
        if cached is None:
            smoothed_score = instant_score
        else:
            # Exponential Moving Average: EMA = beta * prev + (1 - beta) * curr
            smoothed_score = float(
                self.smoothing_factor * cached["smoothed_score"] +
                (1.0 - self.smoothing_factor) * instant_score
            )

        # Tier classification
        if smoothed_score >= 0.70:
            tier = EngagementTier.HIGH
        elif smoothed_score >= 0.45:
            tier = EngagementTier.MEDIUM
        else:
            tier = EngagementTier.LOW

        record = {
            "track_id": tid,
            "student_id": observation.get("student_id"),
            "student_name": observation.get("student_name", f"Student #{tid}"),
            "is_enrolled": bool(observation.get("is_enrolled", False)),
            "score": round(smoothed_score, 3),
            "tier": tier.value,
            "instant_score": round(instant_score, 3),
            "gaze_subscore": round(instant_data["gaze_subscore"], 3),
            "pose_subscore": round(instant_data["pose_subscore"], 3),
            "presence_subscore": round(instant_data["presence_subscore"], 3),
            "audio_subscore": round(instant_data["audio_subscore"], 3),
            "timestamp": observation.get("timestamp", time.time())
        }

        self.student_states[tid] = {
            "smoothed_score": smoothed_score,
            "record": record,
            "last_updated": time.time()
        }
        return record

    def prune_stale_tracks(self, max_age_seconds: float = 3.0):
        """Removes student tracking states that have not been observed recently."""
        now = time.time()
        stale_tids = [
            tid for tid, s in self.student_states.items()
            if (now - s.get("last_updated", now)) > max_age_seconds
        ]
        for tid in stale_tids:
            del self.student_states[tid]

    def reset(self):
        """Clears all cached student states."""
        self.student_states.clear()

    def get_classroom_engagement_summary(
        self,
        active_track_ids: Optional[List[str]] = None,
        max_age_seconds: float = 3.0
    ) -> Dict[str, Any]:
        """
        Aggregates overall engagement across all currently active students in classroom.
        Prunes tracks that have disappeared from view.
        """
        self.prune_stale_tracks(max_age_seconds=max_age_seconds)
        if active_track_ids is not None:
            active_set = set(str(tid) for tid in active_track_ids)
            students = [
                state["record"] for tid, state in self.student_states.items()
                if tid in active_set
            ]
        else:
            students = [state["record"] for state in self.student_states.values()]

        if not students:
            return {
                "active_student_count": 0,
                "average_engagement_score": 0.0,
                "tier_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "disengaged_alert": False
            }

        scores = [s["score"] for s in students]
        avg_score = float(np.mean(scores))
        
        tier_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for s in students:
            t = s["tier"]
            if t in tier_counts:
                tier_counts[t] += 1

        # Alert if room average drops below 0.50
        disengaged_alert = bool(avg_score < 0.50)

        return {
            "active_student_count": len(students),
            "average_engagement_score": round(avg_score, 3),
            "tier_counts": tier_counts,
            "disengaged_alert": disengaged_alert
        }
