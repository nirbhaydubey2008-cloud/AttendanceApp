#!/usr/bin/env python3
"""
tests/test_multimodal_alignment.py
Verification suite for Multimodal Feature Alignment and Temporal Synchronization Service.
"""

import os
import sys
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.multimodal_fusion import TemporalSyncBuffer

def test_empty_buffer_fallback():
    print("Test 1: Empty audio buffer safe fallback...")
    buf = TemporalSyncBuffer(buffer_duration_sec=30.0)
    
    tracks = [{"track_id": "1", "bbox": [100, 100, 80, 80], "confidence": 0.9}]
    poses = [{
        "track_id": "1",
        "yaw": 2.5,
        "pitch": -1.0,
        "roll": 0.5,
        "ear": 0.25,
        "is_blinking": False,
        "gaze_score": 0.92,
        "is_looking_forward": True,
        "face_center": [140, 140]
    }]
    
    synced = buf.synchronize_frame(frame_timestamp=0.033, tracks=tracks, pose_estimates=poses)
    assert len(synced) == 1
    rec = synced[0]
    assert rec["track_id"] == "1"
    assert rec["audio_state"] == "QUIET"
    assert rec["audio_engagement_factor"] == 1.0
    print("  [PASS] Empty audio buffer handled safely with default ambient state.")

def test_temporal_alignment_logic():
    print("\nTest 2: Temporal alignment across asynchronous audio & video timestamps...")
    buf = TemporalSyncBuffer(buffer_duration_sec=30.0)
    
    # Ingest 3 distinct audio chunks
    buf.add_audio_chunk({
        "timestamp": 0.0,
        "duration_sec": 2.0,
        "state": "QUIET",
        "rms": 0.0038,
        "speech_confidence": 0.05,
        "is_speech": False,
        "is_disturbance": False,
        "engagement_audio_factor": 1.0
    })
    buf.add_audio_chunk({
        "timestamp": 2.0,
        "duration_sec": 4.0,
        "state": "SPEECH",
        "rms": 0.025,
        "speech_confidence": 0.95,
        "is_speech": True,
        "is_disturbance": False,
        "engagement_audio_factor": 0.85
    })
    buf.add_audio_chunk({
        "timestamp": 8.0,
        "duration_sec": 1.5,
        "state": "DISTURBANCE",
        "rms": 0.045,
        "speech_confidence": 0.1,
        "is_speech": False,
        "is_disturbance": True,
        "engagement_audio_factor": 0.35
    })

    # Test alignment at t = 1.0s (should be QUIET)
    c1 = buf.get_audio_context_at(1.0)
    assert c1["audio_state"] == "QUIET"
    assert c1["audio_is_speech"] is False
    print(f"  [PASS] t=1.0s matched audio state: {c1['audio_state']}")

    # Test alignment at t = 3.5s (should be SPEECH)
    c2 = buf.get_audio_context_at(3.5)
    assert c2["audio_state"] == "SPEECH"
    assert c2["audio_is_speech"] is True
    print(f"  [PASS] t=3.5s matched audio state: {c2['audio_state']} (Speech Conf={c2['audio_speech_conf']:.2f})")

    # Test alignment at t = 8.5s (should be DISTURBANCE)
    c3 = buf.get_audio_context_at(8.5)
    assert c3["audio_state"] == "DISTURBANCE"
    assert c3["audio_is_disturbance"] is True
    print(f"  [PASS] t=8.5s matched audio state: {c3['audio_state']}")

def test_multi_student_synchronization():
    print("\nTest 3: Multi-student tracking and identity synchronization...")
    buf = TemporalSyncBuffer()
    buf.add_audio_chunk({"timestamp": 0.0, "duration_sec": 5.0, "state": "SPEECH", "rms": 0.022})
    
    tracks = [
        {"track_id": "1", "bbox": [100, 150, 90, 90], "confidence": 0.95},
        {"track_id": "2", "bbox": [350, 150, 90, 90], "confidence": 0.88}
    ]
    poses = [
        {"track_id": "1", "yaw": 2.0, "pitch": 0.0, "gaze_score": 0.90, "is_looking_forward": True, "ear": 0.25, "is_blinking": False, "face_center": [145, 195]},
        {"track_id": "2", "yaw": 32.0, "pitch": 10.0, "gaze_score": 0.35, "is_looking_forward": False, "ear": 0.24, "is_blinking": False, "face_center": [395, 195]}
    ]
    identities = {
        "1": {"student_id": "STU001", "name": "Nirbhay Dubey", "is_enrolled": True},
        "2": {"student_id": None, "name": "Student #2", "is_enrolled": False}
    }

    synced = buf.synchronize_frame(2.5, tracks, poses, identities)
    assert len(synced) == 2
    
    s1 = next(s for s in synced if s["track_id"] == "1")
    s2 = next(s for s in synced if s["track_id"] == "2")
    
    assert s1["student_name"] == "Nirbhay Dubey"
    assert s1["is_enrolled"] is True
    assert s1["is_looking_forward"] is True
    assert s1["audio_state"] == "SPEECH"
    
    assert s2["student_name"] == "Student #2"
    assert s2["is_enrolled"] is False
    assert s2["is_looking_forward"] is False
    assert s2["audio_state"] == "SPEECH"
    print("  [PASS] Both students fused with visual pose, enrolled identity, and shared acoustic context.")

def test_rolling_window_summary():
    print("\nTest 4: Rolling window summary calculations...")
    buf = TemporalSyncBuffer()
    buf.add_audio_chunk({"timestamp": 0.0, "duration_sec": 10.0, "state": "QUIET", "rms": 0.004})
    
    # Simulate 30 frames over 1.5 seconds for Track 1
    for f in range(30):
        t_sec = f * 0.05
        tracks = [{"track_id": "1", "bbox": [100, 100, 80, 80]}]
        poses = [{"track_id": "1", "yaw": 3.0, "pitch": -2.0, "gaze_score": 0.85, "is_looking_forward": True, "is_blinking": (f == 10)}]
        buf.synchronize_frame(t_sec, tracks, poses)

    summary = buf.get_track_window_summary("1", window_sec=5.0)
    assert summary["sample_count"] == 30
    assert summary["forward_gaze_ratio"] == 1.0
    assert summary["blink_count"] == 1
    assert summary["dominant_audio_state"] == "QUIET"
    assert summary["presence_ratio"] > 0.0
    print(f"  [PASS] Rolling window summary: Samples={summary['sample_count']}, Forward Gaze={summary['forward_gaze_ratio']*100:.0f}%, Blinks={summary['blink_count']}")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 4.1 — Feature Alignment & Sync")
    print("=" * 60)
    try:
        test_empty_buffer_fallback()
        test_temporal_alignment_logic()
        test_multi_student_synchronization()
        test_rolling_window_summary()
        print("\n" + "=" * 60)
        print("RESULT: ALL MULTIMODAL FEATURE ALIGNMENT TESTS PASSED!")
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
