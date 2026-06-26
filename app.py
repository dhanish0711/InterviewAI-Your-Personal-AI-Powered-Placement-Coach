import streamlit as st
import os
from database import init_db, get_user_stats
from dotenv import load_dotenv

st.set_page_config(
    page_title="InterviewAI - AI Interview Coach",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv(override=True)
init_db()

css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# ── Load IBM credentials into session ──
def _load_env():
    ibm_key = os.getenv("WATSONX_APIKEY") or os.getenv("IBM_API_KEY") or os.getenv("WATSONX_API_KEY") or ""
    ibm_pid = os.getenv("IBM_PROJECT_ID") or os.getenv("WATSONX_PROJECT_ID") or ""
    return ibm_key, ibm_pid

if "ibm_api_key" not in st.session_state:
    k, p = _load_env()
    st.session_state.ibm_api_key = k
    st.session_state.ibm_project_id = p
st.session_state.api_key = st.session_state.ibm_api_key

# ── Sidebar ──
st.sidebar.markdown("""
<div style='text-align:center;padding:20px 0 10px;'>
    <div style='font-size:2.2rem;margin-bottom:4px;'>🎤</div>
    <h2 style='color:#818CF8;margin:0;font-size:1.3rem;letter-spacing:-0.02em;'>InterviewAI</h2>
    <p style='color:#475569;font-size:0.78rem;margin:4px 0 0;'>AI-Powered Placement Coach</p>
</div>
<hr style='border-color:rgba(255,255,255,0.05);margin:12px 0;'>
""", unsafe_allow_html=True)

ibm_key = st.session_state.get("ibm_api_key", "")
project_id = st.session_state.get("ibm_project_id", "")

if not ibm_key or not project_id:
    st.sidebar.warning("⚠️ IBM Granite credentials missing — go to Settings.")
else:
    st.sidebar.markdown("""
    <div style='background:rgba(129,140,248,0.1);border:1px solid rgba(129,140,248,0.2);
                border-radius:8px;padding:8px 12px;font-size:0.82rem;color:#818CF8;margin-bottom:8px;'>
        ✅ IBM Granite Active
    </div>""", unsafe_allow_html=True)

if st.session_state.logged_in:
    uname = st.session_state.user['username']
    st.sidebar.markdown(f"""
    <div style='background:rgba(22,33,54,0.8);padding:14px 16px;border-radius:12px;
                border:1px solid rgba(255,255,255,0.06);margin-bottom:14px;display:flex;align-items:center;gap:12px;'>
        <div style='width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#6366F1,#C084FC);
                    display:flex;align-items:center;justify-content:center;font-weight:800;
                    font-size:1rem;color:white;flex-shrink:0;'>{uname[0].upper()}</div>
        <div>
            <div style='font-size:0.92rem;font-weight:600;color:#F1F5F9;'>{uname}</div>
            <div style='font-size:0.75rem;color:#475569;'>Logged in</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
else:
    st.sidebar.info("👋 Log in to save progress and unlock personalized AI features.")
    if st.sidebar.button("🔑 Login / Register", use_container_width=True):
        st.switch_page("pages/1_👤_Login.py")

# ── Hero Banner ──
st.markdown("""
<div style='text-align:center;padding:48px 20px 32px;'>
    <div style='display:inline-block;background:rgba(99,102,241,0.12);border:1px solid rgba(129,140,248,0.25);
                border-radius:999px;padding:6px 18px;font-size:0.8rem;font-weight:600;color:#818CF8;
                letter-spacing:0.06em;text-transform:uppercase;margin-bottom:20px;'>
        ✦ AI-Powered Placement Preparation
    </div>
    <h1 style='font-size:3.2rem;font-weight:900;letter-spacing:-0.04em;line-height:1.1;margin:0 0 16px;'>
        Ace Every Interview with
        <br><span style='background:linear-gradient(135deg,#818CF8,#C084FC,#38BDF8);
                          -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                          background-clip:text;'>Personalized AI Coaching</span>
    </h1>
    <p style='font-size:1.15rem;color:#94A3B8;max-width:600px;margin:0 auto 28px;line-height:1.7;'>
        Upload your resume once. Get custom mock interviews, coding problems, MCQ tests,
        and a live analytics dashboard — all tailored to <em>your</em> exact profile.
    </p>
</div>
""", unsafe_allow_html=True)

# ── CTA buttons (only when not logged in) ──
if not st.session_state.logged_in:
    _, cta_mid, _ = st.columns([2, 2, 2])
    with cta_mid:
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("🚀 Get Started Free", use_container_width=True):
                st.switch_page("pages/1_👤_Login.py")
        with bc2:
            if st.button("📊 View Dashboard", use_container_width=True):
                st.switch_page("pages/6_📊_Dashboard.py")
    st.markdown("<br>", unsafe_allow_html=True)

# ── Stats bar (when logged in) ──
if st.session_state.logged_in:
    stats = get_user_stats(st.session_state.user['id'])
    s1, s2, s3, s4, s5 = st.columns(5)
    stat_items = [
        (s1, stats['total_interviews'], "Interviews Done", "#818CF8"),
        (s2, f"{stats['avg_score']}/10", "Avg Score", "#10B981"),
        (s3, stats['total_coding'], "Code Submissions", "#C084FC"),
        (s4, stats.get('mcq_total', 0), "MCQ Tests", "#38BDF8"),
        (s5, stats['total_filler'], "Filler Words", "#F59E0B"),
    ]
    for col, val, label, color in stat_items:
        col.markdown(f"""
        <div class='glass-card' style='text-align:center;padding:20px 10px;border-top:2px solid {color};margin-bottom:0;'>
            <div style='font-size:1.7rem;font-weight:800;color:{color};line-height:1;'>{val}</div>
            <div style='font-size:0.73rem;color:#64748B;margin-top:6px;text-transform:uppercase;
                        letter-spacing:0.06em;font-weight:600;'>{label}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    db_col1, db_col2, db_col3 = st.columns([1,1,1])
    with db_col2:
        if st.button("📊 Open Full Dashboard →", use_container_width=True):
            st.switch_page("pages/6_📊_Dashboard.py")
    st.markdown("<br>", unsafe_allow_html=True)

# ── Feature Cards ── (full-width 3-col native Streamlit columns)
st.markdown("""
<div style='text-align:center;margin-bottom:6px;'>
    <span style='font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#475569;'>
        Everything you need
    </span>
</div>
<h3 style='text-align:center;margin-bottom:24px;letter-spacing:-0.02em;'>🛠️ Core Capabilities</h3>
""", unsafe_allow_html=True)

fc1, fc2, fc3 = st.columns(3, gap="medium")

CARD_STYLE = "border-radius:16px;padding:22px;margin-bottom:12px;background:rgba(22,33,54,0.65);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.07);box-shadow:0 8px 32px rgba(0,0,0,0.4);transition:all 0.25s ease;"

with fc1:
    st.markdown(f"""
<div style='{CARD_STYLE}border-top:3px solid #818CF8;'>
    <div style='font-size:1.8rem;margin-bottom:10px;'>📄</div>
    <h4 style='color:#818CF8;margin:0 0 8px;font-size:1rem;'>Resume &amp; ATS Scorer</h4>
    <p style='font-size:0.85rem;color:#94A3B8;line-height:1.6;margin:0;'>
        Parse your PDF resume, extract skills &amp; projects, then get an ATS compatibility score
        against any job description with precise rewrite recommendations.
    </p>
</div>""", unsafe_allow_html=True)

    st.markdown(f"""
<div style='{CARD_STYLE}border-top:3px solid #F59E0B;'>
    <div style='font-size:1.8rem;margin-bottom:10px;'>🧠</div>
    <h4 style='color:#F59E0B;margin:0 0 8px;font-size:1rem;'>MCQ Test Center</h4>
    <p style='font-size:0.85rem;color:#94A3B8;line-height:1.6;margin:0;'>
        Timed tests — Technical questions generated from your resume skills,
        and Aptitude (Quant + Reasoning + Verbal). Full explanations after each attempt.
    </p>
</div>""", unsafe_allow_html=True)

with fc2:
    st.markdown(f"""
<div style='{CARD_STYLE}border-top:3px solid #10B981;'>
    <div style='font-size:1.8rem;margin-bottom:10px;'>🎤</div>
    <h4 style='color:#10B981;margin:0 0 8px;font-size:1rem;'>Voice Mock Interviews</h4>
    <p style='font-size:0.85rem;color:#94A3B8;line-height:1.6;margin:0;'>
        Resume-personalized HR, Technical &amp; Behavioral rounds via voice or text.
        AI grades STAR method, filler words, grammar, and speech pace in real time.
    </p>
</div>""", unsafe_allow_html=True)

    st.markdown(f"""
<div style='{CARD_STYLE}border-top:3px solid #38BDF8;'>
    <div style='font-size:1.8rem;margin-bottom:10px;'>📊</div>
    <h4 style='color:#38BDF8;margin:0 0 8px;font-size:1rem;'>Analytics Dashboard</h4>
    <p style='font-size:0.85rem;color:#94A3B8;line-height:1.6;margin:0;'>
        Radar skill map, score trend graphs, coding &amp; MCQ history, and
        AI-driven study recommendations — all updated after every session.
    </p>
</div>""", unsafe_allow_html=True)

with fc3:
    st.markdown(f"""
<div style='{CARD_STYLE}border-top:3px solid #C084FC;'>
    <div style='font-size:1.8rem;margin-bottom:10px;'>💻</div>
    <h4 style='color:#C084FC;margin:0 0 8px;font-size:1rem;'>AI Coding Sandbox</h4>
    <p style='font-size:0.85rem;color:#94A3B8;line-height:1.6;margin:0;'>
        AI generates coding problems based on your resume tech stack, or choose classic DSA.
        Get time/space complexity analysis and optimized reference solutions.
    </p>
</div>""", unsafe_allow_html=True)

    st.markdown(f"""
<div style='{CARD_STYLE}border-top:3px solid #FB923C;'>
    <div style='font-size:1.8rem;margin-bottom:10px;'>📥</div>
    <h4 style='color:#FB923C;margin:0 0 8px;font-size:1rem;'>PDF Interview Reports</h4>
    <p style='font-size:0.85rem;color:#94A3B8;line-height:1.6;margin:0;'>
        Download a professional PDF for every session — full transcript, per-question
        scores, strengths, weaknesses, and STAR framework analysis.
    </p>
</div>""", unsafe_allow_html=True)

# ── How it works ──
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<h3 style='text-align:center;margin-bottom:24px;'>⚡ How It Works</h3>
""", unsafe_allow_html=True)

hw1, hw2, hw3, hw4 = st.columns(4, gap="medium")
steps = [
    (hw1, "1", "#818CF8", "Upload Resume", "Upload your PDF resume. Our AI extracts skills, projects, and experience to build your profile."),
    (hw2, "2", "#10B981", "Set API Key", "Add your free Groq API key in Settings. Llama 3.3 70B powers all AI features at no cost."),
    (hw3, "3", "#C084FC", "Practice All Modules", "Run mock interviews, solve coding problems, and take MCQ tests — all personalized to your resume."),
    (hw4, "4", "#F59E0B", "Track & Improve", "Check your Dashboard after every session to see which competencies need work and follow the study guide."),
]
for col, num, color, title, desc in steps:
    col.markdown(f"""
<div style='text-align:center;padding:20px 14px;background:rgba(22,33,54,0.5);border-radius:16px;
            border:1px solid rgba(255,255,255,0.06);height:100%;'>
    <div style='width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,{color}33,{color}55);
                border:2px solid {color};display:flex;align-items:center;justify-content:center;
                font-size:1.1rem;font-weight:800;color:{color};margin:0 auto 12px;'>{num}</div>
    <h4 style='color:#F1F5F9;font-size:0.95rem;margin:0 0 8px;'>{title}</h4>
    <p style='font-size:0.82rem;color:#94A3B8;line-height:1.55;margin:0;'>{desc}</p>
</div>
""", unsafe_allow_html=True)

# ── Pro Tips ──
st.markdown("<br>", unsafe_allow_html=True)
tip1, tip2 = st.columns(2, gap="medium")
with tip1:
    st.markdown("""
<div class='glass-card' style='border-left:3px solid #818CF8;'>
    <h4 style='color:#818CF8;margin-top:0;'>💡 Pro Tips</h4>
    <ul style='color:#CBD5E1;padding-left:18px;font-size:0.88rem;line-height:2;margin:0;'>
        <li>Upload your <strong>resume first</strong> — every module personalizes to it.</li>
        <li>Use <strong>Voice Mode</strong> to catch filler words and pacing issues.</li>
        <li>Frame answers using <strong>STAR</strong> — the AI specifically grades it.</li>
        <li>Check the <strong>Dashboard radar</strong> chart to find your weakest skill areas.</li>
    </ul>
</div>
""", unsafe_allow_html=True)
with tip2:
    st.markdown("""
<div class='glass-card' style='border-left:3px solid #10B981;'>
    <h4 style='color:#10B981;margin-top:0;'>🎯 Interview Tracks Available</h4>
    <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;'>
        <div style='background:rgba(129,140,248,0.08);border-radius:8px;padding:10px;text-align:center;
                    border:1px solid rgba(129,140,248,0.15);font-size:0.83rem;color:#E2E8F0;'>
            💼 HR Round
        </div>
        <div style='background:rgba(192,132,252,0.08);border-radius:8px;padding:10px;text-align:center;
                    border:1px solid rgba(192,132,252,0.15);font-size:0.83rem;color:#E2E8F0;'>
            🔧 Technical
        </div>
        <div style='background:rgba(16,185,129,0.08);border-radius:8px;padding:10px;text-align:center;
                    border:1px solid rgba(16,185,129,0.15);font-size:0.83rem;color:#E2E8F0;'>
            👔 Behavioral
        </div>
        <div style='background:rgba(245,158,11,0.08);border-radius:8px;padding:10px;text-align:center;
                    border:1px solid rgba(245,158,11,0.15);font-size:0.83rem;color:#E2E8F0;'>
            📊 Managerial
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Footer ──
st.markdown("""
<hr style='border-color:rgba(255,255,255,0.04);margin:40px 0 20px;'>
<div style='text-align:center;padding-bottom:20px;'>
    <p style='color:#334155;font-size:0.83rem;margin:0;'>
        © 2026 <strong style='color:#475569;'>InterviewAI</strong> &nbsp;·&nbsp;
        Powered by <strong style='color:#6366F1;'>Groq Llama 3.3 70B</strong> &nbsp;·&nbsp;
        Built with <strong style='color:#475569;'>Streamlit</strong>
    </p>
</div>
""", unsafe_allow_html=True)
