"""
services/attendance_service.py
Attendance Tracking and Verification Service.
Manages classroom lecture sessions, presence accumulation, threshold-based
attendance qualification (PRESENT, PARTIAL, ABSENT), and report generation.
"""

import os
import time
import logging
from enum import Enum
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Set
import pandas as pd

logger = logging.getLogger(__name__)


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    PARTIAL = "PARTIAL"
    ABSENT = "ABSENT"


class AttendanceService:
    """
    Session attendance manager with presence accumulation and threshold verification.
    """
    def __init__(
        self,
        present_threshold: float = 0.75,
        partial_threshold: float = 0.50
    ):
        """
        Initializes AttendanceService.
        
        Args:
            present_threshold: Minimum presence ratio for PRESENT status (default 75%).
            partial_threshold: Minimum presence ratio for PARTIAL status (default 50%).
        """
        self.present_threshold = present_threshold
        self.partial_threshold = partial_threshold
        
        # Session state
        self.session_id: Optional[str] = None
        self.session_title: str = "Classroom Lecture"
        self.course_code: str = "CS101"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.is_active: bool = False
        self.first_frame_timestamp: Optional[float] = None
        self.last_frame_timestamp: Optional[float] = None
        
        # Student records keyed by unique key (student_id if enrolled, else track_id)
        self.records: Dict[str, Dict[str, Any]] = {}
        # Set of enrolled student IDs for active course session
        self.enrolled_student_ids: Optional[Set[str]] = None

    def start_session(
        self,
        session_id: Optional[str] = None,
        title: str = "Classroom Lecture",
        course_code: str = "CS101",
        enrolled_student_ids: Optional[List[str]] = None,
        enrolled_students_list: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Begins a new attendance tracking session. Pre-seeds enrolled students as ABSENT.
        """
        self.session_id = session_id or f"SESS_{int(time.time())}"
        self.session_title = title
        self.course_code = course_code
        self.start_time = time.time()
        self.end_time = None
        self.is_active = True
        self.first_frame_timestamp: Optional[float] = None
        self.last_frame_timestamp: Optional[float] = None
        self.records.clear()
        self.enrolled_student_ids = {str(sid).strip().upper() for sid in enrolled_student_ids} if enrolled_student_ids is not None else None
        
        # Pre-seed enrolled course roster so every registered student begins as ABSENT
        if enrolled_students_list:
            for s_info in enrolled_students_list:
                s_id = s_info.get("student_id")
                s_name = s_info.get("name") or s_id
                if s_id:
                    self.records[s_id] = {
                        "student_key": s_id,
                        "student_id": s_id,
                        "student_name": s_name,
                        "is_enrolled": True,
                        "first_seen_timestamp": None,
                        "last_seen_timestamp": None,
                        "total_seconds_present": 0.0,
                        "presence_ratio": 0.0,
                        "mean_engagement": 0.0,
                        "status": AttendanceStatus.ABSENT.value,
                        "engagement_history": []
                    }

        logger.info(f"Started attendance session: {self.session_id} - {title} ({course_code}) [Enrolled students: {len(self.enrolled_student_ids) if self.enrolled_student_ids is not None else 'Unrestricted'}]")
        return {
            "session_id": self.session_id,
            "title": self.session_title,
            "course_code": self.course_code,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() + "Z",
            "is_active": True
        }

    def end_session(self) -> Dict[str, Any]:
        """
        Finalizes active session, recalculates final statuses, and produces session summary.
        """
        if self.end_time is None:
            self.end_time = time.time()
        self.is_active = False
        
        # Final pass on presence ratio and qualification
        session_duration = self.get_session_elapsed_seconds()
        for r in self.records.values():
            ratio = float(min(1.0, r["total_seconds_present"] / max(session_duration, 1.0)))
            r["presence_ratio"] = round(ratio, 3)
            if not r.get("manual_override"):
                if r.get("is_enrolled"):
                    r["status"] = self._qualify_status(ratio).value
                else:
                    r["status"] = "UNENROLLED"
            if r["engagement_history"]:
                r["mean_engagement"] = round(float(sum(r["engagement_history"]) / len(r["engagement_history"])), 3)

        report = self.get_session_attendance_report()
        logger.info(f"Ended session {self.session_id}. Total students recorded: {len(self.records)}")
        return report

    def get_session_elapsed_seconds(self) -> float:
        """Returns total elapsed seconds since session start."""
        # If frame timestamps are tracked, use frame duration for accurate playback/offline alignment
        first_t = getattr(self, "first_frame_timestamp", None)
        last_t = getattr(self, "last_frame_timestamp", None)
        if first_t is not None and last_t is not None:
            frame_elapsed = last_t - first_t
            if frame_elapsed > 0:
                return float(frame_elapsed)
        if not self.start_time:
            return 0.0
        current = self.end_time if self.end_time else time.time()
        return max(0.0, current - self.start_time)

    def _qualify_status(self, presence_ratio: float) -> AttendanceStatus:
        """Classifies presence ratio against thresholds."""
        if presence_ratio >= self.present_threshold:
            return AttendanceStatus.PRESENT
        elif presence_ratio >= self.partial_threshold:
            return AttendanceStatus.PARTIAL
        else:
            return AttendanceStatus.ABSENT

    def update_frame(
        self,
        frame_timestamp: float,
        synced_observations: List[Dict[str, Any]]
    ):
        """
        Updates student attendance records with current frame observations.
        
        Args:
            frame_timestamp: Relative or absolute timestamp of the current video frame.
            synced_observations: List of multimodal records from TemporalSyncBuffer.
        """
        if not self.is_active:
            return

        if self.first_frame_timestamp is None:
            self.first_frame_timestamp = frame_timestamp

        # Compute delta time between frames
        if self.last_frame_timestamp is not None and frame_timestamp > self.last_frame_timestamp:
            dt = frame_timestamp - self.last_frame_timestamp
            # Cap dt at 2.0s to avoid large jumps if video paused or skipped
            dt = min(dt, 2.0)
        else:
            dt = 0.05  # Default ~20fps interval for initial frame
        
        self.last_frame_timestamp = frame_timestamp
        session_elapsed = self.get_session_elapsed_seconds()

        for obs in synced_observations:
            track_id = str(obs["track_id"])
            student_id = obs.get("student_id")
            name = obs.get("student_name", f"Student #{track_id}")
            is_biometric_enrolled = bool(obs.get("is_enrolled", False))

            # Enforce that student must be enrolled in the active course if course roster is provided
            if self.enrolled_student_ids is not None:
                is_course_enrolled = is_biometric_enrolled and bool(student_id and str(student_id).strip().upper() in self.enrolled_student_ids)
            else:
                is_course_enrolled = True

            # If enrolled in course, use student_id as primary key
            key = student_id if (student_id and is_course_enrolled) else f"track_{track_id}"
            if student_id and not is_course_enrolled and "Unenrolled" not in name:
                name = f"{name} (Unenrolled Auditor)"
            
            score = float(obs.get("gaze_score", 0.5))

            if key not in self.records:
                initial_status = AttendanceStatus.PRESENT.value if is_course_enrolled else "UNENROLLED"
                self.records[key] = {
                    "student_key": key,
                    "student_id": student_id if is_course_enrolled else None,
                    "student_name": name,
                    "is_enrolled": is_course_enrolled,
                    "first_seen_timestamp": frame_timestamp,
                    "last_seen_timestamp": frame_timestamp,
                    "total_seconds_present": dt if is_course_enrolled else 0.0,
                    "presence_ratio": 1.0 if is_course_enrolled else 0.0,
                    "mean_engagement": score,
                    "status": initial_status,
                    "engagement_history": [score]
                }
            else:
                r = self.records[key]
                r["last_seen_timestamp"] = frame_timestamp
                # Update enrolled status if newly recognized
                if not r.get("is_enrolled") and is_course_enrolled:
                    r["student_id"] = student_id
                    r["student_name"] = name
                    r["is_enrolled"] = True

                if r.get("is_enrolled"):
                    r["total_seconds_present"] += dt
                    if r.get("first_seen_timestamp") is None:
                        r["first_seen_timestamp"] = frame_timestamp

                r["engagement_history"].append(score)
                # Keep up to 200 recent score samples in memory
                if len(r["engagement_history"]) > 200:
                    r["engagement_history"].pop(0)
                r["mean_engagement"] = round(float(sum(r["engagement_history"]) / len(r["engagement_history"])), 3)

                # Strictly qualify attendance ONLY for enrolled students!
                if r.get("is_enrolled"):
                    first_t = r.get("first_seen_timestamp") or frame_timestamp
                    denom = max(session_elapsed, r["total_seconds_present"])
                    overall_ratio = float(min(1.0, r["total_seconds_present"] / max(denom, 1.0)))
                    since_seen = max(1.0, frame_timestamp - first_t)
                    active_ratio = float(min(1.0, r["total_seconds_present"] / since_seen))
                    # Active students in scene qualify based on attendance since arrival
                    effective_ratio = active_ratio if (frame_timestamp - r["last_seen_timestamp"] < 5.0) else overall_ratio
                    r["presence_ratio"] = round(effective_ratio, 3)
                    if not r.get("manual_override"):
                        r["status"] = self._qualify_status(effective_ratio).value
                else:
                    r["presence_ratio"] = 0.0
                    r["status"] = "UNENROLLED"

    def register_student_join(
        self,
        student_id: str,
        student_name: str,
        meeting_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registers an online student participant joining the live class session
        via Zoom / Google Meet / App background agent.
        """
        if not self.is_active:
            return {"success": False, "detail": "No active lecture session in progress."}

        # Check if student is enrolled in the session's course
        if self.enrolled_student_ids is not None and str(student_id).strip().upper() not in self.enrolled_student_ids:
            return {
                "success": False,
                "detail": f"Attendance Restricted: Student {student_id} is not enrolled in {self.course_code}. You may only attend courses in which you are enrolled."
            }

        now = time.time()
        key = student_id
        session_elapsed = self.get_session_elapsed_seconds()

        if key not in self.records:
            self.records[key] = {
                "student_key": key,
                "student_id": student_id,
                "student_name": student_name,
                "is_enrolled": True,
                "first_seen_timestamp": now,
                "last_seen_timestamp": now,
                "total_seconds_present": max(1.0, min(session_elapsed, 5.0)),
                "presence_ratio": 1.0,
                "mean_engagement": 0.88,
                "status": AttendanceStatus.PRESENT.value,
                "engagement_history": [0.88],
                "is_online_joined": True,
                "has_left": False,
                "meeting_url": meeting_url
            }
        else:
            r = self.records[key]
            r["is_online_joined"] = True
            r["has_left"] = False
            if r.get("first_seen_timestamp") is None:
                r["first_seen_timestamp"] = now
            r["last_seen_timestamp"] = now
            r["total_seconds_present"] = max(r.get("total_seconds_present", 0.0), 1.0)
            r["presence_ratio"] = 1.0
            r["status"] = AttendanceStatus.PRESENT.value
            if not r.get("engagement_history"):
                r["mean_engagement"] = 0.88
                r["engagement_history"] = [0.88]
            if meeting_url:
                r["meeting_url"] = meeting_url

        logger.info(f"Student {student_id} ({student_name}) joined live session {self.session_id}")
        return {
            "success": True,
            "session_id": self.session_id,
            "student_id": student_id,
            "joined_at": datetime.fromtimestamp(now).isoformat() + "Z"
        }

    def register_student_leave(self, student_id: str) -> Dict[str, Any]:
        """Marks student as having left the online class session."""
        if student_id in self.records:
            self.records[student_id]["has_left"] = True
            self.records[student_id]["is_online_joined"] = False
        return {"success": True, "student_id": student_id}

    def sync_online_students_presence(self):
        """Accumulates presence duration for online active students."""
        if not self.is_active:
            return
        now = time.time()
        session_dur = max(1.0, self.get_session_elapsed_seconds())
        for k, r in self.records.items():
            if r.get("is_online_joined") and not r.get("has_left"):
                last_t = r.get("last_seen_timestamp") or now
                dt = max(0.0, min(15.0, now - last_t))
                r["total_seconds_present"] += dt
                r["last_seen_timestamp"] = now
                overall_ratio = float(min(1.0, r["total_seconds_present"] / session_dur))
                first_t = r.get("first_seen_timestamp") or now
                since_seen = max(1.0, now - first_t)
                active_ratio = float(min(1.0, r["total_seconds_present"] / since_seen))
                effective_ratio = max(active_ratio, overall_ratio)
                if r.get("is_enrolled"):
                    r["presence_ratio"] = round(effective_ratio, 3)
                    if not r.get("manual_override"):
                        r["status"] = self._qualify_status(effective_ratio).value
                else:
                    r["presence_ratio"] = 0.0
                    r["status"] = "UNENROLLED"

    def get_live_attendance_table(self) -> List[Dict[str, Any]]:
        """
        Returns structured list of student attendance rows.
        """
        self.sync_online_students_presence()
        rows = []
        for k, r in self.records.items():
            rows.append({
                "student_key": k,
                "student_id": r["student_id"] or "Unenrolled",
                "name": r["student_name"],
                "student_name": r["student_name"],
                "is_enrolled": r["is_enrolled"],
                "time_present_sec": round(r["total_seconds_present"], 1),
                "total_seconds_present": round(r["total_seconds_present"], 1),
                "presence_ratio": r["presence_ratio"],
                "presence_pct": round(r["presence_ratio"] * 100, 1),
                "mean_engagement": r["mean_engagement"],
                "status": r["status"]
            })
        return rows

    def export_to_dataframe(self) -> pd.DataFrame:
        """Exports attendance records to a pandas DataFrame."""
        rows = self.get_live_attendance_table()
        if not rows:
            return pd.DataFrame(columns=[
                "student_id", "name", "is_enrolled", "time_present_sec",
                "presence_pct", "mean_engagement", "status"
            ])
        return pd.DataFrame(rows)

    def export_to_csv(self, file_path: str) -> str:
        """Saves session attendance records to a CSV file."""
        df = self.export_to_dataframe()
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        df.to_csv(file_path, index=False)
        logger.info(f"Attendance exported to CSV: {file_path}")
        return file_path

    def get_session_attendance_report(self) -> Dict[str, Any]:
        """
        Generates comprehensive aggregate report for the session.
        Attendance counts and percentages strictly reflect enrolled course students.
        """
        self.sync_online_students_presence()
        enrolled_records = [r for r in self.records.values() if r.get("is_enrolled")]
        # Prioritize enrolled course roster for official reporting
        target_records = enrolled_records if enrolled_records else list(self.records.values())
        total_students = len(target_records)
        present_count = sum(1 for r in target_records if r["status"] == AttendanceStatus.PRESENT.value)
        partial_count = sum(1 for r in target_records if r["status"] == AttendanceStatus.PARTIAL.value)
        absent_count = sum(1 for r in target_records if r["status"] == AttendanceStatus.ABSENT.value)
        
        attendance_rate = float(present_count / total_students * 100.0) if total_students > 0 else 0.0
        
        mean_engagements = [r["mean_engagement"] for r in self.records.values() if r.get("mean_engagement") is not None]
        avg_session_engagement = float(sum(mean_engagements) / len(mean_engagements)) if mean_engagements else 0.0

        return {
            "session_id": self.session_id,
            "title": self.session_title,
            "course_code": self.course_code,
            "is_active": self.is_active,
            "elapsed_seconds": round(self.get_session_elapsed_seconds(), 1),
            "total_students": total_students,
            "present_count": present_count,
            "partial_count": partial_count,
            "absent_count": absent_count,
            "attendance_rate_pct": round(attendance_rate, 1),
            "average_engagement": round(avg_session_engagement, 3),
            "student_records": list(self.records.values())
        }

    def manual_override_status(self, student_key: str, new_status: str) -> bool:
        """Manually overrides attendance verification status for a student record."""
        target_status = str(new_status).upper()
        if target_status not in [s.value for s in AttendanceStatus]:
            return False
            
        # Match by key or student_id
        for k, r in self.records.items():
            if k == student_key or r.get("student_id") == student_key or r.get("student_key") == student_key:
                r["status"] = target_status
                r["manual_override"] = True
                return True
        return False
