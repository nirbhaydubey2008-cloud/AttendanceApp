#!/usr/bin/env python3
"""
tests/test_rbac_authorization.py
Verification suite for Phase 4: Role-Based Access Control (RBAC),
Server-Side Authorization, and IDOR Defense.
"""

import os
import sys
import time
import uuid
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.main import app
from database.database import SessionLocal
from database.models import User, Teacher, Student, Course, Enrollment, Session as DbSession, AttendanceRecord
import database.crud as crud
from services.auth_service import hash_password


def setup_test_users():
    """Sets up an isolated teacher and two isolated students for RBAC and IDOR testing."""
    db = SessionLocal()
    suffix = str(time.time_ns())[-8:]

    # 1. Test Teacher
    t_user = crud.create_user(
        db,
        username=f"rbac_t_{suffix}",
        hashed_password=hash_password("TeacherSecurePass123!"),
        role="TEACHER",
        email=f"teacher_{suffix}@university.edu"
    )
    t_prof = crud.create_teacher(
        db,
        user_id=t_user.id,
        employee_id=f"EMP_RBAC_{suffix}",
        name=f"Prof. RBAC {suffix}"
    )

    # 2. Test Student A
    s_user_a = crud.create_user(
        db,
        username=f"rbac_s_a_{suffix}",
        hashed_password=hash_password("StudentPassA123!"),
        role="STUDENT",
        email=f"student_a_{suffix}@university.edu"
    )
    s_prof_a = crud.create_or_get_student(
        db,
        student_id=f"STU-2026-A{suffix[:4]}",
        name=f"Alice Student {suffix}",
        roll_no=f"ROLL-A-{suffix[:4]}",
        user_id=s_user_a.id,
        consent_given=True
    )

    # 3. Test Student B
    s_user_b = crud.create_user(
        db,
        username=f"rbac_s_b_{suffix}",
        hashed_password=hash_password("StudentPassB123!"),
        role="STUDENT",
        email=f"student_b_{suffix}@university.edu"
    )
    s_prof_b = crud.create_or_get_student(
        db,
        student_id=f"STU-2026-B{suffix[:4]}",
        name=f"Bob Student {suffix}",
        roll_no=f"ROLL-B-{suffix[:4]}",
        user_id=s_user_b.id,
        consent_given=True
    )

    # 4. Test Course & Enrollments
    course = crud.create_course(
        db,
        course_code=f"RBAC{suffix[:4]}",
        title=f"RBAC Security Analysis {suffix}",
        teacher_id=t_prof.id
    )
    crud.enroll_student_in_course(db, student_id=s_prof_a.student_id, course_id=course.id)
    crud.enroll_student_in_course(db, student_id=s_prof_b.student_id, course_id=course.id)

    # 5. Test Session & Attendance Records
    sess_id = f"SESS_RBAC_{suffix}"
    db_sess = crud.create_session(
        db,
        session_id=sess_id,
        title="Security Lecture",
        course_code=course.course_code,
        teacher_id=t_prof.id,
        status="COMPLETED"
    )
    # Save attendance for both students
    crud.save_attendance_record(
        db,
        session_id=sess_id,
        student_id=s_prof_a.student_id,
        student_name=s_prof_a.name,
        track_id="trk_1",
        time_present_sec=1800.0,
        presence_ratio=0.90,
        status="PRESENT",
        mean_engagement=0.85
    )
    crud.save_attendance_record(
        db,
        session_id=sess_id,
        student_id=s_prof_b.student_id,
        student_name=s_prof_b.name,
        track_id="trk_2",
        time_present_sec=1200.0,
        presence_ratio=0.60,
        status="PARTIAL",
        mean_engagement=0.72
    )
    t_username = t_user.username
    sa_username = s_user_a.username
    sa_student_id = s_prof_a.student_id
    sb_username = s_user_b.username
    sb_student_id = s_prof_b.student_id
    course_code = course.course_code

    db.close()

    return {
        "teacher": {"username": t_username, "password": "TeacherSecurePass123!"},
        "student_a": {"username": sa_username, "student_id": sa_student_id, "password": "StudentPassA123!"},
        "student_b": {"username": sb_username, "student_id": sb_student_id, "password": "StudentPassB123!"},
        "course_code": course_code,
        "session_id": sess_id
    }


