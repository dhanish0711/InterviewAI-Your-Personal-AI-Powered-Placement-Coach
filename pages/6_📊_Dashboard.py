import streamlit as st
import os
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from database import get_user_stats, get_past_interviews, get_interview_details, get_connection

st.set_page_config(page_title="Dashboard - InterviewAI", page_icon="📊", layout="wide")

css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please log in first.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_👤_Login.py")
    st.stop()

user_id = st.session_state.user["id"]
username = st.session_state.user["username"]

# ── Load all stats (safe defaults so nothing crashes if tables empty) ──
stats = get_user_stats(user_id)
past_list = get_past_interviews(user_id)

# ── Also pull coding history separately for chart ──
def get_coding_history(user_id):
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT problem_name, language, score, date FROM coding_history WHERE user_id=? ORDER BY date DESC LIMIT 20",
            (user_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_mcq_history(user_id):
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT mode, score, total, time_taken_sec, taken_at FROM mcq_results WHERE user_id=? ORDER BY taken_at DESC LIMIT 20",
            (user_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

coding_history = get_coding_history(user_id)
mcq_history = get_mcq_history(user_id)

# ── PDF report generator ──
def generate_pdf_report(data):
    header_info = data["header"]
    details = data["details"]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 40, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, "InterviewAI – Detailed Evaluation Report", 0, 1, "C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {header_info.get('date','')}  |  Track: {header_info.get('type','')}", 0, 1, "C")
    pdf.ln(12)
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Overall Summary", 0, 1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(100, 7, f"Score: {header_info.get('overall_score','N/A')}/10", 0, 0)
    pdf.cell(100, 7, f"Filler Words: {header_info.get('filler_words', 0)}", 0, 1)
    pdf.ln(5)
    for idx, item in enumerate(details):
        if pdf.get_y() > 230:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, f"Q{idx+1}: {item.get('question','')}")
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, f"Answer: {item.get('answer','')}")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 5, f"Critique: {item.get('feedback','')}")
        scores = item.get("scores_json", {})
        score_str = (f"Tech: {scores.get('technical_knowledge',0)}/10 | "
                     f"Comm: {scores.get('communication',0)}/10 | "
                     f"STAR: {scores.get('star_structure',0)}/10 | "
                     f"Grammar: {scores.get('grammar',0)}/10")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, score_str, 0, 1)
        pdf.ln(4)
    return pdf.output()


