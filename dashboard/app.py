"""
dashboard/app.py
Role-Based Dashboard for Multimodal Attendance & Engagement Agent.
Supports:
1. Unauthenticated Login Gate
2. Teacher Dashboard (Overview, Lectures, Live Monitoring, Attendance, Enrollment,
   Engagement Analytics, Recommendations, Reports, Data & Audit, Settings)
3. Student Dashboard (Personalized Attendance, Live Session, Courses, Profile)
"""

import os
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

# Configure page layout
st.set_page_config(
    page_title="Multimodal Attendance & Engagement Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

from dashboard.components import api_client, ui
from dashboard.views import (
    login,
    overview,
    lecture_mgmt,
    live_monitoring,
    attendance_mgmt,
    student_enrollment,
    engagement_analytics,
    recommendations,
    student_reports,
    data_exports,
    settings
)
from dashboard.views.student import (
    overview as student_overview,
    attendance as student_attendance,
    courses as student_courses,
    profile as student_profile
)

# Apply Modern Light Theme
ui.apply_light_theme()

# --- 1. Authentication Check ---
auth_token = st.session_state.get("auth_token")

if not auth_token:
    login.render()
    st.stop()

# Validate and retrieve current user
current_user = st.session_state.get("current_user")
if not current_user:
    current_user = api_client.get_me()
    if not current_user:
        # Invalid / expired token
        st.session_state.pop("auth_token", None)
        st.session_state.pop("current_user", None)
        st.rerun()
    st.session_state["current_user"] = current_user

user_role = current_user.get("role", "TEACHER")

# --- 2. Query System Health & Session State ---
health_data = api_client.get_health()
current_session = api_client.get_current_session()
is_active = current_session and current_session.get("is_active", False)


# --- 3. Sidebar Navigation & Layout ---
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 14px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 12px;">
        <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px;">
            <span style="color:#4f46e5;">🎓</span> Classroom Agent
        </div>
        <div style="font-size: 0.76rem; color: #64748b; margin-top: 2px;">
            Offline AI Perception & Attendance
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Render User Profile Card in Sidebar
    t_prof = current_user.get("teacher_profile") or {}
    s_prof = current_user.get("student_profile") or {}
    display_name = current_user.get("name") or current_user.get("username")
    role_badge_class = "badge-present" if user_role == "TEACHER" else "badge-partial"

    st.markdown(f"""
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; margin-bottom:12px;">
        <div style="font-size:0.88rem; font-weight:700; color:#0f172a;">{display_name}</div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
            <span class="badge {role_badge_class}">{user_role}</span>
            <span style="font-size:0.75rem; color:#64748b;"><code>{current_user.get('username')}</code></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if user_role == "TEACHER":
        pages = [
            "📊 Overview",
            "📚 Lecture & Course Management",
            "📹 Live Monitoring",
            "👥 Attendance Management",
            "📝 Student Enrollment & Roster",
            "📈 Engagement Analytics",
            "💡 Teaching Recommendations",
            "📄 Student Session Reports",
            "📥 Data & Audit Logs",
            "⚙️ Settings & Profile"
        ]
        selected_page = st.radio("Navigation Menu", pages, label_visibility="collapsed")

        st.markdown("<hr>", unsafe_allow_html=True)

        # Active Session Indicator
        if is_active:
            st.markdown(f"""
            <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:10px; font-size:0.8rem; margin-bottom:12px;">
                <div style="color:#2563eb; font-weight:600;">● Active Lecture</div>
                <div style="color:#1e293b; font-weight:700; margin-top:2px;">{current_session.get('course_code', 'CS101')}</div>
                <div style="color:#64748b; font-size:0.75rem;">{current_session.get('title', 'Lecture')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; font-size:0.8rem; margin-bottom:12px;">
                <div style="color:#64748b; font-weight:600;">○ Session Idle</div>
                <div style="color:#94a3b8; font-size:0.75rem;">Launch from Lecture Mgmt or Live Monitoring</div>
            </div>
            """, unsafe_allow_html=True)

        # Telemetry Sync
        st.markdown("<b>🔄 Telemetry Sync</b>", unsafe_allow_html=True)
        auto_refresh = st.checkbox("Live Auto-Refresh", value=True)
        refresh_interval = st.session_state.get("refresh_interval", 3)
        if st.button("Manual Refresh", use_container_width=True):
            st.rerun()

    else:
        # Student Navigation
        student_pages = [
            "📊 My Dashboard & Overview",
            "📅 My Attendance History",
            "🏛️ Enrolled Courses",
            "👤 Profile & Change Password"
        ]
        selected_page = st.radio("Student Menu", student_pages, label_visibility="collapsed")
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<b>🔄 Class Sync</b>", unsafe_allow_html=True)
        auto_refresh = st.checkbox("Live Lecture Sync", value=True, key="stu_auto_sync")
        refresh_interval = 4
        if st.button("Manual Sync", key="stu_man_sync", use_container_width=True):
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # Logout Button
    if st.button("🚪 Sign Out", use_container_width=True):
        api_client.logout()
        st.session_state.pop("auth_token", None)
        st.session_state.pop("current_user", None)
        st.rerun()

    st.markdown("""
    <div style="font-size: 0.74rem; color: #94a3b8; line-height: 1.4; margin-top: 14px;">
        <b>Developer:</b> Nirbhay Dubey<br>
        B.Tech CSE (Year 1)<br>
        <i>Role-Based Perception v2.0</i>
    </div>
    """, unsafe_allow_html=True)

# Render Global Top Status Bar
ui.render_top_system_bar(health_data, current_session)


# --- 4. Route to Selected Page ---
if user_role == "TEACHER":
    if selected_page == "📊 Overview":
        overview.render()
    elif selected_page == "📚 Lecture & Course Management":
        lecture_mgmt.render()
    elif selected_page == "📹 Live Monitoring":
        live_monitoring.render()
    elif selected_page == "👥 Attendance Management":
        attendance_mgmt.render()
    elif selected_page == "📝 Student Enrollment & Roster":
        student_enrollment.render()
    elif selected_page == "📈 Engagement Analytics":
        engagement_analytics.render()
    elif selected_page == "💡 Teaching Recommendations":
        recommendations.render()
    elif selected_page == "📄 Student Session Reports":
        student_reports.render()
    elif selected_page == "📥 Data & Audit Logs":
        data_exports.render()
    elif selected_page == "⚙️ Settings & Profile":
        settings.render()

    # Auto-refresh loop for real-time pages
    if auto_refresh and health_data and selected_page in ("📊 Overview", "📹 Live Monitoring", "👥 Attendance Management", "📈 Engagement Analytics"):
        time.sleep(refresh_interval)
        st.rerun()

else:
    # Dedicated Student Views (Phase 7)
    if selected_page == "📊 My Dashboard & Overview":
        student_overview.render()
    elif selected_page == "📅 My Attendance History":
        student_attendance.render()
    elif selected_page == "🏛️ Enrolled Courses":
        student_courses.render()
    elif selected_page == "👤 Profile & Change Password":
        student_profile.render()

    if auto_refresh and selected_page == "📊 My Dashboard & Overview":
        time.sleep(refresh_interval)
        st.rerun()
