import streamlit as st
import os
import time
import tempfile
import wave
import re
from dotenv import load_dotenv
from database import start_interview, log_interview_question, finalize_interview, get_resume
from gemini_service import generate_interview_questions, evaluate_response, generate_final_report, analyze_audio_response

load_dotenv(override=True)

st.set_page_config(page_title="Mock Interview Simulator - InterviewAI", page_icon="🎤", layout="wide")

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

# ── Groq key (STT / Whisper only) ──
groq_key = os.getenv("GROQ_API_KEY", "")

# Keep api_key alias for any legacy references
st.session_state.api_key = st.session_state.ibm_api_key

st.markdown("<h2>🎤 Mock Interview <span class='accent-header'>Simulator</span></h2>",
            unsafe_allow_html=True)
st.markdown("<p style='color:#94A3B8;'>Practice real-world interview conditions. Type or speak your answers and get instant AI evaluation.</p>",
            unsafe_allow_html=True)

# Auth check
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please log in first.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_👤_Login.py")
    st.stop()

ibm_key = st.session_state.ibm_api_key
project_id = st.session_state.ibm_project_id

if not ibm_key or not project_id:
    st.error("⚠️ IBM Granite credentials missing. Please go to ⚙️ Settings and add your IBM API Key and Project ID.")
    if st.button("⚙️ Go to Settings"):
        st.switch_page("pages/7_⚙️_Settings.py")
    st.stop()

# Alias for cleaner code below
api_key = ibm_key

user_id = st.session_state.user['id']

def count_fillers(text):
    fillers = ["um", "uh", "like", "basically", "actually", "literally", "you know", "right", "so"]
    count = 0
    clean_text = text.lower()
    for filler in fillers:
        matches = re.findall(rf"\b{filler}\b", clean_text)
        count += len(matches)
    return count

def get_wav_duration(file_path):
    try:
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except:
        return 0

# Init session states for interview flow
for key_name, default in [
    ("interview_active", False),
    ("current_q_index", 0),
    ("questions", []),
    ("transcript", []),
    ("interview_id", None),
    ("current_eval", None),
    ("total_fillers", 0),
    ("total_wpm", 0),
    ("speech_instances", 0),
    ("duration_start", None),
    ("interview_type", "Technical"),
    ("response_mode", "⌨️ Text Input"),
]:
    if key_name not in st.session_state:
        st.session_state[key_name] = default

