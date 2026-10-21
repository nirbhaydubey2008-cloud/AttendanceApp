"""
tests/test_student_dashboard.py
Verification suite for Phase 7: Student Dashboard APIs, Data Contracts, and IDOR Defense.
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
from services import auth_service
from services.auth_service import hash_password


def run_student_dashboard_tests():
    print("=" * 65)
    print("VERIFICATION SUITE: Phase 7 — Student Dashboard Views & Contracts")
    print("=" * 65)

    client = TestClient(app)
    db = SessionLocal()

    tag = str(int(time.time() * 1000))[-6:]
    teacher_username = f"teacher_p7_{tag}"
    student_username = f"STU-2026-7{tag}"
    course_code = f"CS7{tag}"
    t_password = "TeacherSecret123!"
    s_init_password = "StudentInitPass123!"

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
            employee_id=f"EMP-7{tag}",
            name=f"Prof. Test P7 {tag}",
            department="Computer Science"
        )

        # 2. Provision Course
        course = crud.create_course(
            db,
            course_code=course_code,
            title="Distributed Systems",
            teacher_id=t_prof.id
        )

        # 3. Provision Student
        s_user = crud.create_user(
            db,
            username=student_username,
            hashed_password=hash_password(s_init_password),
            role="STUDENT",
            email=f"{student_username.lower()}@university.edu",
            must_change_password=True
        )
        s_prof = crud.create_or_get_student(
            db,
            student_id=student_username,
            name=f"David Student {tag}",
            roll_no=f"ROLL-7{tag}",
            user_id=s_user.id,
            consent_given=True
        )
        crud.enroll_student_in_course(db, student_id=student_username, course_id=course.id)

        # Create sample session & attendance record
        sess = crud.create_session(
            db,
            session_id=f"SESS-P7-{tag}",
            course_code=course_code,
            title="Lecture 1: Paxos Consensus",
            teacher_id=t_prof.id,
            status="COMPLETED"
        )
        crud.save_attendance_record(
            db,
            session_id=sess.session_id,
            student_id=student_username,
            student_name=s_prof.name,
            track_id="trk_p7",
            time_present_sec=2800.0,
            presence_ratio=0.85,
            status="PRESENT",
            mean_engagement=0.88
        )
        target_session_id = sess.session_id
    finally:
        db.close()

    # Authenticate via /api/auth/login
    t_login = client.post("/api/auth/login", json={"identifier": teacher_username, "password": t_password})
    assert t_login.status_code == 200, f"Teacher login failed: {t_login.text}"
    t_headers = {"Authorization": f"Bearer {t_login.json()['token']}"}

    s_login = client.post("/api/auth/login", json={"identifier": student_username, "password": s_init_password})
    assert s_login.status_code == 200, f"Student login failed: {s_login.text}"
    s_headers = {"Authorization": f"Bearer {s_login.json()['token']}"}

    print("\nTest 1: Student Overview & Personal Attendance API (/api/student/me/attendance)...")
    res = client.get("/api/student/me/attendance", headers=s_headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["student_id"] == student_username, "Student ID mismatch"
    assert data["total_sessions"] >= 1, "Session count should be at least 1"
    assert data["present_sessions"] >= 1, "Present count should be at least 1"
    assert data["overall_attendance_pct"] >= 80.0, "Overall attendance pct calculation incorrect"
    assert len(data["records"]) >= 1, "Should contain at least 1 attendance record"
    rec = data["records"][0]
    assert rec["status"] == "PRESENT", "Status should be PRESENT"
    assert rec["presence_pct"] == 85.0, "Presence pct should be 85.0"
    print("  [PASS] Student attendance summary & record structure verified.")

    print("\nTest 2: Student Enrolled Courses API (/api/student/courses)...")
    res_c = client.get("/api/student/courses", headers=s_headers)
    assert res_c.status_code == 200, f"Expected 200, got {res_c.status_code}: {res_c.text}"
    c_data = res_c.json()
    assert c_data["count"] >= 1, "Course count should be at least 1"
    course_codes = [c["course_code"] for c in c_data["courses"]]
    assert course_code in course_codes, f"Course {course_code} not found in student enrollment"
    print(f"  [PASS] Enrolled courses verified: {course_codes}")

    print("\nTest 3: Student Live Session Tracking (/api/student/sessions/live)...")
    res_live = client.get("/api/student/sessions/live", headers=s_headers)
    assert res_live.status_code == 200, f"Expected 200: {res_live.text}"
    live_info = res_live.json()
    assert "is_active" in live_info, "is_active key missing"
    assert "my_status" in live_info, "my_status key missing"
    print("  [PASS] Live session status API contract verified.")

    print("\nTest 4: First-time Password Reset & Profile State...")
    # Check initial must_change_password=True
    res_me = client.get("/api/auth/me", headers=s_headers)
    assert res_me.status_code == 200
    assert res_me.json()["must_change_password"] is True, "Expected must_change_password=True"

    # Change password
    new_permanent_pw = "StudentPermanentPass456!"
    ch_res = client.post(
        "/api/auth/change-password",
        headers=s_headers,
        json={"old_password": s_init_password, "new_password": new_permanent_pw}
    )
    assert ch_res.status_code == 200, f"Password change failed: {ch_res.text}"

    # Check updated must_change_password=False
    res_me2 = client.get("/api/auth/me", headers=s_headers)
    assert res_me2.json()["must_change_password"] is False, "Expected must_change_password=False after change"

    # Verify old password no longer works
    bad_login = client.post("/api/auth/login", json={"identifier": student_username, "password": s_init_password})
    assert bad_login.status_code == 401, "Old temporary password should be rejected"

    # Verify new password works
    good_login = client.post("/api/auth/login", json={"identifier": student_username, "password": new_permanent_pw})
    assert good_login.status_code == 200, "New password should succeed"
    print("  [PASS] Student first-time password reset successfully cleared temporary flag.")

    print("\nTest 5: Anti-IDOR and Role Isolation Verification...")
    # Student cannot call teacher audit logs
    res_audit = client.get("/api/teacher/audit-logs", headers=s_headers)
    assert res_audit.status_code == 403, "Student must not be allowed to access teacher audit logs"

    # Student cannot toggle camera
    res_cam = client.post("/api/camera/toggle", headers=s_headers)
    assert res_cam.status_code == 403, "Student must not be allowed to toggle camera"

    # Student cannot create courses
    res_new_c = client.post("/api/teacher/courses", headers=s_headers, json={"course_code": "HACK", "title": "Hacked"})
    assert res_new_c.status_code == 403, "Student must not be allowed to create courses"

    # Student cannot query teacher-only session attendance for all students
    res_all_att = client.get(f"/api/sessions/{target_session_id}/attendance", headers=s_headers)
    assert res_all_att.status_code == 200
    # Because of IDOR protection, student only sees their own record
    assert len(res_all_att.json()["records"]) == 1
    assert res_all_att.json()["records"][0]["student_id"] == student_username
    print("  [PASS] Role isolation & anti-IDOR boundaries verified.")

    # 6. Online Class Background Join & Presence Tracking
    print("\nTest 6: Online Class Background Join & Attendance Tracking...")
    # Start a live session as teacher
    client.post("/api/sessions/start", json={"title": "Online Algorithms", "course_code": course_code}, headers=t_headers)

    # Student joins live session
    res_join = client.post("/api/student/sessions/join", headers=s_headers)
    assert res_join.status_code == 200, f"Join failed: {res_join.text}"
    assert res_join.json()["success"] is True

    # Verify student is now marked present and is_joined in student live session
    res_live = client.get("/api/student/sessions/live", headers=s_headers)
    assert res_live.status_code == 200
    assert res_live.json()["is_joined"] is True
    assert res_live.json()["my_status"] == "PRESENT"

    # Verify student is visible in teacher's live attendance table
    res_t_live = client.get("/api/attendance/live", headers=t_headers)
    assert res_t_live.status_code == 200
    t_records = res_t_live.json()["records"]
    matching = [r for r in t_records if r.get("student_id") == student_username]
    assert len(matching) == 1, "Joined student must appear in teacher live attendance table"
    assert matching[0]["status"] == "PRESENT"

    # Student leaves live session
    res_leave = client.post("/api/student/sessions/leave", headers=s_headers)
    assert res_leave.status_code == 200
    assert res_leave.json()["success"] is True

    # Teacher finalizes session
    client.post("/api/sessions/stop", headers=t_headers)
    print("  [PASS] Online class background join, teacher sync, and leave flow verified.")

    print("\n" + "=" * 65)
    print("RESULT: ALL PHASE 7 STUDENT DASHBOARD TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    run_student_dashboard_tests()
