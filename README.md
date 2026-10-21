# Multimodal Attendance & Engagement Agent

An offline-first, multimodal AI perception system with **Role-Based Access Control (RBAC)**, dedicated **Teacher & Student Dashboards**, automated student provisioning, and real-time attendance & engagement analytics.

**Developer:** Nirbhay Dubey — B.Tech Computer Science & Engineering (Year 1)  
**Version:** 2.0.0 (Production RBAC Release)

---

## 1. System Architecture

```
                    ┌───────────────────────────┐
                    │ Multimodal Input Sources  │
                    │  (Webcam / Test Video &   │
                    │   Mic / Audio Chunks)     │
                    └─────────────┬─────────────┘
                                  │
            ┌─────────────────────┴─────────────────────┐
            ▼                                           ▼
┌───────────────────────────┐               ┌───────────────────────────┐
│     Vision Pipeline       │               │      Audio Pipeline       │
│  - MediaPipe FaceLandmark │               │  - Librosa Audio Features │
│  - DeepSort Multi-Track   │               │  - SoundFile Chunking     │
│  - Head Pose & Eye Gaze   │               │  - Energy-based VAD       │
│  - 512-d Face Embeddings  │               │  - Noise Classifier       │
└─────────────┬─────────────┘               └─────────────┬─────────────┘
            │                                           │
            └─────────────────────┬─────────────────────┘
                                  ▼
                    ┌───────────────────────────┐
                    │ Multimodal Fusion Agent   │
                    │  - Temporal Sync Buffer   │
                    │  - Engagement Engine (0-1)│
                    │  - Attendance Verifier    │
                    └─────────────┬─────────────┘
                                  │
            ┌─────────────────────┴─────────────────────┐
            ▼                                           ▼
┌───────────────────────────┐               ┌───────────────────────────┐
│   FastAPI Security Engine │               │ Streamlit Dual Dashboards │
│  - PBKDF2-HMAC-SHA256 Auth│◄─────────────►│  - Unauthenticated Gate   │
│  - Role Guards (RBAC)     │               │  - Teacher Cockpit        │
│  - Anti-IDOR Defense      │               │  - Student Portal         │
│  - SQLite Audit Logging   │               │  - Live Lecture Sync      │
└───────────────────────────┘               └───────────────────────────┘
```

---

## 2. Core Capabilities

- **Offline-First AI Perception:** Real-time facial landmark detection (MediaPipe), 512-dimensional face recognition, DeepSort multi-student tracking, voice activity detection (VAD), and acoustic disturbance classification. Zero cloud transmission.
- **Role-Based Access Control (RBAC):** Backend-enforced authorization rules. Students are strictly prohibited from camera feeds, session controls, student enrollment, and administrative endpoints.
- **Anti-IDOR Defense:** Insecure Direct Object Reference prevention. Students can strictly query their own verified attendance; cross-student snooping attempts return `HTTP 403 Forbidden`.
- **Teacher Dashboard:** Course management, lecture scheduling, one-click live session launcher, annotated video stream preview, live presence qualification ($\ge 75\%$ Present, $40-74\%$ Partial, $<40\%$ Absent), audit-logged manual status overrides, and CSV export.
- **Student Dashboard:** Personalized student overview, real-time live lecture synchronization alert, personal attendance history, enrolled courses list, and self-service password update.
- **Student Provisioning:** Automatic institutional `STU-YYYY-XXXX` Student ID generation, temporary activation credentials, and duplicate roll number / email prevention.

---

## 3. Quick Demonstration Credentials

| Role | Username / Identifier | Password | Access Level |
|---|---|---|---|
| **Teacher** | `teacher` | `TeacherPassword123!` | Full administrative, perception, and session authority |
| **Student (Permanent)** | `STU-2026-0001` | `DavidPermanentPass123!` | Personal attendance records and live class indicator |
| **Student (Activation)** | `STU-2026-0002` | `StudentTempPass123!` | First-time login workflow with mandatory password change |

To provision a fresh teacher account via CLI:
```bash
python api/setup_teacher.py --username prof_smith --password SecurePassword123! --name "Prof. Smith" --employee-id EMP042
```

---

## 4. Installation & Setup

### Step 1: Navigate to repository
```bash
cd /Users/roly/Desktop/AttendanceApp
```

### Step 2: Activate virtual environment
```bash
source venv/bin/activate
```

### Step 3: Verify environment & dependencies
```bash
python verify_env.py
```

### Step 4: Run database migrations (non-destructive)
```bash
python database/migrate.py
```

---

## 5. Running the Application

### 1. Launch FastAPI Backend
```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
*API Swagger Documentation:* `http://127.0.0.1:8000/docs`

### 2. Launch Streamlit Multi-Dashboard
```bash
streamlit run dashboard/app.py --server.port 8501
```
*Web Application:* `http://localhost:8501`

---

## 6. Automated Testing & Verification

The project includes 17 test suites covering security, RBAC, computer vision, audio, and database operations.

Execute the Master Test Runner:
```bash
python tests/run_all_tests.py
```

**Scorecard Summary:**
- 17/17 test suites passing (100% success rate in ~46 seconds).
- Full zero-regression verification across all original and RBAC modules.

---

## 7. Documentation Directory

- **[docs/DEMONSTRATION_GUIDE.md](file:///Users/roly/Desktop/AttendanceApp/docs/DEMONSTRATION_GUIDE.md):** Step-by-step evaluation guide and demonstration scripts for faculty demonstration.
- **[docs/RBAC_IMPLEMENTATION_PHASES.md](file:///Users/roly/Desktop/AttendanceApp/docs/RBAC_IMPLEMENTATION_PHASES.md):** Detailed 10-phase engineering tracking record with architecture diagrams and API contracts.

---

## 8. Privacy & Ethical Guardrails

1. **Local Offline Processing:** All facial recognition embeddings, voice features, and telemetry run 100% locally on the host workstation. No student biometric data is transmitted to cloud servers.
2. **Explicit Biometric Consent:** Facial recognition is strictly opt-in. Non-consenting students are assigned temporary anonymous track IDs without automated identity attribution.
3. **Role Isolation:** Strict separation of teacher administrative controls and student private views with full anti-IDOR enforcement.
4. **Behavioral Indicators, Not Diagnoses:** Engagement metrics reflect observable physical geometry (gaze vector, head pose, speech presence), not psychological or emotional diagnoses.