# ─────────────── SETUP SCREEN ───────────────
if not st.session_state.interview_active:
    st.markdown("### ⚙️ Configure Your Mock Interview Round")
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        int_type = st.selectbox("Interview Track:", ["Technical", "HR", "Managerial", "Behavioral"])
        response_mode = st.radio("Answer Mode:", ["⌨️ Text Input", "🎙️ Voice Input (Microphone)"])
        q_count = st.slider("Number of Questions:", min_value=3, max_value=7, value=5)

        resume = get_resume(user_id)
        if resume:
            st.success("✅ Resume found! Questions will be personalized to your skills, projects, and experience.")
            resume_text = resume['extracted_text']
        else:
            st.warning("⚠️ No resume found. Questions will be generic. Upload your resume for personalized questions.")
            resume_text = "General engineering student with basic programming knowledge."

        if st.button("🚀 Start Mock Interview", use_container_width=True):
            with st.spinner(f"Generating {q_count} personalized {int_type} questions from your resume..."):
                questions = generate_interview_questions(
                    resume_text=resume_text,
                    interview_type=int_type,
                    count=q_count,
                    api_key=api_key,
                        project_id=project_id
                )

            if questions and len(questions) > 0:
                st.session_state.questions = questions
                st.session_state.interview_active = True
                st.session_state.current_q_index = 0
                st.session_state.transcript = []
                st.session_state.current_eval = None
                st.session_state.total_fillers = 0
                st.session_state.total_wpm = 0
                st.session_state.speech_instances = 0
                st.session_state.duration_start = time.time()
                st.session_state.interview_type = int_type
                st.session_state.response_mode = response_mode
                st.session_state.interview_id = start_interview(user_id, int_type)
                st.rerun()
            else:
                st.error("❌ Failed to generate questions. Please check your API key in Settings.")

    with col2:
        st.markdown("""
        <div class='glass-card'>
            <h4>📝 How to Answer Well (STAR Method)</h4>
            <ol style='color:#E2E8F0; font-size:0.9rem; line-height:1.8;'>
                <li><strong style='color:#818CF8;'>Situation:</strong> Set the context — what was the background?</li>
                <li><strong style='color:#818CF8;'>Task:</strong> What was your goal or challenge?</li>
                <li><strong style='color:#818CF8;'>Action:</strong> What specific steps did <em>you</em> take?</li>
                <li><strong style='color:#818CF8;'>Result:</strong> What was the outcome? Use numbers if possible.</li>
            </ol>
            <hr style='border-color:rgba(255,255,255,0.05);margin:12px 0;'>
            <h4>🎙️ Voice Tips</h4>
            <ul style='color:#94A3B8; font-size:0.85rem;'>
                <li>Speak clearly, aim for 120–150 words/minute</li>
                <li>Avoid filler words: "um", "like", "basically"</li>
                <li>Pause intentionally instead of using fillers</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ─────────────── ACTIVE INTERVIEW ───────────────
else:
    q_index = st.session_state.current_q_index
    total_q = len(st.session_state.questions)
    current_question = st.session_state.questions[q_index]

    # Progress bar
    st.progress((q_index) / total_q)
    st.markdown(f"**Question {q_index + 1} of {total_q}** &nbsp;|&nbsp; Track: `{st.session_state.interview_type}` &nbsp;|&nbsp; Mode: `{st.session_state.response_mode}`")

    # Current Question Card
    st.markdown(f"""
    <div class='glass-card pulse-card' style='border-left:4px solid #818CF8;'>
        <h4 style='color:#818CF8;margin-bottom:8px;'>🤖 AI Interviewer</h4>
        <h3 style='margin:0;'>"{current_question}"</h3>
    </div>
    """, unsafe_allow_html=True)

    # ── EVALUATION DISPLAY (after submission) ──
    if st.session_state.current_eval is not None:
        eval_res = st.session_state.current_eval
        scores = eval_res.get("scores", {})
        overall = eval_res.get("overall", 0.0)

        ecol1, ecol2 = st.columns([1, 2])
        with ecol1:
            # Score badge colors
            color = "#10B981" if overall >= 7 else "#F59E0B" if overall >= 5 else "#EF4444"
            st.markdown(f"""
            <div class='glass-card' style='text-align:center;'>
                <div style='font-size:2.5rem;font-weight:800;color:{color};'>{overall}/10</div>
                <div style='color:#94A3B8;font-size:0.8rem;text-transform:uppercase;margin-bottom:15px;'>Overall Score</div>
                <hr style='border-color:rgba(255,255,255,0.05);margin:10px 0;'>
                <div style='font-size:0.85rem;text-align:left;'>
                    <div style='display:flex;justify-content:space-between;margin:6px 0;'><span>🔧 Technical</span><strong>{scores.get('technical_knowledge',0)}/10</strong></div>
                    <div style='display:flex;justify-content:space-between;margin:6px 0;'><span>💬 Communication</span><strong>{scores.get('communication',0)}/10</strong></div>
                    <div style='display:flex;justify-content:space-between;margin:6px 0;'><span>⭐ STAR Structure</span><strong>{scores.get('star_structure',0)}/10</strong></div>
                    <div style='display:flex;justify-content:space-between;margin:6px 0;'><span>📝 Grammar</span><strong>{scores.get('grammar',0)}/10</strong></div>
                    <div style='display:flex;justify-content:space-between;margin:6px 0;'><span>🎯 Relevance</span><strong>{scores.get('relevance',0)}/10</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Voice diagnostics
            if "wpm" in eval_res:
                wpm_color = "#10B981" if eval_res.get("wpm_status") == "Perfect Speed" else "#F59E0B"
                st.markdown(f"""
                <div class='glass-card' style='padding:12px;'>
                    <strong>🎙️ Speech Analysis</strong><br>
                    <small>Filler words: <strong style='color:#EF4444;'>{eval_res.get('fillers_count',0)}</strong></small><br>
                    <small>Pace: <strong style='color:{wpm_color};'>{eval_res.get('wpm',0)} WPM — {eval_res.get('wpm_status','')}</strong></small>
                </div>
                """, unsafe_allow_html=True)

        with ecol2:
            st.markdown(f"""
            <div class='glass-card' style='padding:18px;'>
                <h4 style='color:#818CF8;margin-bottom:8px;'>💡 AI Feedback</h4>
                <p style='font-size:0.9rem;line-height:1.6;'>{eval_res.get('feedback','')}</p>
                <hr style='border-color:rgba(255,255,255,0.05);margin:12px 0;'>
                <h4 style='color:#F59E0B;margin-bottom:6px;'>⭐ STAR Structure Review</h4>
                <p style='font-size:0.85rem;color:#E2E8F0;'>{eval_res.get('star_check','')}</p>
                <hr style='border-color:rgba(255,255,255,0.05);margin:12px 0;'>
                <h4 style='color:#10B981;margin-bottom:6px;'>🌟 AI-Improved Answer</h4>
                <p style='font-size:0.9rem;font-style:italic;color:#D1FAE5;'>"{eval_res.get('improved_answer','')}"</p>
            </div>
            """, unsafe_allow_html=True)

            # Follow-up display
            if eval_res.get("is_followup_needed") and eval_res.get("followup_question"):
                st.markdown(f"""
                <div class='glass-card' style='border-left:4px solid #F59E0B;padding:12px;'>
                    <strong style='color:#F59E0B;'>🔄 AI Follow-up Question:</strong>
                    <p style='margin:6px 0 0;'>"{eval_res['followup_question']}"</p>
                </div>
                """, unsafe_allow_html=True)

        # Navigation button
        btn_label = "Next Question →" if q_index + 1 < total_q else "🏁 Finish & Generate Report"
        if st.button(btn_label, use_container_width=True):
            # Save to DB and transcript
            log_interview_question(
                interview_id=st.session_state.interview_id,
                question=current_question,
                answer=eval_res.get("user_answer", ""),
                feedback=eval_res.get("feedback", ""),
                scores_dict=scores
            )
            st.session_state.transcript.append({
                "question": current_question,
                "answer": eval_res.get("user_answer", ""),
                "feedback": eval_res.get("feedback", ""),
                "scores": scores
            })

            if q_index + 1 < total_q:
                st.session_state.current_q_index += 1
                st.session_state.current_eval = None
                st.rerun()
            else:
                with st.spinner("🧠 AI is compiling your final performance report..."):
                    end_time = time.time()
                    duration = round(end_time - st.session_state.duration_start, 2)

                    report = generate_final_report(
                        type_name=st.session_state.interview_type,
                        qna_history=st.session_state.transcript,
                        api_key=api_key,
                        project_id=project_id
                    )

                    avg_score = report.get("overall_score", 0.0)
                    if not avg_score and st.session_state.transcript:
                        all_scores = [item['scores'] for item in st.session_state.transcript]
                        avg_score = sum(
                            sum(s.values()) / len(s) for s in all_scores
                        ) / len(all_scores)

                    avg_wpm = int(st.session_state.total_wpm / st.session_state.speech_instances) if st.session_state.speech_instances > 0 else 0

                    finalize_interview(
                        interview_id=st.session_state.interview_id,
                        overall_score=round(avg_score, 1),
                        filler_words=st.session_state.total_fillers,
                        wpm=avg_wpm,
                        duration=duration,
                        strengths=report.get("strengths", []),
                        weaknesses=report.get("weaknesses", []),
                        recommendations=report.get("recommendations", [])
                    )

                    st.session_state.interview_active = False
                    st.session_state.current_eval = None
                    st.balloons()
                    st.success("🎉 Interview complete! View your detailed report in the Dashboard.")
                    time.sleep(2)
                    st.switch_page("pages/6_📊_Dashboard.py")

    # ── ANSWER INPUT (before submission) ──
    else:
        if st.session_state.response_mode == "⌨️ Text Input":
            user_ans = st.text_area(
                "Your Answer:",
                height=160,
                placeholder="Describe your answer clearly. Try to follow the STAR structure: Situation → Task → Action → Result..."
            )
            if st.button("✅ Submit Answer", use_container_width=True):
                if not user_ans.strip():
                    st.error("Please type your answer before submitting.")
                elif len(user_ans.strip()) < 20:
                    st.error("Answer too short. Please provide a more detailed response.")
                else:
                    with st.spinner("🤖 AI is evaluating your answer..."):
                        evaluation = evaluate_response(current_question, user_ans, api_key=api_key,
                        project_id=project_id)
                        evaluation["user_answer"] = user_ans
                        evaluation["fillers_count"] = count_fillers(user_ans)
                        st.session_state.total_fillers += evaluation["fillers_count"]
                        st.session_state.current_eval = evaluation
                    st.rerun()

        else:  # Voice mode
            st.markdown("""
            <div class='glass-card' style='border-left:4px solid #818CF8; padding:15px;'>
                <h4 style='color:#818CF8; margin:0 0 8px;'>🎙️ Voice Recording Instructions</h4>
                <ol style='color:#E2E8F0; font-size:0.9rem; margin:0; padding-left:20px; line-height:1.8;'>
                    <li>Click the <strong>microphone icon</strong> below to start recording</li>
                    <li>Speak your answer clearly (aim for 30+ seconds)</li>
                    <li>Click the <strong>stop button</strong> to finish</li>
                    <li>Click <strong>Evaluate Voice Answer</strong> to transcribe & grade</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)

            audio_value = st.audio_input("🎙️ Record your answer here:")

            if audio_value is not None:
                # Read the raw bytes from the Streamlit UploadedFile
                audio_value.seek(0)
                audio_bytes = audio_value.read()
                audio_size = len(audio_bytes)

                st.info(f"✅ Audio captured: **{audio_size // 1024} KB** — Click below to evaluate.")

                if audio_size < 2000:
                    st.error("⚠️ Recording too short or empty. Please record for at least 5 seconds.")
                elif st.button("🎧 Evaluate Voice Answer", use_container_width=True):
                    with st.spinner("🎧 Transcribing with Groq Whisper... then evaluating with IBM Granite..."):
                        # Check Groq key for STT
                        if not groq_key:
                            st.warning("⚠️ No Groq API key found. Voice transcription requires a free Groq key.")
                            st.info("Go to ⚙️ Settings → Optional Groq Key section to add it.")
                            st.stop()
                        # Save webm audio temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
                            tmp_file.write(audio_bytes)
                            tmp_path = tmp_file.name

                        try:
                            # groq_key → Whisper STT | ibm_key + project_id → Granite evaluation
                            audio_result = analyze_audio_response(
                                tmp_path, current_question,
                                api_key=ibm_key,
                                project_id=project_id,
                                groq_key=groq_key
                            )
                            transcription_text = audio_result.get("transcription", "")

                            if not transcription_text or "Could not transcribe" in transcription_text:
                                st.error("❌ Transcription failed. Please try again or switch to Text Input mode.")
                                st.stop()

                            eval_obj = audio_result.get("evaluation", {})
                            eval_obj["user_answer"] = transcription_text
                            eval_obj["transcription"] = transcription_text

                            # WPM calculation using word count vs estimated duration
                            word_count = len(transcription_text.split())
                            est_duration = get_wav_duration(tmp_path)
                            wpm = int(word_count / (est_duration / 60)) if est_duration > 5 else max(word_count * 2, 80)
                            eval_obj["wpm"] = wpm
                            eval_obj["wpm_status"] = "Too Slow" if wpm < 100 else "Too Fast" if wpm > 160 else "Perfect Speed"

                            fillers_found = audio_result.get("filler_words_detected", [])
                            eval_obj["fillers_count"] = len(fillers_found)
                            st.session_state.total_fillers += eval_obj["fillers_count"]
                            st.session_state.total_wpm += wpm
                            st.session_state.speech_instances += 1
                            st.session_state.current_eval = eval_obj
                        except Exception as e:
                            st.error(f"Audio analysis error: {e}")
                            st.info("💡 Tip: Try switching to **Text Input** mode if voice keeps failing.")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)

                    if st.session_state.current_eval is not None:
                        st.rerun()

    # Cancel button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("❌ Cancel Interview", type="secondary"):
        st.session_state.interview_active = False
        st.session_state.current_eval = None
        st.rerun()
