import streamlit as st
import os
from dotenv import load_dotenv, set_key
from database import init_db, get_connection

load_dotenv(override=True)

st.set_page_config(page_title="Settings - InterviewAI", page_icon="⚙️", layout="centered")

css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Load IBM credentials into session ──
def _load_env():
    ibm_key = os.getenv("WATSONX_APIKEY") or os.getenv("IBM_API_KEY") or os.getenv("WATSONX_API_KEY") or ""
    ibm_pid = os.getenv("IBM_PROJECT_ID") or os.getenv("WATSONX_PROJECT_ID") or ""
    return ibm_key, ibm_pid

if "ibm_api_key" not in st.session_state:
    k, p = _load_env()
    st.session_state.ibm_api_key = k
    st.session_state.ibm_project_id = p

# Keep api_key in session for sidebar display compatibility
st.session_state.api_key = st.session_state.ibm_api_key

st.markdown("<h2>⚙️ Configuration & <span class='accent-header'>Settings</span></h2>",
            unsafe_allow_html=True)
st.markdown("<p style='color:#94A3B8;'>Manage your IBM Granite credentials, preferences, and data.</p>",
            unsafe_allow_html=True)

# ══════════════════════════════════════
# 1. IBM GRANITE CREDENTIALS
# ══════════════════════════════════════
st.markdown("### 🤖 IBM Granite (Watsonx) Credentials")

