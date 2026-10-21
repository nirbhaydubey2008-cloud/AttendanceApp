#!/usr/bin/env python3
"""
tests/test_student_enrollment_provisioning.py
Verification suite for Phase 5: Student Enrollment & Account Provisioning.
Validates:
1. Automatic sequential Student ID generation (STU-YYYY-XXXX).
2. Automatic User account creation with role STUDENT and temporary password.
3. Duplicate enrollment defenses (roll number, email, and ID collision guards).
4. Course enrollment linkage in SQLite.
5. Student initial login with temporary password and mandatory password change.
6. Role-based permission enforcement on enrollment endpoints.
"""

import os
import sys
import time
import numpy as np
import cv2
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.main import app
from database.database import SessionLocal
from database.models import User, Student, Course, Enrollment
import database.crud as crud


def create_synthetic_face_bytes() -> bytes:
    """Generates synthetic JPEG face image for testing enrollment."""
    img = np.full((300, 300, 3), 215, dtype=np.uint8)
    cv2.circle(img, (150, 150), 85, (170, 170, 170), -1)
    cv2.circle(img, (120, 130), 10, (40, 40, 40), -1)
    cv2.circle(img, (180, 130), 10, (40, 40, 40), -1)
    cv2.line(img, (150, 135), (150, 165), (60, 60, 60), 3)
    cv2.ellipse(img, (150, 185), (30, 15), 0, 0, 180, (40, 40, 40), 3)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def main():
    print("=" * 70)
    print("VERIFICATION SUITE: Phase 5 — Student Enrollment & Account Provisioning")
    print("=" * 70)

    client = TestClient(app)
    img_bytes = create_synthetic_face_bytes()
    suffix = str(time.time_ns())[-6:]

    # 1. Authenticate as Teacher
    t_login = client.post("/api/auth/login", json={"identifier": "teacher", "password": "TeacherPassword123!"})
    assert t_login.status_code == 200, f"Teacher login failed: {t_login.text}"
    t_token = t_login.json()["token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}
    print("  ✓ Authenticated as Teacher.")

    # Create a test course to test automatic course enrollment
    course_code = f"CSE{suffix}"
    crs_resp = client.post(
        "/api/teacher/courses",
        json={"course_code": course_code, "title": f"Computer Architecture {suffix}"},
        headers=t_headers
    )
    assert crs_resp.status_code == 200
    print(f"  ✓ Target course {course_code} created.")

    # -----------------------------------------------------------------
    # Test 1: Auto-generated Student ID and Account Provisioning
    # -----------------------------------------------------------------
    print("\nTest 1: Auto-generated Student ID & Temporary Password Provisioning...")
    st_name = f"David Student {suffix}"
    st_roll = f"ROLL-{suffix}"
    st_email = f"david_{suffix}@university.edu"

    # Teacher enrolls student WITHOUT specifying student_id
    enroll_resp = client.post(
        "/api/students/enroll",
        data={
            "name": st_name,
            "roll_no": st_roll,
            "email": st_email,
            "course_code": course_code,
            "consent_given": "true"
        },
        files={"photo": ("face.jpg", img_bytes, "image/jpeg")},
        headers=t_headers
    )
    assert enroll_resp.status_code == 200, f"Enrollment failed: {enroll_resp.text}"
    enroll_data = enroll_resp.json()
    assert enroll_data["success"] is True

    # Validate generated Student ID format (STU-YYYY-XXXX)
    gen_student_id = enroll_data["student"]["student_id"]
    assert gen_student_id.startswith("STU-"), f"Unexpected ID format: {gen_student_id}"
    print(f"  [PASS] Auto-generated Student ID: {gen_student_id}")

    # Validate credentials payload
    creds = enroll_data["credentials"]
    assert creds["username"] == gen_student_id
    temp_pass = creds["temporary_password"]
    assert temp_pass.startswith("Temp-")
    assert creds["must_change_password"] is True
    print(f"  [PASS] Temporary activation credentials generated: {temp_pass}")

    # Verify database persistence
    with SessionLocal() as db:
        user_rec = crud.get_user_by_username(db, gen_student_id)
        assert user_rec is not None
        assert user_rec.role == "STUDENT"
        assert user_rec.email == st_email
        assert user_rec.must_change_password is True

        student_rec = crud.get_student_by_id(db, gen_student_id)
        assert student_rec is not None
        assert student_rec.user_id == user_rec.id
        assert student_rec.roll_no == st_roll

        # Verify course enrollment link
        enrollments = crud.get_student_enrollments(db, gen_student_id)
        assert len(enrollments) >= 1
        assert any(e.course.course_code == course_code for e in enrollments)
        print("  [PASS] Student linked to User account and Course enrollment in SQLite.")

    # -----------------------------------------------------------------
    # Test 2: Initial Student Login & Mandatory Password Change
    # -----------------------------------------------------------------
    print("\nTest 2: Student Login with Temp Password & Password Change Flow...")
    stu_login = client.post("/api/auth/login", json={
        "identifier": gen_student_id,
        "password": temp_pass
    })
    assert stu_login.status_code == 200, f"Student login failed: {stu_login.text}"
    stu_login_data = stu_login.json()
    assert stu_login_data["user"]["must_change_password"] is True
    stu_token = stu_login_data["token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}
    print("  [PASS] Student authenticated successfully using temporary credentials.")

    # Student updates password
    new_perm_pass = "DavidPermanentPass123!"
    pw_resp = client.post(
        "/api/auth/change-password",
        json={"old_password": temp_pass, "new_password": new_perm_pass},
        headers=stu_headers
    )
    assert pw_resp.status_code == 200
    print("  [PASS] Student updated password successfully.")

    # Verify old temp password no longer works
    bad_relogin = client.post("/api/auth/login", json={
        "identifier": gen_student_id,
        "password": temp_pass
    })
    assert bad_relogin.status_code == 401
    print("  [PASS] Old temporary password successfully invalidated.")

    # Verify new password succeeds and must_change_password is False
    good_relogin = client.post("/api/auth/login", json={
        "identifier": gen_student_id,
        "password": new_perm_pass
    })
    assert good_relogin.status_code == 200
    assert good_relogin.json()["user"]["must_change_password"] is False
    print("  [PASS] Re-login with permanent password succeeded (must_change_password=False).")

    # -----------------------------------------------------------------
    # Test 3: Duplicate Enrollment Prevention Guards
    # -----------------------------------------------------------------
    print("\nTest 3: Duplicate Enrollment Prevention Guards...")

    # A. Duplicate Roll Number
    dup_roll_resp = client.post(
        "/api/students/enroll",
        data={
            "name": "Different Student",
            "roll_no": st_roll,  # Duplicate roll number
            "consent_given": "true"
        },
        files={"photo": ("face.jpg", img_bytes, "image/jpeg")},
        headers=t_headers
    )
    assert dup_roll_resp.status_code == 400
    assert "already assigned" in dup_roll_resp.json()["detail"].lower() or "roll number" in dup_roll_resp.json()["detail"].lower()
    print(f"  [PASS] Duplicate roll number rejected: {dup_roll_resp.json()['detail']}")

    # B. Duplicate Email Address
    dup_email_resp = client.post(
        "/api/students/enroll",
        data={
            "name": "Different Student 2",
            "roll_no": f"NEW_ROLL_{suffix}",
            "email": st_email,  # Duplicate email
            "consent_given": "true"
        },
        files={"photo": ("face.jpg", img_bytes, "image/jpeg")},
        headers=t_headers
    )
    assert dup_email_resp.status_code == 400
    assert "email" in dup_email_resp.json()["detail"].lower()
    print(f"  [PASS] Duplicate email rejected: {dup_email_resp.json()['detail']}")

    # C. Duplicate Student ID with different name
    dup_id_resp = client.post(
        "/api/students/enroll",
        data={
            "name": "Different Student 3",
            "student_id": gen_student_id,  # Colliding ID
            "consent_given": "true"
        },
        files={"photo": ("face.jpg", img_bytes, "image/jpeg")},
        headers=t_headers
    )
    assert dup_id_resp.status_code == 400
    assert "already registered" in dup_id_resp.json()["detail"].lower()
    print(f"  [PASS] Student ID collision rejected: {dup_id_resp.json()['detail']}")

    # -----------------------------------------------------------------
    # Test 4: Authorization Guards on Enrollment Endpoint
    # -----------------------------------------------------------------
    print("\nTest 4: RBAC on Student Enrollment...")
    # Student attempting to enroll another student
    stu_enroll_try = client.post(
        "/api/students/enroll",
        data={"name": "Hacked Student", "consent_given": "true"},
        files={"photo": ("face.jpg", img_bytes, "image/jpeg")},
        headers=stu_headers
    )
    assert stu_enroll_try.status_code == 403
    print("  [PASS] Student role rejected from enrolling students (403 Forbidden).")

    # Unauthenticated request
    anon_try = client.post(
        "/api/students/enroll",
        data={"name": "Anon Student", "consent_given": "true"},
        files={"photo": ("face.jpg", img_bytes, "image/jpeg")}
    )
    assert anon_try.status_code == 401
    print("  [PASS] Unauthenticated request rejected (401 Unauthorized).")

    print("\n" + "=" * 70)
    print("RESULT: ALL PHASE 5 ENROLLMENT & PROVISIONING TESTS PASSED!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
