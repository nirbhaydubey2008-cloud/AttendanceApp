"""
dashboard/components/api_client.py
Safe HTTP Client for FastAPI backend communications.
Includes role-aware bearer token injection, fallback handling, and timeouts.
"""

import os
from typing import Dict, List, Optional, Any
import requests

API_BASE = os.getenv("API_URL", "http://127.0.0.1:8000")


def get_stored_token() -> Optional[str]:
    """Retrieves session token from Streamlit state if available."""
    try:
        import streamlit as st
        return st.session_state.get("auth_token")
    except Exception:
        return None


def fetch_api(
    endpoint: str,
    method: str = "GET",
    data: Any = None,
    files: Any = None,
    token: Optional[str] = None,
    timeout: float = 4.0
) -> Optional[Dict[str, Any]]:
    """Safe HTTP client communicating with backend."""
    url = f"{API_BASE}{endpoint}"
    active_token = token or get_stored_token()
    headers = {}
    if active_token:
        headers["Authorization"] = f"Bearer {active_token}"

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            if files:
                resp = requests.post(url, data=data, files=files, headers=headers, timeout=timeout)
            else:
                resp = requests.post(url, json=data, headers=headers, timeout=timeout)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=timeout)
        elif method == "PUT":
            resp = requests.put(url, json=data, headers=headers, timeout=timeout)
        elif method == "PATCH":
            resp = requests.patch(url, json=data, headers=headers, timeout=timeout)
        else:
            return None

        if resp.status_code in (200, 201):
            return resp.json()
        elif resp.status_code in (400, 401, 403, 404):
            try:
                err_data = resp.json()
                return {"_error": True, "status_code": resp.status_code, "detail": err_data.get("detail", "Error")}
            except Exception:
                return {"_error": True, "status_code": resp.status_code, "detail": resp.text}
        return None
    except requests.exceptions.RequestException as e:
        return None


# --- Authentication Endpoints ---

