"""
services/audio_analysis.py
Audio Processing, Feature Extraction, Voice Activity Detection (VAD),
and Environmental Classroom Noise Classification Service.
Extracts: RMS, dBFS, ZCR, Spectral Centroid, Rolloff, 13 MFCCs,
Dynamic Noise Floor, SNR, Speech Confidence, and Acoustic Classroom State.
"""

import os
import time
import logging
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Union
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


class ClassroomAcousticState(str, Enum):
    QUIET = "QUIET"
    SPEECH = "SPEECH"
    MODERATE_NOISE = "MODERATE_NOISE"
    DISTURBANCE = "DISTURBANCE"


class AudioAnalyzer:
    """
    Real-time chunk-based and file-based audio analysis engine with
    energy-based VAD, adaptive noise floor tracking, and classroom state classification.
    """
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_sec: float = 2.0,
        n_mfcc: int = 13,
        speech_energy_threshold: float = 0.015,
        disturbance_threshold: float = 0.040
    ):
        self.sample_rate = sample_rate
        self.chunk_duration_sec = chunk_duration_sec
        self.chunk_samples = int(sample_rate * chunk_duration_sec)
        self.n_mfcc = n_mfcc
        self.speech_energy_threshold = speech_energy_threshold
        self.disturbance_threshold = disturbance_threshold
        
        # Adaptive noise floor tracker
        self.noise_floor: float = 0.004
        self.alpha_noise: float = 0.85

    def bytes_to_float32(self, chunk_bytes: bytes) -> np.ndarray:
        """Converts raw 16-bit signed integer or 32-bit float audio bytes into a float32 numpy array."""
        if not chunk_bytes:
            return np.zeros(0, dtype=np.float32)

        try:
            int16_arr = np.frombuffer(chunk_bytes, dtype=np.int16)
            return int16_arr.astype(np.float32) / 32768.0
        except Exception:
            pass

        try:
            return np.frombuffer(chunk_bytes, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to parse audio bytes: {e}")
            return np.zeros(0, dtype=np.float32)

    def extract_features(self, y: np.ndarray) -> Dict[str, Any]:
        """Extracts acoustic features from a 1D audio waveform array."""
        if y is None or len(y) == 0:
            return {
                "rms": 0.0,
                "db_level": -80.0,
                "zcr": 0.0,
                "spectral_centroid": 0.0,
                "spectral_rolloff": 0.0,
                "mfcc": [0.0] * self.n_mfcc,
                "duration_sec": 0.0,
                "num_samples": 0
            }

        if y.ndim > 1:
            y = np.mean(y, axis=1)
        y = y.astype(np.float32)

        # 1. RMS Energy & dBFS
        rms_series = librosa.feature.rms(y=y, frame_length=512, hop_length=256)[0]
        rms_val = float(np.mean(rms_series))
        db_level = float(20.0 * np.log10(max(rms_val, 1e-6)))

        # 2. Zero-Crossing Rate
        zcr_series = librosa.feature.zero_crossing_rate(y=y, frame_length=512, hop_length=256)[0]
        zcr_val = float(np.mean(zcr_series))

        # 3. Spectral Centroid
        centroid_series = librosa.feature.spectral_centroid(
            y=y, sr=self.sample_rate, n_fft=512, hop_length=256
        )[0]
        centroid_val = float(np.mean(centroid_series))

        # 4. Spectral Rolloff
        rolloff_series = librosa.feature.spectral_rolloff(
            y=y, sr=self.sample_rate, n_fft=512, hop_length=256, roll_percent=0.85
        )[0]
        rolloff_val = float(np.mean(rolloff_series))

        # 5. MFCCs
        mfcc_matrix = librosa.feature.mfcc(
            y=y, sr=self.sample_rate, n_mfcc=self.n_mfcc, n_fft=512, hop_length=256
        )
        mfcc_means = [float(val) for val in np.mean(mfcc_matrix, axis=1)]

        return {
            "rms": rms_val,
            "db_level": db_level,
            "zcr": zcr_val,
            "spectral_centroid": centroid_val,
            "spectral_rolloff": rolloff_val,
            "mfcc": mfcc_means,
            "duration_sec": float(len(y) / self.sample_rate),
            "num_samples": int(len(y))
        }

    def classify_acoustic_state(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies rule-based reasoning on extracted features to determine Voice Activity (VAD),
        noise floor, SNR, and the classroom acoustic state.
        """
        rms = features["rms"]
        zcr = features["zcr"]
        centroid = features["spectral_centroid"]

        # Signal-to-Noise Ratio (dB) relative to dynamic noise floor
        snr_db = float(20.0 * np.log10(max(rms, 1e-6) / max(self.noise_floor, 1e-6)))

        # Human vocal formants predominantly reside in 300 - 3500 Hz, with lower ZCR (< 0.35)
        is_in_vocal_range = (300.0 <= centroid <= 3500.0)
        has_voiced_zcr = (zcr <= 0.35)
        has_speech_energy = (rms >= self.speech_energy_threshold or snr_db >= 10.0)

        # 1. Speech Classification
        if has_speech_energy and is_in_vocal_range and has_voiced_zcr:
            state = ClassroomAcousticState.SPEECH
            is_speech = True
            is_disturbance = False
            # Confidence scaled from energy and formant alignment
            speech_confidence = float(min(1.0, max(0.60, 0.5 + (rms / (2.0 * self.speech_energy_threshold)) * 0.5)))
            engagement_audio_factor = 0.85  # Listening to lecture/discussion is productive
        # 2. Disturbance / Noise Burst Classification
        elif (rms >= self.disturbance_threshold) or (
            rms >= self.noise_floor * 2.0 and (zcr > 0.40 or centroid > 3600.0) and rms >= 0.008
        ):
            state = ClassroomAcousticState.DISTURBANCE
            is_speech = False
            is_disturbance = True
            speech_confidence = 0.1
            engagement_audio_factor = 0.35  # Distracting noise reduces attentiveness environment
        # 3. Moderate Noise
        elif rms >= self.noise_floor * 1.5 or (rms >= 0.008 and not is_in_vocal_range):
            state = ClassroomAcousticState.MODERATE_NOISE
            is_speech = False
            is_disturbance = False
            speech_confidence = 0.2
            engagement_audio_factor = 0.65
            # Update ambient noise floor
            self.noise_floor = float(self.alpha_noise * self.noise_floor + (1.0 - self.alpha_noise) * rms)
        # 4. Quiet / Silent Classroom
        else:
            state = ClassroomAcousticState.QUIET
            is_speech = False
            is_disturbance = False
            speech_confidence = 0.05
            engagement_audio_factor = 1.0  # Silent classroom is ideal for focused work
            # Adapt noise floor during silence
            if rms > 0.0:
                self.noise_floor = float(self.alpha_noise * self.noise_floor + (1.0 - self.alpha_noise) * rms)

        return {
            "state": state.value,
            "is_speech": is_speech,
            "is_disturbance": is_disturbance,
            "speech_confidence": speech_confidence,
            "snr_db": snr_db,
            "noise_floor": float(self.noise_floor),
            "engagement_audio_factor": engagement_audio_factor
        }

    def analyze_audio_chunk(
        self,
        audio_data: Union[bytes, np.ndarray],
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Analyzes a single streaming chunk of audio, extracting features and classifying state."""
        if isinstance(audio_data, bytes):
            waveform = self.bytes_to_float32(audio_data)
        elif isinstance(audio_data, np.ndarray):
            waveform = audio_data
        else:
            raise TypeError("audio_data must be bytes or np.ndarray")

        ts = timestamp if timestamp is not None else time.time()
        features = self.extract_features(waveform)
        features["timestamp"] = ts
        
        # Classify acoustic state
        classification = self.classify_acoustic_state(features)
        features.update(classification)
        return features

    def process_audio_file(
        self,
        file_path: str,
        chunk_duration_sec: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Processes an audio file in sequential chunks with classification."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
        chunk_sec = chunk_duration_sec or self.chunk_duration_sec
        samples_per_chunk = int(sr * chunk_sec)

        chunk_results = []
        total_samples = len(y)
        num_chunks = int(np.ceil(total_samples / samples_per_chunk))

        for idx in range(num_chunks):
            start_sample = idx * samples_per_chunk
            end_sample = min(total_samples, start_sample + samples_per_chunk)
            chunk_y = y[start_sample:end_sample]
            
            chunk_ts = float(start_sample / sr)
            features = self.extract_features(chunk_y)
            features["chunk_index"] = idx
            features["timestamp"] = chunk_ts
            
            classification = self.classify_acoustic_state(features)
            features.update(classification)
            chunk_results.append(features)

        logger.info(f"Processed audio file {file_path}: {len(chunk_results)} chunks classified.")
        return chunk_results
