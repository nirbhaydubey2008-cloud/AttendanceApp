#!/usr/bin/env python3
"""
tests/test_vad_noise_classifier.py
Verification suite for Voice Activity Detection (VAD) and Environmental Noise Classification.
"""

import os
import sys
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.audio_analysis import AudioAnalyzer, ClassroomAcousticState

def test_adaptive_noise_floor_and_silence():
    print("Test 1: Adaptive noise floor and silence classification...")
    analyzer = AudioAnalyzer(sample_rate=16000)
    initial_floor = analyzer.noise_floor
    
    # Very quiet ambient noise (RMS ~ 0.002)
    ambient_quiet = np.random.normal(0, 0.002, 32000).astype(np.float32)
    res = analyzer.analyze_audio_chunk(ambient_quiet)
    
    assert res["state"] == ClassroomAcousticState.QUIET.value
    assert res["is_speech"] is False
    assert res["is_disturbance"] is False
    assert res["engagement_audio_factor"] == 1.0
    print(f"  [PASS] Quiet chunk classified: State={res['state']}, Noise Floor={res['noise_floor']:.5f}")

def test_speech_detection_accuracy():
    print("\nTest 2: Voice Activity Detection (VAD) on synthesized vocal speech...")
    analyzer = AudioAnalyzer(sample_rate=16000)
    
    # 2.0s of vocal harmonics (F0 = 180 Hz with formants, RMS ~ 0.035)
    t = np.linspace(0, 2.0, 32000, endpoint=False)
    vocal = (0.04 * np.sin(2 * np.pi * 180 * t) +
             0.03 * np.sin(2 * np.pi * 360 * t) +
             0.02 * np.sin(2 * np.pi * 1500 * t)).astype(np.float32)
    
    res = analyzer.analyze_audio_chunk(vocal)
    assert res["state"] == ClassroomAcousticState.SPEECH.value, f"Expected SPEECH, got {res['state']}"
    assert res["is_speech"] is True
    assert res["speech_confidence"] >= 0.60
    assert res["snr_db"] > 10.0, f"Expected high SNR, got {res['snr_db']:.1f} dB"
    print(f"  [PASS] Speech classified: State={res['state']}, Conf={res['speech_confidence']:.2f}, SNR={res['snr_db']:.1f} dB")

def test_disturbance_detection():
    print("\nTest 3: Environmental noise burst / disturbance classification...")
    analyzer = AudioAnalyzer(sample_rate=16000, disturbance_threshold=0.035)
    
    # High amplitude broadband noise burst (RMS ~ 0.045, high ZCR)
    burst = np.random.normal(0, 0.045, 32000).astype(np.float32)
    res = analyzer.analyze_audio_chunk(burst)
    
    assert res["state"] == ClassroomAcousticState.DISTURBANCE.value, f"Expected DISTURBANCE, got {res['state']}"
    assert res["is_disturbance"] is True
    assert res["is_speech"] is False
    assert res["engagement_audio_factor"] < 0.50
    print(f"  [PASS] Disturbance classified: State={res['state']}, Engagement Factor={res['engagement_audio_factor']:.2f}")

def test_classroom_audio_file_sequence():
    print("\nTest 4: Classroom acoustic state sequence on test_classroom.wav...")
    audio_path = os.path.join(PROJECT_ROOT, "test_media", "test_classroom.wav")
    assert os.path.exists(audio_path)
    
    analyzer = AudioAnalyzer(sample_rate=16000, chunk_duration_sec=1.0)
    chunks = analyzer.process_audio_file(audio_path, chunk_duration_sec=1.0)
    
    states = [c["state"] for c in chunks]
    print(f"  10-second states sequence (1s chunks):")
    for idx, (c, s) in enumerate(zip(chunks, states)):
        print(f"    - [{idx}s - {idx+1}s]: State={s:<14} (RMS={c['rms']:.5f}, Centroid={c['spectral_centroid']:.0f}Hz, SNR={c['snr_db']:.1f}dB)")

    # Assert 0-2s is QUIET
    assert states[0] == "QUIET", f"Expected Chunk 0 to be QUIET, got {states[0]}"
    assert states[1] == "QUIET", f"Expected Chunk 1 to be QUIET, got {states[1]}"
    
    # Assert speech is detected during 3-6s
    speech_chunks = [s for s in states[3:6] if s == "SPEECH"]
    assert len(speech_chunks) >= 2, f"Expected at least 2 speech chunks during 3-6s, got {speech_chunks}"
    
    # Assert disturbance or elevated noise is detected during 8-9s burst
    burst_chunk = chunks[8]
    assert burst_chunk["state"] in ["DISTURBANCE", "MODERATE_NOISE"], f"Expected disturbance/noise at 8s, got {burst_chunk['state']}"
    assert burst_chunk["is_speech"] is False
    
    print("  [PASS] Full audio file acoustic sequence verified across all phases.")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 3.2 — VAD & Noise Classification")
    print("=" * 60)
    try:
        test_adaptive_noise_floor_and_silence()
        test_speech_detection_accuracy()
        test_disturbance_detection()
        test_classroom_audio_file_sequence()
        print("\n" + "=" * 60)
        print("RESULT: ALL VAD & NOISE CLASSIFICATION TESTS PASSED!")
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
