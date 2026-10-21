"""
dashboard/components/ui.py
Shared UI Design System, Modern Light Theme Styles, and Reusable Layout Components.
"""

from typing import List, Dict, Optional, Any
import streamlit as st


def apply_light_theme():
    """Applies a clean, modern, professional light-theme design system."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap');

        /* Global Typography & Base */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #1e293b;
        }

        h1, h2, h3, h4, .outfit-font {
            font-family: 'Outfit', sans-serif;
            color: #0f172a;
            letter-spacing: -0.02em;
        }

        .stApp {
            background-color: #f8fafc;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        [data-testid="stSidebar"] hr {
            margin: 1rem 0;
            border-color: #f1f5f9;
        }

        /* White Cards & Native Containers */
        .white-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }
        .white-card:empty {
            display: none !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
        }
        .white-card:hover {
            border-color: #cbd5e1;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }

        /* Streamlit Bordered Containers styled as modern cards */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03) !important;
            margin-bottom: 16px !important;
            padding: 4px !important;
        }

        /* Metric KPI Stat Box */
        .stat-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
            text-align: left;
        }
        .stat-card-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 6px;
        }
        .stat-card-value {
            font-family: 'Outfit', sans-serif;
            font-size: 2.0rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.1;
        }
        .stat-card-sub {
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 6px;
        }

        /* Status Badges */
        .badge {
            display: inline-block;
            padding: 3px 9px;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .badge-present {
            background-color: #ecfdf5;
            color: #059669;
            border: 1px solid #a7f3d0;
        }
        .badge-partial {
            background-color: #fffbeb;
            color: #d97706;
            border: 1px solid #fde68a;
        }
        .badge-absent {
            background-color: #fff1f2;
            color: #e11d48;
            border: 1px solid #fecdd3;
        }

        /* Recommendation Priority Badges */
        .badge-urgent {
            background-color: #fff1f2;
            color: #e11d48;
            border: 1px solid #fecdd3;
        }
        .badge-warning {
            background-color: #fffbeb;
            color: #d97706;
            border: 1px solid #fde68a;
        }
        .badge-info {
            background-color: #eff6ff;
            color: #2563eb;
            border: 1px solid #bfdbfe;
        }

        /* Recommendation Ribbon */
        .rec-card-urgent {
            border-left: 4px solid #ef4444 !important;
            background: #fffafa !important;
        }
        .rec-card-warning {
            border-left: 4px solid #f59e0b !important;
            background: #fffdfa !important;
        }
        .rec-card-info {
            border-left: 4px solid #3b82f6 !important;
            background: #f8faff !important;
        }

        /* Buttons & Forms */
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.15s ease;
        }
        .stButton>button[kind="primary"] {
            background-color: #4f46e5;
            border-color: #4f46e5;
            color: #ffffff;
        }
        .stButton>button[kind="primary"]:hover {
            background-color: #4338ca;
            border-color: #4338ca;
        }

        /* Video Display Box */
        .video-box {
            background-color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        }
    </style>
    """, unsafe_allow_html=True)


def render_page_header(title: str, description: str):
    """Renders standardized top section for each page."""
    st.markdown(f"""
    <div style="margin-bottom: 22px;">
        <h2 style="margin: 0; font-size: 1.75rem; font-weight: 700; color: #0f172a;">{title}</h2>
        <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.92rem;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_top_system_bar(health: Optional[Dict[str, Any]], session: Optional[Dict[str, Any]]):
    """Top bar displaying backend status, hardware camera state, and active session."""
    c1, c2, c3 = st.columns([2.5, 1.3, 1.2])

    with c1:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: #4f46e5; color: white; width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: bold;">
                🎓
            </div>
            <div>
                <div style="font-weight: 700; font-size: 1.05rem; color: #0f172a; line-height: 1.2;">Attendance & Engagement Agent</div>
                <div style="color: #64748b; font-size: 0.75rem;">Offline-First Multimodal AI Perception System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        if health:
            cam_active = health.get("camera_active", False)
            cam_fallback = health.get("camera_fallback", False)
            cam_text = "Synthetic Stream" if cam_fallback else "Hardware Webcam"
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 6px 10px; font-size: 0.76rem;">
                <div style="color: #16a34a; font-weight: 600;">● Backend Online (Port 8000)</div>
                <div style="color: #64748b;">Camera: {cam_text}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 6px 10px; font-size: 0.76rem;">
                <div style="color: #dc2626; font-weight: 600;">○ Backend Offline</div>
                <div style="color: #64748b;">Run uvicorn api.main:app</div>
            </div>
            """, unsafe_allow_html=True)

    with c3:
        is_active = session and session.get("is_active", False)
        if is_active:
            elapsed = session.get("elapsed_seconds", 0.0)
            mins, secs = divmod(int(elapsed), 60)
            st.markdown(f"""
            <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 6px 10px; font-size: 0.76rem;">
                <div style="color: #2563eb; font-weight: 600;">● Active: {session.get('course_code', 'CS101')}</div>
                <div style="color: #64748b;">Elapsed: <b>{mins:02d}:{secs:02d}</b></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 10px; font-size: 0.76rem;">
                <div style="color: #64748b; font-weight: 600;">○ Session Idle</div>
                <div style="color: #94a3b8;">Ready to start</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='margin: 10px 0 20px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)


def render_html_table(headers: List[str], rows: List[List[Any]], empty_message: str = "No records found."):
    """Renders a clean, styled HTML table that never triggers PyArrow serialization errors."""
    if not rows:
        st.info(empty_message)
        return

    th_html = "".join([f'<th style="padding: 10px 14px; font-weight: 600; color: #475569; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em;">{h}</th>' for h in headers])

    tr_html = ""
    for r in rows:
        td_html = ""
        for cell in r:
            td_html += f'<td style="padding: 11px 14px; color: #1e293b; font-size: 0.86rem; border-top: 1px solid #f1f5f9;">{cell}</td>'
        tr_html += f'<tr style="transition: background 0.15s;" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'transparent\'">{td_html}</tr>'

    html = f"""
    <div style="overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 10px; background: #ffffff;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">{th_html}</tr>
            </thead>
            <tbody>{tr_html}</tbody>
        </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
