"""
services/face_recognition.py
Offline Face Recognition and Student Biometric Enrollment Service using DeepFace (Facenet).
Strictly privacy-preserving: consent-based enrollment, zero cloud telemetry,
and unknown tracks default to anonymous track IDs without automated assumption.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import cv2
from deepface import DeepFace

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """
    Offline Student Face Recognizer and Biometric Enrollment Manager.
    """
    def __init__(
        self,
        db_path: str = "student_db",
        model_name: str = "Facenet",
        distance_threshold: float = 0.15
    ):
        """
        Initializes FaceRecognizer.
        
        Args:
            db_path: Directory for enrolled student biometric images and index.
            model_name: DeepFace model ('Facenet' default, 128-d embeddings).
            distance_threshold: Maximum cosine distance threshold for positive match.
        """
        self.db_path = os.path.abspath(db_path)
        self.model_name = model_name
        self.distance_threshold = distance_threshold
        self.index_file = os.path.join(self.db_path, "students_index.json")
        self.enrolled_students: Dict[str, Dict[str, Any]] = {}
        self.track_identity_cache: Dict[str, Dict[str, Any]] = {}
        
        os.makedirs(self.db_path, exist_ok=True)
        self._load_enrolled_database()

    def _load_enrolled_database(self):
        """Loads enrolled students metadata and embeddings from disk."""
        if not os.path.exists(self.index_file):
            self.enrolled_students = {}
            logger.info("Initialized empty student enrollment database.")
            return

        try:
            with open(self.index_file, "r") as f:
                data = json.load(f)
                self.enrolled_students = {
                    s["student_id"]: {
                        "student_id": s["student_id"],
                        "name": s["name"],
                        "roll_no": s.get("roll_no", ""),
                        "photo_path": s.get("photo_path", ""),
                        "enrolled_at": s.get("enrolled_at", ""),
                        "consent_given": s.get("consent_given", True),
                        "embedding": np.array(s["embedding"], dtype=np.float32)
                    }
                    for s in data
                }
            logger.info(f"Loaded {len(self.enrolled_students)} enrolled students from {self.index_file}")
        except Exception as e:
            logger.error(f"Error loading student database index: {e}")
            self.enrolled_students = {}

    def _save_enrolled_database(self):
        """Persists enrolled students metadata and serialized embeddings."""
        try:
            serializable_list = []
            for s in self.enrolled_students.values():
                item = {
                    "student_id": s["student_id"],
                    "name": s["name"],
                    "roll_no": s["roll_no"],
                    "photo_path": s["photo_path"],
                    "enrolled_at": s["enrolled_at"],
                    "consent_given": s["consent_given"],
                    "embedding": s["embedding"].tolist()
                }
                serializable_list.append(item)
            
            with open(self.index_file, "w") as f:
                json.dump(serializable_list, f, indent=2)
            logger.info(f"Persisted {len(serializable_list)} students to {self.index_file}")
        except Exception as e:
            logger.error(f"Failed to save student index: {e}")

    def compute_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """
        Extracts 128-d Facenet embedding from face crop.
        """
        if face_img is None or face_img.size == 0:
            return None

        # Resize to standard input dimensions for consistency
        h, w = face_img.shape[:2]
        if h < 60 or w < 60:
            face_img = cv2.resize(face_img, (160, 160), interpolation=cv2.INTER_CUBIC)

        try:
            res = DeepFace.represent(
                img_path=face_img,
                model_name=self.model_name,
                detector_backend="skip",
                enforce_detection=False
            )
            if res and len(res) > 0 and "embedding" in res[0]:
                emb = np.array(res[0]["embedding"], dtype=np.float32)
                norm = np.linalg.norm(emb)
                return emb / norm if norm > 1e-6 else emb
        except Exception as e:
            logger.warning(f"Error computing face embedding: {e}")

        return None

    def enroll_student(
        self,
        student_id: str,
        name: str,
        face_img: np.ndarray,
        roll_no: str = "",
        consent_given: bool = True
    ) -> Dict[str, Any]:
        """
        Enrolls a new student biometrically with explicit privacy consent.
        """
        if not consent_given:
            raise PermissionError(f"Biometric enrollment rejected: Consent not granted for {student_id}")

        embedding = self.compute_embedding(face_img)
        if embedding is None:
            raise ValueError(f"Could not extract valid biometric facial embedding for student {student_id}")

        photo_filename = f"{student_id}.jpg"
        photo_path = os.path.join(self.db_path, photo_filename)
        cv2.imwrite(photo_path, face_img)

        student_record = {
            "student_id": student_id,
            "name": name,
            "roll_no": roll_no,
            "photo_path": photo_path,
            "enrolled_at": datetime.utcnow().isoformat() + "Z",
            "consent_given": True,
            "embedding": embedding
        }

        self.enrolled_students[student_id] = student_record
        self._save_enrolled_database()
        
        logger.info(f"Student successfully enrolled: {student_id} ({name})")
        return {
            "success": True,
            "student_id": student_id,
            "name": name,
            "roll_no": roll_no,
            "photo_path": photo_path
        }

    def recognize_face(self, face_crop: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Compares face crop against all enrolled students using cosine distance.
        Returns matching student dict or None if no enrolled student matches within threshold.
        """
        if not self.enrolled_students or face_crop is None or face_crop.size == 0:
            return None

        target_emb = self.compute_embedding(face_crop)
        if target_emb is None:
            return None

        best_student = None
        best_distance = float("inf")

        for student_id, student in self.enrolled_students.items():
            enrolled_emb = student["embedding"]
            # Cosine distance: 1.0 - dot_product (both embeddings are L2 normalized)
            cosine_dist = float(1.0 - np.dot(target_emb, enrolled_emb))
            if cosine_dist < best_distance:
                best_distance = cosine_dist
                best_student = student

        if best_distance <= self.distance_threshold and best_student is not None:
            confidence = float(max(0.0, min(1.0, 1.0 - (best_distance / self.distance_threshold))))
            return {
                "student_id": best_student["student_id"],
                "name": best_student["name"],
                "roll_no": best_student["roll_no"],
                "confidence": confidence,
                "distance": best_distance,
                "is_enrolled": True
            }

        return None

    def get_track_identity(
        self,
        track_id: str,
        face_crop: np.ndarray,
        frame_idx: int = 0,
        recheck_interval: int = 25
    ) -> Dict[str, Any]:
        """
        Maintains identity cache per active DeepSort track.
        Runs DeepFace recognition periodically or on first detection to preserve high FPS.
        """
        cached = self.track_identity_cache.get(track_id)
        
        if cached is not None:
            last_checked = cached.get("last_checked", 0)
            # If already recognized or checked recently, return cached identity
            if cached.get("is_enrolled") or (frame_idx - last_checked < recheck_interval):
                return cached

        # Perform recognition on current face crop
        match = self.recognize_face(face_crop)
        if match:
            identity = {
                "track_id": track_id,
                "student_id": match["student_id"],
                "name": match["name"],
                "roll_no": match["roll_no"],
                "confidence": match["confidence"],
                "is_enrolled": True,
                "last_checked": frame_idx
            }
        else:
            identity = {
                "track_id": track_id,
                "student_id": None,
                "name": f"Student #{track_id}",
                "roll_no": "",
                "confidence": 0.5,
                "is_enrolled": False,
                "last_checked": frame_idx
            }

        self.track_identity_cache[track_id] = identity
        return identity

    def clear_track_cache(self, track_id: Optional[str] = None):
        """Clears cached identity records for a track or all tracks."""
        if track_id is not None:
            self.track_identity_cache.pop(track_id, None)
        else:
            self.track_identity_cache.clear()

    def remove_student(self, student_id: str) -> bool:
        """Removes a student from biometric database, deletes stored photo, and refreshes index."""
        target_id = None
        clean_target = str(student_id).strip().upper()
        for sid in list(self.enrolled_students.keys()):
            if sid.strip().upper() == clean_target:
                target_id = sid
                break

        if not target_id:
            return False

        student = self.enrolled_students.pop(target_id, None)
        if isinstance(student, dict):
            photo_path = student.get("photo_path")
            if photo_path and os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except Exception as e:
                    logger.warning(f"Could not delete photo file {photo_path}: {e}")

        self._save_enrolled_database()
        self.clear_track_cache()
        logger.info(f"Student {target_id} successfully removed from biometric registry.")
        return True
