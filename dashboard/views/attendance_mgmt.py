"""
dashboard/views/attendance_mgmt.py
Page 3: Attendance Management
Real-time attendance roster, automated presence thresholds, manual status overrides,
and instantaneous CSV report exports.
"""

import time
import textwrap
import streamlit as st
import pandas as pd
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Attendance Management & Verification",
        description="Real-time attendance roster, automated presence thresholds, manual status overrides, and CSV reports."
    )

    # Toast notifications
    if "override_success_msg" in st.session_state:
        st.success(st.session_state.pop("override_success_msg"))

    attendance = api_client.get_live_attendance()
    curr_session = api_client.get_current_session() or {}
    is_active = curr_session.get("is_active", False)
    records = attendance.get("records", []) if attendance else []
    sess_id = curr_session.get("session_id", "current")

    # KPI Summary Row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div class="stat-card-title">Total Observed</div>
            <div class="stat-card-value">{len(records)}</div>
            <div class="stat-card-sub">Students tracked</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    with k2:
        present_count = sum(1 for r in records if r.get("status") == "PRESENT")
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div class="stat-card-title">Present Students</div>
            <div class="stat-card-value" style="color: #059669;">{present_count}</div>
            <div class="stat-card-sub">Verified Present ($\ge 75\%$)</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    with k3:
        partial_count = sum(1 for r in records if r.get("status") == "PARTIAL")
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div class="stat-card-title">Partial Presence</div>
            <div class="stat-card-value" style="color: #d97706;">{partial_count}</div>
            <div class="stat-card-sub">Partial Present ($40\%-74\%$)</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    with k4:
        absent_count = sum(1 for r in records if r.get("status") == "ABSENT")
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div class="stat-card-title">Absent Students</div>
            <div class="stat-card-value" style="color: #e11d48;">{absent_count}</div>
            <div class="stat-card-sub">Absent / Low ($< 40\%$)</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Attendance Table Card
    with st.container(border=True):
        header_col, export_col = st.columns([2.5, 1.5])
        with header_col:
            st.markdown("<h3 style='margin:0;'>📋 Attendance Roster</h3>", unsafe_allow_html=True)
            if is_active:
                st.markdown(f"<span style='font-size:0.8rem; color:#2563eb;'>● Live Session Active: <b>{curr_session.get('title', 'Lecture')} ({curr_session.get('course_code', 'CS101')})</b></span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='font-size:0.8rem; color:#64748b;'>○ Session Idle</span>", unsafe_allow_html=True)

        with export_col:
            # Build CSV Data in-memory for instant, bulletproof download
            export_rows = []
            for r in records:
                export_rows.append({
                    "student_id": r.get("student_id") or "Unenrolled",
                    "student_name": r.get("student_name", "Student"),
                    "track_id": r.get("student_key", r.get("track_id", "")),
                    "presence_duration_sec": round(r.get("total_seconds_present", r.get("time_present_sec", 0.0)), 1),
                    "presence_ratio_pct": round(r.get("presence_ratio", 0.0) * 100, 1),
                    "status": r.get("status", "ABSENT"),
                    "mean_engagement_pct": round(r.get("mean_engagement", 0.0) * 100, 1)
                })

            df_export = pd.DataFrame(export_rows) if export_rows else pd.DataFrame(columns=[
                "student_id", "student_name", "track_id", "presence_duration_sec", "presence_ratio_pct", "status", "mean_engagement_pct"
            ])
            csv_bytes = df_export.to_csv(index=False).encode("utf-8")
            file_name = f"attendance_{sess_id}.csv"

            st.download_button(
                label="📥 Export Attendance CSV",
                data=csv_bytes,
                file_name=file_name,
                mime="text/csv",
                type="primary",
                use_container_width=True,
                key="download_attendance_csv_btn"
            )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Filter Controls
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            status_filter = st.selectbox("Filter Status", ["ALL", "PRESENT", "PARTIAL", "ABSENT"], key="att_filter_status")
        with f_col2:
            search_query = st.text_input("Search student name or ID", placeholder="Filter by name or ID...", key="att_search_query")

        # Filter records
        filtered_records = records
        if status_filter != "ALL":
            filtered_records = [r for r in filtered_records if r.get("status") == status_filter]
        if search_query.strip():
            q = search_query.strip().lower()
            filtered_records = [
                r for r in filtered_records
                if q in r.get("student_name", "").lower() or q in str(r.get("student_id", "")).lower()
            ]

        # Format Rows for Table
        headers = ["Student Name", "Student ID", "Track ID", "Presence Duration", "Presence Ratio", "Status", "Avg Engagement"]
        table_rows = []
        for r in filtered_records:
            st_val = r.get("status", "ABSENT")
            badge_class = f"badge-{st_val.lower()}"
            override_tag = " ✏️" if r.get("manual_override") else ""
            badge_html = f'<span class="badge {badge_class}">{st_val}{override_tag}</span>'

            table_rows.append([
                f"<b>{r.get('student_name', 'Student')}</b>",
                f"<code>{r.get('student_id') or 'Unenrolled'}</code>",
                r.get("student_key", r.get("track_id", "")),
                f"{round(r.get('total_seconds_present', r.get('time_present_sec', 0.0)), 1)}s",
                f"<b>{round(r.get('presence_ratio', 0.0) * 100, 1)}%</b>",
                badge_html,
                f"{round(r.get('mean_engagement', 0.0) * 100, 1)}%"
            ])

        ui.render_html_table(headers, table_rows, empty_message="No matching student records found in current session.")

    # Manual Status Override Card
    override_container = st.container(border=True)
    with override_container:
        st.markdown("<h3 style='margin-top:0;'>✏️ Manual Attendance Status Override</h3>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.88rem; color: #64748b;'>Override an automated presence verdict (e.g. excuse an absence, verify an excused student). Updates both live session and database audit logs permanently.</p>", unsafe_allow_html=True)

        if not records:
            st.info("Manual overrides will be enabled once students are observed or checked in to a session.")
        else:
            with st.form("manual_override_form", clear_on_submit=False):
                c_st, c_status, c_reason = st.columns([1.5, 1.2, 1.5])
                
                # Select student
                student_options = {
                    f"{r.get('student_name', 'Student')} ({r.get('student_key')})": r.get("student_key")
                    for r in records
                }
                with c_st:
                    selected_label = st.selectbox("Select Student", list(student_options.keys()), key="override_select_student")
                    target_key = student_options.get(selected_label)
                with c_status:
                    new_status = st.selectbox("New Verification Status", ["PRESENT", "PARTIAL", "ABSENT"], key="override_select_status")
                with c_reason:
                    override_reason = st.text_input("Override Reason (Audit)", value="Instructor visual confirmation", key="override_input_reason")

                apply_btn = st.form_submit_button("Apply Correction", type="primary", use_container_width=True)

                if apply_btn and target_key:
                    res = api_client.correct_attendance(session_id=sess_id, student_key=target_key, status=new_status)
                    if res and res.get("success"):
                        st.session_state["override_success_msg"] = f"✅ Successfully updated status for {selected_label} to {new_status}!"
                        st.rerun()
                    else:
                        st.error("Failed to apply manual correction. Please check backend connection.")
