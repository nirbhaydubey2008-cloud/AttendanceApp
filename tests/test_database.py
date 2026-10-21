#!/usr/bin/env python3
"""
tests/test_database.py
Verification suite for SQLite Schema, SQLAlchemy ORM Models, and CRUD Operations.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import Base, init_db
from database.models import Student, Session as DbSession, AttendanceRecord, PersonMetric, Recommendation
import database.crud as crud

TEST_DB_URL = "sqlite:///:memory:"

def get_test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    init_db(target_engine=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestingSessionLocal()

def test_schema_creation():
    print("Test 1: Schema creation & table verification...")
    engine, db = get_test_db()
    
    table_names = engine.table_names() if hasattr(engine, "table_names") else list(Base.metadata.tables.keys())
    expected_tables = {"students", "sessions", "attendance_records", "person_metrics", "recommendations"}
    for t in expected_tables:
        assert t in table_names, f"Expected table '{t}' in database schema"
    print(f"  [PASS] All {len(expected_tables)} ORM tables created: {sorted(list(expected_tables))}")
    db.close()

def test_student_crud():
    print("\nTest 2: Student enrollment CRUD...")
    _, db = get_test_db()
    
    student = crud.create_or_get_student(
        db,
        student_id="STU001",
        name="Nirbhay Dubey",
        roll_no="2024BCSE001",
        photo_path="student_db/STU001.jpg",
        consent_given=True
    )
    assert student.id is not None
    assert student.student_id == "STU001"
    assert student.name == "Nirbhay Dubey"
    assert student.consent_given is True

    # Duplicate call should fetch existing without error
    same_student = crud.create_or_get_student(db, student_id="STU001", name="Nirbhay Dubey")
    assert same_student.id == student.id
    print(f"  [PASS] Student persisted and queried: {student}")
    db.close()

def test_session_lifecycle_crud():
    print("\nTest 3: Session lifecycle CRUD...")
    _, db = get_test_db()
    
    sess = crud.create_session(db, session_id="SESS_001", title="AI Lecture", course_code="CS101")
    assert sess.is_active is True
    assert sess.session_id == "SESS_001"
    assert sess.end_time is None

    # End session
    ended = crud.end_session(db, session_id="SESS_001")
    assert ended.is_active is False
    assert ended.end_time is not None
    assert ended.end_time >= ended.start_time
    print(f"  [PASS] Session lifecycle: Start={sess.start_time.isoformat()} -> End={ended.end_time.isoformat()}")
    db.close()

def test_attendance_and_metrics_crud():
    print("\nTest 4: AttendanceRecord and PersonMetric telemetry CRUD...")
    _, db = get_test_db()
    
    # Setup session & student
    crud.create_session(db, session_id="SESS_002", title="Machine Learning")
    crud.create_or_get_student(db, student_id="STU001", name="Nirbhay Dubey")

    # 1. Save Attendance Record
    att = crud.save_attendance_record(
        db,
        session_id="SESS_002",
        student_id="STU001",
        student_name="Nirbhay Dubey",
        track_id="1",
        time_present_sec=52.5,
        presence_ratio=0.875,
        status="PRESENT",
        mean_engagement=0.912
    )
    assert att.id is not None
    assert att.status == "PRESENT"

    # Query attendance
    records = crud.get_session_attendance(db, session_id="SESS_002")
    assert len(records) == 1
    assert records[0].student_name == "Nirbhay Dubey"
    print(f"  [PASS] Attendance record verified: {records[0]}")

    # 2. Save Person Metric Telemetry
    metric = crud.save_person_metric(
        db,
        session_id="SESS_002",
        student_id="STU001",
        track_id="1",
        timestamp=1.5,
        gaze_score=0.92,
        yaw=2.1,
        pitch=-1.0,
        roll=0.5,
        ear=0.25,
        is_blinking=False,
        is_looking_forward=True,
        audio_state="SPEECH",
        audio_rms=0.024,
        engagement_score=0.945,
        tier="HIGH"
    )
    assert metric.id is not None
    assert metric.tier == "HIGH"

    queried_metrics = crud.get_session_metrics(db, session_id="SESS_002")
    assert len(queried_metrics) == 1
    assert queried_metrics[0].engagement_score == 0.945
    print(f"  [PASS] PersonMetric telemetry verified: {queried_metrics[0]}")
    db.close()

def test_recommendation_crud():
    print("\nTest 5: Pedagogical Recommendation CRUD...")
    _, db = get_test_db()
    crud.create_session(db, session_id="SESS_003")

    rec = crud.save_recommendation(
        db,
        session_id="SESS_003",
        trigger_type="LOW_ENGAGEMENT",
        suggestion_text="Average engagement dropped below 50%. Consider an interactive check-in question.",
        priority="WARNING"
    )
    assert rec.id is not None
    assert rec.priority == "WARNING"

    recs = crud.get_session_recommendations(db, session_id="SESS_003")
    assert len(recs) == 1
    assert recs[0].trigger_type == "LOW_ENGAGEMENT"
    print(f"  [PASS] Recommendation verified: {recs[0]}")
    db.close()

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 5.1 — SQLite Schema & ORM Models")
    print("=" * 60)
    try:
        test_schema_creation()
        test_student_crud()
        test_session_lifecycle_crud()
        test_attendance_and_metrics_crud()
        test_recommendation_crud()
        print("\n" + "=" * 60)
        print("RESULT: ALL DATABASE SCHEMA & ORM TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] Assertion error: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
