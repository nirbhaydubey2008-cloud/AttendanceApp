#!/usr/bin/env python3
"""
tests/test_reasoning_engine.py
Verification suite for Rule-Based AI Reasoning and Pedagogical Recommendation Engine (Activity 5.3).
Tests rule logic, debounce cooldown mechanics, history limits, API endpoints, and SQLite persistence.
"""

import os
import sys
import time
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.reasoning_engine import RecommendationEngine, RecommendationPriority
from api.main import app, recommendation_engine


def test_rule_low_engagement():
    print("Test 1: Low engagement rule (Warning vs. Urgent)...")
    engine = RecommendationEngine(cooldown_seconds=30.0)

    # 1. Warning tier (0.35 <= engagement < 0.50)
    ctx_warning = {
        "timestamp": 1000.0,
        "average_engagement": 0.42,
        "active_student_count": 3
    }
    recs = engine.evaluate_rules(ctx_warning)
    assert len(recs) == 1, f"Expected 1 rec, got {len(recs)}"
    assert recs[0]["trigger_type"] == "LOW_ENGAGEMENT"
    assert recs[0]["priority"] == RecommendationPriority.WARNING.value
    print(f"  [PASS] Low engagement WARNING triggered: {recs[0]['title']} ({recs[0]['priority']})")

    # 2. Urgent tier (engagement < 0.35)
    engine.reset()
    ctx_urgent = {
        "timestamp": 1000.0,
        "average_engagement": 0.28,
        "active_student_count": 3
    }
    recs_urg = engine.evaluate_rules(ctx_urgent)
    assert len(recs_urg) == 1
    assert recs_urg[0]["priority"] == RecommendationPriority.URGENT.value
    print(f"  [PASS] Low engagement URGENT triggered: {recs_urg[0]['title']} ({recs_urg[0]['priority']})")


def test_debounce_cooldown():
    print("\nTest 2: Debounce cooldown mechanics...")
    engine = RecommendationEngine(cooldown_seconds=30.0)

    # First trigger at t=100.0
    ctx1 = {"timestamp": 100.0, "average_engagement": 0.40, "active_student_count": 2}
    r1 = engine.evaluate_rules(ctx1)
    assert len(r1) == 1

    # Immediate next trigger at t=105.0 (within 30s cooldown) -> should be suppressed
    ctx2 = {"timestamp": 105.0, "average_engagement": 0.38, "active_student_count": 2}
    r2 = engine.evaluate_rules(ctx2)
    assert len(r2) == 0, f"Expected 0 recs due to debounce cooldown, got {len(r2)}"
    print("  [PASS] Immediate re-trigger suppressed within cooldown period.")

    # Trigger at t=131.0 (after 30s cooldown) -> should trigger again
    ctx3 = {"timestamp": 131.0, "average_engagement": 0.39, "active_student_count": 2}
    r3 = engine.evaluate_rules(ctx3)
    assert len(r3) == 1
    assert r3[0]["trigger_type"] == "LOW_ENGAGEMENT"
    print("  [PASS] Re-trigger succeeded after cooldown expiration.")


def test_acoustic_disturbance_rule():
    print("\nTest 3: Acoustic disturbance rule...")
    engine = RecommendationEngine(cooldown_seconds=20.0)

    ctx = {
        "timestamp": 200.0,
        "audio_state": "DISTURBANCE",
        "audio_db": -18.5
    }
    recs = engine.evaluate_rules(ctx)
    assert len(recs) == 1
    assert recs[0]["trigger_type"] == "ACOUSTIC_DISTURBANCE"
    assert recs[0]["priority"] == RecommendationPriority.WARNING.value
    print(f"  [PASS] Disturbance rule triggered: {recs[0]['title']}")


def test_gaze_aversion_rule():
    print("\nTest 4: Gaze aversion / slide disconnect rule...")
    engine = RecommendationEngine(cooldown_seconds=20.0)

    ctx = {
        "timestamp": 300.0,
        "active_student_count": 4,
        "forward_gaze_ratio": 0.30
    }
    recs = engine.evaluate_rules(ctx)
    assert len(recs) == 1
    assert recs[0]["trigger_type"] == "GAZE_AVERSION"
    assert recs[0]["priority"] == RecommendationPriority.INFO.value
    print(f"  [PASS] Gaze aversion triggered: {recs[0]['title']}")