def main():
    print("=" * 65)
    print("VERIFICATION SUITE: Phase 4 — RBAC, Server-Side Guards & IDOR Defense")
    print("=" * 65)

    fixtures = setup_test_users()
    session_id = fixtures["session_id"]
    client = TestClient(app)

    # Login and obtain tokens
    # 1. Teacher
    t_resp = client.post("/api/auth/login", json={
        "identifier": fixtures["teacher"]["username"],
        "password": fixtures["teacher"]["password"]
    })
    assert t_resp.status_code == 200
    t_token = t_resp.json()["token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # 2. Student A
    sa_resp = client.post("/api/auth/login", json={
        "identifier": fixtures["student_a"]["student_id"],
        "password": fixtures["student_a"]["password"]
    })
    assert sa_resp.status_code == 200
    sa_token = sa_resp.json()["token"]
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 3. Student B
    sb_resp = client.post("/api/auth/login", json={
        "identifier": fixtures["student_b"]["student_id"],
        "password": fixtures["student_b"]["password"]
    })
    assert sb_resp.status_code == 200
    sb_token = sb_resp.json()["token"]
    sb_headers = {"Authorization": f"Bearer {sb_token}"}

    # -----------------------------------------------------------------
    # Test 1: Unauthenticated requests rejected with 401 Unauthorized
    # -----------------------------------------------------------------
    print("\nTest 1: Unauthenticated request handling (401 Unauthorized)...")
    res1 = client.post("/api/sessions/start", json={"session_id": "NOAUTH", "title": "Test", "course_code": "CS101"})
    assert res1.status_code == 401, f"Expected 401, got {res1.status_code}"
    print(f"  [PASS] Missing token returns HTTP 401: {res1.json()['detail']}")

    res1_bad = client.post(
        "/api/sessions/start",
        json={"session_id": "BAD", "title": "Test", "course_code": "CS101"},
        headers={"Authorization": "Bearer invalid_junk_token"}
    )
    assert res1_bad.status_code == 401, f"Expected 401, got {res1_bad.status_code}"
    print(f"  [PASS] Invalid token returns HTTP 401: {res1_bad.json()['detail']}")

    # -----------------------------------------------------------------
    # Test 2: Role Violations — Student attempting Teacher endpoints (403 Forbidden)
    # -----------------------------------------------------------------
    print("\nTest 2: Role violations — Student attempting Teacher operations (403 Forbidden)...")
    # Student attempts to start session
    res_s_sess = client.post(
        "/api/sessions/start",
        json={"session_id": "STU_TRY_SESS", "title": "Hack", "course_code": "CS101"},
        headers=sa_headers
    )
    assert res_s_sess.status_code == 403, f"Expected 403, got {res_s_sess.status_code}"
    print(f"  [PASS] Student starting session rejected with 403: {res_s_sess.json()['detail']}")

    # Student attempts to toggle camera
    res_s_cam = client.post("/api/camera/toggle?enabled=false", headers=sa_headers)
    assert res_s_cam.status_code == 403
    print("  [PASS] Student camera toggle rejected with 403.")

    # Student attempts attendance correction override
    res_s_corr = client.post(
        "/api/attendance/correct",
        json={"session_id": session_id, "student_key": "trk_1", "status": "PRESENT"},
        headers=sa_headers
    )
    assert res_s_corr.status_code == 403
    print("  [PASS] Student attendance override rejected with 403.")

    # Student attempts to create course
    res_s_crs = client.post(
        "/api/teacher/courses",
        json={"course_code": "STU999", "title": "Unauthorized"},
        headers=sa_headers
    )
    assert res_s_crs.status_code == 403
    print("  [PASS] Student course creation rejected with 403.")

    # -----------------------------------------------------------------
    # Test 3: Teacher access to Teacher-dedicated endpoints (200 OK)
    # -----------------------------------------------------------------
    print("\nTest 3: Teacher access to Teacher-dedicated endpoints (200 OK)...")
    res_t_crs = client.get("/api/teacher/courses", headers=t_headers)
    assert res_t_crs.status_code == 200
    print(f"  [PASS] Teacher retrieved courses ({len(res_t_crs.json()['courses'])} course(s)).")

    res_t_lect = client.post(
        "/api/teacher/lectures",
        json={
            "lecture_id": f"LEC_{fixtures['course_code']}_01",
            "course_code": fixtures["course_code"],
            "title": "Threat Modeling",
            "topic": "IDOR and Broken Access Control"
        },
        headers=t_headers
    )
    assert res_t_lect.status_code == 200
    assert res_t_lect.json()["success"] is True
    print(f"  [PASS] Teacher scheduled lecture successfully: {res_t_lect.json()['lecture']['title']}")

    res_t_logs = client.get("/api/teacher/audit-logs", headers=t_headers)
    assert res_t_logs.status_code == 200
    assert res_t_logs.json()["count"] > 0
    print(f"  [PASS] Teacher retrieved audit logs ({res_t_logs.json()['count']} entries).")

    # -----------------------------------------------------------------
    # Test 4: Student-dedicated endpoints & Role enforcement
    # -----------------------------------------------------------------
    print("\nTest 4: Student-dedicated endpoints (My Attendance, Live, Courses)...")
    # Teacher attempting student-only endpoint
    res_t_stu = client.get("/api/student/me/attendance", headers=t_headers)
    assert res_t_stu.status_code == 403
    print(f"  [PASS] Teacher calling student-only endpoint rejected with 403: {res_t_stu.json()['detail']}")

    # Student A calling student-only endpoint
    res_sa_att = client.get("/api/student/me/attendance", headers=sa_headers)
    assert res_sa_att.status_code == 200
    sa_data = res_sa_att.json()
    assert sa_data["student_id"] == fixtures["student_a"]["student_id"]
    assert sa_data["total_sessions"] >= 1
    print(f"  [PASS] Student A personal attendance history retrieved ({sa_data['total_sessions']} session(s), {sa_data['overall_attendance_pct']}%).")

    res_sa_live = client.get("/api/student/sessions/live", headers=sa_headers)
    assert res_sa_live.status_code == 200
    print(f"  [PASS] Student A live session check: {res_sa_live.json()['my_status']}")

    res_sa_crs = client.get("/api/student/courses", headers=sa_headers)
    assert res_sa_crs.status_code == 200
    assert res_sa_crs.json()["count"] >= 1
    print(f"  [PASS] Student A enrolled courses retrieved: {res_sa_crs.json()['courses'][0]['course_code']}")

    # -----------------------------------------------------------------
    # Test 5: IDOR Protection on Session Attendance
    # -----------------------------------------------------------------
    print("\nTest 5: IDOR Protection verification...")
    # 1. Teacher views session: sees BOTH students
    t_view = client.get(f"/api/sessions/{session_id}/attendance", headers=t_headers)
    assert t_view.status_code == 200
    assert t_view.json()["count"] == 2
    print(f"  [PASS] Teacher query returns all student records (count={t_view.json()['count']}).")

    # 2. Student A views session without parameters: sees ONLY their own record
    sa_view = client.get(f"/api/sessions/{session_id}/attendance", headers=sa_headers)
    assert sa_view.status_code == 200
    sa_records = sa_view.json()["records"]
    assert len(sa_records) == 1
    assert sa_records[0]["student_id"] == fixtures["student_a"]["student_id"]
    print(f"  [PASS] Student A query naturally filters to ONLY their record ({sa_records[0]['student_id']}).")

    # 3. Student A attempts IDOR: tries to query Student B's record explicitly (?student_id=Student_B)
    target_id_b = fixtures["student_b"]["student_id"]
    idor_attempt = client.get(f"/api/sessions/{session_id}/attendance?student_id={target_id_b}", headers=sa_headers)
    assert idor_attempt.status_code == 403, f"Expected 403 on IDOR attempt, got {idor_attempt.status_code}"
    print(f"  [PASS] IDOR defense triggered: 403 Forbidden — {idor_attempt.json()['detail']}")

    # 4. Student B views session: sees ONLY their own record
    sb_view = client.get(f"/api/sessions/{session_id}/attendance", headers=sb_headers)
    assert sb_view.status_code == 200
    sb_records = sb_view.json()["records"]
    assert len(sb_records) == 1
    assert sb_records[0]["student_id"] == fixtures["student_b"]["student_id"]
    print(f"  [PASS] Student B query naturally filters to ONLY their record ({sb_records[0]['student_id']}).")

    # -----------------------------------------------------------------
    # Test 6: Video Feed Stream Authorization
    # -----------------------------------------------------------------
    print("\nTest 6: Video stream authentication & authorization...")
    # Missing token
    v_noauth = client.get("/api/video/feed")
    assert v_noauth.status_code == 401
    print("  [PASS] Video feed without token rejected with 401.")

    # Student token
    v_student = client.get(f"/api/video/feed?token={sa_token}")
    assert v_student.status_code == 403
    print("  [PASS] Video feed with student token rejected with 403.")

    print("\n" + "=" * 65)
    print("RESULT: ALL RBAC & IDOR VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
