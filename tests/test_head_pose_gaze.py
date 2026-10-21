#!/usr/bin/env python3
"""
tests/test_head_pose_gaze.py
Verification suite for 3D Head Pose and Eye Gaze Estimation Service.
"""

import os
import sys
import cv2
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.head_pose_gaze import HeadPoseGazeEstimator

def test_estimator_initialization():
    print("Test 1: Estimator initialization...")
    estimator = HeadPoseGazeEstimator()
    assert estimator is not None
    assert estimator.mp_detector is not None, "MediaPipe detector should be initialized with model asset"
    print("  [PASS] HeadPoseGazeEstimator initialized with MediaPipe engine.")

def test_bbox_geometric_fallback():
    print("\nTest 2: Bounding-box solvePnP geometry estimation...")
    estimator = HeadPoseGazeEstimator()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Frontal centered face
    frontal_bbox = [260, 180, 120, 120]
    res_front = estimator.estimate_from_bbox(frame, frontal_bbox)
    
    assert "yaw" in res_front and "pitch" in res_front and "roll" in res_front
    assert abs(res_front["yaw"]) <= 10.0, f"Frontal face yaw should be near 0 deg, got {res_front['yaw']}"
    assert res_front["gaze_score"] >= 0.70, f"Frontal face gaze score should be high, got {res_front['gaze_score']}"
    assert res_front["is_looking_forward"] is True
    print(f"  [PASS] Frontal pose: Yaw={res_front['yaw']:.1f}°, Gaze Score={res_front['gaze_score']:.2f}")

def test_video_pose_and_gaze_processing():
    print("\nTest 3: Pose & Gaze estimation on test_classroom.mp4...")
    video_path = os.path.join(PROJECT_ROOT, "test_media", "test_classroom.mp4")
    assert os.path.exists(video_path), f"Video missing: {video_path}"

    cap = cv2.VideoCapture(video_path)
    estimator = HeadPoseGazeEstimator()
    
    estimates_found = 0
    yaws = []
    gaze_scores = []
    
    # Process first 25 frames
    for f_idx in range(25):
        ret, frame = cap.read()
        if not ret: break
        
        results = estimator.process_frame(frame)
        if results:
            estimates_found += len(results)
            for r in results:
                yaws.append(r["yaw"])
                gaze_scores.append(r["gaze_score"])
                assert -90.0 <= r["yaw"] <= 90.0, f"Yaw angle out of bounds: {r['yaw']}"
                assert -90.0 <= r["pitch"] <= 90.0, f"Pitch angle out of bounds: {r['pitch']}"
                assert 0.0 <= r["gaze_score"] <= 1.0, f"Gaze score out of range: {r['gaze_score']}"
    
    cap.release()
    assert estimates_found > 0, "Should have detected and estimated poses from test video"
    avg_yaw = float(np.mean(np.abs(yaws)))
    avg_gaze = float(np.mean(gaze_scores))
    print(f"  [PASS] Processed {estimates_found} face pose estimations.")
    print(f"         - Mean absolute yaw: {avg_yaw:.2f}°")
    print(f"         - Mean gaze attentiveness: {avg_gaze:.2f}")

def test_frame_annotation():
    print("\nTest 4: Pose and gaze visual annotation...")
    estimator = HeadPoseGazeEstimator()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    estimates = [{
        "yaw": 5.0,
        "pitch": -2.0,
        "gaze_score": 0.88,
        "is_looking_forward": True,
        "nose_pt": [320, 240]
    }]
    annotated = estimator.annotate_pose_and_gaze(frame.copy(), estimates)
    assert annotated.shape == frame.shape
    # Ensure drawing modified pixels
    assert np.any(annotated > 0), "Annotated frame should contain rendered pixels"
    print("  [PASS] Frame annotation verified.")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 2.3 — Head Pose & Gaze Estimation")
    print("=" * 60)
    try:
        test_estimator_initialization()
        test_bbox_geometric_fallback()
        test_video_pose_and_gaze_processing()
        test_frame_annotation()
        print("\n" + "=" * 60)
        print("RESULT: ALL HEAD POSE & GAZE ESTIMATION TESTS PASSED!")
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
