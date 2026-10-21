"""
dashboard/views/live_monitoring.py
Page 2: Live Classroom Monitoring
Command center for real-time camera perception, lecture lifecycle synchronization,
multimodal attention metrics, and live student attendance tracking.
"""

import time
import textwrap
import streamlit as st
import pandas as pd
from dashboard.components import api_client, ui

API_BASE = api_client.API_BASE


def render():
    ui.render_page_header(
        title="Live Classroom Monitoring",
        description="Real-time multimodal perception feed, active tracking metrics, camera controls, and audio state."
    )

    # Display clean lifecycle notifications if freshly transitioned
    if st.session_state.pop("live_session_started_toast", False):
        st.success("✅ Classroom perception session started successfully!")
    if st.session_state.pop("live_session_ended_toast", False):
        st.success("✅ Classroom lecture finalized! Attendance records saved.")

    health = api_client.get_health() or {}
    curr_session = api_client.get_current_session() or {}
    engagement = api_client.get_engagement_summary() or {}
    is_active = bool(curr_session.get("is_active", False))

    backend_cam_active = health.get("camera_active", True)
    if "camera_enabled" not in st.session_state:
        st.session_state["camera_enabled"] = backend_cam_active

    cam_enabled = st.session_state["camera_enabled"]

    # =========================================================================
    # 1. TOP COCKPIT: Video Stream (Left) & Mutually Exclusive Session Controls (Right)
    # =========================================================================
    col_video, col_session = st.columns([1.55, 1.1])

    # --- LEFT COLUMN: Live Perception Feed ---
    with col_video:
        with st.container(border=True):
            # Header Row
            v_head_l, v_head_r = st.columns([1.3, 0.7])
            with v_head_l:
                cam_status_dot = "🟢" if cam_enabled else "⚪"
                cam_status_text = "Hardware Active" if cam_enabled else "Standby / Paused"
                cam_status_bg = "#dcfce7" if cam_enabled else "#f1f5f9"
                cam_status_color = "#15803d" if cam_enabled else "#64748b"

                cam_header_html = textwrap.dedent(f"""
<div style="display:flex; align-items:center; gap:10px;">
<span style="font-size:1.18rem; font-weight:700; color:#0f172a; font-family:'Outfit', sans-serif;">
📹 Video Stream
</span>
<span style="font-size:0.75rem; font-weight:600; color:{cam_status_color}; background:{cam_status_bg}; padding:3px 9px; border-radius:12px; border:1px solid {cam_status_bg};">
{cam_status_dot} {cam_status_text}
</span>
</div>
""").strip()
                st.markdown(cam_header_html, unsafe_allow_html=True)

            with v_head_r:
                btn_label = "⏸️ Pause Camera" if cam_enabled else "▶️ Resume Camera"
                if st.button(btn_label, key="toggle_cam_top_btn", use_container_width=True):
                    new_state = not cam_enabled
                    st.session_state["camera_enabled"] = new_state
                    api_client.toggle_camera(new_state)
                    time.sleep(0.2)
                    st.rerun()

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # Camera View Area
            if cam_enabled:
                token = api_client.get_stored_token()
                video_url = f"{API_BASE}/api/video/feed?token={token}" if token else f"{API_BASE}/api/video/feed"
                stream_html = textwrap.dedent(f"""
<div style="background: #0f172a; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.2); position: relative; min-height: 380px; display: flex; align-items: center; justify-content: center;">
<img src="{video_url}" width="100%" style="display: block; border-radius: 12px; max-height: 400px; object-fit: contain;" onerror="this.onerror=null; this.src='https://placehold.co/640x380/0f172a/94a3b8?text=Connecting+to+Classroom+Camera+Stream...';"/>
</div>
""").strip()
                st.markdown(stream_html, unsafe_allow_html=True)
            else:
                standby_html = textwrap.dedent("""
<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; height: 380px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #94a3b8; text-align: center; padding: 30px;">
<div style="width: 72px; height: 72px; border-radius: 50%; background: #1e293b; display: flex; align-items: center; justify-content: center; font-size: 2.2rem; margin-bottom: 14px; box-shadow: 0 0 20px rgba(0,0,0,0.3);">
📷
</div>
<div style="font-weight: 700; font-size: 1.25rem; color: #f8fafc; font-family: 'Outfit', sans-serif;">
Camera Feed on Standby
</div>
<div style="font-size: 0.88rem; margin-top: 8px; max-width: 400px; color: #94a3b8; line-height: 1.5;">
Webcam hardware capture has been temporarily released. Flip the toggle above or click below to resume live visual perception.
</div>
</div>
""").strip()
                st.markdown(standby_html, unsafe_allow_html=True)
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("▶️ Turn On Camera Hardware", key="turn_on_cam_inside", type="primary", use_container_width=True):
                    st.session_state["camera_enabled"] = True
                    api_client.toggle_camera(True)
                    time.sleep(0.2)
                    st.rerun()

            # Footer Metadata Row
            footer_html = textwrap.dedent("""
<div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 0.78rem; color: #64748b; padding: 4px 6px; border-top: 1px solid #f1f5f9;">
<span>● <b>Overlays:</b> 3D Head Pose, Attentiveness %, Tracking IDs</span>
<span>● <b>Privacy:</b> Unenrolled faces stay anonymous</span>
</div>
""").strip()
            st.markdown(footer_html, unsafe_allow_html=True)

    # --- RIGHT COLUMN: Mutually Exclusive Session Lifecycle Cockpit ---
    with col_session:
        with st.container(border=True):
            ctrl_title_html = textwrap.dedent("""
<div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
<span style="font-size:1.18rem; font-weight:700; color:#0f172a; font-family:'Outfit', sans-serif;">
🎙️ Session Controls
</span>
</div>
""").strip()
            st.markdown(ctrl_title_html, unsafe_allow_html=True)

            # --- CASE 1: ACTIVE SESSION RUNNING ---
            if is_active:
                elapsed = curr_session.get("elapsed_seconds", 0.0)
                mins, secs = divmod(int(elapsed), 60)
                course_code = curr_session.get("course_code", "CS101")
                sess_title = curr_session.get("title", "Active Lecture")
                sess_id = curr_session.get("session_id", "LIVE")

                active_box_html = textwrap.dedent(f"""
<div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border: 1px solid #bfdbfe; border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.06);">
<div style="display: flex; justify-content: space-between; align-items: center;">
<span style="background: #2563eb; color: white; padding: 3px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: inline-flex; align-items: center; gap: 5px;">
<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#86efac;"></span> Live Session Active
</span>
<span style="font-size: 0.85rem; color: #1e40af; font-weight: 700;">{course_code}</span>
</div>
<div style="font-size: 1.2rem; font-weight: 700; color: #0f172a; margin-top: 10px; font-family: 'Outfit', sans-serif;">
{sess_title}
</div>
<div style="font-size: 0.78rem; color: #475569; margin-top: 2px;">
Session ID: <code style="background:#e0e7ff; color:#3730a3; padding:1px 5px; border-radius:4px;">{sess_id}</code>
</div>
<div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #bfdbfe; display: flex; justify-content: space-between; align-items: baseline;">
<span style="font-size: 0.85rem; font-weight: 600; color: #334155;">Elapsed Duration:</span>
<span style="font-family: 'Outfit', sans-serif; font-size: 2.1rem; font-weight: 700; color: #1d4ed8; letter-spacing: -0.02em;">
{mins:02d}:{secs:02d}
</span>
</div>
</div>
""").strip()
                st.markdown(active_box_html, unsafe_allow_html=True)

                st.markdown("<p style='font-size:0.82rem; color:#64748b; margin-bottom:12px;'>Student presence and continuous gaze metrics are actively being recorded and aggregated.</p>", unsafe_allow_html=True)

                if st.button("⏹️ Finalize & End Session", key="stop_active_sess_btn", type="primary", use_container_width=True):
                    with st.spinner("Finalizing student attendance records and committing to SQLite database..."):
                        res = api_client.stop_session()
                    if res and res.get("success"):
                        st.session_state["live_session_ended_toast"] = True
                        st.rerun()
                    else:
                        st.error("Failed to finalize session. Please retry.")

            # --- CASE 2: SESSION IDLE (LAUNCH FORM) ---
            else:
                st.markdown("<p style='font-size:0.85rem; color:#64748b; margin-bottom:12px;'>Select a scheduled class or enter course details to initiate multimodal perception.</p>", unsafe_allow_html=True)

                # Fetch teacher's scheduled lectures for 1-click launch
                lectures_resp = api_client.get_teacher_lectures()
                lectures = lectures_resp.get("lectures", []) if lectures_resp else []
                pending_lectures = [l for l in lectures if l.get("status") != "COMPLETED"]

                sched_options = ["Custom Lecture"] + [f"{l['lecture_id']} — {l['title']} ({l['course_code']})" for l in pending_lectures]
                selected_lecture_opt = st.selectbox("Select Scheduled Class", options=sched_options, key="quick_lec_select")

                default_title = "Introduction to Algorithms"
                default_course = "CS101"
                selected_lid = None

                if selected_lecture_opt != "Custom Lecture":
                    selected_lid = selected_lecture_opt.split(" — ")[0].strip()
                    matching = next((l for l in lectures if l["lecture_id"] == selected_lid), None)
                    if matching:
                        default_title = matching.get("title", default_title)
                        default_course = matching.get("course_code", default_course)

                s_title = st.text_input("Lecture Title *", value=default_title, key="start_title_input")
                c_code_col, c_id_col = st.columns([1, 1])
                with c_code_col:
                    s_code = st.text_input("Course Code *", value=default_course, key="start_code_input")
                with c_id_col:
                    s_id = st.text_input("Session ID (Optional)", placeholder="Leave blank for auto-ID", key="start_id_input")

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

                if st.button("▶️ Start Session", key="launch_new_sess_btn", type="primary", use_container_width=True):
                    if not s_title.strip() or not s_code.strip():
                        st.error("Lecture Title and Course Code are required.")
                    else:
                        with st.spinner("Initializing classroom perception session..."):
                            res = api_client.start_session(
                                title=s_title.strip(),
                                course_code=s_code.strip(),
                                session_id=s_id.strip() if s_id.strip() else None,
                                lecture_id=selected_lid
                            )
                        if res and res.get("success"):
                            st.session_state["live_session_started_toast"] = True
                            st.rerun()
                        else:
                            st.error(res.get("detail", "Failed to start session. Ensure the backend is running."))

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # 2. REAL-TIME MULTIMODAL TELEMETRY CARDS
    # =========================================================================
    active_faces = engagement.get("active_student_count", 0) if engagement else 0
    tiers = engagement.get("tier_counts", {}) if engagement else {}
    avg_eng = engagement.get("average_engagement_score", 0.0) if engagement else 0.0
    audio_ctx = engagement.get("audio_context", "QUIET") if engagement else "QUIET"

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(textwrap.dedent(f"""
<div class="stat-card">
<div class="stat-card-title">Faces in Scene</div>
<div class="stat-card-value" style="color: #2563eb;">{active_faces}</div>
<div class="stat-card-sub">Active DeepSort tracks</div>
</div>
""").strip(), unsafe_allow_html=True)

    with k2:
        eng_pct = round(avg_eng * 100.0, 1)
        eng_color = "#059669" if eng_pct >= 70.0 else ("#d97706" if eng_pct >= 40.0 else "#dc2626")
        st.markdown(textwrap.dedent(f"""
<div class="stat-card">
<div class="stat-card-title">Mean Engagement</div>
<div class="stat-card-value" style="color: {eng_color};">{eng_pct}%</div>
<div class="stat-card-sub">Multimodal attention index</div>
</div>
""").strip(), unsafe_allow_html=True)

    with k3:
        tier_str = f"🟢 {tiers.get('HIGH', 0)} &nbsp; 🟡 {tiers.get('MEDIUM', 0)} &nbsp; 🔴 {tiers.get('LOW', 0)}"
        st.markdown(textwrap.dedent(f"""
<div class="stat-card">
<div class="stat-card-title">Attention Breakdown</div>
<div class="stat-card-value" style="font-size: 1.3rem; padding-top: 6px;">{tier_str}</div>
<div class="stat-card-sub">High / Medium / Low tiers</div>
</div>
""").strip(), unsafe_allow_html=True)

    with k4:
        ctx_color = "#059669" if audio_ctx in ("SPEECH", "ACTIVE") else ("#dc2626" if audio_ctx == "DISTURBANCE" else "#64748b")
        st.markdown(textwrap.dedent(f"""
<div class="stat-card">
<div class="stat-card-title">Acoustic Context</div>
<div class="stat-card-value" style="font-size: 1.4rem; color: {ctx_color};">{audio_ctx}</div>
<div class="stat-card-sub">VAD & noise classifier</div>
</div>
""").strip(), unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # 3. INTERACTIVE SECTION: Live Attendance Roster & Pipeline Diagnostics
    # =========================================================================
    tab_roster, tab_diagnostics = st.tabs([
        "👥 Live Detected Attendance Roster",
        "⚙️ AI Perception Pipeline Diagnostics"
    ])

    with tab_roster:
        with st.container(border=True):
            live_att_resp = api_client.get_live_attendance()
            records = live_att_resp.get("records", []) if live_att_resp else []

            enrolled_records = [r for r in records if r.get("is_enrolled")]
            unenrolled_records = [r for r in records if not r.get("is_enrolled")]

            # Attendance KPI breakdown strictly reflects registered course students
            p_cnt = sum(1 for r in enrolled_records if r.get("status") == "PRESENT")
            part_cnt = sum(1 for r in enrolled_records if r.get("status") == "PARTIAL")
            abs_cnt = sum(1 for r in enrolled_records if r.get("status") == "ABSENT")
            tot_cnt = len(enrolled_records)

            # Prominent Attendance Breakdown Row (Enrolled Roster, Present, Partial, Absent)
            r_c1, r_c2, r_c3, r_c4 = st.columns(4)
            with r_c1:
                st.markdown(f"""
                <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:0.75rem; color:#1e40af; font-weight:700; text-transform:uppercase;">👥 Enrolled Roster</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#1d4ed8; margin-top:2px;">{tot_cnt}</div>
                </div>
                """, unsafe_allow_html=True)
            with r_c2:
                st.markdown(f"""
                <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:0.75rem; color:#065f46; font-weight:700; text-transform:uppercase;">🟢 Present Students</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#059669; margin-top:2px;">{p_cnt}</div>
                </div>
                """, unsafe_allow_html=True)
            with r_c3:
                st.markdown(f"""
                <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:0.75rem; color:#92400e; font-weight:700; text-transform:uppercase;">🟡 Partial Presence</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#d97706; margin-top:2px;">{part_cnt}</div>
                </div>
                """, unsafe_allow_html=True)
            with r_c4:
                st.markdown(f"""
                <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:0.75rem; color:#991b1b; font-weight:700; text-transform:uppercase;">🔴 Absent Students</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#dc2626; margin-top:2px;">{abs_cnt}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # Official Enrolled Course Student Attendance Table
            if enrolled_records:
                df_data = []
                for r in enrolled_records:
                    st_val = r.get("status", "ABSENT")
                    badge_icon = "🟢 " if st_val == "PRESENT" else ("🟡 " if st_val == "PARTIAL" else "🔴 ")
                    df_data.append({
                        "Student ID": r.get("student_id", "—"),
                        "Student Name": r.get("student_name", "Unknown"),
                        "Course Enrollment": "✅ Enrolled",
                        "Time Present (s)": r.get("total_seconds_present", 0.0),
                        "Presence Ratio": f"{r.get('presence_pct', 0.0)}%",
                        "Mean Engagement": f"{round(r.get('mean_engagement', 0.0) * 100, 1)}%",
                        "Live Status": f"{badge_icon}{st_val}"
                    })
                df_live = pd.DataFrame(df_data)
                st.dataframe(df_live, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ No enrolled students detected yet. Only students enrolled in this course are tracked in the official attendance roster.")

            # Diagnostic View for Anonymous / Unidentified Faces in Scene
            if unenrolled_records:
                with st.expander(f"👁️ Anonymous / Unidentified Camera Faces in Scene ({len(unenrolled_records)})", expanded=False):
                    df_un_data = []
                    for r in unenrolled_records:
                        df_un_data.append({
                            "Track ID": r.get("student_key", "—"),
                            "Observation Label": r.get("student_name", "Unknown"),
                            "Enrollment": "Unregistered / Room Visitor",
                            "Duration in Scene (s)": r.get("total_seconds_present", 0.0),
                            "Attentiveness": f"{round(r.get('mean_engagement', 0.0) * 100, 1)}%",
                            "Status": "⚪ UNENROLLED"
                        })
                    st.dataframe(pd.DataFrame(df_un_data), use_container_width=True, hide_index=True)

    with tab_diagnostics:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            with st.container(border=True):
                st.markdown("<h4 style='margin-top:0;'>👁️ Visual Perception Pipeline</h4>", unsafe_allow_html=True)
                diag_p1_html = textwrap.dedent("""
<div style="font-size: 0.86rem; line-height: 1.9; color: #475569;">
● <b>Face Detection:</b> OpenCV Haar Cascades + MediaPipe FaceMesh (478 3D landmarks)<br>
● <b>Identity Tracking:</b> DeepSort with Kalman Filtering & persistent track assignments<br>
● <b>Gaze & Orientation:</b> solvePnP 3D perspective projection for Head Pose (Pitch/Yaw/Roll)<br>
● <b>Biometric Verification:</b> Offline FaceNet cosine distance comparison against enrolled embeddings
</div>
""").strip()
                st.markdown(diag_p1_html, unsafe_allow_html=True)

        with col_p2:
            with st.container(border=True):
                st.markdown("<h4 style='margin-top:0;'>🎙️ Acoustic & Multimodal Engine</h4>", unsafe_allow_html=True)
                diag_p2_html = textwrap.dedent("""
<div style="font-size: 0.86rem; line-height: 1.9; color: #475569;">
● <b>Voice Activity Detection (VAD):</b> Energy-based VAD with adaptive spectral noise floor<br>
● <b>Feature Extraction:</b> Librosa acoustic feature extraction (RMS, MFCC, Zero-Crossing Rate)<br>
● <b>Temporal Fusion:</b> Multimodal feature alignment matching visual tracking with audio context<br>
● <b>Qualification Thresholds:</b> Continuous presence calculation (≥ 75% Present, 40-74% Partial)
</div>
""").strip()
                st.markdown(diag_p2_html, unsafe_allow_html=True)
