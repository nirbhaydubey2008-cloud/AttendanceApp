"""
dashboard/pages/recommendations.py
Page 5: Teaching Recommendations — Rule-based AI suggestions, evidence, explanations, and recommended actions.
"""

import time
import streamlit as st
from dashboard.components import api_client, ui


def render():
    ui.render_page_header(
        title="AI Pedagogical Recommendations",
        description="Real-time rule-based pedagogical insights with debounce cooldowns, evidence explanations, and actionable classroom interventions."
    )

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("⚡ Evaluate Current Telemetry Now", use_container_width=True, type="primary"):
            with st.spinner("Evaluating classroom telemetry rules..."):
                res = api_client.evaluate_recommendations()
                if res:
                    st.success(f"Evaluated! Triggered: {res.get('triggered_count', 0)} new recommendation(s).")
                    time.sleep(0.5)
                    st.rerun()

    with col_info:
        st.markdown("""
        <div style="font-size:0.83rem; color:#64748b; line-height:1.4;">
            <b>Debounce Cooldown:</b> 30 seconds per rule to prevent alert fatigue.<br>
            <b>Priority Tiers:</b> <span class="badge badge-urgent">URGENT</span> <span class="badge badge-warning">WARNING</span> <span class="badge badge-info">INFO</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    recent_recs = api_client.get_recent_recommendations(limit=15)
    recs_list = recent_recs.get("recommendations", []) if recent_recs else []

    if not recs_list:
        st.info("ℹ️ No active recommendations triggered yet. Suggestions trigger dynamically when attention dips, gaze diverges, or acoustic disturbance occurs.")
    else:
        for rec in recs_list:
            priority = rec.get("priority", "INFO")
            p_class = f"rec-card-{priority.lower()}"
            badge_class = f"badge-{priority.lower()}"
            title = rec.get("title", "Pedagogical Insight")
            desc = rec.get("suggestion_text", "")
            steps = rec.get("actionable_steps", [])
            trigger = rec.get("trigger_type", "TELEMETRY_RULE")

            st.markdown(f"""
            <div class="white-card {p_class}" style="margin-bottom: 16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span class="badge {badge_class}">{priority}</span>
                    <span style="font-size: 0.78rem; color: #64748b;">Rule Code: <code>{trigger}</code></span>
                </div>
                <h3 style="margin: 4px 0 6px 0; color: #0f172a; font-size: 1.2rem;">💡 {title}</h3>
                <p style="margin: 0 0 10px 0; color: #334155; font-size: 0.95rem; line-height: 1.5;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

            if steps:
                with st.expander(f"Recommended Action Steps for: {title}"):
                    for s in steps:
                        st.markdown(f"- {s}")

    # Rules Engine Specification Card
    with st.container(border=True):
        st.markdown("<h3 style='margin-top:0;'>📖 Active Pedagogical Rule Catalog</h3>", unsafe_allow_html=True)

        rule_headers = ["Rule Name", "Trigger Condition", "Priority", "Pedagogical Objective"]
        rule_rows = [
            ["<b>Low Engagement Alert</b>", "Average engagement < 50% (< 35% Urgent)", '<span class="badge badge-warning">WARNING</span>', "Mitigate attention fatigue via formative check-ins"],
            ["<b>Acoustic Disturbance</b>", "Audio state == DISTURBANCE (> -18 dBFS)", '<span class="badge badge-warning">WARNING</span>', "Pause briefly and re-establish classroom focus"],
            ["<b>Gaze Aversion Divergence</b>", "Forward visual focus < 45% (≥ 2 students)", '<span class="badge badge-info">INFO</span>', "Direct student focus explicitly to whiteboard/display"],
            ["<b>Optimal Attention Window</b>", "Average engagement ≥ 82%", '<span class="badge badge-info">INFO</span>', "Introduce complex or conceptually dense material"],
            ["<b>Low Attendance Alert</b>", "Presence ratio < 60% after 2 minutes", '<span class="badge badge-warning">WARNING</span>', "Verify attendance roster and camera visibility"]
        ]
        ui.render_html_table(rule_headers, rule_rows)
