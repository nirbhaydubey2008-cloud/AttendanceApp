"""
dashboard/views/student/attendance.py
Student Portal: Personal Attendance History
Provides filterable personal attendance records, presence metrics,
status breakdowns, and threshold guidance. Anti-IDOR compliant.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="My Attendance History",
        description="Filterable personal record of verified lecture presence, duration, and status qualification."
    )

    att_data = api_client.get_student_my_attendance() or {}
    records = att_data.get("records", [])

    # Summary Stats
    total = len(records)
    present_cnt = sum(1 for r in records if r.get("status") == "PRESENT")
    partial_cnt = sum(1 for r in records if r.get("status") == "PARTIAL")
    absent_cnt = sum(1 for r in records if r.get("status") == "ABSENT")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Total Sessions</div>
            <div class="stat-card-value">{total}</div>
            <div class="stat-card-sub">Recorded lectures</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Verified Present</div>
            <div class="stat-card-value" style="color: #059669;">{present_cnt}</div>
            <div class="stat-card-sub">$\ge 75\%$ Presence ratio</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Partial Presence</div>
            <div class="stat-card-value" style="color: #d97706;">{partial_cnt}</div>
            <div class="stat-card-sub">$40\% - 74\%$ Presence ratio</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Absent / Low</div>
            <div class="stat-card-value" style="color: #dc2626;">{absent_cnt}</div>
            <div class="stat-card-sub">$< 40\%$ Presence ratio</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Search & Filter Controls
    col_search, col_filter, col_refresh = st.columns([2, 1.2, 0.8])
    with col_search:
        search_query = st.text_input("🔍 Search by Session ID", placeholder="Filter by session ID...", key="stu_att_search")
    with col_filter:
        status_filter = st.selectbox("Status Filter", ["All Statuses", "PRESENT", "PARTIAL", "ABSENT"], key="stu_att_filter")
    with col_refresh:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    filtered = records
    if search_query:
        filtered = [r for r in filtered if search_query.lower() in r.get("session_id", "").lower()]
    if status_filter != "All Statuses":
        filtered = [r for r in filtered if r.get("status") == status_filter]

    with st.container(border=True):
        st.markdown("<h3 style='margin-top:0;'>📜 Attendance Records</h3>", unsafe_allow_html=True)

        if not filtered:
            st.info("No attendance records found matching your filters.")
        else:
            headers = ["Session ID", "Presence Duration", "Presence Ratio", "Status", "Attentiveness", "Recorded At"]
            rows = []
            for r in filtered:
                status = r.get("status", "ABSENT")
                badge_class = "badge-present" if status == "PRESENT" else ("badge-partial" if status == "PARTIAL" else "badge-absent")
                dur = r.get("time_present_sec", 0.0)
                mins, secs = divmod(int(dur), 60)
                dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

                eng = r.get("mean_engagement")
                eng_str = f"{eng * 100:.1f}%" if eng is not None else "—"

                rows.append([
                    f"<code>{r.get('session_id')}</code>",
                    dur_str,
                    f"<b>{r.get('presence_pct', 0.0)}%</b>",
                    f'<span class="badge {badge_class}">{status}</span>',
                    eng_str,
                    r.get("created_at", "Recorded")[:16].replace("T", " ")
                ])

            ui.render_html_table(headers, rows)

    # Threshold & Privacy Guide Card
    with st.container(border=True):
        st.markdown("<h4 style='margin-top:0;'>ℹ️ Attendance Qualification Policies & Privacy</h4>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.86rem; color:#475569; line-height:1.7;">
            ● <b>PRESENT:</b> Awarded when visual presence in the classroom camera exceeds <b>75%</b> of the active lecture duration.<br>
            ● <b>PARTIAL:</b> Awarded for presence between <b>40%</b> and <b>74%</b> of the active lecture duration.<br>
            ● <b>ABSENT:</b> Recorded if presence is below <b>40%</b> of the active lecture duration.<br>
            ● <b>Strict Privacy Isolation (Anti-IDOR):</b> As a student, you can only access your own attendance records. You cannot view peers' attendance, and video feeds are restricted to faculty.
        </div>
        """, unsafe_allow_html=True)