# ──────────────────────── PAGE HEADER ────────────────────────
st.markdown(f"""
<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>
    <div>
        <h2 style='margin:0;'>📊 Performance <span class='accent-header'>Dashboard</span></h2>
        <p style='color:#94A3B8;margin:4px 0 0;'>Complete analytics for <strong>{username}</strong></p>
    </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────── TOP METRIC CARDS ────────────────────────
st.markdown("### 🏆 Your Progress at a Glance")

m1, m2, m3, m4, m5, m6 = st.columns(6)
metrics = [
    (m1, stats.get("total_interviews", 0), "Mock Rounds", "#818CF8"),
    (m2, f"{stats.get('avg_score', 0.0)}/10", "Avg Interview Score", "#10B981"),
    (m3, stats.get("total_coding", 0), "Coding Submitted", "#F59E0B"),
    (m4, f"{stats.get('avg_coding_score', 0.0)}", "Avg Code Score", "#C084FC"),
    (m5, stats.get("mcq_total", 0), "MCQ Tests Taken", "#38BDF8"),
    (m6, f"{stats.get('mcq_avg_pct', 0.0)}%", "Avg MCQ Score", "#FB923C"),
]
for col, val, label, color in metrics:
    col.markdown(f"""
    <div class='glass-card' style='text-align:center;padding:18px 10px;border-top:3px solid {color};'>
        <div style='font-size:1.8rem;font-weight:800;color:{color};line-height:1.2;'>{val}</div>
        <div style='color:#94A3B8;font-size:0.78rem;margin-top:6px;line-height:1.3;'>{label}</div>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────── CHARTS ROW 1 ────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

if stats["total_interviews"] == 0 and not coding_history and not mcq_history:
    st.markdown("""
    <div class='glass-card' style='text-align:center;padding:60px;border-left:4px solid #818CF8;'>
        <div style='font-size:3rem;'>🚀</div>
        <h3>No activity yet!</h3>
        <p style='color:#94A3B8;'>Complete a Mock Interview, solve a Coding problem, or take an MCQ test to see your analytics here.</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🎤 Start Mock Interview", use_container_width=True):
            st.switch_page("pages/3_🎤_Mock_Interview.py")
    with c2:
        if st.button("💻 Coding Sandbox", use_container_width=True):
            st.switch_page("pages/4_💻_Coding_Sandbox.py")
    with c3:
        if st.button("🧠 MCQ Tests", use_container_width=True):
            st.switch_page("pages/5_🧠_MCQ_Tests.py")
    st.stop()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 🕸️ Skill Competency Radar")
    avg_bd = stats.get("avg_breakdown", {})
    categories = list(avg_bd.keys())
    values = list(avg_bd.values())
    if any(v > 0 for v in values):
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(99,102,241,0.2)",
            line=dict(color="#818CF8", width=2.5),
            marker=dict(color="#C084FC", size=6),
            name="Your Scores"
        ))
        # Add benchmark ring at 7.5
        fig_radar.add_trace(go.Scatterpolar(
            r=[7.5] * (len(categories) + 1),
            theta=categories + [categories[0]],
            mode="lines",
            line=dict(color="rgba(251,146,60,0.4)", width=1.5, dash="dot"),
            name="Target (7.5)",
            showlegend=True
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10],
                    gridcolor="rgba(255,255,255,0.07)", linecolor="rgba(255,255,255,0.07)",
                    tickfont=dict(color="#94A3B8", size=10)),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.07)", linecolor="rgba(255,255,255,0.07)",
                    tickfont=dict(color="#E2E8F0", size=11)),
                bgcolor="rgba(15,23,42,0.3)"
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#F8FAFC", "family": "Inter"},
            height=320, margin=dict(l=40, r=40, t=20, b=20),
            legend=dict(font=dict(color="#94A3B8"), bgcolor="rgba(0,0,0,0)")
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Complete interview sessions to populate the radar chart.")

with col2:
    st.markdown("### 📈 Interview Score Trend")
    history_data = stats.get("history", [])
    if len(history_data) >= 1:
        dates = [item["date"].split()[0] for item in history_data]
        scores = [item["overall_score"] for item in history_data]
        types = [item["type"] for item in history_data]

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=list(range(1, len(scores)+1)), y=scores,
            mode="lines+markers+text",
            text=[f"{s}" for s in scores],
            textposition="top center",
            textfont=dict(color="#C084FC", size=11),
            line=dict(color="#818CF8", width=3),
            marker=dict(size=10, color="#C084FC", line=dict(color="#818CF8", width=2)),
            hovertext=types, name="Score"
        ))
        # Target line at 7.5
        fig_line.add_hline(y=7.5, line_dash="dot", line_color="rgba(251,146,60,0.5)",
                           annotation_text="Target 7.5", annotation_font_color="#FB923C")
        fig_line.update_layout(
            xaxis=dict(
                title=dict(text="Session #", font=dict(color="#94A3B8")),
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(color="#94A3B8")
            ),
            yaxis=dict(
                title=dict(text="Score", font=dict(color="#94A3B8")),
                range=[0, 10.5],
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(color="#94A3B8")
            ),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#F8FAFC", "family": "Inter"},
            height=320, margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Complete at least one mock interview to see your score trend.")

# ──────────────────────── CHARTS ROW 2 ────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col3, col4 = st.columns([1, 1], gap="large")

with col3:
    st.markdown("### 💻 Coding Performance")
    if coding_history:
        names = [r["problem_name"][:25] for r in coding_history[:10]][::-1]
        scores_c = [r["score"] for r in coding_history[:10]][::-1]
        colors_c = ["#10B981" if s >= 75 else "#F59E0B" if s >= 50 else "#EF4444" for s in scores_c]
        fig_bar = go.Figure(go.Bar(
            y=names, x=scores_c, orientation="h",
            marker=dict(color=colors_c, line=dict(color="rgba(255,255,255,0.1)", width=1)),
            text=[f"{s:.0f}" for s in scores_c], textposition="outside",
            textfont=dict(color="#E2E8F0")
        ))
        fig_bar.update_layout(
            xaxis=dict(
                range=[0, 110],
                title=dict(text="Score /100", font=dict(color="#94A3B8")),
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(color="#94A3B8")
            ),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#E2E8F0")),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#F8FAFC", "family": "Inter"},
            height=300, margin=dict(l=10, r=30, t=10, b=20)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.markdown("""
        <div class='glass-card' style='text-align:center;padding:40px;'>
            <div style='font-size:2rem;'>💻</div>
            <p style='color:#94A3B8;'>No coding submissions yet.<br>Head to the Coding Sandbox!</p>
        </div>
        """, unsafe_allow_html=True)

with col4:
    st.markdown("### 🧠 MCQ Test History")
    if mcq_history:
        labels_m = [f"{r['mode'].title()} #{i+1}" for i, r in enumerate(reversed(mcq_history[:10]))]
        pcts_m = [round(r["score"] / r["total"] * 100, 1) if r["total"] else 0 for r in reversed(mcq_history[:10])]
        colors_m = ["#10B981" if p >= 70 else "#F59E0B" if p >= 50 else "#EF4444" for p in pcts_m]
        fig_mcq = go.Figure(go.Bar(
            x=labels_m, y=pcts_m,
            marker=dict(color=colors_m, line=dict(color="rgba(255,255,255,0.1)", width=1)),
            text=[f"{p}%" for p in pcts_m], textposition="outside",
            textfont=dict(color="#E2E8F0")
        ))
        fig_mcq.add_hline(y=70, line_dash="dot", line_color="rgba(16,185,129,0.4)",
                          annotation_text="Pass 70%", annotation_font_color="#10B981")
        fig_mcq.update_layout(
            yaxis=dict(
                range=[0, 115],
                title=dict(text="Score %", font=dict(color="#94A3B8")),
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(color="#94A3B8")
            ),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#E2E8F0")),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#F8FAFC", "family": "Inter"},
            height=300, margin=dict(l=10, r=10, t=10, b=20)
        )
        st.plotly_chart(fig_mcq, use_container_width=True)
    else:
        st.markdown("""
        <div class='glass-card' style='text-align:center;padding:40px;'>
            <div style='font-size:2rem;'>🧠</div>
            <p style='color:#94A3B8;'>No MCQ tests completed yet.<br>Try a Technical or Aptitude test!</p>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────── STUDY RECOMMENDATIONS ────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 💡 Personalized Study Recommendations")

avg_bd = stats.get("avg_breakdown", {})
recs = []
if avg_bd.get("Technical Knowledge", 10) < 7.5:
    recs.append(("🛠️ Technical Knowledge", "#EF4444",
        "Your technical scores are below target. Review DSA fundamentals, DBMS concepts, and OOP principles.",
        ["LeetCode DFS/BFS patterns", "SOLID design principles", "SQL joins & normalization"]))
if avg_bd.get("STAR Structure", 10) < 7.0:
    recs.append(("🌟 STAR Method", "#F59E0B",
        "Structure answers clearly: Situation → Task → Action → measurable Result.",
        ["STAR method examples for SWE", "Behavioral interview STAR templates"]))
if avg_bd.get("Communication", 10) < 7.5:
    recs.append(("🎙️ Communication & Fillers", "#3B82F6",
        f"You've used {stats.get('total_filler',0)} filler words across sessions. Practice pausing silently instead.",
        ["How to stop saying 'um' and 'like'", "Professional speech pacing exercises"]))
if avg_bd.get("Grammar", 10) < 8.0:
    recs.append(("✍️ Grammar & Vocabulary", "#8B5CF6",
        "Improve sentence structure and precision. Use active voice and technical terminology correctly.",
        ["Grammarly writing suggestions", "Technical English for interviews"]))
if stats.get("avg_coding_score", 100) < 70:
    recs.append(("💻 Code Quality", "#C084FC",
        "Your code submissions average below 70. Focus on time/space complexity optimization.",
        ["Big-O complexity cheat sheet", "Hash map pattern problems"]))

if recs:
    rec_cols = st.columns(min(len(recs), 3))
    for i, (title, color, desc, links) in enumerate(recs):
        with rec_cols[i % len(rec_cols)]:
            links_html = "".join([f"<li><em>{l}</em></li>" for l in links])
            st.markdown(f"""
            <div class='glass-card' style='border-left:4px solid {color};padding:16px;height:100%;'>
                <strong style='color:{color};font-size:1rem;'>{title}</strong>
                <p style='font-size:0.87rem;color:#E2E8F0;margin:8px 0;line-height:1.5;'>{desc}</p>
                <ul style='font-size:0.8rem;color:#94A3B8;padding-left:16px;margin:0;'>
                    {links_html}
                </ul>
            </div>
            """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class='glass-card' style='border-left:4px solid #10B981;text-align:center;padding:20px;'>
        <strong style='color:#10B981;font-size:1.1rem;'>🎉 Outstanding performance across all metrics!</strong>
        <p style='color:#94A3B8;margin-top:8px;'>Keep practicing to maintain your edge. Try harder interview tracks or personalized MCQs.</p>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────── INTERVIEW TRANSCRIPTS ────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 📝 Interview Session History")

finished = [i for i in past_list if i.get("overall_score") is not None]
if not finished:
    st.info("No completed interview sessions yet. Finish a Mock Interview round to see transcripts here.")
else:
    for item in finished:
        date_str = str(item["date"]).split()[0]
        score = item["overall_score"]
        score_color = "#10B981" if score >= 7.5 else "#F59E0B" if score >= 5 else "#EF4444"
        with st.expander(f"📋 {item['type']} Interview — {date_str} — Score: {score}/10"):
            details_data = get_interview_details(item["id"])
            if details_data:
                hdr = details_data["header"]
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Overall Score", f"{score}/10")
                col_b.metric("Filler Words", hdr.get("filler_words", 0))
                col_c.metric("Speech WPM", hdr.get("wpm", "N/A"))
                col_d.metric("Duration", f"{int(hdr.get('duration',0))}s")

                strengths = hdr.get("strengths", [])
                weaknesses = hdr.get("weaknesses", [])
                if strengths or weaknesses:
                    sw1, sw2 = st.columns(2)
                    with sw1:
                        if strengths:
                            st.markdown("**✅ Strengths:**")
                            for s in strengths:
                                st.markdown(f"• {s}")
                    with sw2:
                        if weaknesses:
                            st.markdown("**⚠️ Areas to Improve:**")
                            for w in weaknesses:
                                st.markdown(f"• {w}")

                # PDF download
                try:
                    pdf_bytes = generate_pdf_report(details_data)
                    st.download_button(
                        "📥 Download PDF Report", data=pdf_bytes,
                        file_name=f"InterviewAI_{item['type']}_{date_str}.pdf",
                        mime="application/pdf", key=f"dl_{item['id']}"
                    )
                except Exception as e:
                    st.warning(f"PDF generation error: {e}")

                st.markdown("---")
                for q_idx, qna in enumerate(details_data["details"]):
                    sub = qna.get("scores_json", {})
                    st.markdown(f"**Q{q_idx+1}:** *{qna.get('question','')}*")
                    st.markdown(f"**Your Answer:** {qna.get('answer','—')}")
                    st.markdown(f"**AI Feedback:** {qna.get('feedback','')}")
                    st.markdown(f"""
                    <div style='background:rgba(129,140,248,0.08);border-radius:6px;padding:6px 12px;font-size:0.83rem;color:#94A3B8;margin-bottom:12px;'>
                    Tech: <strong>{sub.get('technical_knowledge',0)}/10</strong> &nbsp;|&nbsp;
                    Comm: <strong>{sub.get('communication',0)}/10</strong> &nbsp;|&nbsp;
                    STAR: <strong>{sub.get('star_structure',0)}/10</strong> &nbsp;|&nbsp;
                    Grammar: <strong>{sub.get('grammar',0)}/10</strong>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Could not load session details.")
