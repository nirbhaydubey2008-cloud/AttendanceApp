#!/usr/bin/env python3
"""
tests/test_face_recognition.py
Verification suite for Face Recognition, Biometric Enrollment, and Privacy Enforcement.
"""

import os
import sys
import shutil
import numpy as np
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.face_recognition import FaceRecognizer

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "test_student_db")

def create_synthetic_face(base_val: int = 140) -> np.ndarray:
    """Generates a structured synthetic face crop with eyebrows, eyes, and mouth."""
    img = np.ones((160, 160, 3), dtype=np.uint8) * base_val
    # Skin tone tint
    img[:, :, 0] = np.clip(base_val - 20, 0, 255)
    img[:, :, 1] = np.clip(base_val, 0, 255)
    img[:, :, 2] = np.clip(base_val + 20, 0, 255)
    # Eyes
    cv2.circle(img, (50, 65), 10, (30, 30, 30), -1)
    cv2.circle(img, (110, 65), 10, (30, 30, 30), -1)
    # Nose
    cv2.line(img, (80, 75), (80, 95), (60, 60, 60), 3)
    # Mouth
    cv2.line(img, (60, 115), (100, 115), (50, 50, 120), 4)
    return img

def setup_test_db():
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)
    os.makedirs(TEST_DB_PATH, exist_ok=True)

def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

def test_privacy_consent():
    print("Test 1: Privacy consent enforcement...")
    rec = FaceRecognizer(db_path=TEST_DB_PATH)
    face = create_synthetic_face(150)
    try:
        rec.enroll_student(
            student_id="STU_NO_CONSENT",
            name="Anonymous User",
            face_img=face,
            consent_given=False
        )
        assert False, "Should have raised PermissionError when consent is False"
    except PermissionError as e:
        print(f"  [PASS] Consent properly enforced: {e}")

def test_biometric_enrollment_and_matching():
    print("\nTest 2: Biometric enrollment & recognition matching...")
    rec = FaceRecognizer(db_path=TEST_DB_PATH)
    
    # Enroll Student 1: Nirbhay Dubey
    face1 = create_synthetic_face(145)
    enroll_res = rec.enroll_student(
        student_id="STU001",
        name="Nirbhay Dubey",
        roll_no="2024BCSE001",
        face_img=face1,
        consent_given=True
    )
    assert enroll_res["success"] is True
    assert os.path.exists(enroll_res["photo_path"])
    print(f"  [PASS] Successfully enrolled: {enroll_res['name']} ({enroll_res['student_id']})")

    # Match with slight noise added (simulating camera frame variance)
    noisy_face = face1.copy().astype(np.int16)
    noise = np.random.randint(-5, 5, noisy_face.shape)
    noisy_face = np.clip(noisy_face + noise, 0, 255).astype(np.uint8)

    match = rec.recognize_face(noisy_face)
    assert match is not None, "Recognition should match enrolled student"
    assert match["student_id"] == "STU001", f"Expected STU001, got {match['student_id']}"
    assert match["name"] == "Nirbhay Dubey", f"Expected Nirbhay Dubey, got {match['name']}"
    assert match["is_enrolled"] is True
    print(f"  [PASS] Positive recognition match: {match['name']} with confidence {match['confidence']:.2f}")

def test_unidentified_student_handling():
    print("\nTest 3: Unidentified person handling (zero false assumption)...")
    rec = FaceRecognizer(db_path=TEST_DB_PATH)
    
    # Completely different face (dark pattern)
    unknown_face = np.zeros((160, 160, 3), dtype=np.uint8)
    cv2.rectangle(unknown_face, (20, 20), (140, 140), (240, 240, 240), -1)
    
    match = rec.recognize_face(unknown_face)
    assert match is None, "Unenrolled face must not be matched to any enrolled student"
    print("  [PASS] Unenrolled face returned None (unidentified).")

def test_track_identity_caching():
    print("\nTest 4: Track identity caching...")
    rec = FaceRecognizer(db_path=TEST_DB_PATH)
    
    face1 = create_synthetic_face(145)
    # Track 1 -> Known student
    id1 = rec.get_track_identity("1", face1, frame_idx=0)
    assert id1["name"] == "Nirbhay Dubey"
    assert id1["is_enrolled"] is True
    
    # Track 2 -> Unknown student
    unknown_face = np.zeros((160, 160, 3), dtype=np.uint8)
    id2 = rec.get_track_identity("2", unknown_face, frame_idx=0)
    assert id2["name"] == "Student #2"
    assert id2["is_enrolled"] is False
    assert id2["student_id"] is None
    print(f"  [PASS] Track 1 identified as: {id1['name']}")
    print(f"  [PASS] Track 2 defaulted to:  {id2['name']}")

def test_database_persistence():
    print("\nTest 5: Database index persistence and reload...")
    rec2 = FaceRecognizer(db_path=TEST_DB_PATH)
    assert "STU001" in rec2.enrolled_students
    student = rec2.enrolled_students["STU001"]
    assert student["name"] == "Nirbhay Dubey"
    assert student["embedding"].shape == (128,)
    print(f"  [PASS] Reloaded database successfully: {len(rec2.enrolled_students)} enrolled student(s).")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 2.2 — Face Recognition & Enrollment")
    print("=" * 60)
    setup_test_db()
    try:
        test_privacy_consent()
        test_biometric_enrollment_and_matching()
        test_unidentified_student_handling()
        test_track_identity_caching()
        test_database_persistence()
        print("\n" + "=" * 60)
        print("RESULT: ALL FACE RECOGNITION & ENROLLMENT TESTS PASSED!")
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
        cleanup_test_db()

if __name__ == "__main__":
    sys.exit(main())
