#!/usr/bin/env python3
"""
tests/test_face_detection.py
Verification suite for Face Detection and DeepSort Tracking Service.
"""

import os
import sys
import cv2
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.face_detection import FaceDetector, FaceTracker, FaceDetectionService, extract_appearance_embedding
from services.camera_service import CameraService

def test_extract_appearance_embedding():
    print("Test 1: Appearance embedding extraction...")
    dummy_crop = np.random.randint(0, 255, (80, 80, 3), dtype=np.uint8)
    feat = extract_appearance_embedding(dummy_crop, dim=128)
    assert isinstance(feat, np.ndarray), "Feature must be a numpy array"
    assert feat.shape == (128,), f"Feature shape must be (128,), got {feat.shape}"
    norm = np.linalg.norm(feat)
    assert abs(norm - 1.0) < 1e-4, f"Feature must be L2 normalized (norm={norm})"
    print("  [PASS] Appearance embedding unit check.")

def test_face_detector_initialization():
    print("Test 2: FaceDetector initialization and single frame detection...")
    detector = FaceDetector(scale_factor=1.05, min_neighbors=2)
    assert detector.cascade is not None, "Cascade must not be None"
    
    # Test on a blank frame (should produce 0 detections safely)
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    dets = detector.detect_faces(blank)
    assert isinstance(dets, list), "Detections must be a list"
    assert len(dets) == 0, "Blank frame should have 0 detections"
    print("  [PASS] FaceDetector initialization & blank frame handling.")

def test_detection_and_tracking_pipeline():
    print("Test 3: Detection & DeepSort Tracking on synthetic classroom video...")
    video_path = os.path.join(PROJECT_ROOT, "test_media", "test_classroom.mp4")
    assert os.path.exists(video_path), f"Test video missing: {video_path}"

    cap = cv2.VideoCapture(video_path)
    assert cap.isOpened(), "Could not open test video"
    
    service = FaceDetectionService(scale_factor=1.05, min_neighbors=2, max_age=30, n_init=2)
    
    frame_count = 0
    total_detections = 0
    confirmed_tracks_seen = set()
    track_lifespans = {}
    
    max_test_frames = 50
    while frame_count < max_test_frames:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        
        frame_count += 1
        annotated_frame, tracks = service.process_frame(frame)
        
        # Validate output shapes and types
        assert annotated_frame.shape == frame.shape, "Annotated frame shape mismatch"
        assert isinstance(tracks, list), "Tracks must be returned as a list"
        
        total_detections += len(tracks)
        
        for t in tracks:
            tid = t["track_id"]
            x, y, w, h = t["bbox"]
            conf = t["confidence"]
            
            # Assert coordinates inside image bounds
            assert 0 <= x < frame.shape[1], f"Track {tid} x out of bounds: {x}"
            assert 0 <= y < frame.shape[0], f"Track {tid} y out of bounds: {y}"
            assert w > 0 and h > 0, f"Track {tid} invalid dimensions: {w}x{h}"
            assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"
            
            confirmed_tracks_seen.add(tid)
            track_lifespans[tid] = track_lifespans.get(tid, 0) + 1

    cap.release()

    print(f"  Processed {frame_count} frames.")
    print(f"  Total track observations: {total_detections}")
    print(f"  Unique confirmed tracks established: {len(confirmed_tracks_seen)} -> IDs: {sorted(list(confirmed_tracks_seen))}")
    for tid, span in track_lifespans.items():
        print(f"    - Track ID {tid}: active across {span} frames ({span / frame_count * 100:.1f}% persistence)")

    assert len(confirmed_tracks_seen) >= 1, "At least one persistent track must be established"
    max_lifespan = max(track_lifespans.values()) if track_lifespans else 0
    assert max_lifespan >= 10, f"Max track lifespan ({max_lifespan}) must be >= 10 frames for persistence"
    print("  [PASS] Detection & Tracking persistence assertions passed.")

def test_camera_service_integration():
    print("Test 4: CameraService integration with FaceDetectionService...")
    cam = CameraService(camera_id=999)  # Force synthetic video fallback
    assert cam.start() == True, "CameraService failed to start"
    
    service = FaceDetectionService()
    frames_tested = 0
    for _ in range(10):
        ret, frame = cam.get_frame()
        if not ret or frame is None:
            continue
        annotated, tracks = service.process_frame(frame)
        assert annotated is not None
        frames_tested += 1

    cam.stop()
    assert frames_tested == 10, f"Expected 10 frames tested, got {frames_tested}"
    print(f"  [PASS] CameraService integration verified across {frames_tested} frames.")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 2.1 — Face Detection & Tracking")
    print("=" * 60)
    try:
        test_extract_appearance_embedding()
        test_face_detector_initialization()
        test_detection_and_tracking_pipeline()
        test_camera_service_integration()
        print("\n" + "=" * 60)
        print("RESULT: ALL FACE DETECTION & TRACKING TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] Assertion error: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
