"""
dashboard/views/settings.py
Teacher View: Settings & Profile
Teacher profile details, password updates, attendance thresholds,
refresh settings, and privacy principles.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Settings & Teacher Profile",
        description="Teacher account credentials, attendance thresholds, telemetry refresh, and privacy controls."
    )

    curr_user = st.session_state.get("current_user") or api_client.get_me()

    tab_profile, tab_thresh, tab_privacy = st.tabs(["👤 Profile & Security", "⚙️ Attendance Thresholds", "🛡️ Privacy Guardrails"])

    with tab_profile:
        col_prof, col_pwd = st.columns([1.2, 1.2])

        with col_prof:
            with st.container(border=True):
                st.markdown("<h3 style='margin-top:0;'>👨‍🏫 Faculty Profile</h3>", unsafe_allow_html=True)
                teacher_info = curr_user.get("teacher_profile") if curr_user else None
                teacher_name = teacher_info.get("name") if teacher_info else (curr_user.get("username", "Faculty"))
                emp_id = teacher_info.get("employee_id", "EMP001") if teacher_info else "EMP001"
                dept = teacher_info.get("department", "Computer Science") if teacher_info else "Computer Science"
                email = curr_user.get("email") if curr_user else "nirbhay@univ.edu"

                st.markdown(f"""
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:16px; font-size:0.9rem; line-height:1.8;">
                    ● <b>Faculty Name:</b> {teacher_name}<br>
                    ● <b>Role:</b> <span class="badge badge-present">{curr_user.get('role', 'TEACHER')}</span><br>
                    ● <b>Username:</b> <code>{curr_user.get('username')}</code><br>
                    ● <b>Employee ID:</b> <code>{emp_id}</code><br>
                    ● <b>Department:</b> {dept}<br>
                    ● <b>Email:</b> {email or 'Not set'}<br>
                    ● <b>Status:</b> {'Active' if curr_user.get('is_active', True) else 'Inactive'}
                </div>
                """, unsafe_allow_html=True)

        with col_pwd:
            with st.container(border=True):
                st.markdown("<h3 style='margin-top:0;'>🔐 Change Password</h3>", unsafe_allow_html=True)
                st.markdown("<p style='font-size:0.85rem; color:#64748b;'>Update your faculty account password. Minimum 8 characters.</p>", unsafe_allow_html=True)

                old_pwd = st.text_input("Current Password", type="password", key="teacher_old_pwd")
                new_pwd = st.text_input("New Password", type="password", key="teacher_new_pwd")
                confirm_pwd = st.text_input("Confirm New Password", type="password", key="teacher_conf_pwd")

                if st.button("Update Password", type="primary", use_container_width=True):
                    if not old_pwd or not new_pwd:
                        st.error("Please fill in both current and new password.")
                    elif len(new_pwd) < 8:
                        st.error("New password must be at least 8 characters long.")
                    elif new_pwd != confirm_pwd:
                        st.error("New passwords do not match.")
                    else:
                        with st.spinner("Updating password..."):
                            res = api_client.change_password(old_pwd, new_pwd)
                        if res and (res.get("success") or res.get("status") == "success"):
                            st.success("✅ Password updated successfully!")
                        else:
                            st.error(res.get("detail", "Failed to update password."))

    with tab_thresh:
        c1, c2 = st.columns([1.3, 1.2])
        with c1:
            with st.container(border=True):
                st.markdown("<h3 style='margin-top:0;'>⚙️ Qualification Thresholds</h3>", unsafe_allow_html=True)
                st.markdown("<p style='font-size:0.88rem; color:#64748b;'>Set the percentage of total lecture time a student must be visually present in the camera scene to qualify.</p>", unsafe_allow_html=True)

                present_th = st.slider("Verified Present Threshold (%)", min_value=50, max_value=90, value=75, step=5, help="Students present for at least this percentage of lecture receive PRESENT status.")
                partial_th = st.slider("Partial Attendance Threshold (%)", min_value=20, max_value=60, value=40, step=5, help="Students present between this and the present threshold receive PARTIAL status.")

                st.markdown(f"""
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 14px; font-size:0.83rem; margin-top:10px;">
                    ● <b>PRESENT:</b> $\ge {present_th}\%$ presence<br>
                    ● <b>PARTIAL:</b> ${partial_th}\% - {present_th-1}\%$ presence<br>
                    ● <b>ABSENT:</b> $< {partial_th}\%$ presence
                </div>
                """, unsafe_allow_html=True)

        with c2:
            with st.container(border=True):
                st.markdown("<h3 style='margin-top:0;'>🔄 Telemetry Polling</h3>", unsafe_allow_html=True)
                refresh_rate = st.select_slider(
                    "Live Telemetry Refresh Interval (seconds)",
                    options=[1, 2, 3, 5, 10],
                    value=3
                )
                st.session_state["refresh_interval"] = refresh_rate
                st.info(f"Dashboard telemetry will refresh every {refresh_rate} seconds on active monitoring pages.")

    with tab_privacy:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>🛡️ Privacy & Compliance Guardrails</h3>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size: 0.88rem; line-height: 1.8;">
                <div style="margin-bottom: 12px;">
                    <div style="font-weight: 600; color: #0f172a;">1. Zero Cloud Transmission</div>
                    <div style="color: #64748b;">All computer vision, facial embeddings, audio VAD, and attendance tracking run 100% locally on this machine. No student video, audio, or biometric data is ever sent to cloud servers.</div>
                </div>
                <div style="margin-bottom: 12px;">
                    <div style="font-weight: 600; color: #0f172a;">2. Explicit Biometric Consent</div>
                    <div style="color: #64748b;">Facial recognition is strictly opt-in. Unregistered or non-consenting individuals are assigned temporary anonymous track IDs with zero automated identity attribution.</div>
                </div>
                <div style="margin-bottom: 12px;">
                    <div style="font-weight: 600; color: #0f172a;">3. Behavioral Indicators (Not Diagnoses)</div>
                    <div style="color: #64748b;">Attention scores reflect observable physical geometry (eye gaze vector, head orientation, audio levels). The system makes zero psychological, emotional, or neurological claims.</div>
                </div>
                <div>
                    <div style="font-weight: 600; color: #0f172a;">4. Role Isolation & Anti-IDOR</div>
                    <div style="color: #64748b;">Students can only access their own attendance history and course schedules. Live video feeds and biometric controls are restricted exclusively to authenticated instructors.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
