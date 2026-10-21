"""
dashboard/views/lecture_mgmt.py
Teacher View: Lecture & Course Management
Allows teachers to define courses, schedule lectures, track status,
and launch active perception sessions tied directly to scheduled lectures.
"""

from datetime import datetime
import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Lecture & Course Management",
        description="Schedule academic lectures, manage course curricula, and launch live attendance sessions."
    )

    tab_lectures, tab_courses = st.tabs(["📚 Scheduled Lectures & Sessions", "🏛️ Course Catalog"])

    with tab_lectures:
        render_lectures_tab()

    with tab_courses:
        render_courses_tab()


def render_lectures_tab():
    curr_session = api_client.get_current_session()
    is_active = curr_session and curr_session.get("is_active", False)
    active_lecture_title = curr_session.get("title", "") if is_active else ""

    # Fetch lectures and courses
    lectures_resp = api_client.get_teacher_lectures()
    lectures = lectures_resp.get("lectures", []) if lectures_resp else []

    courses_resp = api_client.get_teacher_courses()
    courses = courses_resp.get("courses", []) if courses_resp else []
    course_options = [c["course_code"] for c in courses] if courses else ["CS101"]

    c_form, c_list = st.columns([1.1, 1.4])

    with c_form:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>➕ Schedule New Lecture</h3>", unsafe_allow_html=True)

            selected_course = st.selectbox("Course Code", options=course_options, key="lec_course")
            lec_title = st.text_input("Lecture Title *", placeholder="e.g. Lecture 5: Backpropagation", key="lec_title")
            lec_topic = st.text_input("Syllabus Topic", placeholder="e.g. Gradient Descent & Loss Functions", key="lec_topic")

            dur_col, id_col = st.columns(2)
            with dur_col:
                duration_min = st.number_input("Duration (Min)", min_value=15, max_value=180, value=60, step=15, key="lec_dur")
            with id_col:
                auto_id = f"LEC-{selected_course}-{len(lectures) + 1:03d}"
                lec_id = st.text_input("Lecture ID", value=auto_id, key="lec_id")

            scheduled_date = st.text_input(
                "Scheduled Time",
                value=datetime.now().strftime("%Y-%m-%d %H:%M"),
                key="lec_date"
            )

            if st.button("📅 Schedule Lecture", type="primary", use_container_width=True):
                if not lec_title.strip():
                    st.error("Lecture Title is required.")
                elif not selected_course:
                    st.error("Course must be selected.")
                else:
                    with st.spinner("Registering scheduled lecture..."):
                        res = api_client.create_lecture(
                            lecture_id=lec_id.strip(),
                            course_code=selected_course,
                            title=lec_title.strip(),
                            topic=lec_topic.strip() if lec_topic.strip() else None,
                            scheduled_date=scheduled_date.strip(),
                            planned_duration_min=int(duration_min)
                        )
                    if res and (res.get("success") or res.get("status") == "success"):
                        st.success(f"Lecture '{lec_title}' registered successfully!")
                        st.rerun()
                    else:
                        err = res.get("detail") if res else "Could not register lecture."
                        st.error(f"Error: {err}")

    with c_list:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>📋 Scheduled & Historical Lectures</h3>", unsafe_allow_html=True)

            if not lectures:
                st.info("No lectures scheduled yet. Create your first lecture on the left.")
            else:
                for lec in lectures:
                    lid = lec.get("lecture_id")
                    title = lec.get("title")
                    ccode = lec.get("course_code")
                    status = lec.get("status", "SCHEDULED")
                    topic = lec.get("topic") or "General"
                    dur = lec.get("planned_duration_min", 60)

                    status_color = "#2563eb" if status == "LIVE" else ("#059669" if status == "COMPLETED" else "#d97706")
                    status_badge = f'<span style="background:{status_color}18; color:{status_color}; padding:2px 8px; border-radius:12px; font-weight:600; font-size:0.75rem;">{status}</span>'

                    st.markdown(f"""
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 14px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="font-weight:700; color:#0f172a; font-size:0.95rem;">
                                {title}
                            </div>
                            <div>{status_badge}</div>
                        </div>
                        <div style="font-size:0.8rem; color:#64748b; margin-top:4px;">
                            <code>{ccode}</code> | ID: <code>{lid}</code> | Topic: {topic} | {dur} mins
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Quick Launch button for lectures that are not yet COMPLETED
                    if status != "COMPLETED":
                        col_btn1, col_btn2 = st.columns([1, 1])
                        with col_btn1:
                            if is_active and active_lecture_title == title:
                                st.success("● Currently Running Live")
                            elif not is_active:
                                if st.button(f"▶️ Launch Live Session", key=f"launch_{lid}", use_container_width=True):
                                    with st.spinner("Starting session for this lecture..."):
                                        res = api_client.start_session(course_code=ccode, title=title, lecture_id=lid)
                                    if res and (res.get("success") or res.get("status") == "success"):
                                        st.success(f"Session started for {title}!")
                                        st.rerun()
                                    else:
                                        st.error(res.get("detail", "Failed to start session"))

                        with col_btn2:
                            if is_active and active_lecture_title == title:
                                if st.button(f"⏹️ End Session", key=f"end_{lid}", use_container_width=True):
                                    with st.spinner("Finalizing session..."):
                                        res = api_client.stop_session()
                                    if res and res.get("success"):
                                        st.success("Session finalized.")
                                        st.rerun()
                                    else:
                                        st.error("Failed to stop session.")


def render_courses_tab():
    courses_resp = api_client.get_teacher_courses()
    courses = courses_resp.get("courses", []) if courses_resp else []

    c1, c2 = st.columns([1.1, 1.4])

    with c1:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>➕ Register New Course</h3>", unsafe_allow_html=True)
            ccode = st.text_input("Course Code *", placeholder="e.g. CS102", key="new_ccode")
            ctitle = st.text_input("Course Title *", placeholder="e.g. Object Oriented Programming", key="new_ctitle")
            cdesc = st.text_area("Course Syllabus Summary", placeholder="Brief description of subjects...", key="new_cdesc")

            if st.button("🏛️ Create Course", type="primary", use_container_width=True):
                if not ccode.strip() or not ctitle.strip():
                    st.error("Both Course Code and Title are required.")
                else:
                    with st.spinner("Creating course..."):
                        res = api_client.create_course(
                            course_code=ccode.strip().upper(),
                            title=ctitle.strip(),
                            description=cdesc.strip() if cdesc.strip() else None
                        )
                    if res and (res.get("success") or res.get("status") == "success"):
                        st.success(f"Course {ccode.upper()} registered successfully!")
                        st.rerun()
                    else:
                        st.error(res.get("detail", "Failed to create course."))

    with c2:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>📚 Enrolled Courses</h3>", unsafe_allow_html=True)
            if not courses:
                st.info("No courses registered yet. Create one using the form.")
            else:
                headers = ["Code", "Course Title", "Description", "Created"]
                rows = []
                for c in courses:
                    dt = c.get("created_at", "Recorded")
                    date_str = dt[:10] if isinstance(dt, str) else "Recorded"
                    rows.append([
                        f"<code>{c.get('course_code')}</code>",
                        f"<b>{c.get('title')}</b>",
                        c.get("description") or "—",
                        date_str
                    ])
                ui.render_html_table(headers, rows)

                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
                with st.expander("🗑️ Remove Course from System", expanded=False):
                    course_dict = {f"{c.get('course_code')} - {c.get('title')}": c.get('course_code') for c in courses}
                    sel_course_label = st.selectbox("Select Course to Remove", options=list(course_dict.keys()), key="sel_del_course")
                    del_code = course_dict.get(sel_course_label)

                    st.warning(f"⚠️ Removing **{del_code}** will permanently delete the course, its scheduled lectures, and student enrollment links.")
                    confirm_del = st.checkbox(f"Confirm permanent deletion of course {del_code}", key="confirm_del_course_box")

                    if st.button("🗑️ Delete Course Permanently", type="primary", key="btn_del_course", disabled=not confirm_del, use_container_width=True):
                        with st.spinner(f"Deleting course {del_code}..."):
                            res = api_client.delete_course(del_code)
                        if res and (res.get("success") or res.get("status") == "success"):
                            st.success(f"✅ Course {del_code} successfully removed!")
                            import time
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            err_detail = res.get("detail", "Failed to delete course.") if isinstance(res, dict) else "Failed to delete course. Please verify backend connection."
                            st.error(f"❌ {err_detail}")
