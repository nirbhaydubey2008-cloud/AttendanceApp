"""
tests/test_session_lifecycle_sync.py
Verification suite for Phase 8: Session Lifecycle & Real-Time Synchronization.
Validates Lecture state transitions (SCHEDULED -> LIVE -> COMPLETED),
real-time student live lecture tracking, and graceful finalization.
"""

import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from starlette.testclient import TestClient
from api.main import app
from database.database import SessionLocal
from database import crud
from services.auth_service import hash_password


def run_session_lifecycle_sync_tests():
    print("=" * 70)
    print("VERIFICATION SUITE: Phase 8 — Session Lifecycle & Real-Time Sync")
    print("=" * 70)

    client = TestClient(app)
    db = SessionLocal()

    tag = str(int(time.time() * 1000))[-6:]
    teacher_username = f"teacher_sync_{tag}"
    student_username = f"STU-2026-S{tag}"
    course_code = f"SYNC{tag}"
    t_password = "TeacherSyncPass123!"
    s_password = "StudentSyncPass123!"
    lecture_id = f"LEC-{course_code}-001"
    lecture_title = f"Lecture 1: State Machine Replication {tag}"

    try:
        # 1. Provision Teacher
        t_user = crud.create_user(
            db,
            username=teacher_username,
            hashed_password=hash_password(t_password),
            role="TEACHER",
            email=f"{teacher_username}@university.edu"
        )
        t_prof = crud.create_teacher(
            db,
            user_id=t_user.id,
            employee_id=f"EMP-SYNC-{tag}",
            name=f"Prof. Sync {tag}",
            department="Computer Science"
        )

        # 2. Provision Course & Student
        course = crud.create_course(
            db,
            course_code=course_code,
            title="Distributed Consensus",
            teacher_id=t_prof.id
        )
        s_user = crud.create_user(
            db,
            username=student_username,
            hashed_password=hash_password(s_password),
            role="STUDENT",
            email=f"{student_username.lower()}@university.edu"
        )
        s_prof = crud.create_or_get_student(
            db,
            student_id=student_username,
            name=f"Sync Student {tag}",
            roll_no=f"ROLL-S-{tag}",
            user_id=s_user.id,
            consent_given=True
        )
        crud.enroll_student_in_course(db, student_id=student_username, course_id=course.id)

        # 3. Schedule Lecture
        lecture = crud.create_lecture(
            db,
            lecture_id=lecture_id,
            course_id=course.id,
            teacher_id=t_prof.id,
            title=lecture_title,
            topic="Raft & Multi-Paxos",
            planned_duration_min=60
        )
        assert lecture.status == "SCHEDULED", f"Initial lecture status should be SCHEDULED, got {lecture.status}"
        saved_lecture_id = lecture.lecture_id

    finally:
        db.close()

    # Authenticate
    t_login = client.post("/api/auth/login", json={"identifier": teacher_username, "password": t_password})
    assert t_login.status_code == 200, f"Teacher login failed: {t_login.text}"
    t_headers = {"Authorization": f"Bearer {t_login.json()['token']}"}

    s_login = client.post("/api/auth/login", json={"identifier": student_username, "password": s_password})
    assert s_login.status_code == 200, f"Student login failed: {s_login.text}"
    s_headers = {"Authorization": f"Bearer {s_login.json()['token']}"}

    print("\nTest 1: Pre-session Student Live State (Idle)...")
    res_idle = client.get("/api/student/sessions/live", headers=s_headers)
    assert res_idle.status_code == 200
    idle_data = res_idle.json()
    assert idle_data["is_active"] is False, "Expected is_active=False when idle"
    assert idle_data["my_status"] == "NO_ACTIVE_SESSION"
    print("  [PASS] Student receives idle classroom state.")

    print("\nTest 2: Teacher Launches Session & Lecture State Transitions to LIVE...")
    start_res = client.post("/api/sessions/start", headers=t_headers, json={
        "title": lecture_title,
        "course_code": course_code,
        "lecture_id": saved_lecture_id
    })
    assert start_res.status_code == 200, f"Failed to start session: {start_res.text}"
    start_data = start_res.json()
    assert start_data["success"] is True
    live_sess_id = start_data["session"]["session_id"]

    # Verify Database Lecture Status transitioned to LIVE
    db_check = SessionLocal()
    try:
        lec_db = crud.get_lecture_by_id(db_check, saved_lecture_id)
        assert lec_db is not None, "Lecture record missing"
        assert lec_db.status == "LIVE", f"Expected lecture status LIVE, got {lec_db.status}"

        sess_db = crud.get_session_by_id(db_check, live_sess_id)
        assert sess_db is not None, "Session record missing"
        assert sess_db.lecture_id == lec_db.id, "Session not linked to lecture"
        assert sess_db.is_active is True, "Session should be active"
    finally:
        db_check.close()
    print("  [PASS] Lecture successfully transitioned: SCHEDULED -> LIVE.")

    print("\nTest 3: Real-Time Synchronization on Student Dashboard during LIVE Session...")
    res_live = client.get("/api/student/sessions/live", headers=s_headers)
    assert res_live.status_code == 200
    live_info = res_live.json()
    assert live_info["is_active"] is True, "Expected is_active=True"
    assert live_info["course_code"] == course_code, "Course code mismatch"
    assert live_info["title"] == lecture_title, "Lecture title mismatch"
    assert live_info["is_enrolled"] is True, "Student should be enrolled in live class"
    assert live_info["session_id"] == live_sess_id, "Session ID mismatch"
    print(f"  [PASS] Student synchronized in real time with active class: '{lecture_title}' ({course_code}).")

    print("\nTest 4: Teacher Finalizes Session & Lecture State Transitions to COMPLETED...")
    stop_res = client.post("/api/sessions/stop", headers=t_headers)
    assert stop_res.status_code == 200, f"Failed to stop session: {stop_res.text}"
    stop_data = stop_res.json()
    assert stop_data["success"] is True

    # Verify Database Lecture Status transitioned to COMPLETED
    db_check2 = SessionLocal()
    try:
        lec_db2 = crud.get_lecture_by_id(db_check2, saved_lecture_id)
        assert lec_db2.status == "COMPLETED", f"Expected lecture status COMPLETED, got {lec_db2.status}"

        sess_db2 = crud.get_session_by_id(db_check2, live_sess_id)
        assert sess_db2.is_active is False, "Session is_active should be False"
    finally:
        db_check2.close()
    print("  [PASS] Lecture successfully transitioned: LIVE -> COMPLETED.")

    print("\nTest 5: Post-Session Synchronization & Finalized Records...")
    res_post = client.get("/api/student/sessions/live", headers=s_headers)
    assert res_post.status_code == 200
    assert res_post.json()["is_active"] is False, "is_active should return False after finalization"
    print("  [PASS] Student live status cleanly reset to idle after lecture concludes.")

    print("\n" + "=" * 70)
    print("RESULT: ALL PHASE 8 SESSION LIFECYCLE & SYNC TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_session_lifecycle_sync_tests()
