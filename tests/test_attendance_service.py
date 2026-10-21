#!/usr/bin/env python3
"""
tests/test_attendance_service.py
Verification suite for Attendance Tracking, Verification Thresholds, and Reporting Service.
"""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.attendance_service import AttendanceService, AttendanceStatus

def test_session_lifecycle():
    print("Test 1: Attendance session lifecycle...")
    service = AttendanceService()
    
    start_info = service.start_session(session_id="TEST_001", title="AI Lecture", course_code="CS101")
    assert service.is_active is True
    assert start_info["session_id"] == "TEST_001"
    assert service.session_title == "AI Lecture"
    
    # End session
    report = service.end_session()
    assert service.is_active is False
    assert report["session_id"] == "TEST_001"
    assert report["total_students"] == 0
    print("  [PASS] Session start and end lifecycle verified.")

def test_presence_threshold_qualification():
    print("\nTest 2: Presence accumulation and threshold verification (PRESENT, PARTIAL, ABSENT)...")
    service = AttendanceService(present_threshold=0.75, partial_threshold=0.50)
    service.start_session(session_id="SESS_TEST_MULTI", title="Multimodal AI", course_code="CS101")
    
    # Override start time to simulate 100 seconds of session
    service.start_time = 1000.0
    
    # Frame sequence simulation (100 frames, 1 frame per second)
    for f in range(100):
        t = 1000.0 + f + 1
        observations = []
        
        # Student 1: Present in 90 out of 100 frames (90% -> PRESENT)
        if f < 90:
            observations.append({
                "track_id": "1",
                "student_id": "STU001",
                "student_name": "Nirbhay Dubey",
                "is_enrolled": True,
                "gaze_score": 0.92
            })
            
        # Student 2: Present in 60 out of 100 frames (60% -> PARTIAL)
        if f < 60:
            observations.append({
                "track_id": "2",
                "student_id": None,
                "student_name": "Student #2",
                "is_enrolled": False,
                "gaze_score": 0.65
            })
            
        # Student 3: Present in only 25 out of 100 frames (25% -> ABSENT)
        if f < 25:
            observations.append({
                "track_id": "3",
                "student_id": None,
                "student_name": "Student #3",
                "is_enrolled": False,
                "gaze_score": 0.40
            })

        service.update_frame(t, observations)

    # Freeze end time at 100s elapsed
    service.end_time = 1100.0
    report = service.end_session()
    
    records = {r["student_name"]: r for r in report["student_records"]}
    
    # Verify Student 1 (Nirbhay Dubey) -> PRESENT
    r1 = records["Nirbhay Dubey"]
    print(f"  Student 1 (Nirbhay Dubey): Presence={r1['presence_ratio']*100:.1f}%, Status={r1['status']}")
    assert r1["status"] == AttendanceStatus.PRESENT.value, f"Expected PRESENT, got {r1['status']}"
    assert r1["presence_ratio"] >= 0.75
    assert r1["is_enrolled"] is True
    
    # Verify Student 2 -> PARTIAL
    r2 = records["Student #2"]
    print(f"  Student 2 (Student #2)  : Presence={r2['presence_ratio']*100:.1f}%, Status={r2['status']}")
    assert r2["status"] == AttendanceStatus.PARTIAL.value, f"Expected PARTIAL, got {r2['status']}"
    assert 0.50 <= r2["presence_ratio"] < 0.75
    
    # Verify Student 3 -> ABSENT
    r3 = records["Student #3"]
    print(f"  Student 3 (Student #3)  : Presence={r3['presence_ratio']*100:.1f}%, Status={r3['status']}")
    assert r3["status"] == AttendanceStatus.ABSENT.value, f"Expected ABSENT, got {r3['status']}"
    assert r3["presence_ratio"] < 0.50

    # Verify overall report metrics
    assert report["total_students"] == 3
    assert report["present_count"] == 1
    assert report["partial_count"] == 1
    assert report["absent_count"] == 1
    assert abs(report["attendance_rate_pct"] - 33.3) < 1.0
    print(f"  [PASS] Overall Attendance Rate: {report['attendance_rate_pct']}% (1 Present, 1 Partial, 1 Absent)")

def test_dataframe_and_csv_export():
    print("\nTest 3: DataFrame and CSV export...")
    service = AttendanceService()
    service.start_session("CSV_TEST")
    service.records = {
        "STU001": {
            "student_id": "STU001",
            "student_name": "Nirbhay Dubey",
            "is_enrolled": True,
            "total_seconds_present": 85.0,
            "presence_ratio": 0.85,
            "mean_engagement": 0.91,
            "status": "PRESENT"
        }
    }
    
    df = service.export_to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Nirbhay Dubey"
    
    csv_path = os.path.join(PROJECT_ROOT, "test_media", "test_attendance_export.csv")
    service.export_to_csv(csv_path)
    assert os.path.exists(csv_path), "CSV file should be created"
    
    # Read back to verify
    df_read = pd.read_csv(csv_path)
    assert len(df_read) == 1
    assert df_read.iloc[0]["status"] == "PRESENT"
    print(f"  [PASS] CSV exported and verified at {csv_path}")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 4.3 — Attendance Tracking")
    print("=" * 60)
    try:
        test_session_lifecycle()
        test_presence_threshold_qualification()
        test_dataframe_and_csv_export()
        print("\n" + "=" * 60)
        print("RESULT: ALL ATTENDANCE TRACKING & VERIFICATION TESTS PASSED!")
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