def login(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates teacher (username/email) or student (student_id/username)."""
    return fetch_api("/api/auth/login", method="POST", data={"identifier": identifier, "password": password})


def logout() -> Optional[Dict[str, Any]]:
    """Revokes active session token."""
    return fetch_api("/api/auth/logout", method="POST")


def get_me() -> Optional[Dict[str, Any]]:
    """Retrieves authenticated profile metadata."""
    return fetch_api("/api/auth/me")


def change_password(old_password: str, new_password: str) -> Optional[Dict[str, Any]]:
    """Updates user password."""
    return fetch_api("/api/auth/change-password", method="POST", data={"old_password": old_password, "new_password": new_password})


# --- System & Session Endpoints ---

def get_health() -> Optional[Dict[str, Any]]:
    return fetch_api("/health")


def get_current_session() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/sessions/current")


def start_session(title: str, course_code: str, session_id: Optional[str] = None, lecture_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    payload = {"title": title, "course_code": course_code}
    if session_id and session_id.strip():
        payload["session_id"] = session_id.strip()
    if lecture_id and lecture_id.strip():
        payload["lecture_id"] = lecture_id.strip()
    return fetch_api("/api/sessions/start", method="POST", data=payload)


def stop_session() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/sessions/stop", method="POST")


def get_live_attendance() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/attendance/live")


def get_engagement_summary() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/engagement/summary")


def get_recent_recommendations(limit: int = 10) -> Optional[Dict[str, Any]]:
    return fetch_api(f"/api/recommendations/recent?limit={limit}")


def evaluate_recommendations() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/recommendations/evaluate", method="POST")


def get_all_sessions(limit: int = 50) -> Optional[Dict[str, Any]]:
    return fetch_api(f"/api/sessions?limit={limit}")


def get_session_attendance(session_id: str, student_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    query = f"?student_id={student_id}" if student_id else ""
    return fetch_api(f"/api/sessions/{session_id}/attendance{query}")


def get_session_recommendations(session_id: str) -> Optional[Dict[str, Any]]:
    return fetch_api(f"/api/sessions/{session_id}/recommendations")


def correct_attendance(session_id: str, student_key: str, status: str) -> Optional[Dict[str, Any]]:
    payload = {
        "session_id": session_id,
        "student_key": student_key,
        "status": status
    }
    return fetch_api("/api/attendance/correct", method="POST", data=payload)


def get_system_stats() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/system/stats")


def get_enrolled_students() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/students")


def toggle_camera(enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    query = f"?enabled={str(enabled).lower()}" if enabled is not None else ""
    return fetch_api(f"/api/camera/toggle{query}", method="POST")


# --- Teacher Management Endpoints ---

def get_teacher_courses() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/teacher/courses")


def create_course(course_code: str, title: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    payload = {"course_code": course_code, "title": title, "description": description}
    return fetch_api("/api/teacher/courses", method="POST", data=payload)


def delete_course(course_code: str) -> Optional[Dict[str, Any]]:
    """Deletes a course and its associated enrollments."""
    return fetch_api(f"/api/teacher/courses/{course_code}", method="DELETE")


def get_teacher_lectures() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/teacher/lectures")


def create_lecture(
    lecture_id: str,
    course_code: str,
    title: str,
    topic: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    planned_duration_min: int = 60
) -> Optional[Dict[str, Any]]:
    payload = {
        "lecture_id": lecture_id,
        "course_code": course_code,
        "title": title,
        "topic": topic,
        "scheduled_date": scheduled_date,
        "planned_duration_min": planned_duration_min
    }
    return fetch_api("/api/teacher/lectures", method="POST", data=payload)


def get_audit_logs(limit: int = 50) -> Optional[Dict[str, Any]]:
    return fetch_api(f"/api/teacher/audit-logs?limit={limit}")


def enroll_student(
    name: str,
    photo_bytes: bytes,
    student_id: Optional[str] = None,
    roll_no: str = "",
    email: Optional[str] = None,
    course_code: Optional[str] = None,
    consent_given: bool = True
) -> Optional[Dict[str, Any]]:
    """Enrolls student and auto-provisions account."""
    data = {
        "name": name,
        "roll_no": roll_no,
        "consent_given": "true" if consent_given else "false"
    }
    if student_id and student_id.strip():
        data["student_id"] = student_id.strip()
    if email and email.strip():
        data["email"] = email.strip()
    if course_code and course_code.strip():
        data["course_code"] = course_code.strip()

    files = {"photo": ("student_photo.jpg", photo_bytes, "image/jpeg")}
    return fetch_api("/api/students/enroll", method="POST", data=data, files=files, timeout=8.0)


def enroll_student_camera(
    name: str,
    student_id: Optional[str] = None,
    roll_no: str = "",
    email: Optional[str] = None,
    course_code: Optional[str] = None,
    consent_given: bool = True
) -> Optional[Dict[str, Any]]:
    """Enrolls student using current camera snapshot."""
    payload = {
        "name": name,
        "student_id": student_id.strip() if student_id and student_id.strip() else None,
        "roll_no": roll_no,
        "email": email.strip() if email and email.strip() else None,
        "course_code": course_code.strip() if course_code and course_code.strip() else None,
        "consent_given": consent_given
    }
    return fetch_api("/api/students/enroll_camera", method="POST", data=payload, timeout=8.0)


def delete_student(student_id: str) -> Optional[Dict[str, Any]]:
    """Deletes a student profile, biometric vectors, and login credentials."""
    return fetch_api(f"/api/students/{student_id}", method="DELETE")


def get_camera_snapshot() -> Optional[bytes]:
    """Retrieves raw JPEG image bytes directly from active camera snapshot endpoint."""
    token = get_stored_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        url = f"{API_BASE}/api/camera/snapshot"
        resp = requests.get(url, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


# --- Student Dedicated Endpoints ---

def get_student_my_attendance() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/student/me/attendance")


def get_student_live_session() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/student/sessions/live")


def get_student_courses() -> Optional[Dict[str, Any]]:
    return fetch_api("/api/student/courses")


def join_live_session(meeting_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Enables student to check in / join active live class session."""
    payload = {"meeting_url": meeting_url} if meeting_url else {}
    return fetch_api("/api/student/sessions/join", method="POST", data=payload)


def leave_live_session() -> Optional[Dict[str, Any]]:
    """Enables student to leave the active live class session."""
    return fetch_api("/api/student/sessions/leave", method="POST")
