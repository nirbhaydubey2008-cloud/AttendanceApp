"""
dashboard/pages/overview.py
Page 1: Overview — High-level session summary, verified attendance KPIs, duration, and system status.
"""

from datetime import datetime
import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Session Overview",
        description="High-level lecture session summary, verified attendance progress, and operational system health."
    )

    health = api_client.get_health()
    curr_session = api_client.get_current_session()
    attendance = api_client.get_live_attendance()
    engagement = api_client.get_engagement_summary()
    enrolled = api_client.get_enrolled_students()

    is_active = curr_session and curr_session.get("is_active", False)
    records = attendance.get("records", []) if attendance else []
    total_enrolled = enrolled.get("count", 0) if enrolled else 0

    # Top KPI Metrics Row
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Active Session</div>
            <div class="stat-card-value" style="font-size: 1.5rem; color: {'#2563eb' if is_active else '#64748b'};">
                {curr_session.get('course_code', 'None') if is_active else 'Idle'}
            </div>
            <div class="stat-card-sub">{'In Progress' if is_active else 'Ready to launch'}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        verified_count = sum(1 for r in records if r.get("status") == "PRESENT")
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Verified Attendance</div>
            <div class="stat-card-value" style="color: #059669;">{verified_count}</div>
            <div class="stat-card-sub">Students meeting $\ge 75\%$ threshold</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        elapsed = curr_session.get("elapsed_seconds", 0.0) if is_active else 0.0
        mins, secs = divmod(int(elapsed), 60)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Session Duration</div>
            <div class="stat-card-value">{mins:02d}:{secs:02d}</div>
            <div class="stat-card-sub">Active lecture time</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        avg_eng = engagement.get("average_engagement_score", 0.0) if engagement else 0.0
        eng_pct = int(avg_eng * 100)
        eng_color = "#059669" if eng_pct >= 70 else ("#d97706" if eng_pct >= 45 else "#e11d48")
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Avg Engagement</div>
            <div class="stat-card-value" style="color: {eng_color};">{eng_pct}%</div>
            <div class="stat-card-sub">Multimodal attention index</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Detailed Cards (Left: Session Summary, Right: System Diagnostics)
    col_left, col_right = st.columns([1.6, 1.2])

    with col_left:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>📚 Current Lecture Session</h3>", unsafe_allow_html=True)
            if is_active:
                st.markdown(f"""
                <table style="width:100%; font-size: 0.9rem; line-height: 2.0;">
                    <tr><td style="color:#64748b; width: 35%;">Session Title:</td><td><b>{curr_session.get('title', 'Lecture')}</b></td></tr>
                    <tr><td style="color:#64748b;">Course Code:</td><td><code>{curr_session.get('course_code', 'CS101')}</code></td></tr>
                    <tr><td style="color:#64748b;">Session ID:</td><td><code>{curr_session.get('session_id')}</code></td></tr>
                    <tr><td style="color:#64748b;">Status:</td><td><span class="badge badge-present">Active Tracking</span></td></tr>
                    <tr><td style="color:#64748b;">Total Students In Scene:</td><td><b>{len(records)}</b> student(s) observed</td></tr>
                </table>
                """, unsafe_allow_html=True)
            else:
                st.info("No active lecture session running currently.")
                st.markdown("""
                To start a classroom lecture session, navigate to the **Live Monitoring** page and click **▶️ Start Session**.
                All biometric tracking, presence qualification, and engagement scoring will begin automatically.
                """)

        # Recent Pedagogical Suggestions Preview
        recent_recs = api_client.get_recent_recommendations(limit=2)
        recs_list = recent_recs.get("recommendations", []) if recent_recs else []
        if recs_list:
            with st.container(border=True):
                st.markdown("<h4 style='margin-top:0;'>💡 Active AI Teaching Insights</h4>", unsafe_allow_html=True)
                for r in recs_list:
                    prio = r.get("priority", "INFO")
                    p_badge = f"badge-{prio.lower()}"
                    st.markdown(f"""
                    <div style="padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 4px;">
                            <span class="badge {p_badge}">{prio}</span>
                            <span style="font-size: 0.75rem; color: #94a3b8;">Trigger: {r.get('trigger_type')}</span>
                        </div>
                        <div style="font-weight: 600; color: #0f172a;">{r.get('title')}</div>
                        <div style="font-size: 0.85rem; color: #475569;">{r.get('suggestion_text')}</div>
                    </div>
                    """, unsafe_allow_html=True)

    with col_right:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>⚙️ System & Hardware Status</h3>", unsafe_allow_html=True)

            cam_active = health.get("camera_active", False) if health else False
            cam_fallback = health.get("camera_fallback", False) if health else True
            backend_ok = health is not None

            st.markdown(f"""
            <div style="font-size: 0.88rem; line-height: 2.2;">
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">FastAPI Perception Server:</span>
                    <span style="font-weight:600; color: {'#16a34a' if backend_ok else '#dc2626'};">
                        {'● Connected' if backend_ok else '○ Offline'}
                    </span>
                </div>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">Camera Capture Mode:</span>
                    <span style="font-weight:600; color: {'#ea580c' if not cam_active else '#0f172a'};">
                        {'Paused / Disabled' if not cam_active else ('Synthetic Classroom' if cam_fallback else 'Hardware Webcam')}
                    </span>
                </div>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">Enrolled Biometric Profiles:</span>
                    <span style="font-weight:600; color: #0f172a;">{total_enrolled} enrolled student(s)</span>
                </div>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">Local SQLite Database:</span>
                    <span style="font-weight:600; color: #16a34a;">● Synchronized</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#64748b;">Cloud Telemetry / Privacy:</span>
                    <span style="font-weight:600; color: #4f46e5;">100% Local & Offline</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Quick Navigation Links
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>🚀 Quick Actions</h4>", unsafe_allow_html=True)
            st.markdown("""
            - 📹 **Live Classroom Monitoring**: View live video feed and stream analytics.
            - 👥 **Attendance Management**: View live roster, verify presence, or export CSV.
            - 💡 **Teaching Recommendations**: Review AI pedagogical interventions.
            - 📝 **Biometric Enrollment**: Register new student faces with privacy consent.
            """)
