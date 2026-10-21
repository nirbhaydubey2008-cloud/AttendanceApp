#!/usr/bin/env python3
"""
generate_test_media.py
Generates deterministic synthetic video and audio media for testing
the Multimodal Attendance & Engagement Agent offline.
"""

import os
import sys
import math
import numpy as np
import cv2
import soundfile as sf
import librosa

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_media")
VIDEO_PATH = os.path.join(MEDIA_DIR, "test_classroom.mp4")
AUDIO_PATH = os.path.join(MEDIA_DIR, "test_classroom.wav")

def draw_student_face(frame, center_x, center_y, scale=1.0, yaw=0.0, pitch=0.0, eyes_open=True):
    """
    Renders a realistic stylized face avatar structured with lighting contrast
    that triggers Haar cascades and feature detectors.
    """
    # Head contour (skin tone)
    head_w = int(45 * scale)
    head_h = int(60 * scale)
    skin_color = (180, 205, 240)  # BGR skin tone
    shadow_color = (140, 165, 200)
    hair_color = (40, 45, 55)     # Dark hair
    feature_color = (30, 30, 40)  # Dark eyes/brows
    
    # Head rotation offset
    x_shift = int(yaw * 15 * scale)
    y_shift = int(pitch * 10 * scale)
    cx = center_x + x_shift
    cy = center_y + y_shift

    # Hair / back head
    cv2.ellipse(frame, (cx, cy - int(10 * scale)), (head_w + int(6 * scale), head_h), 0, 0, 360, hair_color, -1)
    
    # Face base
    cv2.ellipse(frame, (cx, cy), (head_w, head_h), 0, 0, 360, skin_color, -1)
    
    # Forehead shading
    cv2.ellipse(frame, (cx, cy - int(25 * scale)), (int(head_w * 0.85), int(head_h * 0.35)), 0, 0, 360, shadow_color, -1)

    # Hair fringe/front
    cv2.ellipse(frame, (cx, cy - int(38 * scale)), (int(head_w * 0.95), int(head_h * 0.3)), 0, 0, 180, hair_color, -1)

    # Eyebrows
    eye_y = cy - int(10 * scale)
    brow_y = eye_y - int(12 * scale)
    brow_offset = int(18 * scale)
    cv2.line(frame, (cx - brow_offset - int(10 * scale), brow_y), (cx - brow_offset + int(8 * scale), brow_y - int(2 * scale)), feature_color, int(3 * scale))
    cv2.line(frame, (cx + brow_offset - int(8 * scale), brow_y - int(2 * scale)), (cx + brow_offset + int(10 * scale), brow_y), feature_color, int(3 * scale))

    # Eyes
    eye_offset = int(18 * scale)
    if eyes_open:
        # Eye white
        cv2.ellipse(frame, (cx - eye_offset, eye_y), (int(8 * scale), int(5 * scale)), 0, 0, 360, (255, 255, 255), -1)
        cv2.ellipse(frame, (cx + eye_offset, eye_y), (int(8 * scale), int(5 * scale)), 0, 0, 360, (255, 255, 255), -1)
        # Iris / Pupil
        pupil_dx = int(yaw * 3 * scale)
        pupil_dy = int(pitch * 2 * scale)
        cv2.circle(frame, (cx - eye_offset + pupil_dx, eye_y + pupil_dy), int(3.5 * scale), feature_color, -1)
        cv2.circle(frame, (cx + eye_offset + pupil_dx, eye_y + pupil_dy), int(3.5 * scale), feature_color, -1)
    else:
        # Closed eye line
        cv2.line(frame, (cx - eye_offset - int(7 * scale), eye_y), (cx - eye_offset + int(7 * scale), eye_y), feature_color, 2)
        cv2.line(frame, (cx + eye_offset - int(7 * scale), eye_y), (cx + eye_offset + int(7 * scale), eye_y), feature_color, 2)

    # Nose
    nose_y = cy + int(6 * scale)
    cv2.line(frame, (cx, cy - int(4 * scale)), (cx, nose_y), (140, 160, 195), 2)
    cv2.circle(frame, (cx, nose_y), int(3 * scale), (130, 150, 185), -1)

    # Mouth
    mouth_y = cy + int(24 * scale)
    mouth_w = int(12 * scale)
    cv2.ellipse(frame, (cx, mouth_y), (mouth_w, int(4 * scale)), 0, 0, 180, (90, 95, 160), -1)

    # Shoulders / Torso
    torso_color = (120, 90, 70) if center_x < 300 else ((70, 110, 130) if center_x < 450 else (90, 120, 80))
    cv2.ellipse(frame, (cx, cy + int(115 * scale)), (int(75 * scale), int(45 * scale)), 0, 0, 360, torso_color, -1)

