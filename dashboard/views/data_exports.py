"""
dashboard/views/data_exports.py
Teacher View: Data Management & Exports
Provides session attendance CSV exports, database diagnostics, biometric roster,
and security audit logs for administrative oversight.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Data Management & Audit Logs",
        description="Attendance reports, CSV downloads, SQLite database health, biometric registry, and security audit trail."
    )

    stats = api_client.get_system_stats()
    curr_session = api_client.get_current_session()
    counts = stats.get("counts", {}) if stats else {}
    db_size = stats.get("database_size_kb", 0.0) if stats else 0.0

    # Top Database Diagnostics KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Database Storage</div>
            <div class="stat-card-value">{db_size} KB</div>
            <div class="stat-card-sub">SQLite (attendance.db)</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Sessions Logged</div>
            <div class="stat-card-value">{counts.get('sessions', 0)}</div>
            <div class="stat-card-sub">Lecture archives</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Attendance Records</div>
            <div class="stat-card-value">{counts.get('attendance_records', 0)}</div>
            <div class="stat-card-sub">Student session records</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">AI Insights Logged</div>
            <div class="stat-card-value">{counts.get('recommendations', 0)}</div>
            <div class="stat-card-sub">Pedagogical suggestions</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    tab_export, tab_audit = st.tabs(["📥 Attendance CSV Export", "🛡️ Administrative Audit Trail"])

    with tab_export:
        # Export Center Card
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>📥 Attendance Export Center</h3>", unsafe_allow_html=True)

            e_col1, e_col2 = st.columns([1.5, 1])
            with e_col1:
                st.markdown("#### Export Current / Active Session")
                sess_name = curr_session.get("session_id", "current") if curr_session else "current"
                token = st.session_state.get("auth_token", "")
                csv_url = f"{api_client.API_BASE}/api/attendance/export?token={token}"
                st.markdown(f"""
                Download the verified student presence table and engagement metrics for session <code>{sess_name}</code> as a standard CSV spreadsheet.
                """)
                import pandas as pd
                live_att = api_client.get_live_attendance()
                records = live_att.get("records", []) if live_att else []
                export_rows = [
                    {
                        "student_id": r.get("student_id") or "Unenrolled",
                        "student_name": r.get("student_name", "Student"),
                        "track_id": r.get("student_key", r.get("track_id", "")),
                        "presence_duration_sec": round(r.get("total_seconds_present", r.get("time_present_sec", 0.0)), 1),
                        "presence_ratio_pct": round(r.get("presence_ratio", 0.0) * 100, 1),
                        "status": r.get("status", "ABSENT"),
                        "mean_engagement_pct": round(r.get("mean_engagement", 0.0) * 100, 1)
                    }
                    for r in records
                ]
                df_export = pd.DataFrame(export_rows) if export_rows else pd.DataFrame(columns=[
                    "student_id", "student_name", "track_id", "presence_duration_sec", "presence_ratio_pct", "status", "mean_engagement_pct"
                ])
                csv_bytes = df_export.to_csv(index=False).encode("utf-8")

                st.download_button(
                    label="📥 Download Active Session CSV",
                    data=csv_bytes,
                    file_name=f"attendance_{sess_name}.csv",
                    mime="text/csv",
                    type="primary",
                    key="data_exports_download_btn"
                )

            with e_col2:
                st.markdown("#### Export Format Specifications")
                st.markdown("""
                - **Fields Included:** Student ID, Name, Track ID, Present Duration (sec), Presence Ratio %, Verification Status, Mean Engagement.
                - **Compatibility:** Microsoft Excel, Google Sheets, Pandas, SIS/LMS formats.
                """)

    with tab_audit:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>🛡️ Immutable Audit Logs</h3>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:0.85rem; color:#64748b;'>Chronological audit log of teacher actions: manual attendance corrections, student enrollments, camera toggles, and session operations.</p>", unsafe_allow_html=True)

            audit_resp = api_client.get_audit_logs(limit=50)
            logs = audit_resp.get("audit_logs", []) if audit_resp else []

            if not logs:
                st.info("No audit logs recorded yet in the system.")
            else:
                headers = ["Timestamp", "User / Teacher", "Action", "Entity", "IP Address", "Details"]
                rows = []
                for l in logs:
                    ts = l.get("created_at", "")[:19]
                    rows.append([
                        f"<code>{ts}</code>",
                        f"<b>{l.get('username', 'system')}</b>",
                        f"<code>{l.get('action')}</code>",
                        f"{l.get('entity_type', '')} #{l.get('entity_id', '')}",
                        l.get("ip_address") or "local",
                        l.get("details") or "—"
                    ])
                ui.render_html_table(headers, rows)