st.markdown("""
<div class='glass-card' style='border-left:4px solid #818CF8;padding:16px;margin-bottom:14px;'>
    <strong style='color:#818CF8;'>IBM Granite 3.3-8B-Instruct</strong>
    <p style='color:#94A3B8;font-size:0.88rem;margin:8px 0 0;'>
        Powers all AI features — resume parsing, mock interviews, coding problems, MCQ generation.<br>
        Get your free credentials at
        <a href='https://cloud.ibm.com/registration' target='_blank' style='color:#38BDF8;'>
        cloud.ibm.com</a> → Create Project → Manage → General → Project ID.
    </p>
    <div style='margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
        <div style='background:rgba(129,140,248,0.08);border-radius:8px;padding:10px;font-size:0.82rem;color:#E2E8F0;'>
            <strong>Model:</strong><br>ibm/granite-3-3-8b-instruct
        </div>
        <div style='background:rgba(129,140,248,0.08);border-radius:8px;padding:10px;font-size:0.82rem;color:#E2E8F0;'>
            <strong>URL:</strong><br>us-south.ml.cloud.ibm.com
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

new_ibm_key = st.text_input(
    "IBM Cloud API Key:",
    value=st.session_state.ibm_api_key,
    type="password",
    placeholder="Your IBM IAM API Key (from cloud.ibm.com/iam/apikeys)",
    key="ibm_key_input"
)
new_ibm_pid = st.text_input(
    "Watsonx Project ID:",
    value=st.session_state.ibm_project_id,
    placeholder="e.g. a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    key="ibm_pid_input"
)

save_col, test_col = st.columns(2)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

with save_col:
    if st.button("💾 Save Credentials", use_container_width=True):
        if new_ibm_key.strip() and new_ibm_pid.strip():
            st.session_state.ibm_api_key = new_ibm_key.strip()
            st.session_state.ibm_project_id = new_ibm_pid.strip()
            st.session_state.api_key = new_ibm_key.strip()
            try:
                set_key(env_path, "IBM_API_KEY", new_ibm_key.strip())
                set_key(env_path, "IBM_PROJECT_ID", new_ibm_pid.strip())
                st.success("✅ IBM credentials saved to session and .env!")
            except Exception:
                st.success("✅ Saved to session. (.env write failed — check permissions)")
        else:
            st.error("Please enter both IBM API Key and Project ID.")

with test_col:
    if st.button("🔌 Test IBM Connection", use_container_width=True):
        key = new_ibm_key.strip() or st.session_state.ibm_api_key
        pid = new_ibm_pid.strip() or st.session_state.ibm_project_id
        if not key or not pid:
            st.error("Enter API Key and Project ID first.")
        else:
            with st.spinner("Testing IBM Granite connection..."):
                try:
                    from ibm_watsonx_ai import Credentials
                    from ibm_watsonx_ai.foundation_models import ModelInference
                    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params
                    creds = Credentials(url="https://us-south.ml.cloud.ibm.com", api_key=key)
                    model = ModelInference(
                        model_id="ibm/granite-3-3-8b-instruct",
                        credentials=creds,
                        project_id=pid,
                        params={Params.MAX_NEW_TOKENS: 20, Params.TEMPERATURE: 0.1}
                    )
                    result = model.generate_text(
                        prompt="<|system|>\nYou reply with one word.\n<|user|>\nSay OK\n<|assistant|>\n"
                    )
                    st.success(f"✅ IBM Granite Connected! Reply: '{result.strip()}'")
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")

# Optional Groq key for voice transcription
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🎤 Optional: Groq API Key (for Voice Transcription only)"):
    st.markdown("""
    <p style='color:#94A3B8;font-size:0.88rem;'>
    IBM Granite does not have speech-to-text. If you want voice interview mode,
    add a free Groq key (starts with <code>gsk_</code>) from
    <a href='https://console.groq.com' target='_blank' style='color:#38BDF8;'>console.groq.com</a>.
    This is used ONLY for audio transcription (Whisper).
    </p>
    """, unsafe_allow_html=True)
    groq_key = os.getenv("GROQ_API_KEY", "")
    new_groq = st.text_input("Groq API Key (optional):", value=groq_key,
                              type="password", placeholder="gsk_...")
    if st.button("Save Groq Key", use_container_width=True):
        if new_groq.strip():
            try:
                set_key(env_path, "GROQ_API_KEY", new_groq.strip())
                st.success("✅ Groq key saved to .env")
            except Exception:
                st.warning("Saved for this session only.")
        else:
            st.error("Enter a key first.")

st.markdown("<hr>", unsafe_allow_html=True)

# ══════════════════════════════════════
# 2. CURRENT STATUS
# ══════════════════════════════════════
st.markdown("### 📡 Connection Status")

ibm_k = st.session_state.ibm_api_key
ibm_p = st.session_state.ibm_project_id
groq_k = os.getenv("GROQ_API_KEY", "")

c1, c2, c3 = st.columns(3)
c1.markdown(f"""
<div class='glass-card' style='text-align:center;padding:16px;border-top:3px solid {"#10B981" if ibm_k else "#EF4444"};'>
    <div style='font-size:1.5rem;'>{"✅" if ibm_k else "❌"}</div>
    <div style='font-size:0.8rem;color:#94A3B8;margin-top:4px;'>IBM API Key</div>
    <div style='font-size:0.75rem;color:{"#10B981" if ibm_k else "#EF4444"};font-weight:600;'>
        {"Set" if ibm_k else "Missing"}
    </div>
</div>""", unsafe_allow_html=True)

c2.markdown(f"""
<div class='glass-card' style='text-align:center;padding:16px;border-top:3px solid {"#10B981" if ibm_p else "#EF4444"};'>
    <div style='font-size:1.5rem;'>{"✅" if ibm_p else "❌"}</div>
    <div style='font-size:0.8rem;color:#94A3B8;margin-top:4px;'>Project ID</div>
    <div style='font-size:0.75rem;color:{"#10B981" if ibm_p else "#EF4444"};font-weight:600;'>
        {"Set" if ibm_p else "Missing"}
    </div>
</div>""", unsafe_allow_html=True)

c3.markdown(f"""
<div class='glass-card' style='text-align:center;padding:16px;border-top:3px solid {"#10B981" if groq_k else "#F59E0B"};'>
    <div style='font-size:1.5rem;'>{"✅" if groq_k else "⚠️"}</div>
    <div style='font-size:0.8rem;color:#94A3B8;margin-top:4px;'>Groq (Voice)</div>
    <div style='font-size:0.75rem;color:{"#10B981" if groq_k else "#F59E0B"};font-weight:600;'>
        {"Set" if groq_k else "Optional"}
    </div>
</div>""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ══════════════════════════════════════
# 3. ACCOUNT OVERVIEW
# ══════════════════════════════════════
if st.session_state.get("logged_in"):
    st.markdown("### 👤 Account Overview")
    uid = st.session_state.user["id"]
    uname = st.session_state.user["username"]
    try:
        conn = get_connection()
        interviews = conn.execute(
            "SELECT COUNT(*) as c FROM interviews WHERE user_id=?", (uid,)
        ).fetchone()["c"]
        codings = conn.execute(
            "SELECT COUNT(*) as c FROM coding_history WHERE user_id=?", (uid,)
        ).fetchone()["c"]
        conn.execute("""CREATE TABLE IF NOT EXISTS mcq_results
            (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, mode TEXT,
             score INTEGER, total INTEGER, time_taken_sec INTEGER,
             taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        mcqs = conn.execute(
            "SELECT COUNT(*) as c FROM mcq_results WHERE user_id=?", (uid,)
        ).fetchone()["c"]
        has_resume = conn.execute(
            "SELECT COUNT(*) as c FROM resumes WHERE user_id=?", (uid,)
        ).fetchone()["c"]
        conn.close()

        st.markdown(f"""
<div class='glass-card' style='padding:20px;'>
    <div style='display:flex;align-items:center;gap:16px;margin-bottom:18px;'>
        <div style='width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#6366F1,#C084FC);
                    display:flex;align-items:center;justify-content:center;font-size:1.4rem;
                    font-weight:800;color:white;'>{uname[0].upper()}</div>
        <div>
            <div style='font-size:1.1rem;font-weight:700;color:#F1F5F9;'>{uname}</div>
            <div style='font-size:0.8rem;color:#475569;'>User ID #{uid}</div>
        </div>
    </div>
    <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:10px;'>
        <div class='custom-metric'><div class='custom-metric-value'>{interviews}</div>
            <div class='custom-metric-label'>Interviews</div></div>
        <div class='custom-metric'><div class='custom-metric-value'>{codings}</div>
            <div class='custom-metric-label'>Code Runs</div></div>
        <div class='custom-metric'><div class='custom-metric-value'>{mcqs}</div>
            <div class='custom-metric-label'>MCQ Tests</div></div>
        <div class='custom-metric'><div class='custom-metric-value'>{"✅" if has_resume else "❌"}</div>
            <div class='custom-metric-label'>Resume</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Could not load account stats: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Data Management ──
    st.markdown("### 🗑️ Data Management")
    with st.expander("⚠️ Delete All My Data"):
        st.warning("This will permanently delete all your interviews, coding history, and MCQ results. Your account will remain.")
        confirm = st.text_input("Type DELETE to confirm:", key="del_confirm")
        if st.button("🗑️ Permanently Delete My Data", use_container_width=True):
            if confirm == "DELETE":
                try:
                    conn = get_connection()
                    conn.execute("DELETE FROM interviews WHERE user_id=?", (uid,))
                    conn.execute("DELETE FROM coding_history WHERE user_id=?", (uid,))
                    conn.execute("DELETE FROM mcq_results WHERE user_id=?", (uid,))
                    conn.commit()
                    conn.close()
                    st.success("✅ All data deleted.")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Type DELETE exactly to confirm.")

else:
    st.info("👤 Log in to view account settings and data management.")

st.markdown("<hr>", unsafe_allow_html=True)

# ══════════════════════════════════════
# 4. HOW TO GET IBM CREDENTIALS
# ══════════════════════════════════════
st.markdown("### 📖 How to Get IBM Granite Credentials (Free)")
st.markdown("""
<div class='glass-card' style='padding:20px;'>
    <ol style='color:#E2E8F0;font-size:0.9rem;line-height:2.2;padding-left:20px;'>
        <li>Go to <a href='https://cloud.ibm.com/registration' target='_blank' style='color:#38BDF8;'>cloud.ibm.com/registration</a>
            and create a free IBM Cloud account.</li>
        <li>Open <a href='https://cloud.ibm.com/iam/apikeys' target='_blank' style='color:#38BDF8;'>cloud.ibm.com/iam/apikeys</a>
            → click <strong>Create</strong> → copy your <strong>IBM Cloud API Key</strong>.</li>
        <li>Go to <a href='https://dataplatform.cloud.ibm.com' target='_blank' style='color:#38BDF8;'>dataplatform.cloud.ibm.com</a>
            → Create a new project.</li>
        <li>Inside the project → <strong>Manage</strong> tab → <strong>General</strong> section
            → copy the <strong>Project ID</strong>.</li>
        <li>Paste both values above and click <strong>Save Credentials</strong>.</li>
    </ol>
    <div style='background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);border-radius:8px;
                padding:10px 14px;margin-top:8px;font-size:0.85rem;color:#10B981;'>
        ✅ IBM Watsonx Lite plan is free — includes Granite model access with no credit card required.
    </div>
</div>
""", unsafe_allow_html=True)
