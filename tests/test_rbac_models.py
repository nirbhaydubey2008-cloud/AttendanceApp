#!/usr/bin/env python3
"""
tests/test_rbac_models.py
Verification suite for RBAC Database Models and CRUD operations:
Users, Teachers, Courses, Enrollments, Lectures, and AuditLogs.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import Base
import database.models as models
import database.crud as crud

TEST_DB_URL = "sqlite:///:memory:"

def test_user_and_teacher_creation(db_session):
    print("Test 1: User and Teacher profile creation...")
    # 1. Create Teacher User
    teacher_user = crud.create_user(
        db_session,
        username="prof_sharma",
        email="sharma@univ.edu",
        hashed_password="pbkdf2_hash_mock_123",
        role="TEACHER"
    )
    assert teacher_user.id is not None
    assert teacher_user.role == "TEACHER"
    assert teacher_user.is_active is True

    # 2. Create Teacher Profile
    teacher = crud.create_teacher(
        db_session,
        user_id=teacher_user.id,
        employee_id="EMP-1001",
        name="Dr. Sharma",
        department="Computer Science"
    )
    assert teacher.id is not None
    assert teacher.user.username == "prof_sharma"
    assert teacher.employee_id == "EMP-1001"
    print(f"  [PASS] Teacher created: {teacher}")


def test_course_and_enrollment(db_session):
    print("\nTest 2: Course creation and Student enrollment...")
    # 1. Create Teacher and Course
    t_user = crud.create_user(db_session, username="prof_smith", hashed_password="pw", role="TEACHER")
    teacher = crud.create_teacher(db_session, user_id=t_user.id, employee_id="EMP-2001", name="Prof. Smith")
    course = crud.create_course(db_session, course_code="CS101", title="Intro to CS", teacher_id=teacher.id)
    assert course.course_code == "CS101"

    # 2. Create Student User & Profile
    s_user = crud.create_user(db_session, username="john_doe", hashed_password="pw", role="STUDENT")
    student = crud.create_or_get_student(db_session, student_id="STU-2026-001", name="John Doe", user_id=s_user.id)
    assert student.user_id == s_user.id

    # 3. Enroll Student in Course
    enrollment = crud.enroll_student_in_course(db_session, student_id=student.id, course_id=course.id)
    assert enrollment.id is not None

    # Verify duplicate enrollment is safely handled
    enrollment_dup = crud.enroll_student_in_course(db_session, student_id=student.id, course_id=course.id)
    assert enrollment_dup.id == enrollment.id

    # Verify query
    courses = crud.get_enrolled_courses_for_student(db_session, student.id)
    assert len(courses) == 1
    assert courses[0].course_code == "CS101"

    students = crud.get_enrolled_students_for_course(db_session, course.id)
    assert len(students) == 1
    assert students[0].student_id == "STU-2026-001"
    print(f"  [PASS] Student {student.name} successfully enrolled in {course.course_code}")


def test_lecture_and_session_lifecycle(db_session):
    print("\nTest 3: Lecture lifecycle and Session binding...")
    # Setup Course and Teacher
    t_user = crud.create_user(db_session, username="prof_alan", hashed_password="pw", role="TEACHER")
    teacher = crud.create_teacher(db_session, user_id=t_user.id, employee_id="EMP-3001", name="Prof. Alan")
    course = crud.create_course(db_session, course_code="CS102", title="Data Structures", teacher_id=teacher.id)

    # 1. Create Lecture
    lecture = crud.create_lecture(
        db_session,
        lecture_id="LEC-CS102-01",
        course_id=course.id,
        teacher_id=teacher.id,
        title="Arrays & Pointers",
        topic="Memory layout and pointer arithmetic",
        planned_duration_min=60,
        status="SCHEDULED"
    )
    assert lecture.status == "SCHEDULED"

    # 2. Start Live Session bound to Lecture
    session = crud.create_session(
        db_session,
        session_id="SESS_TEST_LIVE_01",
        title=lecture.title,
        course_code=course.course_code,
        lecture_id=lecture.id,
        teacher_id=teacher.id,
        status="LIVE"
    )
    assert session.is_active is True
    assert session.lecture_id == lecture.id
    assert session.teacher_id == teacher.id

    # 3. Update Lecture to LIVE
    crud.update_lecture_status(db_session, lecture.lecture_id, "LIVE")
    assert crud.get_lecture_by_id(db_session, lecture.lecture_id).status == "LIVE"

    # 4. End Session and verify status transition to COMPLETED
    ended_session = crud.end_session(db_session, session.session_id)
    assert ended_session.is_active is False
    assert ended_session.status == "COMPLETED"

    # Verify lecture completed
    updated_lec = crud.get_lecture_by_id(db_session, lecture.lecture_id)
    assert updated_lec.status == "COMPLETED"
    print(f"  [PASS] Lecture lifecycle verified: SCHEDULED -> LIVE -> COMPLETED")


def test_audit_logs(db_session):
    print("\nTest 4: AuditLog recording...")
    user = crud.create_user(db_session, username="admin_actor", hashed_password="pw", role="TEACHER")
    log = crud.create_audit_log(
        db_session,
        user_id=user.id,
        action="ATTENDANCE_OVERRIDE",
        target_entity="AttendanceRecord:STU-2026-001",
        details="Changed status from ABSENT to PRESENT. Reason: Medical certificate verified."
    )
    assert log.id is not None
    assert log.action == "ATTENDANCE_OVERRIDE"

    logs = crud.get_audit_logs(db_session, limit=10)
    assert len(logs) == 1
    assert logs[0].target_entity == "AttendanceRecord:STU-2026-001"
    print(f"  [PASS] Audit log verified: {logs[0]}")


def main():
    print("=" * 60)
    print("VERIFICATION SUITE: RBAC Database Models & CRUD (Phase 2)")
    print("=" * 60)
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        test_user_and_teacher_creation(session)
        test_course_and_enrollment(session)
        test_lecture_and_session_lifecycle(session)
        test_audit_logs(session)
        print("\n" + "=" * 60)
        print("RESULT: ALL RBAC DATABASE MODEL TESTS PASSED!")
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
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())