def test_high_engagement_and_attendance_rules():
    print("\nTest 5: High engagement praise & low attendance rules...")
    engine = RecommendationEngine(cooldown_seconds=20.0)

    # High engagement
    ctx_high = {
        "timestamp": 400.0,
        "active_student_count": 5,
        "average_engagement": 0.88
    }
    recs_high = engine.evaluate_rules(ctx_high)
    assert len(recs_high) == 1
    assert recs_high[0]["trigger_type"] == "HIGH_ENGAGEMENT"
    print(f"  [PASS] High engagement praise: {recs_high[0]['title']}")

    # Low attendance alert
    ctx_att = {
        "timestamp": 500.0,
        "session_elapsed_sec": 150.0,
        "attendance_rate_pct": 45.0
    }
    recs_att = engine.evaluate_rules(ctx_att)
    assert len(recs_att) == 1
    assert recs_att[0]["trigger_type"] == "LOW_ATTENDANCE"
    print(f"  [PASS] Low attendance alert: {recs_att[0]['title']}")


def test_recommendation_history_retention():
    print("\nTest 6: Recommendation history ring-buffer cap (100 items)...")
    engine = RecommendationEngine(cooldown_seconds=0.0)  # zero cooldown for stress test

    for i in range(120):
        engine.evaluate_rules({
            "timestamp": float(i),
            "audio_state": "DISTURBANCE",
            "audio_db": -20.0
        })

    assert len(engine.recommendations_history) == 100, f"Expected 100, got {len(engine.recommendations_history)}"
    recent = engine.get_recent_recommendations(limit=5)
    assert len(recent) == 5
    # Should be sorted newest first
    assert recent[0]["timestamp"] > recent[-1]["timestamp"]
    print("  [PASS] History capped at exactly 100 entries, newest retrieved first.")


def test_api_recommendation_endpoints(client: TestClient):
    print("\nTest 7: Recommendation REST endpoints & DB persistence...")
    recommendation_engine.reset()

    # 1. Start session to enable DB persistence
    client.post("/api/sessions/start", json={"session_id": "RECS_TEST_SESS", "title": "Pedagogy Test"})

    # 2. Evaluate recommendations via POST /api/recommendations/evaluate
    eval_resp = client.post(
        "/api/recommendations/evaluate",
        json={
            "timestamp": time.time(),
            "average_engagement": 0.32,
            "active_student_count": 3,
            "audio_state": "QUIET"
        }
    )
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert data["triggered_count"] >= 1
    assert data["new_recommendations"][0]["trigger_type"] == "LOW_ENGAGEMENT"
    print(f"  [PASS] POST /api/recommendations/evaluate triggered {data['triggered_count']} recommendations.")

    # 3. Query GET /api/recommendations/recent
    rec_resp = client.get("/api/recommendations/recent?limit=5")
    assert rec_resp.status_code == 200
    recs_data = rec_resp.json()
    assert recs_data["count"] >= 1
    print(f"  [PASS] GET /api/recommendations/recent returned {len(recs_data['recommendations'])} entries.")

    # 4. Verify SQLite DB persistence via GET /api/sessions/RECS_TEST_SESS/recommendations
    db_resp = client.get("/api/sessions/RECS_TEST_SESS/recommendations")
    assert db_resp.status_code == 200
    db_data = db_resp.json()
    assert db_data["count"] >= 1
    print(f"  [PASS] DB persistence verified: {db_data['count']} recommendation(s) committed to SQLite.")

    # 5. Stop session
    client.post("/api/sessions/stop")


def main():
    print("=" * 65)
    print("VERIFICATION SUITE: Activity 5.3 — Reasoning & Recommendation Engine")
    print("=" * 65)
    try:
        test_rule_low_engagement()
        test_debounce_cooldown()
        test_acoustic_disturbance_rule()
        test_gaze_aversion_rule()
        test_high_engagement_and_attendance_rules()
        test_recommendation_history_retention()

        with TestClient(app) as client:
            auth_resp = client.post("/api/auth/login", json={"identifier": "teacher", "password": "TeacherPassword123!"})
            assert auth_resp.status_code == 200, f"Teacher login failed: {auth_resp.text}"
            token = auth_resp.json()["token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
            test_api_recommendation_endpoints(client)

        print("\n" + "=" * 65)
        print("RESULT: ALL REASONING & RECOMMENDATION ENGINE TESTS PASSED!")
        print("=" * 65)
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
