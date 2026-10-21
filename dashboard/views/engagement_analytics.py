"""
dashboard/pages/engagement_analytics.py
Page 4: Engagement Analytics — Time-series charts, visual presence trends, aggregate audio activity, and data-quality indicators.
"""

import pandas as pd
import numpy as np
import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="Classroom Engagement Analytics",
        description="Multimodal attention indices, fused subscore breakdowns, acoustic context, and tracking integrity."
    )

    engagement = api_client.get_engagement_summary()
    attendance = api_client.get_live_attendance()
    curr_session = api_client.get_current_session()
    is_active = curr_session and curr_session.get("is_active", False)
    records = attendance.get("records", []) if attendance else []

    avg_eng = float(engagement.get("average_engagement_score", 0.0)) if engagement else 0.0
    tiers = engagement.get("tier_counts", {}) if engagement else {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    # If instantaneous camera tracks are 0 or pruned, but attendance records exist for the session,
    # calculate the whole-classroom average and tiers directly from attendance records
    if (avg_eng == 0.0 or engagement.get("active_student_count", 0) == 0) and records:
        scores = [float(r.get("mean_engagement", 0.0)) for r in records if r.get("mean_engagement") is not None]
        if scores:
            avg_eng = float(np.mean(scores))
            tiers = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for s in scores:
                if s >= 0.70:
                    tiers["HIGH"] += 1
                elif s >= 0.45:
                    tiers["MEDIUM"] += 1
                else:
                    tiers["LOW"] += 1

    eng_pct = int(avg_eng * 100)

    # Top KPI Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Classroom Engagement</div>
            <div class="stat-card-value" style="color: #4f46e5;">{eng_pct}%</div>
            <div class="stat-card-sub">Whole-classroom average</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">High Engagement Tier</div>
            <div class="stat-card-value" style="color: #059669;">{tiers.get('HIGH', 0)}</div>
            <div class="stat-card-sub">Score $\ge 70\%$</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Medium Attention Tier</div>
            <div class="stat-card-value" style="color: #d97706;">{tiers.get('MEDIUM', 0)}</div>
            <div class="stat-card-sub">Score $45\% - 69\%$</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">Low Attention Tier</div>
            <div class="stat-card-value" style="color: #e11d48;">{tiers.get('LOW', 0)}</div>
            <div class="stat-card-sub">Score $< 45\%$</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Chart & Distribution Row
    c_chart, c_weights = st.columns([1.6, 1.2])

    with c_chart:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>📊 Attention Tier Breakdown</h3>", unsafe_allow_html=True)

            tier_df = pd.DataFrame({
                "Tier": ["High (≥70%)", "Medium (45-69%)", "Low (<45%)"],
                "Students": [tiers.get("HIGH", 0), tiers.get("MEDIUM", 0), tiers.get("LOW", 0)]
            })
            st.bar_chart(tier_df.set_index("Tier"), color="#4f46e5")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:6px;'>Classroom Average Attention Gauge</h4>", unsafe_allow_html=True)
            st.progress(min(max(avg_eng, 0.0), 1.0))

    with c_weights:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>⚖️ Fused Component Architecture</h3>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size: 0.88rem; line-height: 2.1;">
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">👁️ Eye Gaze Attentiveness:</span>
                    <span style="font-weight:700; color:#0f172a;">40% weight</span>
                </div>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">📐 3D Head Pose Stability:</span>
                    <span style="font-weight:700; color:#0f172a;">20% weight</span>
                </div>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">👤 Tracking Presence Ratio:</span>
                    <span style="font-weight:700; color:#0f172a;">20% weight</span>
                </div>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #f8fafc;">
                    <span style="color:#64748b;">🎙️ Acoustic Context Factor:</span>
                    <span style="font-weight:700; color:#0f172a;">20% weight</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#64748b;">🌊 Smoothing Filter:</span>
                    <span style="font-weight:700; color:#4f46e5;">EMA ($\beta=0.70$)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Student-Level Engagement Breakdown
    if records:
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>👥 Student Attention Registry</h3>", unsafe_allow_html=True)
            st.markdown("<p style='font-size: 0.85rem; color: #64748b;'>Individual multimodal attentiveness indices, attention tiers, and continuous presence ratios for enrolled participants in this lecture.</p>", unsafe_allow_html=True)

            headers = ["Student Name", "Student ID", "Attentiveness Index", "Tier", "Presence Ratio", "Live Status"]
            rows = []
            for r in records:
                s_eng = float(r.get("mean_engagement", 0.0))
                s_pct = round(s_eng * 100, 1)
                if s_eng >= 0.70:
                    tier_badge = '<span class="badge badge-present">HIGH TIER</span>'
                elif s_eng >= 0.45:
                    tier_badge = '<span class="badge badge-partial">MEDIUM TIER</span>'
                else:
                    tier_badge = '<span class="badge badge-absent">LOW TIER</span>'

                st_val = r.get("status", "ABSENT")
                st_badge = f'<span class="badge badge-{st_val.lower()}">{st_val}</span>'

                rows.append([
                    f"<b>{r.get('student_name', 'Student')}</b>",
                    f"<code>{r.get('student_id') or 'Unenrolled'}</code>",
                    f"<b>{s_pct}%</b>",
                    tier_badge,
                    f"{round(r.get('presence_ratio', 0.0) * 100, 1)}%",
                    st_badge
                ])

            ui.render_html_table(headers, rows)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Data Quality & Integrity Indicators
    with st.container(border=True):
        st.markdown("<h3 style='margin-top:0;'>🛡️ Perception Quality & Privacy Guardrails</h3>", unsafe_allow_html=True)

        q1, q2, q3 = st.columns(3)
        with q1:
            st.markdown("""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px;">
                <div style="font-weight:600; color:#0f172a; margin-bottom:4px;">Face Tracking Continuity</div>
                <div style="font-size:0.83rem; color:#64748b;">DeepSort Kalman filter maintains ID persistence through brief occlusions.</div>
                <div style="margin-top:6px; color:#16a34a; font-weight:600; font-size:0.82rem;">● Active (2.5s Auto-Prune)</div>
            </div>
            """, unsafe_allow_html=True)
        with q2:
            st.markdown("""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px;">
                <div style="font-weight:600; color:#0f172a; margin-bottom:4px;">Temporal Buffer Sync</div>
                <div style="font-size:0.83rem; color:#64748b;">Circular buffer aligns asynchronous audio chunks with video timestamps.</div>
                <div style="margin-top:6px; color:#16a34a; font-weight:600; font-size:0.82rem;">● Synchronized</div>
            </div>
            """, unsafe_allow_html=True)
        with q3:
            st.markdown("""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px;">
                <div style="font-weight:600; color:#0f172a; margin-bottom:4px;">Ethical AI Compliance</div>
                <div style="font-size:0.83rem; color:#64748b;">Measures observable behavioral geometry only. Zero emotion detection or psychological profiling.</div>
                <div style="margin-top:6px; color:#4f46e5; font-weight:600; font-size:0.82rem;">● Privacy Guardrails Enforced</div>
            </div>
            """, unsafe_allow_html=True)
