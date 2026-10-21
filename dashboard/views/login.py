"""
dashboard/views/login.py
Role-Aware Authentication View for Multimodal Attendance & Engagement Agent.
Provides explicit role selection (Teacher / Faculty vs Student Portal),
customized input labels, one-click demo pre-fill buttons, and graceful error handling.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    st.markdown("""
    <style>
    .login-container {
        max-width: 540px;
        margin: 20px auto 10px auto;
        padding: 24px 30px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04);
    }
    .login-logo {
        font-size: 2.2rem;
        text-align: center;
        margin-bottom: 4px;
    }
    .login-title {
        font-size: 1.45rem;
        font-weight: 700;
        color: #0f172a;
        text-align: center;
        margin-bottom: 2px;
    }
    .login-subtitle {
        font-size: 0.85rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 18px;
    }
    .role-badge-t {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .role-badge-s {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #166534;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .demo-box {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 0.82rem;
        color: #475569;
        margin-top: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2.2, 1])

    with col_m:
        st.markdown("""
        <div class="login-container">
            <div class="login-logo">🎓</div>
            <div class="login-title">Classroom AI Agent</div>
            <div class="login-subtitle">Multimodal Attendance & Engagement System</div>
        </div>
        """, unsafe_allow_html=True)

        # Explicit Role Selection Tabs
        tab_teacher, tab_student = st.tabs([
            "👨‍🏫 Teacher / Faculty Sign In",
            "🎓 Student Portal Sign In"
        ])

        with tab_teacher:
            render_teacher_login()

        with tab_student:
            render_student_login()


def render_teacher_login():
    st.markdown("""
    <div style="margin-bottom: 12px;">
        <span class="role-badge-t">Faculty Access</span>
        <div style="font-size: 0.84rem; color: #64748b; margin-top: 6px;">
            Full control over lecture scheduling, live AI monitoring, attendance verification, and audit logs.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pre-fill Demo Button Callback
    def fill_teacher():
        st.session_state["t_id_field"] = "teacher"
        st.session_state["t_pwd_field"] = "TeacherPassword123!"

    st.button("⚡ Fill Demo Teacher Credentials", key="btn_fill_teacher", on_click=fill_teacher, use_container_width=True)

    with st.form("teacher_form"):
        teacher_id = st.text_input(
            "Faculty Username or Email",
            placeholder="e.g. teacher or nirbhay@univ.edu",
            key="t_id_field"
        )
        teacher_pwd = st.text_input(
            "Password",
            type="password",
            placeholder="Enter faculty password",
            key="t_pwd_field"
        )
        submit = st.form_submit_button("Sign In to Teacher Dashboard →", type="primary", use_container_width=True)

        if submit:
            process_login(teacher_id, teacher_pwd, expected_role="TEACHER")

    st.markdown("""
    <div class="demo-box">
        <b>🔑 Default Teacher Account:</b><br>
        ● Username: <code>teacher</code> &nbsp;|&nbsp; Password: <code>TeacherPassword123!</code>
    </div>
    """, unsafe_allow_html=True)


def render_student_login():
    st.markdown("""
    <div style="margin-bottom: 12px;">
        <span class="role-badge-s">Student Access</span>
        <div style="font-size: 0.84rem; color: #64748b; margin-top: 6px;">
            View your verified presence history, enrolled courses, and live lecture attendance indicator.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pre-fill Demo Button Callback
    def fill_student():
        st.session_state["s_id_field"] = "STU-2026-0001"
        st.session_state["s_pwd_field"] = "DavidPermanentPass123!"

    st.button("⚡ Fill Demo Student Credentials", key="btn_fill_student", on_click=fill_student, use_container_width=True)

    with st.form("student_form"):
        student_id = st.text_input(
            "Institutional Student ID or Roll Number",
            placeholder="e.g. STU-2026-0001",
            key="s_id_field"
        )
        student_pwd = st.text_input(
            "Password",
            type="password",
            placeholder="Enter permanent or temporary password",
            key="s_pwd_field"
        )
        submit = st.form_submit_button("Sign In to Student Portal →", type="primary", use_container_width=True)

        if submit:
            process_login(student_id, student_pwd, expected_role="STUDENT")

    st.markdown("""
    <div class="demo-box">
        <b>🔑 Default Student Accounts:</b><br>
        ● Student ID: <code>STU-2026-0001</code> &nbsp;|&nbsp; Pass: <code>DavidPermanentPass123!</code><br>
        ● Activation: <code>STU-2026-0002</code> &nbsp;|&nbsp; Pass: <code>StudentTempPass123!</code>
    </div>
    """, unsafe_allow_html=True)


def process_login(identifier: str, password: str, expected_role: str):
    if not identifier.strip() or not password.strip():
        st.error("Please enter both identifier and password.")
        return

    with st.spinner("Authenticating..."):
        resp = api_client.login(identifier.strip(), password)

    if resp and resp.get("success"):
        user = resp.get("user", {})
        st.session_state["auth_token"] = resp["token"]
        st.session_state["current_user"] = user

        actual_role = user.get("role", "TEACHER")
        if actual_role != expected_role:
            st.info(f"Signed in as {actual_role}. Redirecting to your authorized portal...")
        else:
            st.success(f"Welcome, {user.get('name', identifier)}! Redirecting...")
        st.rerun()
    else:
        err = resp.get("detail", "Invalid username, student ID, or password.") if resp else "Backend server unreachable. Ensure FastAPI backend is running on port 8000."
        st.error(f"❌ Authentication Failed: {err}")
