# Demonstration & Evaluation Guide
## Multimodal Attendance & Engagement Agent (RBAC & Multi-Dashboard Edition)

**Project:** Multimodal Attendance & Engagement Agent  
**Developer:** Nirbhay Dubey — B.Tech Computer Science & Engineering (Year 1)  
**System Architecture:** Offline-First AI Perception, FastAPI Backend, SQLite RBAC Models, Streamlit Dual-Role Dashboard  
**Authentication Standard:** PBKDF2-HMAC-SHA256 (600,000 iterations, 32-byte cryptographic salt)  
**Security Boundary:** Server-Side Role-Based Access Control (RBAC) & Anti-Insecure Direct Object Reference (IDOR)  

---

## 1. Quick Demonstration Credentials

| Role | Username / Identifier | Default Password | Primary Dashboard Capabilities |
|---|---|---|---|
| **Teacher / Faculty** | `teacher` | `TeacherPassword123!` | Lecture Scheduling, Camera Stream, Live Session Cockpit, Manual Overrides, Biometric Enrollment, Audit Logs |
| **Student (Permanent)** | `STU-2026-0001` | `DavidPermanentPass123!` | Real-Time Live Lecture Sync, Private Attendance History, Enrolled Courses, Password Management |
| **Student (Activation)** | `STU-2026-0002` | `StudentTempPass123!` | Tests first-time login workflow and mandatory password change alert |

---

## 2. Launching the Application Services

Open two terminal tabs from `/Users/roly/Desktop/AttendanceApp`:

### Terminal 1: FastAPI Backend
```bash
source venv/bin/activate
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health Check URL:* `http://127.0.0.1:8000/health`  
*API Documentation (Swagger UI):* `http://127.0.0.1:8000/docs`

### Terminal 2: Streamlit Frontend
```bash
source venv/bin/activate
streamlit run dashboard/app.py --server.port 8501
```
*Frontend URL:* `http://localhost:8501`

---

## 3. Demonstration Script for Faculty Evaluation

### Scenario A: Teacher Workflow — Course, Lecture & Session Management

1. **Sign In as Teacher:**
   - Open `http://localhost:8501`.
   - The unauthenticated login gate will appear.
   - Enter `teacher` and `TeacherPassword123!`. Click **Sign In**.
   - Notice the teacher profile card appears in the sidebar displaying **Prof. Nirbhay Dubey** (`EMP001`), `TEACHER` badge, and full academic navigation.

2. **Schedule an Academic Lecture:**
   - Click **📚 Lecture & Course Management** from the sidebar menu.
   - In the **Schedule New Lecture** form:
     - Select Course: `CS101` (or register a new course in the **Course Catalog** tab).
     - Title: `Lecture 6: Deep Convolutional Networks`.
     - Topic: `Feature Maps & Pooling Layers`.
     - Duration: `60` minutes.
     - Click **📅 Schedule Lecture**.
   - Observe the lecture appears in the **Scheduled & Historical Lectures** list with `SCHEDULED` status badge.

3. **Launch the Live Lecture Session:**
   - Click **▶️ Launch Live Session** next to the lecture you scheduled.
   - Notice the session status immediately updates to `LIVE` in the database, and the active session banner displays in the sidebar.

4. **Monitor Live Perception & Video Stream:**
   - Click **📹 Live Monitoring**.
   - The live annotated camera stream appears with token-authenticated security (`/api/video/feed?token=...`).
   - Face bounding boxes, 68-point facial mesh landmarks, head orientation pitch/yaw/roll, and gaze vectors are computed offline in real time.

5. **Course-Restricted Live Roster & Room Track Isolation:**
   - In **📹 Live Monitoring** $\to$ **👥 Live Detected Attendance Roster**:
     - Notice that the roster automatically pre-seeds all registered students for this lecture's course as `🔴 ABSENT` (0.0% presence).
     - As enrolled students are detected by camera or check in online, their presence increments toward qualification.
     - Unidentified faces in the room are strictly categorized as `⚪ UNENROLLED` and isolated to the expandable *Anonymous / Unidentified Camera Faces in Scene* drawer—ensuring transient room tracks **never** register as `PRESENT`.

6. **Verify Presence & Perform Audit-Logged Manual Override:**
   - Click **👥 Attendance Management**.
   - Observe the live attendance roster with computed presence seconds and qualification thresholds ($\ge 75\%$ Present, $40-74\%$ Partial, $<40\%$ Absent).
   - In the **Manual Status Override** card:
     - Select student `STU-2026-0001`.
     - Change status from `ABSENT` to `PRESENT`.
     - Click **Apply Manual Status Correction**.
   - Navigate to **📥 Data & Audit Logs** $\to$ **Administrative Audit Trail**:
     - Point out the immutable audit log recording the override with teacher username, timestamp, and entity ID.

