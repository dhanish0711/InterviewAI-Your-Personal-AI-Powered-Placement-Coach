import streamlit as st
import os
import plotly.graph_objects as go
from pypdf import PdfReader
from dotenv import load_dotenv
from database import save_resume, get_resume
from ai_service import parse_resume_with_ai, evaluate_ats_compatibility

load_dotenv(override=True)

# Page configuration
st.set_page_config(page_title="Resume Analyst & ATS Optimizer - InterviewAI", page_icon="📄", layout="wide")

# Load CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── IBM credentials (for all text AI) ──
env_key = os.getenv("WATSONX_APIKEY") or os.getenv("IBM_API_KEY") or os.getenv("WATSONX_API_KEY") or ""
if "ibm_api_key" not in st.session_state or not st.session_state.ibm_api_key:
    st.session_state.ibm_api_key = env_key
if "ibm_project_id" not in st.session_state:
    st.session_state.ibm_project_id = os.getenv("IBM_PROJECT_ID") or os.getenv("WATSONX_PROJECT_ID") or ""

st.session_state.api_key = st.session_state.ibm_api_key

st.markdown("<h2>📄 Resume Analyst & <span class='accent-header'>ATS Optimizer</span></h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #94A3B8;'>Upload your PDF resume to extract structured data and test compatibility against job descriptions.</p>", unsafe_allow_html=True)

# Auth check
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please log in first to manage your resume.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_👤_Login.py")
    st.stop()

user_id = st.session_state.user['id']
ibm_key = st.session_state.ibm_api_key
project_id = st.session_state.ibm_project_id

# IBM Credentials check
if not ibm_key or not project_id:
    st.error("⚠️ IBM Granite credentials missing. Please go to ⚙️ Settings and add your IBM API Key and Project ID.")
    st.stop()

def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

