"""
services/reasoning_engine.py
Rule-Based AI Reasoning and Pedagogical Recommendation Engine.
Operates 100% locally and offline without cloud dependencies.
Evaluates multimodal telemetry rules, triggers educational suggestions with
debounce cooldowns, and maintains priority tiers (INFO, WARNING, URGENT).
Optional Groq cloud LLM fallback is provided as commented/pluggable code.
"""

import os
import time
import logging
from enum import Enum
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class RecommendationPriority(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    URGENT = "URGENT"


class RecommendationEngine:
    """
    Offline Rule-Based Pedagogical Reasoning Engine.
    """
    def __init__(self, cooldown_seconds: float = 30.0, use_cloud_llm: bool = False):
        """
        Initializes RecommendationEngine.
        
        Args:
            cooldown_seconds: Minimum seconds before the same rule can trigger again.
            use_cloud_llm: Optional toggle for cloud LLM reasoning (False by default).
        """
        self.cooldown_seconds = cooldown_seconds
        self.use_cloud_llm = use_cloud_llm
        self.last_trigger_times: Dict[str, float] = {}
        self.recommendations_history: List[Dict[str, Any]] = []

    def reset(self):
        """Resets engine cooldowns and history for a new session or test run."""
        self.last_trigger_times.clear()
        self.recommendations_history.clear()

    def _can_trigger(self, trigger_type: str, current_time: float) -> bool:
        """Enforces debounce cooldown per trigger type."""
        last_t = self.last_trigger_times.get(trigger_type)
        if last_t is not None and (current_time - last_t < self.cooldown_seconds):
            return False
        self.last_trigger_times[trigger_type] = current_time
        return True

    def evaluate_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluates real-time classroom telemetry against pedagogical rules.
        
        Args:
            context: Dictionary containing:
              - average_engagement: float [0.0, 1.0]
              - active_student_count: int
              - forward_gaze_ratio: Optional[float]
              - audio_state: str ("QUIET", "SPEECH", "DISTURBANCE", "MODERATE_NOISE")
              - audio_rms: float
              - audio_db: float
              - attendance_rate_pct: Optional[float]
              - session_elapsed_sec: Optional[float]
        """
        now = float(context.get("timestamp", time.time()))
        avg_eng = float(context.get("average_engagement", 0.70))
        student_count = int(context.get("active_student_count", 0))
        forward_gaze = float(context.get("forward_gaze_ratio", 0.75))
        audio_state = str(context.get("audio_state", "QUIET"))
        audio_db = float(context.get("audio_db", -45.0))
        attendance_rate = float(context.get("attendance_rate_pct", 100.0))
        elapsed_sec = float(context.get("session_elapsed_sec", 0.0))

        new_recs = []

        # Rule 1: Prolonged Low Engagement
        if student_count > 0 and avg_eng < 0.50:
            trigger = "LOW_ENGAGEMENT"
            if self._can_trigger(trigger, now):
                priority = RecommendationPriority.URGENT if avg_eng < 0.35 else RecommendationPriority.WARNING
                pct = int(avg_eng * 100)
                rec = {
                    "recommendation_id": f"REC_{int(now)}_{trigger}",
                    "timestamp": now,
                    "trigger_type": trigger,
                    "priority": priority.value,
                    "title": "Low Classroom Engagement",
                    "suggestion_text": f"Average student engagement has dipped to {pct}%. Pacing or material density may be causing attention fatigue.",
                    "actionable_steps": [
                        "Pose a quick check-in question or formative poll",
                        "Invite student questions on the preceding section",
                        "Change physical positioning or introduce a live example"
                    ]
                }
                new_recs.append(rec)

        # Rule 2: Acoustic Disturbance
        if audio_state == "DISTURBANCE":
            trigger = "ACOUSTIC_DISTURBANCE"
            if self._can_trigger(trigger, now):
                rec = {
                    "recommendation_id": f"REC_{int(now)}_{trigger}",
                    "timestamp": now,
                    "trigger_type": trigger,
                    "priority": RecommendationPriority.WARNING.value,
                    "title": "Acoustic Disturbance Detected",
                    "suggestion_text": f"Elevated noise burst detected ({round(audio_db, 1)} dBFS). Background disturbance or side chatter may be interfering with student focus.",
                    "actionable_steps": [
                        "Pause briefly and request quiet before continuing",
                        "Verify microphone placement and room acoustics",
                        "Address classroom commotion gently"
                    ]
                }
                new_recs.append(rec)

        # Rule 3: Visual Gaze Aversion / Slide Disconnect
        if student_count >= 2 and forward_gaze < 0.45:
            trigger = "GAZE_AVERSION"
            if self._can_trigger(trigger, now):
                pct = int(forward_gaze * 100)
                rec = {
                    "recommendation_id": f"REC_{int(now)}_{trigger}",
                    "timestamp": now,
                    "trigger_type": trigger,
                    "priority": RecommendationPriority.INFO.value,
                    "title": "Visual Attention Diverging",
                    "suggestion_text": f"Only {pct}% of students are visually focusing on the display area. Focus may be drifting away from the visual slides.",
                    "actionable_steps": [
                        "Direct student attention explicitly to a key diagram or bullet",
                        "Check slide font size, readability, or screen brightness",
                        "Highlight core terms on the whiteboard"
                    ]
                }
                new_recs.append(rec)

        # Rule 4: Sustained High Engagement Praise
        if student_count > 0 and avg_eng >= 0.82:
            trigger = "HIGH_ENGAGEMENT"
            if self._can_trigger(trigger, now):
                pct = int(avg_eng * 100)
                rec = {
                    "recommendation_id": f"REC_{int(now)}_{trigger}",
                    "timestamp": now,
                    "trigger_type": trigger,
                    "priority": RecommendationPriority.INFO.value,
                    "title": "Optimal Attention Window",
                    "suggestion_text": f"Classroom engagement is exceptionally high ({pct}%). The current explanatory cadence is highly effective.",
                    "actionable_steps": [
                        "Ideal window to introduce complex or conceptually challenging topics",
                        "Maintain steady vocal modulation and pacing",
                        "Reinforce positive student engagement"
                    ]
                }
                new_recs.append(rec)

        # Rule 5: Low Verified Attendance Alert
        if elapsed_sec > 120.0 and attendance_rate < 60.0:
            trigger = "LOW_ATTENDANCE"
            if self._can_trigger(trigger, now):
                pct = int(attendance_rate)
                rec = {
                    "recommendation_id": f"REC_{int(now)}_{trigger}",
                    "timestamp": now,
                    "trigger_type": trigger,
                    "priority": RecommendationPriority.WARNING.value,
                    "title": "Low Verified Attendance",
                    "suggestion_text": f"Only {pct}% of expected students currently meet the presence verification threshold.",
                    "actionable_steps": [
                        "Remind students to ensure clear visibility to the camera",
                        "Check attendance roster for unregistered or late arrivals"
                    ]
                }
                new_recs.append(rec)

        for r in new_recs:
            self.recommendations_history.append(r)
            if len(self.recommendations_history) > 100:
                self.recommendations_history.pop(0)

        return new_recs

    def get_recent_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent recommendations in reverse chronological order."""
        return list(reversed(self.recommendations_history[-limit:]))

    def generate_cloud_llm_insight(self, session_summary: Dict[str, Any]) -> Optional[str]:
        """
        Optional cloud LLM fallback using Groq API (commented out by default to adhere to offline-first design).
        To activate: install groq (`pip install groq`), set GROQ_API_KEY in .env, and set use_cloud_llm=True.
        """
        if not self.use_cloud_llm:
            return None

        # --- OPTIONAL GROQ CLOUD CODE (UNCOMMENT IF GROQ API ACTIVATED) ---
        # try:
        #     import os
        #     from groq import Groq
        #     api_key = os.getenv("GROQ_API_KEY")
        #     if not api_key:
        #         return None
        #     client = Groq(api_key=api_key)
        #     prompt = f"Analyze classroom session: {session_summary}. Provide concise pedagogical advice in 2 sentences."
        #     chat_completion = client.chat.completions.create(
        #         messages=[{"role": "user", "content": prompt}],
        #         model="mixtral-8x7b-32768",
        #         max_tokens=150
        #     )
        #     return chat_completion.choices[0].message.content
        # except Exception as e:
        #     logger.warning(f"Groq cloud LLM call skipped: {e}")
        #     return None
        return None