7. **Student Biometric Enrollment & Safe Deregistration:**
   - Click **👤 Student Enrollment & Biometric Roster**:
     - In **➕ Enroll New Student**, notice the clear course assignment picker: **Course to Join / Enroll In * (Kis Course Me Join Karna Hai)**.
     - In **📋 Student Directory & Roster**, expand **🗑️ Deregister / Remove Student from System**: select a student, confirm the checkbox, and click **Delete Student & Revoke Access**. This purges the 512-d facial vector from disk/memory and invalidates the student's login account.

8. **Course Catalog Management & Removal:**
   - Return to **📚 Lecture & Course Management** $\to$ **Course Catalog**:
     - Expand **🗑️ Remove Course from System**, select any obsolete course, confirm the safety check, and delete it with automatic cascade cleanup of scheduled lectures and student enrollment links.

9. **End Lecture Session:**
   - Return to **📚 Lecture & Course Management** (or **Live Monitoring**).
   - Click **⏹️ End Session**.
   - Observe the lecture status cleanly transitions from `LIVE` $\to$ `COMPLETED`.

---

### Scenario B: Student Workflow — Privacy-Isolated Student Portal

1. **Sign Out of Teacher Account:**
   - In the sidebar, click **🚪 Sign Out**.
   - You are immediately redirected back to the secure login gate.

2. **Sign In as Student:**
   - Enter identifier: `STU-2026-0001`.
   - Enter password: `DavidPermanentPass123!`. Click **Sign In**.
   - Point out the interface transformation:
     - All administrative buttons, camera feeds, and teacher menus are removed.
     - Sidebar now displays **Student Account** (`STUDENT` badge).

3. **View Real-Time Live Class Synchronization & Enrollment Gating:**
   - On **📊 My Dashboard & Overview**:
     - If an enrolled lecture is currently active, a pulsing live banner displays `✅ Enrolled` with the class details.
     - Student can click **🚀 Join Live Class (Start Background Attendance)** to accumulate presence while attending class on Zoom, Google Meet, or Microsoft Teams.
     - If the student is **not enrolled** in the active lecture's course, the system displays `❌ Not Enrolled` and blocks the join button:
       > 🚫 **Attendance Restricted:** *You are not enrolled in this course. In accordance with classroom rules, only students enrolled in this course can join and record attendance.*

4. **Inspect Personal Attendance History (Anti-IDOR):**
   - Click **📅 My Attendance History**.
   - Search by Session ID or filter by `PRESENT` / `PARTIAL` / `ABSENT`.
   - Review presence duration in minutes/seconds, presence percentage, and attentiveness scores.
   - *Key Point for Evaluators:* The student can only view their own attendance records.

5. **Student Profile & Self-Service Password Reset:**
   - Click **👤 Profile & Change Password**.
   - Review academic profile credentials and explicit biometric consent status.
   - Update password securely using the form.

---

### Scenario C: Security & Anti-IDOR Verification Proof

To demonstrate backend-enforced security to evaluators:

1. **Attempting Teacher Route as Student:**
   Run this cURL command using a student token:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/camera/toggle \
     -H "Authorization: Bearer <STUDENT_TOKEN>"
   ```
   *Expected Response:*
   ```json
   {"detail": "Forbidden: Teacher access required."}
   ```
   **HTTP Status: 403 Forbidden** (Backend denies access regardless of frontend state).

2. **Attempting to Join Unenrolled Lecture Session (Course Gating Defense):**
   When an unenrolled student attempts to join an active lecture:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/student/sessions/join \
     -H "Authorization: Bearer <UNENROLLED_STUDENT_TOKEN>"
   ```
   *Expected Response:*
   ```json
   {"detail": "Attendance Restricted: You are not enrolled in course 'CS101'. You can only attend and record attendance for courses in which you are enrolled."}
   ```
   **HTTP Status: 403 Forbidden** (Server actively denies unauthorized lecture attendance).

3. **Attempting Cross-Student Query (IDOR Defense):**
   When Student A requests session attendance for Student B:
   ```bash
   curl -s http://127.0.0.1:8000/api/sessions/{SESSION_ID}/attendance?student_id={OTHER_STUDENT_ID} \
     -H "Authorization: Bearer <STUDENT_A_TOKEN>"
   ```
   *Expected Response:*
   ```json
   {"detail": "Access denied: Students are not authorized to view attendance records of other students."}
   ```
   **HTTP Status: 403 Forbidden** (Server actively detects and blocks IDOR tampering).

4. **Attempting Camera Stream without Teacher Authorization:**
   ```bash
   curl -s -I http://127.0.0.1:8000/api/video/feed?token=<STUDENT_TOKEN>
   ```
   *Expected Response:* **HTTP 403 Forbidden**.

---

## 4. Running the Master Test Suite

To prove zero regression across all 17 system components to your faculty, run:

```bash
source venv/bin/activate
python tests/run_all_tests.py
```

*Expected Result:*
- **17/17 test suites PASS** (100.0% success rate in ~46 seconds).
- Full green scorecard covering Auth, RBAC, IDOR Defense, Enrollment Provisioning, Student Dashboard, Lifecycle Sync, MediaPipe FaceLandmarker, FaceNet, Silero VAD, Librosa Audio, and FastAPI endpoints.
