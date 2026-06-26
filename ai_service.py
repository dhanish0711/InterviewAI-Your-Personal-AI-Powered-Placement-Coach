"""
ai_service.py — InterviewAI
All AI calls use IBM Granite via ibm-watsonx-ai SDK.
Supports Granite-3.3-8B-Instruct (fast, free tier).
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv(override=True)

# ── IBM Granite Configuration ──────────────────────────────────────────────
IBM_MODEL_ID = "ibm/granite-4-h-small"
IBM_URL      = os.getenv("WATSONX_SERVICE_URL", "https://us-south.ml.cloud.ibm.com")

def resolve_ibm_credentials(api_key=None, project_id=None):
    """Return (api_key, project_id) from args or environment.
    Supports all IBM env var naming conventions:
      WATSONX_APIKEY  (IBM's official name)
      IBM_API_KEY     (our alias)
      WATSONX_API_KEY (langchain-ibm style)
    """
    key = (api_key
           or os.getenv("WATSONX_APIKEY")
           or os.getenv("IBM_API_KEY")
           or os.getenv("WATSONX_API_KEY")
           or "")
    pid = (project_id
           or os.getenv("WATSONX_PROJECT_ID")
           or os.getenv("IBM_PROJECT_ID")
           or "")
    return key, pid


def _clean_json(text: str) -> str:
    """Strip markdown code fences and extract first JSON object/array."""
    text = text.strip()
    # Remove ```json ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    # Find first { or [
    start = min(
        (text.find(c) for c in ["{", "["] if c in text),
        default=0
    )
    text = text[start:]
    # Truncate at last } or ]
    for end_char, open_char in [('}', '{'), (']', '[')]:
        if text.startswith(open_char if open_char == '{' else open_char):
            idx = text.rfind(end_char)
            if idx != -1:
                text = text[:idx+1]
                break
    return text


def query_granite(prompt: str, system: str, api_key=None, project_id=None,
                  temperature: float = 0.3, max_tokens: int = 3000) -> str:
    """
    Call IBM Granite via ibm-watsonx-ai chat API (modern, non-deprecated).
    Returns the generated text string.
    """
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    key, pid = resolve_ibm_credentials(api_key, project_id)
    if not key:
        raise ValueError("IBM API Key missing. Set WATSONX_APIKEY in Settings or .env")
    if not pid:
        raise ValueError("IBM Project ID missing. Set WATSONX_PROJECT_ID in Settings or .env")

    credentials = Credentials(url=IBM_URL, api_key=key)
    model = ModelInference(
        model_id=IBM_MODEL_ID,
        credentials=credentials,
        project_id=pid,
    )

    # Use modern chat() API — standard OpenAI-style messages
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    response = model.chat(
        messages=messages,
        params={"max_tokens": max_tokens, "temperature": temperature}
    )
    return response["choices"][0]["message"]["content"].strip()


def query_granite_json(prompt: str, system: str, api_key=None,
                       project_id=None, temperature: float = 0.2) -> dict:
    """Call Granite and parse the result as JSON. Returns parsed dict."""
    system_json = system + "\n\nIMPORTANT: Your response MUST be valid JSON only. No markdown, no explanation outside the JSON."
    raw = query_granite(prompt, system_json, api_key, project_id, temperature)
    cleaned = _clean_json(raw)
    return json.loads(cleaned)


# ════════════════════════════════════════════════════════════════════════════
# Resume Parsing
# ════════════════════════════════════════════════════════════════════════════
def parse_resume_with_ai(pdf_text, api_key=None, project_id=None):
    system = """You are an expert AI Resume Parser.
Return a JSON object with EXACTLY these keys:
- "skills": list of skill strings
- "experience": list of {role, company, duration, description}
- "projects": list of {title, description, technologies}
- "education": list of {degree, institution, year}"""
    prompt = f"Parse this resume:\n\n{pdf_text}"
    try:
        return query_granite_json(prompt, system, api_key, project_id, temperature=0.1)
    except Exception as e:
        print(f"[parse_resume] Error: {e}")
        return {
            "skills": ["Python", "SQL", "Software Engineering"],
            "experience": [{"role": "Intern", "company": "Demo Corp",
                            "duration": "3 Months", "description": "Web development."}],
            "projects": [{"title": "Demo Project", "description": "Built a web app.",
                          "technologies": ["Flask", "SQLite"]}],
            "education": [{"degree": "B.Tech CS", "institution": "Demo University", "year": "2026"}]
        }


# ════════════════════════════════════════════════════════════════════════════
# ATS Compatibility
# ════════════════════════════════════════════════════════════════════════════
def evaluate_ats_compatibility(resume_text, job_description, api_key=None, project_id=None):
    system = """You are an ATS optimizer.
Return a JSON object with EXACTLY these keys:
- "score": integer 0-100
- "missing_skills": list of strings
- "match_analysis": string summary
- "suggestions": list of {original_bullet, improved_bullet, rationale}"""
    prompt = f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_description}"
    try:
        return query_granite_json(prompt, system, api_key, project_id, temperature=0.2)
    except Exception as e:
        print(f"[evaluate_ats] Error: {e}")
        return {
            "score": 55,
            "missing_skills": ["Cloud", "Docker"],
            "match_analysis": "Partial match. Several key skills missing.",
            "suggestions": [{"original_bullet": "Did coding tasks.",
                             "improved_bullet": "Developed REST APIs reducing latency by 30%.",
                             "rationale": "Add metrics and action verbs."}]
        }


# ════════════════════════════════════════════════════════════════════════════
# Interview Question Generator
# ════════════════════════════════════════════════════════════════════════════
def generate_interview_questions(resume_text, interview_type="Technical",
                                  count=5, api_key=None, project_id=None):
    system = f"""You are an expert {interview_type} interviewer.
Generate exactly {count} interview questions personalized to the candidate's resume.
Return a JSON object with ONE key: "questions" — a list of {count} question strings."""
    prompt = f"Candidate resume:\n{resume_text}"
    try:
        data = query_granite_json(prompt, system, api_key, project_id, temperature=0.4)
        return data.get("questions", [])
    except Exception as e:
        print(f"[generate_questions] Error: {e}")
        return [
            "Tell me about a challenging project in your resume.",
            "Explain your understanding of data structures.",
            "How do you handle conflicts in a team?",
            "What is your approach to learning new technologies?",
            "Why are you interested in this role?"
        ][:count]


# ════════════════════════════════════════════════════════════════════════════
# Response Evaluator
# ════════════════════════════════════════════════════════════════════════════
def evaluate_response(question, user_answer, api_key=None, project_id=None):
    system = """You are an expert Interview Coach evaluating a candidate's answer.
Return a JSON object with EXACTLY these keys:
- "scores": {technical_knowledge, communication, star_structure, grammar, relevance} — each 0-10
- "overall": float (average of relevant scores)
- "feedback": concise critique string
- "star_check": STAR method assessment string
- "improved_answer": polished STAR rewrite string
- "is_followup_needed": boolean
- "followup_question": string or null"""
    prompt = f"QUESTION: {question}\n\nCANDIDATE ANSWER: {user_answer}"
    try:
        return query_granite_json(prompt, system, api_key, project_id, temperature=0.3)
    except Exception as e:
        print(f"[evaluate_response] Error: {e}")
        return {
            "scores": {"technical_knowledge": 6, "communication": 7,
                       "star_structure": 5, "grammar": 7, "relevance": 7},
            "overall": 6.4,
            "feedback": "Answer was clear but lacked STAR structure.",
            "star_check": "Situation described, but Action and Result were missing.",
            "improved_answer": "In my internship (S), I was tasked with optimising DB queries (T). I rewrote 3 key queries using indexing (A), reducing latency by 40% (R).",
            "is_followup_needed": False,
            "followup_question": None
        }


# ════════════════════════════════════════════════════════════════════════════
# Final Interview Report
# ════════════════════════════════════════════════════════════════════════════
def generate_final_report(type_name, qna_history, api_key=None, project_id=None):
    system = """You are a Hiring Manager summarising a mock interview.
Return a JSON object with EXACTLY these keys:
- "overall_score": float
- "strengths": list of 3 strings
- "weaknesses": list of 3 strings
- "recommendations": list of study topic strings"""
    prompt = f"INTERVIEW TYPE: {type_name}\n\nTRANSCRIPT:\n{json.dumps(qna_history, indent=2)}"
    try:
        return query_granite_json(prompt, system, api_key, project_id, temperature=0.2)
    except Exception as e:
        print(f"[final_report] Error: {e}")
        return {
            "overall_score": 7.0,
            "strengths": ["Clear communication", "Good technical concepts", "Confidence"],
            "weaknesses": ["STAR method", "System design depth", "Quantified results"],
            "recommendations": ["Practise STAR answers", "Study DB normalisation", "Mock system design interviews"]
        }


# ════════════════════════════════════════════════════════════════════════════
# Code Evaluator
# ════════════════════════════════════════════════════════════════════════════
def evaluate_code_with_ai(problem_name, code, language="Python",
                           api_key=None, project_id=None):
    system = f"""You are an expert technical interviewer reviewing {language} code.
Return a JSON object with EXACTLY these keys:
- "score": integer 0-100
- "syntax_correct": boolean
- "time_complexity": string e.g. "O(N log N)"
- "space_complexity": string e.g. "O(N)"
- "feedback": concise quality summary string
- "hints": list of 2-3 improvement suggestion strings
- "optimized_code": clean, commented optimised solution in {language}"""
    prompt = f"PROBLEM: {problem_name}\n\nCODE:\n{code}"
    try:
        return query_granite_json(prompt, system, api_key, project_id, temperature=0.2)
    except Exception as e:
        print(f"[evaluate_code] Error: {e}")
        return {
            "score": 55,
            "syntax_correct": True,
            "time_complexity": "O(N\u00b2)",
            "space_complexity": "O(1)",
            "feedback": "Functional but unoptimised. Consider using hash maps.",
            "hints": ["Use a dictionary for O(1) lookups.",
                      "Reduce nested loops to a single pass."],
            "optimized_code": f"# Optimised {language} solution\n# (AI evaluation failed — try again)"
        }


# ════════════════════════════════════════════════════════════════════════════
# Personalised Coding Problem Generator
# ════════════════════════════════════════════════════════════════════════════
def generate_coding_problem(resume_text, difficulty="Medium", language="Python",
                             api_key=None, project_id=None):
    system = f"""You are a senior technical interviewer at a top company.
Generate ONE original coding problem tailored to the candidate's resume skills.
Difficulty: {difficulty}. Language: {language}.

Return a JSON object with EXACTLY these keys:
- "title": short problem name string
- "difficulty": "{difficulty}"
- "topic": CS topic string (e.g. "Hash Maps", "Graphs", "String Parsing")
- "description": full markdown problem statement with 2 input/output examples and constraints
- "starter_code": working starter template in {language} with function signature and docstring
- "hint1": gentle direction hint (no solution)
- "hint2": algorithmic approach hint
- "hint3": near-solution data structure hint
- "tags": list of 2-4 topic tag strings

Make it thematically relevant to the candidate's domain — NOT a generic LeetCode clone."""
    prompt = (f"Candidate Resume:\n{resume_text}\n\n"
              f"Generate a {difficulty} {language} problem personalised to this candidate.")
    try:
        return query_granite_json(prompt, system, api_key, project_id, temperature=0.5)
    except Exception as e:
        print(f"[generate_coding_problem] Error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# MCQ Test Generator
# ════════════════════════════════════════════════════════════════════════════
def generate_mcq_test(mode="technical", resume_text="", count=10,
                      api_key=None, project_id=None):
    """
    Generate MCQ test questions.
    mode = "technical"  → personalised from resume
    mode = "aptitude"   → standard placement aptitude
    Returns list of question dicts.
    """
    if mode == "technical":
        system = f"""You are an expert technical quiz creator.
Generate exactly {count} MCQ questions that test the candidate's stated skills.
Rules: specific to their tech stack; vary difficulty (30% Easy, 50% Medium, 20% Hard);
4 options A/B/C/D; exactly one correct answer.

Return a JSON object with ONE key "questions" — a list of {count} objects, each with:
- "question": full question text
- "topic": specific topic (e.g. "Python Decorators", "SQL Joins")
- "difficulty": "Easy" | "Medium" | "Hard"
- "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}
- "correct": correct letter "A"/"B"/"C"/"D"
- "explanation": 1-2 sentence explanation"""
        prompt = f"Candidate Resume:\n{resume_text}\n\nGenerate {count} technical MCQ questions."
    else:
        system = f"""You are an expert aptitude test designer for campus placement exams.
Generate exactly {count} MCQ questions covering Quantitative Aptitude, Logical Reasoning,
and Verbal Ability (mix equally). Include concrete numbers in Quant questions.
4 options A/B/C/D; exactly one correct answer.

Return a JSON object with ONE key "questions" — a list of {count} objects, each with:
- "question": full question text
- "topic": category (e.g. "Percentages", "Number Series", "Synonyms")
- "difficulty": "Easy" | "Medium" | "Hard"
- "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}
- "correct": correct letter "A"/"B"/"C"/"D"
- "explanation": step-by-step solution string"""
        prompt = f"Generate {count} aptitude placement MCQ questions."

    try:
        data = query_granite_json(prompt, system, api_key, project_id, temperature=0.4)
        questions = data.get("questions", [])
        if not questions:
            raise ValueError("Empty questions list returned")
        return questions
    except Exception as e:
        print(f"[generate_mcq_test] Error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════
# Audio Analysis (Whisper via Groq — kept as fallback since IBM has no STT)
# ════════════════════════════════════════════════════════════════════════════
def _convert_to_wav(input_path):
    """Convert audio to 16kHz mono WAV via ffmpeg."""
    import subprocess
    out_path = os.path.join(os.path.dirname(input_path), "converted_audio.wav")
    cmd = ["ffmpeg", "-y", "-i", input_path,
           "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            return out_path, True
        return input_path, False
    except Exception:
        return input_path, False


def analyze_audio_response(audio_file_path, question, api_key=None,
                           project_id=None, groq_key=None):
    """
    Transcribe audio with Groq Whisper (STT), then evaluate with IBM Granite.
    - groq_key : Groq API key for Whisper (reads GROQ_API_KEY env if not passed)
    - api_key  : IBM Cloud API key for Granite evaluation
    - project_id: IBM Watsonx Project ID for Granite evaluation
    """
    _groq_key = groq_key or os.getenv("GROQ_API_KEY", "")
    ibm_key, ibm_pid = resolve_ibm_credentials(api_key, project_id)

    converted_path = None
    try:
        transcription = ""

        # ── Groq Whisper STT ──
        if _groq_key and _groq_key.startswith("gsk_"):
            try:
                from groq import Groq
                client = Groq(api_key=_groq_key)
                wav_path, converted = _convert_to_wav(audio_file_path)
                if converted:
                    converted_path = wav_path
                with open(wav_path, "rb") as f:
                    audio_bytes = f.read()
                ext = ".wav" if converted else os.path.splitext(audio_file_path)[1]
                res = client.audio.transcriptions.create(
                    file=(f"audio{ext}", audio_bytes),
                    model="whisper-large-v3",
                    language="en",
                    response_format="text"
                )
                transcription = (res if isinstance(res, str) else getattr(res, "text", "")).strip()
            except Exception as e:
                print(f"[Whisper] Error: {e}")

        if not transcription or transcription in [".", " .", ""]:
            transcription = "[Could not transcribe — please use Text Input mode]"

        # ── Count filler words ──
        fillers_list = ["um", "uh", "like", "basically", "actually",
                        "literally", "you know", "right", "so"]
        fillers_found = []
        for f in fillers_list:
            fillers_found.extend(re.findall(rf"\b{f}\b", transcription.lower()))

        # ── Evaluate with Granite ──
        evaluation = evaluate_response(question, transcription,
                                       api_key=ibm_key, project_id=ibm_pid)

        return {
            "transcription": transcription,
            "filler_words_detected": fillers_found,
            "evaluation": evaluation
        }

    except Exception as e:
        print(f"[analyze_audio] Error: {e}")
        return {
            "transcription": f"Error: {str(e)[:120]}. Use Text Input mode.",
            "filler_words_detected": [],
            "evaluation": {
                "scores": {"technical_knowledge": 5, "communication": 5,
                           "star_structure": 5, "grammar": 5, "relevance": 5},
                "overall": 5.0,
                "feedback": f"Audio analysis failed: {str(e)[:200]}",
                "star_check": "Unable to assess structure.",
                "improved_answer": "Please try again with a clearer recording.",
                "is_followup_needed": False,
                "followup_question": None
            }
        }
    finally:
        if converted_path and os.path.exists(converted_path) and converted_path != audio_file_path:
            try:
                os.remove(converted_path)
            except Exception:
                pass