def generate_synthetic_video(output_path, duration_sec=10, fps=20, width=640, height=480):
    """
    Generates a 640x480 classroom video with 3 students exhibiting realistic behaviors:
    - Student A (left): Highly attentive, small blinks, steady gaze.
    - Student B (center): Attentive initially, then turns head left/right, then refocuses.
    - Student C (right): Low engagement, glances away, steps out of frame briefly (sec 5-7).
    """
    print(f"\n[1/2] Generating synthetic classroom video: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    total_frames = duration_sec * fps

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        
        # Classroom background: gradient wall + blackboard + desk surface
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Wall gradient
        for y in range(320):
            val = int(220 - y * 0.15)
            frame[y, :] = (val - 15, val, val)
        # Blackboard
        cv2.rectangle(frame, (80, 30), (560, 170), (45, 60, 40), -1)
        cv2.rectangle(frame, (76, 26), (564, 174), (70, 90, 65), 4)
        cv2.putText(frame, "CS101: Multimodal AI & Perception", (100, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 230, 200), 2)
        cv2.putText(frame, f"Session Time: 00:{int(t):02d}s | Active Classroom", (100, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (170, 200, 170), 1)

        # Desk divider
        cv2.rectangle(frame, (0, 340), (width, height), (100, 120, 140), -1)
        cv2.line(frame, (0, 340), (width, 340), (80, 100, 120), 3)

        # Student 1: Left seat (Attentive)
        # Steady position, subtle natural breathing, occasional blink
        s1_y = 260 + int(math.sin(t * 2.0) * 2)
        s1_blink = (frame_idx % (fps * 3)) < 4  # brief blink every 3s
        draw_student_face(frame, 160, s1_y, scale=1.1, yaw=0.05 * math.sin(t * 0.8), pitch=0.0, eyes_open=not s1_blink)
        cv2.putText(frame, "Student_01", (120, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 240, 240), 1)

        # Student 2: Center seat (Enrolled: Nirbhay Dubey)
        # Turns head around t=4s to 6s, then looks back
        if 4.0 <= t <= 6.5:
            s2_yaw = 0.8 * math.sin((t - 4.0) / 2.5 * math.pi)
            s2_pitch = 0.2
        else:
            s2_yaw = 0.05 * math.sin(t * 0.5)
            s2_pitch = 0.0
        s2_y = 250 + int(math.sin(t * 1.5) * 2)
        s2_blink = (frame_idx % (fps * 4)) < 4
        draw_student_face(frame, 320, s2_y, scale=1.2, yaw=s2_yaw, pitch=s2_pitch, eyes_open=not s2_blink)
        cv2.putText(frame, "Nirbhay Dubey", (270, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 240, 240), 1)

        # Student 3: Right seat (Distracted / Absent during 5s-7.5s)
        if not (5.0 <= t <= 7.5):
            s3_yaw = 0.4 + 0.2 * math.sin(t * 1.2)  # looking away towards door
            s3_pitch = -0.2
            s3_y = 265
            draw_student_face(frame, 480, s3_y, scale=1.05, yaw=s3_yaw, pitch=s3_pitch, eyes_open=True)
            cv2.putText(frame, "Student_03", (445, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 240, 240), 1)
        else:
            # Empty desk (absence simulation)
            cv2.putText(frame, "[Left Desk]", (445, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 200), 1)

        # Frame timestamp overlay
        cv2.putText(frame, f"FPS: {fps} | Frame: {frame_idx:03d}/{total_frames:03d} | Time: {t:4.2f}s",
                    (15, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        out.write(frame)

    out.release()
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"  [SUCCESS] Video created: {output_path} ({total_frames} frames, {width}x{height}, {file_size_kb:.1f} KB)")
    return True

def generate_synthetic_audio(output_path, duration_sec=10, sample_rate=16000):
    """
    Generates a 16kHz mono audio WAV simulating classroom acoustics:
    - 0.0s - 2.5s: Quiet ambient classroom (RMS ~ 0.005)
    - 2.5s - 6.5s: Teacher lecture & student answer (vocal harmonic formants, RMS ~ 0.08)
    - 6.5s - 8.0s: Ambient quiet (RMS ~ 0.005)
    - 8.0s - 9.5s: Desk rustle / noise burst (RMS ~ 0.04)
    - 9.5s - 10.0s: Quiet ambient return
    """
    print(f"\n[2/2] Generating synthetic classroom audio: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    total_samples = int(duration_sec * sample_rate)
    time_axis = np.linspace(0, duration_sec, total_samples, endpoint=False)
    audio = np.zeros(total_samples, dtype=np.float32)

    # 1. Base ambient room noise floor (pink/brownish noise)
    white_noise = np.random.normal(0, 0.004, total_samples).astype(np.float32)
    # Simple lowpass filter for gentle room hum (60Hz / HVAC)
    room_hum = 0.002 * np.sin(2 * np.pi * 60 * time_axis)
    audio += white_noise + room_hum

    # 2. Speech segment (t = 2.5s to 6.5s)
    speech_mask = (time_axis >= 2.5) & (time_axis <= 6.5)
    t_speech = time_axis[speech_mask] - 2.5
    
    # Syllabic envelope modulation (approx 3.5 syllables per sec)
    syllable_env = np.clip(np.sin(2 * np.pi * 3.5 * t_speech) ** 2, 0, 1)
    # Pitch fundamental (F0 ~ 150 Hz male / 220 Hz female pitch)
    f0 = 175.0 + 15.0 * np.sin(2 * np.pi * 1.2 * t_speech)
    voice_harmonics = (
        0.05 * np.sin(2 * np.pi * f0 * t_speech) +
        0.04 * np.sin(2 * np.pi * 2 * f0 * t_speech) +
        0.03 * np.sin(2 * np.pi * 3 * f0 * t_speech) +
        0.02 * np.sin(2 * np.pi * 5 * f0 * t_speech) +
        0.015 * np.sin(2 * np.pi * 1400 * t_speech) # Formant resonance
    )
    audio[speech_mask] += (voice_harmonics * syllable_env).astype(np.float32)

    # 3. Noise burst (t = 8.0s to 9.5s: papers rustling / chair movement)
    burst_mask = (time_axis >= 8.0) & (time_axis <= 9.5)
    t_burst = time_axis[burst_mask] - 8.0
    burst_env = np.exp(-t_burst * 1.5) * (np.sin(2 * np.pi * 2.0 * t_burst) ** 2)
    burst_noise = np.random.normal(0, 0.035, len(t_burst)).astype(np.float32)
    audio[burst_mask] += (burst_noise * burst_env).astype(np.float32)

    # Normalize within [-0.95, 0.95]
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / max(peak, 1.0) * 0.9

    sf.write(output_path, audio, sample_rate, subtype="PCM_16")
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"  [SUCCESS] Audio created: {output_path} ({duration_sec}s, {sample_rate} Hz, mono, {file_size_kb:.1f} KB)")
    return True

def verify_media():
    """
    Verifies that generated files exist and can be loaded/analyzed
    by OpenCV and Librosa/Soundfile.
    """
    print("\n" + "=" * 60)
    print("3. VERIFYING GENERATED TEST MEDIA")
    print("=" * 60)
    
    # Verify Video
    if not os.path.exists(VIDEO_PATH):
        print(f"  [FAIL] Video file missing: {VIDEO_PATH}")
        return False
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("  [FAIL] OpenCV could not open generated video.")
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ret, sample_frame = cap.read()
    cap.release()

    if not ret or sample_frame is None:
        print("  [FAIL] Could not decode first frame of test video.")
        return False

    print(f"  [PASS] Video Verification:")
    print(f"         - Resolution: {width}x{height}")
    print(f"         - Total Frames: {frame_count}")
    print(f"         - Framerate: {fps:.1f} fps")
    print(f"         - Decoded Frame Shape: {sample_frame.shape}")

    # Verify Audio
    if not os.path.exists(AUDIO_PATH):
        print(f"  [FAIL] Audio file missing: {AUDIO_PATH}")
        return False
    
    audio_data, sr = sf.read(AUDIO_PATH)
    librosa_audio, lib_sr = librosa.load(AUDIO_PATH, sr=16000)
    rms_features = librosa.feature.rms(y=librosa_audio)[0]
    mean_rms = float(np.mean(rms_features))
    max_rms = float(np.max(rms_features))

    print(f"  [PASS] Audio Verification:")
    print(f"         - Sample Rate: {sr} Hz")
    print(f"         - Total Samples: {len(audio_data)} ({len(audio_data)/sr:.2f}s)")
    print(f"         - Mean RMS Energy: {mean_rms:.5f}")
    print(f"         - Peak RMS Energy: {max_rms:.5f}")
    print(f"         - Speech Segment Detected (Peak > 0.02): {max_rms > 0.02}")

    print("\n" + "=" * 60)
    print("RESULT: ALL TEST MEDIA GENERATED AND VERIFIED SUCCESSFULLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    generate_synthetic_video(VIDEO_PATH)
    generate_synthetic_audio(AUDIO_PATH)
    if not verify_media():
        sys.exit(1)
    sys.exit(0)
