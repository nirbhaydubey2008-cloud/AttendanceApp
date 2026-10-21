"""
dashboard/views/student/overview.py
Student Portal: Overview & Live Status
Displays personal identity, aggregate attendance rate, live lecture status,
and first-login password change notices.
"""

import time
import streamlit as st
from dashboard.components import api_client, ui


def render():
    curr_user = st.session_state.get("current_user") or api_client.get_me()
    s_prof = curr_user.get("student_profile") if curr_user else {}
    student_name = curr_user.get("name") if curr_user else "Student"
    stu_id = curr_user.get("username") if curr_user else "STU-2026-0001"
    roll_no = s_prof.get("roll_no") if s_prof else "—"
    dept = s_prof.get("department") if s_prof else "Computer Science & Engineering"
    must_change = curr_user.get("must_change_password", False) if curr_user else False

    ui.render_page_header(
        title=f"Welcome, {student_name}",
        description=f"Student ID: {stu_id} | Roll No: {roll_no} | Department: {dept}"
    )

    # First-login Temporary Password Warning Banner
    if must_change:
        st.markdown("""
        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:16px 20px; margin-bottom:20px;">
            <div style="font-weight:700; color:#b45309; font-size:1.05rem; display:flex; align-items:center; gap:8px;">
                ⚠️ Action Required: Temporary Password in Use
            </div>
            <div style="font-size:0.88rem; color:#92400e; margin-top:4px;">
                You are currently logged in with a temporary activation password. Please navigate to <b>Profile & Security</b> from the menu to set your permanent private password.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Fetch Attendance Stats & Live Status
    att_data = api_client.get_student_my_attendance() or {}
    total_sess = att_data.get("total_sessions", 0)
    pres_sess = att_data.get("present_sessions", 0)
    overall_pct = att_data.get("overall_attendance_pct", 0.0)

    live_data = api_client.get_student_live_session() or {}
    is_live = live_data.get("is_active", False)
    is_enrolled_in_live = live_data.get("is_enrolled", False)
    my_live_status = live_data.get("my_status", "NO_ACTIVE_SESSION")
    my_presence_pct = live_data.get("my_presence_pct", 0.0)

    # Top KPI Metrics Row
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        pct_color = "#059669" if overall_pct >= 75.0 else ("#d97706" if overall_pct >= 40.0 else "#dc2626")
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Overall Attendance</div>
            <div class="stat-card-value" style="color: {pct_color};">{overall_pct:.1f}%</div>
            <div class="stat-card-sub">Verified lecture presence</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Lectures Attended</div>
            <div class="stat-card-value" style="color: #2563eb;">{pres_sess} / {total_sess}</div>
            <div class="stat-card-sub">Sessions qualified</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        courses_resp = api_client.get_student_courses() or {}
        enrolled_count = courses_resp.get("count", len(courses_resp.get("courses", [])))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Enrolled Courses</div>
            <div class="stat-card-value" style="color: #7c3aed;">{enrolled_count}</div>
            <div class="stat-card-sub">Active curricula</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        live_label = "LIVE NOW" if is_live else "IDLE"
        live_color = "#dc2626" if is_live else "#64748b"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Classroom Status</div>
            <div class="stat-card-value" style="font-size:1.4rem; color: {live_color};">{live_label}</div>
            <div class="stat-card-sub">{'Active perception' if is_live else 'No active class'}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Live Class Notification Card & Background Attendance Cockpit
    if is_live:
        course_c = live_data.get("course_code", "CS101")
        lec_t = live_data.get("title", "Lecture")
        is_joined = bool(live_data.get("is_joined", False))

        if is_joined:
            status_text = "PRESENT" if my_presence_pct >= 75.0 else ("PARTIAL" if my_presence_pct >= 40.0 else "ACTIVE")
            status_color = "#059669" if status_text == "PRESENT" else ("#d97706" if status_text == "PARTIAL" else "#2563eb")
            status_bg = "#ecfdf5" if status_text == "PRESENT" else ("#fffbeb" if status_text == "PARTIAL" else "#eff6ff")
        else:
            status_text = "NOT JOINED"
            status_color = "#dc2626"
            status_bg = "#fef2f2"

        elapsed_sec = int(live_data.get("elapsed_seconds", 0.0))
        el_mins, el_secs = divmod(elapsed_sec, 60)

        import textwrap
        student_banner_html = textwrap.dedent(f"""
<div style="background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%); border: 1.5px solid #93c5fd; border-radius: 14px; padding: 22px 24px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);">
<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
<div>
<span style="background: {'#15803d' if is_joined else '#ef4444'}; color: white; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.04em; display: inline-flex; align-items: center; gap: 6px;">
● {'Background Tracking Active' if is_joined else 'Live Lecture Active'}
</span>
<h2 style="margin: 10px 0 4px 0; color: #1e3a8a; font-family: 'Outfit', sans-serif;">{lec_t} ({course_c})</h2>
<div style="font-size: 0.88rem; color: #475569;">
⏱️ Elapsed Class Time: <b>{el_mins:02d}:{el_secs:02d}</b> &nbsp;|&nbsp; Course Enrollment: <b>{'<span style="color:#166534; font-weight:700;">✅ Enrolled</span>' if is_enrolled_in_live else '<span style="color:#b91c1c; font-weight:700;">❌ Not Enrolled</span>'}</b>
</div>
</div>
<div style="text-align: right; background: {status_bg}; border: 1px solid {status_color}; border-radius: 12px; padding: 12px 18px; min-width: 180px;">
<div style="font-size: 0.78rem; font-weight: 600; color: #64748b; text-transform: uppercase;">Your Live Status</div>
<div style="font-size: 1.5rem; font-weight: 800; color: {status_color}; font-family: 'Outfit', sans-serif; margin-top: 2px;">
{status_text}
</div>
<div style="font-size: 0.85rem; font-weight: 600; color: {status_color};">
{my_presence_pct}% Session Time
</div>
</div>
</div>
<div style="margin-top: 16px;">
<div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: #64748b; margin-bottom: 4px;">
<span>Class Attendance Progress: <b>{my_presence_pct}%</b></span>
<span>Qualification Goal: ≥ 75% for PRESENT</span>
</div>
<div style="background: #e2e8f0; border-radius: 9999px; height: 10px; overflow: hidden;">
<div style="width: {min(max(my_presence_pct, 0.0), 100.0)}%; background: {status_color}; height: 100%; border-radius: 9999px;"></div>
</div>
</div>
<div style="background: #ffffff; border: 1px solid #dbeafe; border-radius: 10px; padding: 12px 16px; margin-top: 16px; font-size: 0.84rem; color: #475569; line-height: 1.5;">
💡 <b>Background Attendance Mode:</b> When attending class on <b>Zoom, Google Meet, or MS Teams</b>, click <b>Join Live Class</b> below. Keep this tab open in the background to automatically accumulate your verified lecture presence and engagement score.
</div>
</div>
""").strip()
        st.markdown(student_banner_html, unsafe_allow_html=True)

        # Interactive Join / Leave Action Controls
        with st.container(border=True):
            if not is_enrolled_in_live:
                st.markdown(f"""
                <div style="background:#fff1f2; border:1px solid #fecdd3; border-radius:10px; padding:14px 18px; display:flex; align-items:center; gap:12px;">
                    <div style="font-size:1.6rem;">🚫</div>
                    <div>
                        <div style="font-weight:700; color:#9f1239; font-size:0.95rem;">
                            Attendance Restricted: You are not enrolled in this course
                        </div>
                        <div style="font-size:0.85rem; color:#be123c; margin-top:2px;">
                            This active lecture is for <b>{course_c}</b>. In accordance with classroom rules, only students enrolled in this course can join and record attendance.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif not is_joined:
                col_btn, col_link = st.columns([1.2, 1.0])
                with col_btn:
                    if st.button("🚀 Join Live Class (Start Background Attendance)", key="stu_join_live_btn", type="primary", use_container_width=True):
                        with st.spinner("Connecting to live lecture attendance session..."):
                            res = api_client.join_live_session()
                        if res and res.get("success"):
                            st.success("✅ Checked in! Background attendance tracking is now active for this lecture.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(res.get("detail", "Failed to join session. Please try again."))
                with col_link:
                    st.markdown("""
                    <div style="padding-top: 6px; font-size: 0.85rem; color: #64748b;">
                        Clicking <b>Join</b> marks you active in the teacher's Live Attendance Roster and starts your presence timer.
                    </div>
                    """, unsafe_allow_html=True)
            else:
                col_status, col_leave = st.columns([1.5, 0.8])
                with col_status:
                    st.markdown("""
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.9rem; color: #15803d; font-weight: 600; padding-top: 8px;">
                        <span>🟢</span> You are checked in. Keep this page open while attending on Zoom / Google Meet.
                    </div>
                    """, unsafe_allow_html=True)
                with col_leave:
                    if st.button("🚪 Leave Class Session", key="stu_leave_live_btn", use_container_width=True):
                        with st.spinner("Disconnecting from class session..."):
                            api_client.leave_live_session()
                        st.info("You have left the active lecture session.")
                        time.sleep(0.5)
                        st.rerun()

    # Recent Attendance Summary Table
    with st.container(border=True):
        st.markdown("<h3 style='margin-top:0;'>📋 Recent Attendance History</h3>", unsafe_allow_html=True)
        records = att_data.get("records", [])

        if not records:
            st.info("No recorded attendance sessions yet. Once your professor conducts a lecture, your verified attendance will appear here.")
        else:
            headers = ["Session ID", "Presence Duration", "Presence Ratio", "Status", "Date"]
            rows = []
            for r in records[:5]:
                status = r.get("status", "ABSENT")
                badge_class = "badge-present" if status == "PRESENT" else ("badge-partial" if status == "PARTIAL" else "badge-absent")
                dur = r.get("time_present_sec", 0.0)
                mins, secs = divmod(int(dur), 60)
                dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

                rows.append([
                    f"<code>{r.get('session_id')}</code>",
                    dur_str,
                    f"<b>{r.get('presence_pct', 0.0)}%</b>",
                    f'<span class="badge {badge_class}">{status}</span>',
                    r.get("created_at", "Recorded")[:10]
                ])

            ui.render_html_table(headers, rows)
