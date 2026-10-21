"""
tests/run_all_tests.py
Master Test Suite Runner for Multimodal Attendance & Engagement Agent.
Executes all unit, integration, RBAC, perception, and pipeline test suites,
reporting detailed diagnostics, runtime, and an overall verification scorecard.
"""

import os
import sys
import time
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_BIN = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
if not os.path.exists(PYTHON_BIN):
    PYTHON_BIN = sys.executable

TEST_SUITES = [
    # 1. RBAC & Security Suites (Phases 2 - 8)
    ("Authentication Core (Phase 3)", "tests/test_auth.py"),
    ("RBAC Models & CRUD (Phase 2)", "tests/test_rbac_models.py"),
    ("RBAC Authorization & Anti-IDOR (Phase 4)", "tests/test_rbac_authorization.py"),
    ("Student Enrollment & Provisioning (Phase 5)", "tests/test_student_enrollment_provisioning.py"),
    ("Student Dashboard Contracts (Phase 7)", "tests/test_student_dashboard.py"),
    ("Session Lifecycle & Sync (Phase 8)", "tests/test_session_lifecycle_sync.py"),

    # 2. Perception & Computer Vision Pipelines
    ("Face Detection (MediaPipe)", "tests/test_face_detection.py"),
    ("Face Recognition (Facenet 512-d)", "tests/test_face_recognition.py"),
    ("Head Pose & Gaze (MediaPipe Landmarker)", "tests/test_head_pose_gaze.py"),

    # 3. Audio & Acoustic Processing
    ("VAD & Noise Classifier (Silero & Spectral)", "tests/test_vad_noise_classifier.py"),
    ("Audio Feature Extraction (Librosa)", "tests/test_audio_analysis.py"),

    # 4. Multimodal Fusion & Engagement
    ("Multimodal Feature Alignment", "tests/test_multimodal_alignment.py"),
    ("Engagement Scoring Engine", "tests/test_engagement_engine.py"),
    ("Reasoning & Pedagogical Rules", "tests/test_reasoning_engine.py"),

    # 5. Core Services, Database & Endpoints
    ("SQLite Database & Models", "tests/test_database.py"),
    ("Attendance Qualification Service", "tests/test_attendance_service.py"),
    ("FastAPI REST Endpoints & WebSockets", "tests/test_api_endpoints.py"),
]


def run_master_test_suite():
    print("=" * 76)
    print("🎓 MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT — MASTER VERIFICATION RUNNER")
    print("=" * 76)
    print(f"Timestamp : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python    : {PYTHON_BIN}")
    print(f"Directory : {PROJECT_ROOT}")
    print(f"Total Suites to Execute : {len(TEST_SUITES)}")
    print("=" * 76)

    results = []
    total_start = time.time()

    for idx, (name, test_file) in enumerate(TEST_SUITES, 1):
        test_path = os.path.join(PROJECT_ROOT, test_file)
        if not os.path.exists(test_path):
            print(f"[{idx:02d}/{len(TEST_SUITES):02d}] ❌ {name}: File not found ({test_file})")
            results.append((name, test_file, False, 0.0, "File not found"))
            continue

        print(f"\n[{idx:02d}/{len(TEST_SUITES):02d}] 🚀 RUNNING: {name} ({test_file})...")
        t0 = time.time()
        res = subprocess.run(
            [PYTHON_BIN, test_path],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        elapsed = time.time() - t0
        passed = (res.returncode == 0)

        if passed:
            print(f"       ✅ PASSED in {elapsed:.2f}s")
            results.append((name, test_file, True, elapsed, ""))
        else:
            print(f"       ❌ FAILED in {elapsed:.2f}s (Exit code: {res.returncode})")
            # Show tail of output for debugging
            tail_lines = "\n".join(res.stdout.strip().splitlines()[-12:])
            print(f"       --- Output Tail ---\n{tail_lines}\n       -------------------")
            results.append((name, test_file, False, elapsed, tail_lines))

    total_elapsed = time.time() - total_start
    passed_count = sum(1 for r in results if r[2])
    failed_count = len(results) - passed_count

    # Print Summary Scorecard
    print("\n" + "=" * 76)
    print("🏆 MASTER VERIFICATION SCORECARD")
    print("=" * 76)
    print(f"{'#':<3} | {'Test Suite Name':<42} | {'Time':<7} | {'Status':<10}")
    print("-" * 76)

    for idx, (name, _, passed, elapsed, _) in enumerate(results, 1):
        status_str = "✅ PASS" if passed else "❌ FAIL"
        print(f"{idx:<3} | {name:<42} | {elapsed:>5.2f}s | {status_str:<10}")

    print("-" * 76)
    print(f"Total Suites : {len(results)}")
    print(f"Passed       : {passed_count}")
    print(f"Failed       : {failed_count}")
    print(f"Success Rate : {(passed_count / len(results)) * 100:.1f}%")
    print(f"Total Time   : {total_elapsed:.2f}s")
    print("=" * 76)

    if failed_count == 0:
        print("\n🎉 ALL TESTS PASSED! FULL SYSTEM INTEGRITY & ZERO REGRESSION CONFIRMED.\n")
        sys.exit(0)
    else:
        print(f"\n⚠️ {failed_count} TEST SUITE(S) FAILED. PLEASE REVIEW LOGS ABOVE.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_master_test_suite()
