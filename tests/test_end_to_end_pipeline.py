#!/usr/bin/env python3
"""
tests/test_end_to_end_pipeline.py
Activity 6.2 — Full Pipeline End-to-End System Verification.
Validates the entire perception pipeline from frame & audio ingestion to
multimodal fusion, attendance verification, rule-based reasoning,
SQLite persistence, and WebSocket telemetry streaming.
"""

import os
import sys
import time
import json
import numpy as np
import cv2
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.main import (
    app,
    camera_service,
    face_service,
    recognizer,
    pose_estimator,
    sync_buffer,
    engagement_engine,
    attendance_service,
    recommendation_engine
)
from database.database import SessionLocal
import database.crud as crud


def create_synthetic_face_image() -> np.ndarray:
    """Creates a synthetic 300x300 image containing a simple detectable face-like pattern."""
    img = np.full((300, 300, 3), 220, dtype=np.uint8)
    # Head contour
    cv2.circle(img, (150, 150), 90, (180, 180, 180), -1)
    # Eyes
    cv2.circle(img, (120, 130), 12, (50, 50, 50), -1)
    cv2.circle(img, (180, 130), 12, (50, 50, 50), -1)
    # Nose
    cv2.line(img, (150, 135), (150, 165), (70, 70, 70), 3)
    # Mouth
    cv2.ellipse(img, (150, 185), (35, 15), 0, 0, 180, (50, 50, 50), 3)
    return img


