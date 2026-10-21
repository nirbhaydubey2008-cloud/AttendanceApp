"""
dashboard/views/student_enrollment.py
Teacher View: Student Enrollment & Biometric Registry
Provides student enrollment with automatic STU-YYYY-XXXX ID generation,
temporary activation credentials, and a searchable roster.
"""

import time
from datetime import datetime
import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Student Enrollment & Biometric Roster",
        description="Enroll students with facial embeddings, auto-provision secure student accounts, and manage the student directory."
    )

    tab_enroll, tab_roster = st.tabs(["➕ Enroll New Student", "📋 Student Directory & Roster"])

    with tab_enroll:
        render_enrollment_form()

    with tab_roster:
        render_student_roster()


def render_enrollment_form():
    # Fetch available courses for assignment dropdown
    courses_resp = api_client.get_teacher_courses()
    courses = courses_resp.get("courses", []) if courses_resp else []
    if courses:
        course_options = ["-- Select Course to Join / Enroll In --"] + [f"{c['course_code']} - {c['title']}" for c in courses]
    else:
        course_options = ["None (Register a course in Lecture Management first)"]

    with st.container(border=True):
        st.markdown("<h3 style='margin-top:0;'>📝 Student Registration Details</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.88rem; color:#64748b;'>Enter the student's academic profile. "
            "A unique institutional <code>STU-YYYY-XXXX</code> ID and activation password will be auto-generated.</p>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="e.g. Aditi Sharma", key="enroll_name")
            roll_no = st.text_input("Roll Number / Registration No *", placeholder="e.g. 2026BCSE042", key="enroll_roll")
            email = st.text_input("Institutional Email (Optional)", placeholder="e.g. aditi.s@univ.edu", key="enroll_email")

        with col2:
            selected_course_str = st.selectbox(
                "Course to Join / Enroll In * (Kis Course Me Join Karna Hai)",
                options=course_options,
                index=0,
                help="Select the course this student will attend. Attendance tracking is strictly enforced for this course.",
                key="enroll_course"
            )
            course_code = None
            if selected_course_str and not selected_course_str.startswith("--") and not selected_course_str.startswith("None"):
                course_code = selected_course_str.split(" - ")[0].strip()

            department = st.text_input("Department / Branch", value="Computer Science & Engineering", key="enroll_dept")
            custom_id = st.text_input(
                "Custom Student ID (Optional)",
                placeholder="Leave blank to auto-generate STU-YYYY-XXXX",
                key="enroll_custom_id"
            )

        st.markdown("#### 📷 Biometric Facial Profile")
        method = st.radio(
            "Capture Method",
            ["Live Camera Snapshot", "Upload Photo File", "Browser Webcam Input"],
            horizontal=True,
            key="enroll_capture_method"
        )

        photo_bytes = None

        if method == "Live Camera Snapshot":
            token = api_client.get_stored_token()
            feed_url = f"{api_client.API_BASE}/api/video/feed?token={token}" if token else f"{api_client.API_BASE}/api/video/feed"

            c_cam_view, c_cam_action = st.columns([1.5, 1.2])

            with c_cam_view:
                st.markdown(f"""
                <div style="background: #0f172a; border-radius: 10px; overflow: hidden; border: 1px solid #334155;">
                    <img src="{feed_url}" width="100%" style="display: block; max-height: 250px; object-fit: contain;" onerror="this.onerror=null; this.src='https://placehold.co/480x250/0f172a/94a3b8?text=Connecting+to+Classroom+Camera...';"/>
                </div>
                """, unsafe_allow_html=True)
                st.caption("Live video stream from classroom camera.")

            with c_cam_action:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                if st.button("📸 Snap Photo from Live Camera", key="btn_take_camera_snap", type="primary", use_container_width=True):
                    with st.spinner("Capturing frame from active camera..."):
                        captured = api_client.get_camera_snapshot()
                    if captured:
                        st.session_state["enroll_snapped_bytes"] = captured
                        st.success("✅ Frame captured successfully!")
                    else:
                        st.error("Could not capture frame from camera. Ensure camera is active.")

                if st.session_state.get("enroll_snapped_bytes"):
                    photo_bytes = st.session_state["enroll_snapped_bytes"]
                    st.image(photo_bytes, caption="Captured Portrait Preview", width=160)
                    if st.button("🔄 Retake Photo", key="btn_retake_camera_snap"):
                        st.session_state.pop("enroll_snapped_bytes", None)
                        st.rerun()

        elif method == "Upload Photo File":
            uploaded_file = st.file_uploader(
                "Choose a clear front-facing portrait (JPG or PNG)",
                type=["jpg", "jpeg", "png"],
                key="enroll_photo_file"
            )
            if uploaded_file is not None:
                photo_bytes = uploaded_file.getvalue()
                st.image(photo_bytes, caption="Uploaded Portrait Preview", width=180)

        else:
            st.info("💡 If your browser displays a permission prompt, click **Allow**. If camera is already in use by system, use **Live Camera Snapshot** above.")
            cam_snapshot = st.camera_input("Take a frontal portrait snapshot", key="enroll_cam_input")
            if cam_snapshot is not None:
                photo_bytes = cam_snapshot.getvalue()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        consent = st.checkbox(
            "Explicit Biometric Consent: The student has consented to facial embedding storage for offline classroom verification.",
            value=True,
            key="enroll_consent"
        )

        submit_btn = st.button("🚀 Register & Provision Student", type="primary", use_container_width=True)

        if submit_btn:
            if not name.strip():
                st.error("Student Name is required.")
                return
            if not roll_no.strip():
                st.error("Roll Number is required.")
                return
            if not photo_bytes:
                st.error("A clear biometric portrait photo is required to enroll facial recognition embeddings.")
                return
            if not consent:
                st.error("Biometric consent must be confirmed prior to enrolling student embeddings.")
                return

            with st.spinner("Processing facial embeddings and provisioning credentials..."):
                res = api_client.enroll_student(
                    name=name.strip(),
                    photo_bytes=photo_bytes,
                    student_id=custom_id.strip() if custom_id.strip() else None,
                    roll_no=roll_no.strip(),
                    email=email.strip() if email.strip() else None,
                    course_code=course_code,
                    consent_given=consent
                )

            if res and (res.get("success") or res.get("status") == "success"):
                st.session_state.pop("enroll_snapped_bytes", None)
                st.balloons()
                st.success("✅ Student successfully enrolled and account provisioned!")

                cred = res.get("credentials", {})
                stu = res.get("student", {})
                stu_id = stu.get("student_id") or cred.get("username") or res.get("student_id")
                temp_pwd = cred.get("temporary_password") or res.get("temporary_password") or "StudentTempPass123!"
                stu_name = stu.get("name") or res.get("name") or name.strip()
                stu_roll = stu.get("roll_no") or res.get("roll_no") or roll_no.strip() or "—"
                stu_course = stu.get("enrolled_course") or course_code or "General"

                st.markdown(f"""
                <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:10px; padding:18px; margin-top:14px;">
                    <div style="font-weight:700; color:#166534; font-size:1.15rem; margin-bottom:10px; display:flex; align-items:center; gap:8px;">
                        <span>🎓</span> Student Activation & Sign-In Credentials
                    </div>
                    <div style="font-size:0.92rem; color:#14532d; line-height:1.9;">
                        ● <b>Student Name:</b> {stu_name}<br>
                        ● <b>Assigned Student ID / Username:</b> <code style="font-size:1.05rem; font-weight:700; color:#166534; background:#dcfce7; padding:2px 8px; border-radius:4px;">{stu_id}</code><br>
                        ● <b>Generated Login Password:</b> <code style="font-size:1.05rem; font-weight:700; color:#b91c1c; background:#fee2e2; padding:3px 8px; border-radius:4px; border:1px solid #fca5a5;">{temp_pwd}</code><br>
                        ● <b>Roll Number:</b> <code>{stu_roll}</code><br>
                        ● <b>Enrolled Course:</b> <code>{stu_course}</code><br>
                        ● <b>Biometric Verification:</b> Facial feature vector successfully extracted and indexed offline
                    </div>
                    <div style="margin-top:14px; font-size:0.85rem; color:#15803d; background:#dcfce7; padding:10px 14px; border-radius:8px; border:1px solid #bbf7d0;">
                        🔑 <b>How Student Signs In:</b><br>
                        1. Go to the login screen and click the <b>🎓 Student Portal Sign In</b> tab.<br>
                        2. Enter either the <b>Student ID</b> (<code>{stu_id}</code>) or <b>Roll Number</b> (<code>{stu_roll}</code>).<br>
                        3. Enter the <b>Generated Password</b> (<code>{temp_pwd}</code>).<br>
                        4. Upon first login, they will be prompted to set their private permanent password.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                err = res.get("detail") if res else "Enrollment failed. Please check backend logs."
                st.error(f"❌ Enrollment Error: {err}")


def render_student_roster():
    enrolled = api_client.get_enrolled_students()
    students = enrolled.get("students", []) if enrolled else []

    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        search_query = st.text_input("🔍 Search Roster", placeholder="Filter by Name, ID, or Roll No...", key="roster_search")
    with c2:
        st.markdown(f"""
        <div style="padding-top:28px; font-weight:600; color:#475569;">
            Total Enrolled: <span style="color:#2563eb; font-weight:700;">{len(students)}</span> Students
        </div>
        """, unsafe_allow_html=True)
    with c3:
        if st.button("🔄 Refresh Roster", use_container_width=True):
            st.rerun()

    filtered = students
    if search_query:
        q = search_query.lower()
        filtered = [
            s for s in students
            if q in s.get("name", "").lower()
            or q in s.get("student_id", "").lower()
            or q in (s.get("roll_no") or "").lower()
        ]

    if not filtered:
        st.info("No matching student profiles found in the registry.")
        return

    headers = ["Student Name", "Student ID", "Roll Number", "Login / Activation Password", "Status / Consent", "Registration Date"]
    rows = []
    for s in filtered:
        consent_badge = '<span class="badge badge-present">Active & Consented</span>' if s.get("consent_given", True) else '<span class="badge badge-absent">Pending Consent</span>'
        enrolled_dt = s.get("enrolled_at", "Recorded")
        date_str = enrolled_dt[:10] if isinstance(enrolled_dt, str) else "Recorded"

        pwd_val = s.get("initial_password") or "—"
        must_change = s.get("must_change_password", True)
        if must_change and pwd_val != "—":
            pwd_badge = f'<code style="font-size:0.86rem; font-weight:700; color:#b91c1c; background:#fee2e2; padding:3px 8px; border-radius:6px; border:1px solid #fca5a5;">{pwd_val}</code>'
        elif pwd_val != "—":
            pwd_badge = f'<code style="font-size:0.86rem; font-weight:700; color:#15803d; background:#dcfce7; padding:3px 8px; border-radius:6px; border:1px solid #86efac;">{pwd_val}</code>'
        else:
            pwd_badge = '<span style="color:#94a3b8;">—</span>'

        rows.append([
            f"<b>{s.get('name')}</b>",
            f"<code>{s.get('student_id')}</code>",
            s.get("roll_no") or "—",
            pwd_badge,
            consent_badge,
            date_str
        ])

    ui.render_html_table(headers, rows)

    st.markdown("""
    <div style="margin-top: 14px; font-size: 0.83rem; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px;">
        💡 <b>Faculty Information:</b> The <b>Login / Activation Password</b> column displays the password generated upon registration. Share the <b>Student ID</b> and this password with the student for their initial login to the Student Portal.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    with st.expander("🗑️ Deregister / Remove Student from System", expanded=False):
        stu_dict = {
            f"{s.get('name')} ({s.get('student_id')} - Roll: {s.get('roll_no') or 'N/A'})": s.get('student_id')
            for s in students
        }
        sel_stu_label = st.selectbox(
            "Select Student to Deregister & Remove",
            options=list(stu_dict.keys()),
            key="sel_del_student"
        )
        del_stu_id = stu_dict.get(sel_stu_label)

        st.warning(
            f"⚠️ Removing student **{del_stu_id}** will permanently purge their biometric facial embeddings, "
            f"system account credentials, course enrollments, and past lecture records."
        )
        confirm_stu_del = st.checkbox(
            f"I understand and confirm the permanent deletion of student {del_stu_id}",
            key="confirm_del_stu_box"
        )

        if st.button("🗑️ Delete Student & Revoke Access", type="primary", key="btn_del_student", disabled=not confirm_stu_del, use_container_width=True):
            with st.spinner(f"Purging student {del_stu_id} and biometric indexes..."):
                res = api_client.delete_student(del_stu_id)
            if res and (res.get("success") or res.get("status") == "success"):
                st.success(f"Student {del_stu_id} was successfully deregistered and removed from the system.")
                time.sleep(1.0)
                st.rerun()
            else:
                err_msg = res.get("detail", "Failed to delete student.") if isinstance(res, dict) else "Delete failed."
                st.error(f"❌ Deletion failed: {err_msg}")

