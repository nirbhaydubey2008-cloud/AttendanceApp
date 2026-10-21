#!/usr/bin/env python3
"""
tests/test_api_endpoints.py
Verification suite for FastAPI Backend REST Endpoints and WebSocket Telemetry.
"""

import os
import sys
import json
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.main import app

def test_health_endpoint(client: TestClient):
    print("Test 1: GET /health endpoint...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "healthy"
    assert "camera_active" in data
    print(f"  [PASS] /health response: {data['status']} (Camera active={data['camera_active']})")

def test_session_management_flow(client: TestClient):
    print("\nTest 2: Session management endpoints (start, current, stop)...")
    
    # 1. Start Session
    start_resp = client.post(
        "/api/sessions/start",
        json={"session_id": "TEST_API_SESS", "title": "Perception Lab", "course_code": "CS101"}
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["success"] is True
    assert start_data["session"]["session_id"] == "TEST_API_SESS"
    print(f"  [PASS] /api/sessions/start: {start_data['session']['session_id']}")

    # 2. Query Current Session
    cur_resp = client.get("/api/sessions/current")
    assert cur_resp.status_code == 200
    cur_data = cur_resp.json()
    assert cur_data["is_active"] is True
    assert cur_data["session_id"] == "TEST_API_SESS"
    print(f"  [PASS] /api/sessions/current: active={cur_data['is_active']}")

    # 3. Query Live Attendance & Engagement
    att_resp = client.get("/api/attendance/live")
    assert att_resp.status_code == 200
    assert "records" in att_resp.json()

    eng_resp = client.get("/api/engagement/summary")
    assert eng_resp.status_code == 200
    assert "average_engagement_score" in eng_resp.json()
    print("  [PASS] /api/attendance/live and /api/engagement/summary queried successfully.")

    # 4. Stop Session
    stop_resp = client.post("/api/sessions/stop")
    assert stop_resp.status_code == 200
    stop_data = stop_resp.json()
    assert stop_data["success"] is True
    assert stop_data["report"]["is_active"] is False
    print(f"  [PASS] /api/sessions/stop: session finalized successfully.")

def test_audio_chunk_ingestion(client: TestClient):
    print("\nTest 3: POST /api/audio/chunk ingestion...")
    payload = {
        "timestamp": 1.5,
        "rms": 0.022,
        "state": "SPEECH",
        "is_speech": True,
        "speech_confidence": 0.90,
        "is_disturbance": False,
        "snr_db": 15.2,
        "engagement_audio_factor": 0.85
    }
    resp = client.post("/api/audio/chunk", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    print("  [PASS] /api/audio/chunk ingested successfully.")

def test_websocket_telemetry(client: TestClient):
    print("\nTest 4: WS /ws/telemetry real-time streaming...")
    with client.websocket_connect("/ws/telemetry") as ws:
        msg = ws.receive_text()
        data = json.loads(msg)
        assert "timestamp" in data
        assert "classroom_engagement" in data
        assert "attendance" in data
        assert "audio_context" in data
        print(f"  [PASS] WebSocket message received successfully:")
        print(f"         - Audio Context: {data['audio_context']['audio_state']}")
        print(f"         - Classroom Engagement: {data['classroom_engagement']}")


def test_new_dashboard_endpoints(client: TestClient):
    print("\nTest 5: Multi-page Dashboard endpoints (sessions list, correction, system stats)...")
    # Start temporary session
    client.post("/api/sessions/start", json={"session_id": "DASH_TEST_SESS", "title": "Dashboard Test", "course_code": "CS999"})

    # 1. Test /api/sessions
    sess_resp = client.get("/api/sessions")
    assert sess_resp.status_code == 200
    assert sess_resp.json()["count"] >= 1
    print(f"  [PASS] /api/sessions: retrieved {sess_resp.json()['count']} session(s).")

    # 2. Test /api/system/stats
    stats_resp = client.get("/api/system/stats")
    assert stats_resp.status_code == 200
    assert "counts" in stats_resp.json()
    assert "database_size_kb" in stats_resp.json()
    print(f"  [PASS] /api/system/stats: DB size={stats_resp.json()['database_size_kb']} KB, Sessions={stats_resp.json()['counts']['sessions']}.")

    # 3. Test /api/attendance/correct
    corr_resp = client.post("/api/attendance/correct", json={
        "session_id": "DASH_TEST_SESS",
        "student_key": "track_1",
        "status": "PRESENT"
    })
    assert corr_resp.status_code == 200
    assert corr_resp.json()["success"] is True
    print(f"  [PASS] /api/attendance/correct: manual override status succeeded.")

    # 4. Test /api/sessions/{session_id}/attendance
    att_resp = client.get("/api/sessions/DASH_TEST_SESS/attendance")
    assert att_resp.status_code == 200
    print(f"  [PASS] /api/sessions/DASH_TEST_SESS/attendance: queried records successfully.")

    client.post("/api/sessions/stop")


def test_camera_toggle_endpoint(client: TestClient):
    print("\nTest 6: POST /api/camera/toggle endpoint...")
    # Disable camera
    res_off = client.post("/api/camera/toggle?enabled=false")
    assert res_off.status_code == 200
    assert res_off.json()["camera_active"] is False
    print("  [PASS] /api/camera/toggle?enabled=false: camera stopped successfully.")

    # Re-enable camera
    res_on = client.post("/api/camera/toggle?enabled=true")
    assert res_on.status_code == 200
    assert res_on.json()["camera_active"] is True
    print("  [PASS] /api/camera/toggle?enabled=true: camera re-started successfully.")


def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 5.2 — FastAPI Backend & WebSockets")
    print("=" * 60)
    with TestClient(app) as client:
        try:
            test_health_endpoint(client)
            # Authenticate as provisioned teacher for protected RBAC endpoints
            auth_resp = client.post("/api/auth/login", json={"identifier": "teacher", "password": "TeacherPassword123!"})
            assert auth_resp.status_code == 200, f"Teacher login failed: {auth_resp.text}"
            token = auth_resp.json()["token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
            print(f"  [PASS] Teacher authenticated for API verification suite.")

            test_session_management_flow(client)
            test_audio_chunk_ingestion(client)
            test_websocket_telemetry(client)
            test_new_dashboard_endpoints(client)
            test_camera_toggle_endpoint(client)
            print("\n" + "=" * 60)
            print("RESULT: ALL FASTAPI BACKEND & WEBSOCKET TESTS PASSED!")
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
