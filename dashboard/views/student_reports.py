"""
dashboard/pages/student_reports.py
Page 6: Student Session Reports — Authorized session summaries and individual attendance records from SQLite.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Student Session Reports",
        description="Historical lecture attendance records, individual presence breakdowns, and session archives."
    )

    sessions_resp = api_client.get_all_sessions(limit=50)
    sessions_list = sessions_resp.get("sessions", []) if sessions_resp else []

    if not sessions_list:
        st.info("ℹ️ No recorded sessions found in SQLite database yet. Complete your first lecture session to see historical reports.")
        return

    # Session Selector Dropdown
    with st.container(border=True):
        st.markdown("<h3 style='margin-top:0;'>🔍 Select Recorded Lecture Session</h3>", unsafe_allow_html=True)

        session_map = {
            f"{s.get('title', 'Lecture')} ({s.get('course_code')}) — {s.get('session_id')} [{s.get('start_time', '')[:16]}]": s.get("session_id")
            for s in sessions_list
        }
        selected_label = st.selectbox("Choose Session to Inspect", list(session_map.keys()))
        selected_id = session_map.get(selected_label)

    if not selected_id:
        return

    # Fetch Session Attendance and Details
    att_resp = api_client.get_session_attendance(selected_id)
    records = att_resp.get("records", []) if att_resp else []

    # Session Meta KPI Row
    sel_meta = next((s for s in sessions_list if s.get("session_id") == selected_id), {})
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Course Code</div>
            <div class="stat-card-value" style="font-size:1.6rem; color:#4f46e5;">{sel_meta.get('course_code', 'CS101')}</div>
            <div class="stat-card-sub">{sel_meta.get('title', 'Lecture')}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Total Records</div>
            <div class="stat-card-value">{len(records)}</div>
            <div class="stat-card-sub">Students registered</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        p_count = sum(1 for r in records if r.get("status") == "PRESENT")
        rate = round((p_count / len(records) * 100), 1) if records else 0.0
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Verified Attendance</div>
            <div class="stat-card-value" style="color:#059669;">{rate}%</div>
            <div class="stat-card-sub">{p_count} present of {len(records)}</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        is_act = sel_meta.get("is_active", False)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Session State</div>
            <div class="stat-card-value" style="font-size:1.6rem; color:{'#2563eb' if is_act else '#64748b'};">
                {'Active' if is_act else 'Finalized'}
            </div>
            <div class="stat-card-sub">Stored in SQLite</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Individual Student Records Table
    with st.container(border=True):
        st.markdown(f"<h3 style='margin-top:0;'>👥 Individual Attendance Records: {selected_id}</h3>", unsafe_allow_html=True)

        headers = ["Student Name", "Student ID", "Track ID", "Presence Duration", "Presence Ratio", "Status", "Mean Engagement", "Recorded At"]
        table_rows = []
        for r in records:
            status = r.get("status", "ABSENT")
            badge_class = f"badge-{status.lower()}"
            badge_html = f'<span class="badge {badge_class}">{status}</span>'

            table_rows.append([
                f"<b>{r.get('student_name', 'Student')}</b>",
                f"<code>{r.get('student_id') or 'Unenrolled'}</code>",
                r.get("track_id", ""),
                f"{round(r.get('time_present_sec', 0.0), 1)}s",
                f"<b>{round(r.get('presence_ratio', 0.0) * 100, 1)}%</b>",
                badge_html,
                f"{round(r.get('mean_engagement', 0.0) * 100, 1)}%",
                r.get("created_at", "")[:19]
            ])

        ui.render_html_table(headers, table_rows, empty_message=f"No individual attendance rows found for {selected_id}.")

    # Session Recommendations History
    rec_resp = api_client.get_session_recommendations(selected_id)
    recs = rec_resp.get("recommendations", []) if rec_resp else []
    if recs:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>💡 AI Pedagogical Alerts Logged for this Session</h3>", unsafe_allow_html=True)

            rec_headers = ["Priority", "Rule Trigger", "Teaching Suggestion", "Timestamp"]
            rec_rows = []
            for r in recs:
                prio = r.get("priority", "INFO")
                p_badge = f'<span class="badge badge-{prio.lower()}">{prio}</span>'
                rec_rows.append([
                    p_badge,
                    f"<code>{r.get('trigger_type')}</code>",
                    r.get("suggestion_text"),
                    r.get("created_at", "")[:19]
                ])
            ui.render_html_table(rec_headers, rec_rows)
