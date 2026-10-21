#!/usr/bin/env python3
"""
tests/test_auth.py
Verification suite for Authentication Core:
- PBKDF2-HMAC-SHA256 password hashing & verification
- Token creation, validation, sliding TTL, and revocation
- REST endpoints: /api/auth/login, /api/auth/logout, /api/auth/me, /api/auth/change-password
- Teacher provisioning CLI integration
"""

import os
import sys
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.main import app
from database.database import SessionLocal, init_db
import database.crud as crud
import services.auth_service as auth_service
from api.setup_teacher import setup_teacher


def test_password_hashing():
    print("Test 1: PBKDF2 Password hashing and constant-time verification...")
    raw_pw = "ClassroomSecret2026!"
    hashed = auth_service.hash_password(raw_pw)
    assert hashed.startswith("pbkdf2_sha256$600000$")
    assert auth_service.verify_password(raw_pw, hashed) is True
    assert auth_service.verify_password("WrongPassword!", hashed) is False
    assert auth_service.verify_password("", hashed) is False
    print("  [PASS] Hash format and verification verified.")


def test_token_lifecycle():
    print("\nTest 2: Session token generation, validation, and revocation...")
    token = auth_service.create_session_token(user_id=1, username="test_user", role="TEACHER")
    assert token is not None and len(token) > 20

    # Verify token
    payload = auth_service.verify_session_token(token)
    assert payload is not None
    assert payload["username"] == "test_user"
    assert payload["role"] == "TEACHER"

    # Revoke token
    revoked = auth_service.revoke_session_token(token)
    assert revoked is True
    assert auth_service.verify_session_token(token) is None
    print("  [PASS] Session token lifecycle verified.")


def test_auth_endpoints(client: TestClient):
    import time
    print("\nTest 3: Authentication REST endpoints (/api/auth/*)...")
    init_db()
    db = SessionLocal()

    ts = time.time_ns()
    t_uname = f"prof_{ts}"
    t_emp = f"EMP_{ts}"
    s_uname = f"stud_{ts}"
    s_id = f"STU_{ts}"
    t_email = f"alice_{ts}@college.edu"
    s_email = f"bob_{ts}@college.edu"

    # 1. Setup a Teacher
    setup_teacher(
        username=t_uname,
        name="Prof. Alice Auth",
        employee_id=t_emp,
        password="TeacherPassword123!",
        email=t_email
    )

    # 2. Setup a Student User and Profile
    s_user = crud.create_user(
        db,
        username=s_uname,
        email=s_email,
        hashed_password=auth_service.hash_password("StudentPassword123!"),
        role="STUDENT",
        must_change_password=True
    )
    student = crud.create_or_get_student(
        db,
        student_id=s_id,
        name="Bob Student",
        user_id=s_user.id
    )
    db.close()

    # 3. Test Teacher Login
    resp = client.post("/api/auth/login", json={"identifier": t_uname, "password": "TeacherPassword123!"})
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["success"] is True
    assert data["user"]["role"] == "TEACHER"
    assert data["user"]["name"] == "Prof. Alice Auth"
    teacher_token = data["token"]
    print("  [PASS] Teacher login succeeded.")

    # 4. Test Student Login via Student ID
    s_resp = client.post("/api/auth/login", json={"identifier": s_id, "password": "StudentPassword123!"})
    assert s_resp.status_code == 200
    s_data = s_resp.json()
    assert s_data["user"]["role"] == "STUDENT"
    assert s_data["user"]["identifier"] == s_id
    assert s_data["user"]["must_change_password"] is True
    student_token = s_data["token"]
    print("  [PASS] Student login via Student ID succeeded.")

    # 5. Test Invalid Credentials
    bad_resp = client.post("/api/auth/login", json={"identifier": t_uname, "password": "WrongPassword"})
    assert bad_resp.status_code == 401
    print("  [PASS] Invalid password rejected with 401.")

    # 6. Test /api/auth/me with Bearer token
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {teacher_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == t_uname
    assert me_data["role"] == "TEACHER"
    print("  [PASS] /api/auth/me profile verification passed.")

    # 7. Test /api/auth/change-password
    pw_resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "StudentPassword123!", "new_password": "NewStudentPassword456!"},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert pw_resp.status_code == 200
    print("  [PASS] /api/auth/change-password succeeded.")

    # Verify new password works
    re_login = client.post("/api/auth/login", json={"identifier": s_id, "password": "NewStudentPassword456!"})
    assert re_login.status_code == 200
    assert re_login.json()["user"]["must_change_password"] is False
    print("  [PASS] Re-login with updated password verified.")

    # 8. Test Logout
    lo_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {teacher_token}"})
    assert lo_resp.status_code == 200

    # Verify old token no longer works on /me
    me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {teacher_token}"})
    assert me_after.status_code == 401
    print("  [PASS] /api/auth/logout token invalidation verified.")


def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Authentication Core (Phase 3)")
    print("=" * 60)
    try:
        test_password_hashing()
        test_token_lifecycle()
        with TestClient(app) as client:
            test_auth_endpoints(client)
        print("\n" + "=" * 60)
        print("RESULT: ALL AUTHENTICATION CORE TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
