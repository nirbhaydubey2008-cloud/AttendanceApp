"""
dashboard/views/student/courses.py
Student Portal: Enrolled Academic Courses
Displays courses the student is officially enrolled in, along with
curricula summaries and academic attendance expectations.
"""

import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="My Enrolled Courses",
        description="Academic courses and curricula registered under your student profile."
    )

    courses_resp = api_client.get_student_courses() or {}
    courses = courses_resp.get("courses", [])

    if not courses:
        st.info("No courses currently enrolled under your student profile. Please contact your academic instructor to assign you to a course.")
        return

    st.markdown(f"#### Officially Enrolled Courses ({len(courses)})")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        for c in courses:
            ccode = c.get("course_code", "GEN")
            title = c.get("course_title", "Course")
            enrolled_at = c.get("enrolled_at", "Recorded")[:10]

            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="font-size:1.1rem; font-weight:700; color:#0f172a;">{title}</div>
                        <div style="color:#2563eb; font-weight:600; font-size:0.85rem; margin-top:2px;">
                            Course Code: <code>{ccode}</code>
                        </div>
                    </div>
                    <span class="badge badge-present">Enrolled Active</span>
                </div>
                <div style="font-size:0.83rem; color:#64748b; margin-top:10px; border-top:1px solid #f1f5f9; padding-top:8px;">
                    📅 <b>Registration Date:</b> {enrolled_at} &nbsp;|&nbsp; 🎓 <b>Attendance Requirement:</b> 75% Verified Presence
                </div>
                """, unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>📋 Institutional Policy</h4>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size:0.85rem; color:#475569; line-height:1.7;">
                ● <b>75% Attendance Requirement:</b> The university mandates a minimum of 75% verified presence in each enrolled course to be eligible for end-term examinations.<br>
                ● <b>Biometric Verification:</b> Presence is registered by the classroom AI agent when you are visually present in the camera scene during active lectures.<br>
                ● <b>Queries / Discrepancies:</b> If you notice an attendance discrepancy, contact your course faculty directly.
            </div>
            """, unsafe_allow_html=True)
