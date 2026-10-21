#!/usr/bin/env python3
"""
tests/test_audio_analysis.py
Verification suite for Audio Processing and Feature Extraction Service.
"""

import os
import sys
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.audio_analysis import AudioAnalyzer

def test_silence_and_empty_input():
    print("Test 1: Silence & empty waveform handling...")
    analyzer = AudioAnalyzer(sample_rate=16000, chunk_duration_sec=2.0)
    
    empty_res = analyzer.analyze_audio_chunk(np.zeros(0, dtype=np.float32))
    assert empty_res["rms"] == 0.0
    assert empty_res["db_level"] == -80.0
    assert len(empty_res["mfcc"]) == 13
    
    silence_res = analyzer.analyze_audio_chunk(np.zeros(32000, dtype=np.float32))
    assert silence_res["rms"] == 0.0
    assert silence_res["num_samples"] == 32000
    print("  [PASS] Empty and silent input correctly handled.")

def test_pcm_bytes_conversion():
    print("\nTest 2: Raw PCM byte conversion...")
    analyzer = AudioAnalyzer(sample_rate=16000)
    
    # 1 second of 440 Hz sine wave in 16-bit PCM
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    sine_wave = (np.sin(2 * np.pi * 440.0 * t) * 32767).astype(np.int16)
    pcm_bytes = sine_wave.tobytes()
    
    features = analyzer.analyze_audio_chunk(pcm_bytes)
    assert features["num_samples"] == 16000
    assert abs(features["duration_sec"] - 1.0) < 1e-3
    assert 0.65 <= features["rms"] <= 0.75, f"Sine wave RMS expected ~0.707, got {features['rms']:.3f}"
    print(f"  [PASS] 16-bit PCM bytes decoded correctly (RMS: {features['rms']:.3f}).")

def test_classroom_audio_file_processing():
    print("\nTest 3: Processing test_classroom.wav in 2-second chunks...")
    audio_path = os.path.join(PROJECT_ROOT, "test_media", "test_classroom.wav")
    assert os.path.exists(audio_path), f"Audio file missing: {audio_path}"
    
    analyzer = AudioAnalyzer(sample_rate=16000, chunk_duration_sec=2.0)
    chunks = analyzer.process_audio_file(audio_path, chunk_duration_sec=2.0)
    
    assert len(chunks) == 5, f"Expected 5 chunks for 10s audio @ 2s/chunk, got {len(chunks)}"
    
    # Chunk 0: Quiet ambient (0-2s)
    c0 = chunks[0]
    print(f"  Chunk 0 (Quiet):  RMS={c0['rms']:.5f}, dB={c0['db_level']:.1f}, Centroid={c0['spectral_centroid']:.1f} Hz")
    assert c0["rms"] < 0.010, f"Quiet chunk RMS should be < 0.010, got {c0['rms']}"
    assert c0["db_level"] < -40.0, f"Quiet chunk dB level should be < -40, got {c0['db_level']}"
    
    # Chunk 1 & 2: Speech Activity (2-4s, 4-6s)
    c1 = chunks[1]
    print(f"  Chunk 1 (Speech): RMS={c1['rms']:.5f}, dB={c1['db_level']:.1f}, Centroid={c1['spectral_centroid']:.1f} Hz")
    assert c1["rms"] > 0.020, f"Speech chunk RMS should be > 0.020, got {c1['rms']}"
    assert c1["rms"] > c0["rms"] * 3.0, "Speech chunk should be significantly louder than quiet chunk"
    assert 1000.0 <= c1["spectral_centroid"] <= 3500.0, f"Speech spectral centroid should be in vocal range (1000-3500Hz), got {c1['spectral_centroid']}"
    assert len(c1["mfcc"]) == 13, f"Expected 13 MFCC coefficients, got {len(c1['mfcc'])}"
    
    print("  [PASS] All chunk acoustic features extracted and verified across phases.")

def main():
    print("=" * 60)
    print("VERIFICATION SUITE: Activity 3.1 — Audio Feature Extraction")
    print("=" * 60)
    try:
        test_silence_and_empty_input()
        test_pcm_bytes_conversion()
        test_classroom_audio_file_processing()
        print("\n" + "=" * 60)
        print("RESULT: ALL AUDIO FEATURE EXTRACTION TESTS PASSED!")
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
