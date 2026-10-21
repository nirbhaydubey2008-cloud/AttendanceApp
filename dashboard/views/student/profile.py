"""
dashboard/views/student/profile.py
Student Portal: Profile & Security Management
Displays student profile credentials, biometric consent status,
and provides permanent password update workflow.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Student Profile & Security",
        description="Personal student credentials, biometric consent registry, and password management."
    )

    curr_user = st.session_state.get("current_user") or api_client.get_me()
    s_prof = curr_user.get("student_profile") if curr_user else {}
    must_change = curr_user.get("must_change_password", False) if curr_user else False

    student_name = curr_user.get("name") if curr_user else "Student"
    stu_id = curr_user.get("username") if curr_user else "STU-2026-0001"
    roll_no = s_prof.get("roll_no") if s_prof else "—"
    dept = s_prof.get("department") if s_prof else "Computer Science & Engineering"
    email = curr_user.get("email") or "Not configured"
    consent = s_prof.get("consent_given", True) if s_prof else True
    enrolled_dt = s_prof.get("enrolled_at", "Recorded") if s_prof else "Recorded"
    enrolled_str = enrolled_dt[:10] if isinstance(enrolled_dt, str) else "Recorded"

    if must_change:
        st.markdown("""
        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:16px 20px; margin-bottom:20px;">
            <div style="font-weight:700; color:#b45309; font-size:1.05rem;">
                ⚠️ Activation Password Reset Required
            </div>
            <div style="font-size:0.88rem; color:#92400e; margin-top:4px;">
                You are currently signed in using a temporary activation password provided by your teacher. Please choose a private permanent password below.
            </div>
        </div>
        """, unsafe_allow_html=True)

    col_prof, col_sec = st.columns([1.2, 1.2])

    with col_prof:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>🎓 Academic Profile</h3>", unsafe_allow_html=True)

            consent_badge = '<span class="badge badge-present">Explicitly Consented</span>' if consent else '<span class="badge badge-absent">Pending</span>'

            st.markdown(f"""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:16px; font-size:0.9rem; line-height:1.8;">
                ● <b>Student Name:</b> {student_name}<br>
                ● <b>Student ID:</b> <code>{stu_id}</code><br>
                ● <b>Roll Number:</b> <code>{roll_no}</code><br>
                ● <b>Department:</b> {dept}<br>
                ● <b>Registered Email:</b> {email}<br>
                ● <b>Biometric Consent:</b> {consent_badge}<br>
                ● <b>Registration Date:</b> {enrolled_str}<br>
                ● <b>Role:</b> <span class="badge badge-partial">STUDENT</span>
            </div>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>🛡️ Privacy Guarantees</h4>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size:0.83rem; color:#64748b; line-height:1.6;">
                All facial recognition embeddings are processed and stored exclusively on the offline university workstation. No images or biometric vectors are transmitted over the internet or cloud.
            </div>
            """, unsafe_allow_html=True)

    with col_sec:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>🔐 Update Password</h3>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:0.85rem; color:#64748b;'>Enter your current password and choose a new secure password (minimum 8 characters).</p>", unsafe_allow_html=True)

            old_pass = st.text_input("Current / Temporary Password", type="password", key="stu_prof_old_pwd")
            new_pass = st.text_input("New Permanent Password", type="password", key="stu_prof_new_pwd")
            conf_pass = st.text_input("Confirm New Password", type="password", key="stu_prof_conf_pwd")

            if st.button("Update Password", type="primary", use_container_width=True):
                if not old_pass or not new_pass:
                    st.error("Please fill in both current and new password.")
                elif len(new_pass) < 8:
                    st.error("New password must be at least 8 characters long.")
                elif new_pass != conf_pass:
                    st.error("New passwords do not match.")
                else:
                    with st.spinner("Securing account with new password..."):
                        res = api_client.change_password(old_pass, new_pass)
                    if res and (res.get("success") or res.get("status") == "success"):
                        st.success("✅ Password updated successfully! Your account is now secured.")
                        if curr_user:
                            curr_user["must_change_password"] = False
                            st.session_state["current_user"] = curr_user
                        st.rerun()
                    else:
                        err_msg = res.get("detail", "Failed to update password.") if res else "Server unreachable."
                        st.error(f"❌ {err_msg}")
