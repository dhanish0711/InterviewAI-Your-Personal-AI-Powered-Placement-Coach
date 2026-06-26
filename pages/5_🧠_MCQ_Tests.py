import streamlit as st
import os
import time
from dotenv import load_dotenv
from database import get_resume, get_connection
from gemini_service import generate_mcq_test

load_dotenv(override=True)

st.set_page_config(page_title="MCQ Tests - InterviewAI", page_icon="🧠", layout="wide")

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

st.markdown("<h2>🧠 MCQ Test Center & <span class='accent-header'>Instant Scoring</span></h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#94A3B8;'>Timed multiple-choice tests — Technical (personalized from your resume) and Aptitude.</p>", unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please log in first.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_👤_Login.py")
    st.stop()

ibm_key = st.session_state.ibm_api_key
project_id = st.session_state.ibm_project_id

if not ibm_key or not project_id:
    st.error("⚠️ IBM Granite credentials missing. Please go to ⚙️ Settings and add your IBM API Key and Project ID.")
    st.stop()

user_id = st.session_state.user["id"]
resume = get_resume(user_id)

# ─── Session state init ───
for k, v in [
    ("mcq_active", False), ("mcq_questions", []), ("mcq_answers", {}),
    ("mcq_submitted", False), ("mcq_mode", None), ("mcq_start_time", None),
    ("mcq_score_data", None), ("mcq_time_limit", 600),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Helper to save MCQ result ───
def save_mcq_result(user_id, mode, score, total, time_taken):
    try:
        conn = get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mcq_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mode TEXT,
                score INTEGER,
                total INTEGER,
                time_taken_sec INTEGER,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "INSERT INTO mcq_results (user_id, mode, score, total, time_taken_sec) VALUES (?,?,?,?,?)",
            (user_id, mode, score, total, int(time_taken))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving MCQ result: {e}")

# ─── SETUP SCREEN ───
if not st.session_state.mcq_active and not st.session_state.mcq_submitted:
    st.markdown("### 🎯 Select Your Test")

    tab1, tab2 = st.tabs(["🔬 Technical MCQ (Personalized)", "🧮 Aptitude MCQ"])

    with tab1:
        col_a, col_b = st.columns([3, 2], gap="large")
        with col_a:
            if resume:
                skills = resume.get("skills", [])
                projects = resume.get("projects", [])
                skill_pills = " ".join([
                    f"<span style='background:rgba(129,140,248,0.15);color:#818CF8;padding:3px 10px;border-radius:20px;font-size:0.8rem;margin:3px;display:inline-block;'>{s}</span>"
                    for s in skills[:12]
                ])
                st.markdown(f"""
                <div class='glass-card' style='border-left:4px solid #818CF8;padding:16px;'>
                    <strong style='color:#818CF8;'>✅ Resume Detected — Questions Will Be Personalized!</strong>
                    <div style='margin-top:10px;'>{skill_pills}</div>
                    <div style='color:#94A3B8;font-size:0.8rem;margin-top:8px;'>
                        Questions will test <strong>{len(skills)} detected skills</strong> across {len(projects)} projects.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ No resume found. Upload your resume for personalized technical MCQs.")
                if st.button("📄 Upload Resume"):
                    st.switch_page("pages/2_📄_Resume_&_ATS.py")

            q_count_tech = st.slider("Number of questions:", 5, 15, 10, key="tech_count")
            time_per_q = st.radio("Time per question:", ["45 seconds", "60 seconds", "90 seconds"], index=1, horizontal=True, key="tech_time")
            time_secs_map = {"45 seconds": 45, "60 seconds": 60, "90 seconds": 90}
            total_time = q_count_tech * time_secs_map[time_per_q]
            st.markdown(f"<small style='color:#94A3B8;'>Total time limit: <strong>{total_time // 60} min {total_time % 60} sec</strong></small>", unsafe_allow_html=True)

            if st.button("🚀 Start Technical Test", use_container_width=True, type="primary"):
                if not resume:
                    st.error("Upload a resume first for personalized questions.")
                else:
                    with st.spinner(f"🧠 AI is generating {q_count_tech} personalized technical questions from your resume..."):
                        questions = generate_mcq_test(
                            mode="technical",
                            resume_text=resume["extracted_text"],
                            count=q_count_tech,
                            api_key=ibm_key,
                            project_id=project_id
                        )
                    if questions:
                        st.session_state.mcq_questions = questions
                        st.session_state.mcq_active = True
                        st.session_state.mcq_submitted = False
                        st.session_state.mcq_answers = {}
                        st.session_state.mcq_mode = "technical"
                        st.session_state.mcq_start_time = time.time()
                        st.session_state.mcq_time_limit = total_time
                        st.session_state.mcq_score_data = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate questions. Please check your API key.")

        with col_b:
            st.markdown("""
            <div class='glass-card' style='padding:18px;'>
                <h4 style='color:#818CF8;'>🔬 About Technical MCQ</h4>
                <ul style='color:#E2E8F0;font-size:0.9rem;line-height:1.9;padding-left:18px;'>
                    <li>Questions from your <strong>actual resume skills</strong></li>
                    <li>Tests languages, frameworks & tools you claimed</li>
                    <li>Varies from Easy → Hard progressively</li>
                    <li>Instant correct/wrong feedback after submit</li>
                    <li>Full explanation for every question</li>
                    <li>Score saved to your Dashboard</li>
                </ul>
                <hr style='border-color:rgba(255,255,255,0.05);margin:12px 0;'>
                <h4>📊 Scoring</h4>
                <p style='color:#94A3B8;font-size:0.85rem;'>+1 for correct, 0 for wrong (no negative marking).<br>Score ≥70% = <strong style='color:#10B981;'>Pass</strong></p>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        col_c, col_d = st.columns([3, 2], gap="large")
        with col_c:
            st.markdown("""
            <div class='glass-card' style='border-left:4px solid #C084FC;padding:16px;margin-bottom:16px;'>
                <strong style='color:#C084FC;'>🧮 Aptitude Test</strong>
                <p style='color:#94A3B8;font-size:0.85rem;margin:8px 0 0;'>Standard placement exam questions — Quantitative Aptitude, Logical Reasoning & Verbal Ability. Same format used by TCS, Infosys, Wipro, Accenture.</p>
            </div>
            """, unsafe_allow_html=True)

            q_count_apt = st.slider("Number of questions:", 5, 20, 10, key="apt_count")
            time_per_q_apt = st.radio("Time per question:", ["30 seconds", "45 seconds", "60 seconds"], index=1, horizontal=True, key="apt_time")
            time_secs_map2 = {"30 seconds": 30, "45 seconds": 45, "60 seconds": 60}
            total_time_apt = q_count_apt * time_secs_map2[time_per_q_apt]
            st.markdown(f"<small style='color:#94A3B8;'>Total time limit: <strong>{total_time_apt // 60} min {total_time_apt % 60} sec</strong></small>", unsafe_allow_html=True)

            if st.button("🚀 Start Aptitude Test", use_container_width=True, type="primary"):
                with st.spinner("🧠 Generating aptitude questions (Quant + Reasoning + Verbal)..."):
                    questions = generate_mcq_test(
                        mode="aptitude",
                        resume_text="",
                        count=q_count_apt,
                        api_key=ibm_key,
                        project_id=project_id
                    )
                if questions:
                    st.session_state.mcq_questions = questions
                    st.session_state.mcq_active = True
                    st.session_state.mcq_submitted = False
                    st.session_state.mcq_answers = {}
                    st.session_state.mcq_mode = "aptitude"
                    st.session_state.mcq_start_time = time.time()
                    st.session_state.mcq_time_limit = total_time_apt
                    st.session_state.mcq_score_data = None
                    st.rerun()
                else:
                    st.error("❌ Failed to generate questions. Please check your API key.")

        with col_d:
            st.markdown("""
            <div class='glass-card' style='padding:18px;'>
                <h4 style='color:#C084FC;'>🧮 About Aptitude MCQ</h4>
                <ul style='color:#E2E8F0;font-size:0.9rem;line-height:1.9;padding-left:18px;'>
                    <li><strong>Quant:</strong> %age, ratios, P&L, time-work</li>
                    <li><strong>Reasoning:</strong> series, patterns, arrangements</li>
                    <li><strong>Verbal:</strong> synonyms, sentence completion</li>
                    <li>Modeled on real placement exams</li>
                    <li>Step-by-step solution explanations</li>
                </ul>
                <hr style='border-color:rgba(255,255,255,0.05);margin:12px 0;'>
                <h4>📊 Scoring</h4>
                <p style='color:#94A3B8;font-size:0.85rem;'>+1 for correct, 0 for wrong.<br>Score ≥60% = <strong style='color:#10B981;'>Pass</strong></p>
            </div>
            """, unsafe_allow_html=True)


# ─── ACTIVE TEST SCREEN ───
elif st.session_state.mcq_active:
    questions = st.session_state.mcq_questions
    total_q = len(questions)
    mode_label = "🔬 Technical" if st.session_state.mcq_mode == "technical" else "🧮 Aptitude"
    mode_color = "#818CF8" if st.session_state.mcq_mode == "technical" else "#C084FC"

    # Timer
    elapsed = time.time() - st.session_state.mcq_start_time
    remaining = max(0, st.session_state.mcq_time_limit - elapsed)
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    answered = len(st.session_state.mcq_answers)
    timer_color = "#10B981" if remaining > 120 else "#F59E0B" if remaining > 30 else "#EF4444"

    # Top bar
    hcol1, hcol2, hcol3, hcol4 = st.columns([2, 1, 1, 1])
    with hcol1:
        st.markdown(f"<h4 style='margin:0;'>{mode_label} Test</h4>", unsafe_allow_html=True)
    with hcol2:
        st.markdown(f"<div style='text-align:center;'><div style='font-size:1.6rem;font-weight:800;color:{timer_color};'>⏱ {mins:02d}:{secs:02d}</div><div style='color:#94A3B8;font-size:0.75rem;'>remaining</div></div>", unsafe_allow_html=True)
    with hcol3:
        st.markdown(f"<div style='text-align:center;'><div style='font-size:1.6rem;font-weight:800;color:#818CF8;'>{answered}/{total_q}</div><div style='color:#94A3B8;font-size:0.75rem;'>answered</div></div>", unsafe_allow_html=True)
    with hcol4:
        if st.button("📤 Submit Test", type="primary", use_container_width=True):
            st.session_state.mcq_active = False
            st.session_state.mcq_submitted = True
            time_taken = time.time() - st.session_state.mcq_start_time

            # Calculate score
            correct = sum(
                1 for i, q in enumerate(questions)
                if st.session_state.mcq_answers.get(i) == q.get("correct")
            )
            st.session_state.mcq_score_data = {
                "correct": correct,
                "total": total_q,
                "time_taken": time_taken,
                "pct": round(correct / total_q * 100, 1) if total_q else 0
            }
            save_mcq_result(user_id, st.session_state.mcq_mode, correct, total_q, time_taken)
            st.rerun()

    # Auto-submit on timeout
    if remaining <= 0:
        st.session_state.mcq_active = False
        st.session_state.mcq_submitted = True
        time_taken = st.session_state.mcq_time_limit
        correct = sum(
            1 for i, q in enumerate(questions)
            if st.session_state.mcq_answers.get(i) == q.get("correct")
        )
        st.session_state.mcq_score_data = {
            "correct": correct, "total": total_q,
            "time_taken": time_taken,
            "pct": round(correct / total_q * 100, 1) if total_q else 0
        }
        save_mcq_result(user_id, st.session_state.mcq_mode, correct, total_q, time_taken)
        st.warning("⏰ Time's up! Auto-submitting your test...")
        time.sleep(1)
        st.rerun()

    st.markdown(f"<div style='height:6px;background:rgba(255,255,255,0.05);border-radius:3px;margin:10px 0 20px;'><div style='height:6px;background:{mode_color};border-radius:3px;width:{answered/total_q*100}%;'></div></div>", unsafe_allow_html=True)

    # Question list — 2 per row
    diff_badge = {"Easy": "#10B981", "Medium": "#F59E0B", "Hard": "#EF4444"}

    for i in range(0, total_q, 2):
        cols = st.columns(2, gap="large")
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= total_q:
                break
            q = questions[idx]
            current_ans = st.session_state.mcq_answers.get(idx)
            diff_c = diff_badge.get(q.get("difficulty", "Medium"), "#818CF8")

            with col:
                st.markdown(f"""
                <div class='glass-card' style='padding:18px;min-height:200px;'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;'>
                        <span style='background:rgba(129,140,248,0.15);color:#818CF8;padding:2px 10px;border-radius:20px;font-size:0.75rem;'>Q{idx+1} · {q.get('topic','')}</span>
                        <span style='background:{diff_c}22;color:{diff_c};padding:2px 10px;border-radius:20px;font-size:0.75rem;'>{q.get('difficulty','')}</span>
                    </div>
                    <p style='font-size:0.95rem;font-weight:500;line-height:1.5;margin-bottom:12px;'>{q.get('question','')}</p>
                </div>
                """, unsafe_allow_html=True)

                options = q.get("options", {})
                option_list = [f"{letter}: {options[letter]}" for letter in ["A", "B", "C", "D"] if letter in options]
                selected = st.radio(
                    f"Select answer for Q{idx+1}:",
                    option_list,
                    index=None if current_ans is None else ["A", "B", "C", "D"].index(current_ans),
                    key=f"mcq_q_{idx}",
                    label_visibility="collapsed"
                )
                if selected:
                    letter = selected[0]
                    st.session_state.mcq_answers[idx] = letter

    st.markdown("<br>", unsafe_allow_html=True)
    cancel_col, submit_col = st.columns([1, 2])
    with cancel_col:
        if st.button("❌ Cancel Test", use_container_width=True):
            st.session_state.mcq_active = False
            st.rerun()
    with submit_col:
        if st.button("📤 Submit & See Results", use_container_width=True, type="primary"):
            st.session_state.mcq_active = False
            st.session_state.mcq_submitted = True
            time_taken = time.time() - st.session_state.mcq_start_time
            correct = sum(
                1 for i, q in enumerate(questions)
                if st.session_state.mcq_answers.get(i) == q.get("correct")
            )
            st.session_state.mcq_score_data = {
                "correct": correct, "total": total_q,
                "time_taken": time_taken,
                "pct": round(correct / total_q * 100, 1) if total_q else 0
            }
            save_mcq_result(user_id, st.session_state.mcq_mode, correct, total_q, time_taken)
            st.rerun()


# ─── RESULTS SCREEN ───
elif st.session_state.mcq_submitted and st.session_state.mcq_score_data:
    questions = st.session_state.mcq_questions
    answers = st.session_state.mcq_answers
    data = st.session_state.mcq_score_data
    mode = st.session_state.mcq_mode
    pass_threshold = 70 if mode == "technical" else 60

    correct = data["correct"]
    total = data["total"]
    pct = data["pct"]
    time_taken = data["time_taken"]
    passed = pct >= pass_threshold
    result_color = "#10B981" if passed else "#EF4444"
    mode_label = "🔬 Technical" if mode == "technical" else "🧮 Aptitude"

    # Score Hero Card
    st.markdown(f"""
    <div class='glass-card pulse-card' style='text-align:center;padding:40px;border-left:5px solid {result_color};'>
        <div style='font-size:4rem;margin-bottom:8px;'>{"🏆" if passed else "📚"}</div>
        <div style='font-size:3rem;font-weight:900;color:{result_color};'>{pct}%</div>
        <div style='font-size:1.2rem;font-weight:600;margin:8px 0;color:{"#10B981" if passed else "#EF4444"};'>
            {"✅ PASSED" if passed else "❌ NEEDS IMPROVEMENT"}
        </div>
        <div style='color:#94A3B8;'>{mode_label} Test · {correct}/{total} correct · {int(time_taken//60)}m {int(time_taken%60)}s</div>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    wrong = total - correct
    unanswered = total - len(answers)
    s1, s2, s3, s4 = st.columns(4)
    for col, label, val, color in [
        (s1, "✅ Correct", correct, "#10B981"),
        (s2, "❌ Wrong", wrong - unanswered, "#EF4444"),
        (s3, "⏭ Skipped", unanswered, "#F59E0B"),
        (s4, "⏱ Time/Q", f"{int(time_taken/total)}s", "#818CF8"),
    ]:
        col.markdown(f"""
        <div class='custom-metric' style='text-align:center;'>
            <div class='custom-metric-value' style='color:{color};'>{val}</div>
            <div class='custom-metric-label'>{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Topic breakdown
    topic_stats = {}
    for i, q in enumerate(questions):
        topic = q.get("topic", "General")
        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0}
        topic_stats[topic]["total"] += 1
        if answers.get(i) == q.get("correct"):
            topic_stats[topic]["correct"] += 1

    if len(topic_stats) > 1:
        st.markdown("### 📊 Topic-wise Performance")
        topic_cols = st.columns(min(len(topic_stats), 4))
        for idx, (topic, stats) in enumerate(topic_stats.items()):
            t_pct = round(stats["correct"] / stats["total"] * 100)
            t_color = "#10B981" if t_pct >= 70 else "#F59E0B" if t_pct >= 40 else "#EF4444"
            with topic_cols[idx % len(topic_cols)]:
                st.markdown(f"""
                <div class='glass-card' style='padding:14px;text-align:center;'>
                    <div style='font-size:1.4rem;font-weight:800;color:{t_color};'>{t_pct}%</div>
                    <div style='font-size:0.8rem;color:#94A3B8;margin-top:4px;'>{topic}</div>
                    <div style='font-size:0.75rem;color:#64748B;'>{stats["correct"]}/{stats["total"]}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Full Answer Review")

    # Per-question review
    for i, q in enumerate(questions):
        user_ans = answers.get(i)
        correct_ans = q.get("correct")
        is_correct = user_ans == correct_ans
        options = q.get("options", {})
        diff_c = {"Easy": "#10B981", "Medium": "#F59E0B", "Hard": "#EF4444"}.get(q.get("difficulty", "Medium"), "#818CF8")

        border_color = "#10B981" if is_correct else "#EF4444" if user_ans else "#64748B"
        icon = "✅" if is_correct else "❌" if user_ans else "⏭"

        with st.expander(f"{icon} Q{i+1}: {q.get('question','')[:80]}{'...' if len(q.get('question',''))>80 else ''}", expanded=not is_correct):
            st.markdown(f"""
            <div style='margin-bottom:12px;'>
                <span style='background:{diff_c}22;color:{diff_c};padding:2px 10px;border-radius:20px;font-size:0.75rem;'>{q.get('difficulty','')}</span>
                <span style='background:rgba(129,140,248,0.1);color:#818CF8;padding:2px 10px;border-radius:20px;font-size:0.75rem;margin-left:6px;'>{q.get('topic','')}</span>
            </div>
            <p style='font-size:0.95rem;font-weight:500;'>{q.get('question','')}</p>
            """, unsafe_allow_html=True)

            for letter in ["A", "B", "C", "D"]:
                opt_text = options.get(letter, "")
                if letter == correct_ans and letter == user_ans:
                    bg, tc = "rgba(16,185,129,0.15)", "#10B981"
                    icon_o = "✅"
                elif letter == correct_ans:
                    bg, tc = "rgba(16,185,129,0.10)", "#10B981"
                    icon_o = "✔"
                elif letter == user_ans:
                    bg, tc = "rgba(239,68,68,0.12)", "#EF4444"
                    icon_o = "✗"
                else:
                    bg, tc = "rgba(255,255,255,0.03)", "#94A3B8"
                    icon_o = " "
                st.markdown(f"""
                <div style='background:{bg};border:1px solid {tc}33;border-radius:8px;padding:8px 14px;margin:4px 0;display:flex;align-items:center;'>
                    <span style='color:{tc};font-weight:700;margin-right:10px;'>{icon_o} {letter}.</span>
                    <span style='color:#E2E8F0;font-size:0.9rem;'>{opt_text}</span>
                </div>
                """, unsafe_allow_html=True)

            if not user_ans:
                st.markdown("<small style='color:#F59E0B;'>⏭ You skipped this question.</small>", unsafe_allow_html=True)

            st.markdown(f"""
            <div style='background:rgba(129,140,248,0.08);border-left:3px solid #818CF8;border-radius:6px;padding:10px 14px;margin-top:10px;'>
                <strong style='color:#818CF8;font-size:0.85rem;'>💡 Explanation</strong>
                <p style='color:#E2E8F0;font-size:0.88rem;margin:5px 0 0;line-height:1.5;'>{q.get('explanation','')}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button("🔄 Take Another Test", use_container_width=True):
            for k in ["mcq_active", "mcq_submitted", "mcq_questions", "mcq_answers", "mcq_score_data"]:
                st.session_state[k] = False if "active" in k or "submitted" in k else [] if "questions" in k else {} if "answers" in k else None
            st.rerun()
    with rc2:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.switch_page("pages/6_📊_Dashboard.py")