def run_e2e_verification():
    print("=" * 70)
    print("ACTIVITY 6.2: END-TO-END PIPELINE SYSTEM INTEGRATION VERIFICATION")
    print("=" * 70)

    with TestClient(app) as client:
        # -------------------------------------------------------------
        # STEP 1: Health & Hardware Check
        # -------------------------------------------------------------
        print("\n[Step 1/11] Checking system health & capabilities...")
        resp = client.get("/health")
        assert resp.status_code == 200
        health = resp.json()
        assert health["status"] == "healthy"
        print(f"  ✓ System Status: {health['status']}")
        print(f"  ✓ Camera Active: {health['camera_active']} (Fallback: {health['camera_fallback']})")

        # Authenticate as teacher for subsequent RBAC-protected stages
        auth_resp = client.post("/api/auth/login", json={"identifier": "teacher", "password": "TeacherPassword123!"})
        assert auth_resp.status_code == 200, f"Teacher authentication failed: {auth_resp.text}"
        token = auth_resp.json()["token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        print(f"  ✓ Authenticated as Teacher for end-to-end pipeline verification.")

        # -------------------------------------------------------------
        # STEP 2: Biometric Student Enrollment with Privacy Consent
        # -------------------------------------------------------------
        print("\n[Step 2/11] Enrolling student biometrics with consent...")
        face_img = create_synthetic_face_image()
        _, img_encoded = cv2.imencode(".jpg", face_img)
        img_bytes = img_encoded.tobytes()

        # Consent enforcement test: should fail if consent=False
        fail_resp = client.post(
            "/api/students/enroll",
            data={"student_id": "STU_E2E_01", "name": "Charlie Brown", "roll_no": "2026-E2E-01", "consent_given": "false"},
            files={"photo": ("face.jpg", img_bytes, "image/jpeg")}
        )
        assert fail_resp.status_code == 400
        print("  ✓ Consent enforcement verified: Enrollment rejected when consent is absent.")

        # Valid enrollment with consent=True
        enroll_resp = client.post(
            "/api/students/enroll",
            data={"student_id": "STU_E2E_01", "name": "Charlie Brown", "roll_no": "2026-E2E-01", "consent_given": "true"},
            files={"photo": ("face.jpg", img_bytes, "image/jpeg")}
        )
        assert enroll_resp.status_code == 200
        enroll_data = enroll_resp.json()
        assert enroll_data["success"] is True
        print(f"  ✓ Student enrolled successfully: {enroll_data['student']['student_id']} ({enroll_data['student']['name']})")

        # Query enrolled list
        list_resp = client.get("/api/students")
        assert list_resp.status_code == 200
        assert list_resp.json()["count"] >= 1
        print(f"  ✓ Enrolled student directory contains {list_resp.json()['count']} student(s).")

        # -------------------------------------------------------------
        # STEP 3: Start Classroom Lecture Session
        # -------------------------------------------------------------
        session_id = f"E2E_SESSION_{int(time.time())}"
        print(f"\n[Step 3/11] Starting lecture session: {session_id}...")
        start_resp = client.post(
            "/api/sessions/start",
            json={
                "session_id": session_id,
                "title": "Advanced Multimodal Perception",
                "course_code": "CSE401"
            }
        )
        assert start_resp.status_code == 200
        assert start_resp.json()["success"] is True
        print(f"  ✓ Session successfully started: {session_id}")

        # Verify session is marked active
        cur_resp = client.get("/api/sessions/current")
        assert cur_resp.status_code == 200
        assert cur_resp.json()["is_active"] is True
        assert cur_resp.json()["session_id"] == session_id
        print("  ✓ Current session verified as active.")

        # -------------------------------------------------------------
        # STEP 4: Acoustic Feature Ingestion
        # -------------------------------------------------------------
        print("\n[Step 4/11] Ingesting acoustic stream chunks...")
        audio_chunks = [
            {"timestamp": 1.0, "rms": 0.015, "state": "QUIET", "is_speech": False, "speech_confidence": 0.1, "is_disturbance": False, "snr_db": 5.0, "engagement_audio_factor": 1.0},
            {"timestamp": 2.0, "rms": 0.045, "state": "SPEECH", "is_speech": True, "speech_confidence": 0.92, "is_disturbance": False, "snr_db": 18.0, "engagement_audio_factor": 0.85},
            {"timestamp": 3.0, "rms": 0.120, "state": "DISTURBANCE", "is_speech": False, "speech_confidence": 0.2, "is_disturbance": True, "snr_db": 25.0, "engagement_audio_factor": 0.50}
        ]
        for c in audio_chunks:
            ac_resp = client.post("/api/audio/chunk", json=c)
            assert ac_resp.status_code == 200
        print(f"  ✓ Ingested {len(audio_chunks)} audio chunks across QUIET, SPEECH, and DISTURBANCE states.")

        # -------------------------------------------------------------
        # STEP 5: Multimodal Video Perception & Engagement Fusion
        # -------------------------------------------------------------
        print("\n[Step 5/11] Executing video perception, head pose, gaze & engagement fusion...")
        # Simulate 15 frames of observations for tracking & attendance
        for i in range(15):
            t_stamp = float(i) * 0.2
            mock_observations = [
                {
                    "track_id": "1",
                    "student_id": "STU_E2E_01",
                    "student_name": "Charlie Brown",
                    "timestamp": t_stamp,
                    "confidence": 0.95,
                    "bbox": (50, 50, 150, 150),
                    "gaze_score": 0.85,
                    "pitch": -2.0,
                    "yaw": 1.5,
                    "roll": 0.0,
                    "ear": 0.28,
                    "is_blinking": False,
                    "is_looking_forward": True
                },
                {
                    "track_id": "2",
                    "student_id": None,
                    "student_name": "Student_2",
                    "timestamp": t_stamp,
                    "confidence": 0.88,
                    "bbox": (200, 50, 150, 150),
                    "gaze_score": 0.35,
                    "pitch": 25.0,
                    "yaw": 30.0,
                    "roll": 5.0,
                    "ear": 0.15,
                    "is_blinking": True,
                    "is_looking_forward": False
                }
            ]
            # Update engagement engine
            for obs in mock_observations:
                eng = engagement_engine.update_student_engagement(obs["track_id"], obs)
                obs["smoothed_engagement"] = eng["score"]
                obs["engagement_tier"] = eng["tier"]

            # Update attendance tracking
            attendance_service.update_frame(t_stamp, mock_observations)

        print("  ✓ Simulated 15 multimodal perception frames with engagement updates.")

        # -------------------------------------------------------------
        # STEP 6: Real-Time Attendance Roster Verification
        # -------------------------------------------------------------
        print("\n[Step 6/11] Querying real-time attendance table...")
        att_resp = client.get("/api/attendance/live")
        assert att_resp.status_code == 200
        records = att_resp.json()["records"]
        assert len(records) >= 2
        print(f"  ✓ Verified {len(records)} active student tracks in attendance roster:")
        for r in records:
            print(f"     - Track {r['student_key']} ({r['student_name']}): Status={r['status']}, Ratio={round(r['presence_ratio']*100, 1)}%, Engagement={round(r['mean_engagement']*100, 1)}%")

        # -------------------------------------------------------------
        # STEP 7: Engagement Summary & Disengagement Alerts
        # -------------------------------------------------------------
        print("\n[Step 7/11] Querying classroom engagement analytics...")
        eng_resp = client.get("/api/engagement/summary")
        assert eng_resp.status_code == 200
        summary = eng_resp.json()
        assert summary["active_student_count"] >= 2
        assert "tier_counts" in summary
        print(f"  ✓ Engagement summary: Active={summary['active_student_count']}, Average={round(summary['average_engagement_score']*100, 1)}%")
        print(f"  ✓ Tier counts: {summary['tier_counts']}")

        # -------------------------------------------------------------
        # STEP 8: Rule-Based Pedagogical Reasoning & Cooldowns
        # -------------------------------------------------------------
        print("\n[Step 8/11] Triggering pedagogical reasoning evaluation...")
        recommendation_engine.reset()
        eval_resp = client.post(
            "/api/recommendations/evaluate",
            json={
                "timestamp": time.time(),
                "average_engagement": 0.40,
                "active_student_count": 2,
                "forward_gaze_ratio": 0.35,
                "audio_state": "DISTURBANCE",
                "audio_db": -16.0
            }
        )
        assert eval_resp.status_code == 200
        rec_data = eval_resp.json()
        assert rec_data["triggered_count"] >= 1
        print(f"  ✓ Evaluated rules: {rec_data['triggered_count']} recommendation(s) triggered:")
        for r in rec_data["new_recommendations"]:
            print(f"     - [{r['priority']}] {r['title']}: {r['suggestion_text'][:60]}...")

        # Verify DB persistence of recommendations
        db_recs = client.get(f"/api/sessions/{session_id}/recommendations")
        assert db_recs.status_code == 200
        assert db_recs.json()["count"] >= 1
        print(f"  ✓ Stored recommendations verified in SQLite: {db_recs.json()['count']} record(s).")

        # -------------------------------------------------------------
        # STEP 9: WebSocket Telemetry Streaming Validation
        # -------------------------------------------------------------
        print("\n[Step 9/11] Validating WebSocket telemetry stream (/ws/telemetry)...")
        with client.websocket_connect("/ws/telemetry") as ws:
            packet = json.loads(ws.receive_text())
            assert "timestamp" in packet
            assert packet["session_id"] == session_id
            assert packet["is_active"] is True
            assert "classroom_engagement" in packet
            assert "audio_context" in packet
            assert "attendance" in packet
            assert "recent_recommendations" in packet
            print("  ✓ WebSocket telemetry packet verified:")
            print(f"     - Active Session: {packet['session_id']}")
            print(f"     - Audio State: {packet['audio_context']['audio_state']}")
            print(f"     - Attendance count: {len(packet['attendance'])}")
            print(f"     - Recent recs count: {len(packet['recent_recommendations'])}")

        # -------------------------------------------------------------
        # STEP 10: Finalize Session & Export CSV
        # -------------------------------------------------------------
        print("\n[Step 10/11] Finalizing session and testing CSV export...")
        stop_resp = client.post("/api/sessions/stop")
        assert stop_resp.status_code == 200
        report = stop_resp.json()["report"]
        assert report["is_active"] is False
        total_st = report.get("total_students", len(report.get("student_records", [])))
        print(f"  ✓ Session finalized: {total_st} students recorded.")

        # Test CSV export endpoint
        csv_resp = client.get("/api/attendance/export")
        assert csv_resp.status_code == 200
        assert len(csv_resp.content) > 0
        print(f"  ✓ Attendance CSV exported successfully ({len(csv_resp.content)} bytes).")

        # -------------------------------------------------------------
        # STEP 11: SQLite Database Verification
        # -------------------------------------------------------------
        print("\n[Step 11/11] Verifying SQLite database persistence...")
        with SessionLocal() as db:
            db_sess = db.query(crud.DbSession).filter(crud.DbSession.session_id == session_id).first()
            assert db_sess is not None
            assert db_sess.is_active is False
            print(f"  ✓ SQLite Session verified: {db_sess.session_id} (Active={db_sess.is_active})")

            att_records = crud.get_session_attendance(db, session_id=session_id)
            assert len(att_records) >= 1
            print(f"  ✓ SQLite Attendance records: {len(att_records)} student record(s) persisted.")

            persisted_recs = crud.get_session_recommendations(db, session_id=session_id)
            assert len(persisted_recs) >= 1
            print(f"  ✓ SQLite Recommendations: {len(persisted_recs)} recommendation(s) persisted.")

    print("\n" + "=" * 70)
    print("RESULT: ALL 11 END-TO-END PIPELINE CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_e2e_verification())
    except AssertionError as e:
        print(f"\n[FAIL] Assertion error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