existing_resume = get_resume(user_id)
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📤 Upload Your Resume (PDF)")
    uploaded_file = st.file_uploader("Upload resume PDF", type=["pdf"])

    if uploaded_file is not None:
        if st.button("🤖 Parse Resume with AI", use_container_width=True):
            with st.spinner("Extracting content and structuring with AI..."):
                raw_text = extract_text_from_pdf(uploaded_file)
                if raw_text and len(raw_text) > 50:
                    parsed_data = parse_resume_with_ai(raw_text, api_key=ibm_key,
                        project_id=project_id)
                    save_resume(
                        user_id=user_id,
                        file_name=uploaded_file.name,
                        extracted_text=raw_text,
                        skills=parsed_data.get("skills", []),
                        projects=parsed_data.get("projects", []),
                        experience=parsed_data.get("experience", [])
                    )
                    st.success("✅ Resume parsed and saved! Refreshing...")
                    st.rerun()
                else:
                    st.error("Could not extract text from this PDF. Please try a text-based PDF (not scanned image).")

    st.markdown("### 👤 Extracted Profile")
    if existing_resume:
        st.markdown(f"**File:** `{existing_resume['file_name']}` • Uploaded: `{existing_resume['uploaded_at'][:10]}`")

        st.markdown("#### 🛠️ Skills")
        skills = existing_resume.get("skills", [])
        if skills:
            skills_html = "".join([f"<span class='badge badge-info' style='margin-right:6px;margin-bottom:6px;'>{s}</span>" for s in skills])
            st.markdown(f"<div style='margin-bottom:15px;'>{skills_html}</div>", unsafe_allow_html=True)
        else:
            st.info("No skills detected.")

        st.markdown("#### 💼 Experience")
        exp = existing_resume.get("experience", [])
        if exp:
            for job in exp:
                st.markdown(f"""
                <div class='glass-card' style='padding:15px; margin-bottom:10px;'>
                    <div style='display:flex; justify-content:space-between;'>
                        <strong>{job.get('role','N/A')}</strong>
                        <span style='color:#818CF8;'>{job.get('duration','N/A')}</span>
                    </div>
                    <div style='color:#94A3B8;font-size:0.9rem;'>{job.get('company','N/A')}</div>
                    <p style='font-size:0.85rem;margin-top:5px;'>{job.get('description','N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No work experience detected.")

        st.markdown("#### 🚀 Projects")
        projects = existing_resume.get("projects", [])
        if projects:
            for proj in projects:
                techs = "".join([f"<span class='badge' style='background:rgba(192,132,252,0.1);color:#C084FC;margin-right:5px;font-size:0.75rem;'>{t}</span>" for t in proj.get('technologies', [])])
                st.markdown(f"""
                <div class='glass-card' style='padding:15px;margin-bottom:10px;'>
                    <strong>{proj.get('title','N/A')}</strong>
                    <p style='font-size:0.85rem;margin-top:5px;color:#E2E8F0;'>{proj.get('description','N/A')}</p>
                    <div style='margin-top:5px;'>{techs}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No projects detected.")
    else:
        st.info("📎 Upload and parse a PDF resume above to populate your profile.")

with col2:
    st.markdown("### 💼 Job Description ATS Match")
    job_description = st.text_area("Paste the Job Description (JD) here:", height=220,
                                   placeholder="Paste the full job description including required skills...")

    if st.button("🔍 Run ATS Compatibility Check", use_container_width=True):
        if not existing_resume:
            st.error("Please upload and parse your resume first (left column).")
        elif not job_description.strip():
            st.error("Please paste a job description first.")
        else:
            with st.spinner("Analyzing keyword match and computing ATS score..."):
                analysis = evaluate_ats_compatibility(
                    resume_text=existing_resume['extracted_text'],
                    job_description=job_description,
                    api_key=ibm_key,
                    project_id=project_id
                )
                st.session_state.ats_result = analysis
                st.success("✅ ATS analysis complete!")

    if "ats_result" in st.session_state:
        res = st.session_state.ats_result
        score = res.get("score", 0)

        # Gauge Chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "ATS Fit Score", 'font': {'color': '#F8FAFC', 'size': 18}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#F8FAFC"},
                'bar': {'color': "#818CF8"},
                'bgcolor': "rgba(30, 41, 59, 0.5)",
                'borderwidth': 2,
                'bordercolor': "rgba(255,255,255,0.05)",
                'steps': [
                    {'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.2)'},
                    {'range': [50, 75], 'color': 'rgba(245, 158, 11, 0.2)'},
                    {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.2)'}
                ]
            }
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#F8FAFC", 'family': "Inter"},
            height=250, margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div class='glass-card'>
            <h4>🔍 Match Assessment</h4>
            <p style='font-size:0.95rem;line-height:1.5;'>{res.get('match_analysis','')}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### ❌ Missing Keywords / Skills")
        missing = res.get("missing_skills", [])
        if missing:
            missing_html = "".join([f"<span class='badge badge-danger' style='margin-right:8px;margin-bottom:8px;'>{m}</span>" for m in missing])
            st.markdown(f"<div>{missing_html}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='badge badge-success'>✅ No critical missing skills!</span>", unsafe_allow_html=True)

        st.markdown("#### 💡 AI-Optimized Bullet Rewrites")
        suggestions = res.get("suggestions", [])
        for sugg in suggestions:
            st.markdown(f"""
            <div class='glass-card' style='padding:15px;margin-bottom:12px;border-left:4px solid #C084FC;'>
                <div style='color:#EF4444;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>Original</div>
                <p style='font-size:0.9rem;font-style:italic;margin-bottom:8px;'>"{sugg.get('original_bullet','')}"</p>
                <div style='color:#10B981;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>AI Improved (STAR)</div>
                <p style='font-size:0.95rem;font-weight:500;color:#10B981;margin-bottom:8px;'>"{sugg.get('improved_bullet','')}"</p>
                <div style='color:#94A3B8;font-size:0.8rem;'><strong>Why:</strong> {sugg.get('rationale','')}</div>
            </div>
            """, unsafe_allow_html=True)
