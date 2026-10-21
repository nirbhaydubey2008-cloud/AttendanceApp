#!/usr/bin/env python3
"""
tests/test_engagement_engine.py
Verification suite for Multimodal Engagement Scoring Engine.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.engagement_engine import EngagementEngine, EngagementTier

def test_attentive_student_scoring():
    print("Test 1: Attentive student composite score...")
    engine = EngagementEngine()
    
    obs = {
        "timestamp": 1.0,
        "track_id": "1",
        "student_id": "STU001",
        "student_name": "Nirbhay Dubey",
        "is_enrolled": True,
        "gaze_score": 0.92,
        "yaw": 2.5,
        "pitch": -1.0,
        "detection_confidence": 0.95,
        "audio_engagement_factor": 1.0
    }
    
    res = engine.update_student_engagement("1", obs)
    assert res["tier"] == EngagementTier.HIGH.value
    assert res["score"] >= 0.85, f"Expected score >= 0.85, got {res['score']}"
    assert res["gaze_subscore"] == 0.92
    print(f"  [PASS] Attentive Student: Score={res['score']} -> Tier={res['tier']}")

def test_distracted_student_scoring():
    print("\nTest 2: Distracted student composite score...")
    engine = EngagementEngine()
    
    obs = {
        "timestamp": 1.0,
        "track_id": "2",
        "student_name": "Student #2",
        "is_enrolled": False,
        "gaze_score": 0.35,
        "yaw": 30.0,
        "pitch": 12.0,
        "detection_confidence": 0.80,
        "audio_engagement_factor": 0.85
    }
    
    res = engine.update_student_engagement("2", obs)
    assert res["tier"] in [EngagementTier.MEDIUM.value, EngagementTier.LOW.value]
    assert 0.40 <= res["score"] <= 0.68, f"Expected medium score, got {res['score']}"
    print(f"  [PASS] Distracted Student: Score={res['score']} -> Tier={res['tier']}")

def test_low_engagement_and_disturbance():
    print("\nTest 3: Low engagement and acoustic disturbance...")
    engine = EngagementEngine()
    
    obs = {
        "timestamp": 1.0,
        "track_id": "3",
        "gaze_score": 0.10,
        "yaw": 45.0,
        "pitch": 25.0,
        "detection_confidence": 0.40,
        "audio_engagement_factor": 0.35  # Disturbance
    }
    
    res = engine.update_student_engagement("3", obs)
    assert res["tier"] == EngagementTier.LOW.value
    assert res["score"] < 0.40, f"Expected score < 0.40, got {res['score']}"
    print(f"  [PASS] Low Engagement Student: Score={res['score']} -> Tier={res['tier']}")

def test_temporal_smoothing():
    print("\nTest 4: Temporal EMA smoothing (anti-flicker)...")
    engine = EngagementEngine(smoothing_factor=0.75)
    
    # 5 frames of high engagement
    for t in range(5):
        obs_high = {
            "gaze_score": 0.95, "yaw": 0.0, "pitch": 0.0,
            "detection_confidence": 0.9, "audio_engagement_factor": 1.0
        }
        res = engine.update_student_engagement("1", obs_high)

    initial_score = res["score"]
    assert initial_score >= 0.90
    
    # 1 single momentary blink frame
    obs_blink = {
        "gaze_score": 0.40, "yaw": 0.0, "pitch": 0.0,
        "detection_confidence": 0.9, "audio_engagement_factor": 1.0
    }
    res_blink = engine.update_student_engagement("1", obs_blink)
    
    # Smoothed score should buffer the drop and remain in HIGH tier
    assert res_blink["score"] >= 0.70, f"Smoothed score dropped too sharply: {res_blink['score']}"
    assert res_blink["tier"] == EngagementTier.HIGH.value
    print(f"  [PASS] Anti-flicker verified: Instant={res_blink['instant_score']} -> Smoothed={res_blink['score']} (Remains HIGH)")

def test_classroom_aggregation():
    print("\nTest 5: Classroom-wide aggregation and alerts...")
    engine = EngagementEngine()
    
    # Student 1: High (Score ~0.98)
    engine.update_student_engagement("1", {"gaze_score": 0.95, "yaw": 0.0, "pitch": 0.0, "audio_engagement_factor": 1.0})
    # Student 2: Medium (Score ~0.64)
    engine.update_student_engagement("2", {"gaze_score": 0.40, "yaw": 25.0, "pitch": 10.0, "audio_engagement_factor": 0.85})
    # Student 3: Low (Score ~0.34)
    engine.update_student_engagement("3", {"gaze_score": 0.15, "yaw": 45.0, "pitch": 25.0, "audio_engagement_factor": 0.35})

    summary = engine.get_classroom_engagement_summary()
    assert summary["active_student_count"] == 3
    assert summary["tier_counts"]["HIGH"] == 1
    assert summary["tier_counts"]["MEDIUM"] == 1
    assert summary["tier_counts"]["LOW"] == 1
    assert 0.55 <= summary["average_engagement_score"] <= 0.70
    assert summary["disengaged_alert"] is False
    print(f"  [PASS] Classroom Summary: Active={summary['active_student_count']}, Avg={summary['average_engagement_score']}, Tiers={summary['tier_counts']}")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 4.2 — Engagement Scoring Engine")
    print("=" * 60)
    try:
        test_attentive_student_scoring()
        test_distracted_student_scoring()
        test_low_engagement_and_disturbance()
        test_temporal_smoothing()
        test_classroom_aggregation()
        print("\n" + "=" * 60)
        print("RESULT: ALL ENGAGEMENT SCORING ENGINE TESTS PASSED!")
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
