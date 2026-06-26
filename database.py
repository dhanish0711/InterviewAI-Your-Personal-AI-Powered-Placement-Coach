import sqlite3
import hashlib
import json
import os
from datetime import datetime

DB_NAME = "interview_ai.db"

def get_connection():
    """Establish connection to SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    """Hash password using SHA256 with a salt."""
    if salt is None:
        salt = os.urandom(16).hex()
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{pwdhash.hex()}"

def verify_password(stored_password, provided_password):
    """Verify a stored password hash against a provided password."""
    try:
        salt, stored_hash = stored_password.split(':')
        provided_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return stored_hash == provided_hash
    except Exception:
        return False

def init_db():
    """Initialize database and create all tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Resumes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name TEXT,
            extracted_text TEXT,
            skills TEXT, -- JSON array of strings
            projects TEXT, -- JSON array
            experience TEXT, -- JSON array
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create Interviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL, -- e.g., 'Technical', 'HR', 'Managerial', 'Behavioral'
            overall_score REAL,
            filler_words INTEGER DEFAULT 0,
            wpm INTEGER DEFAULT 0,
            duration REAL DEFAULT 0.0,
            strengths TEXT, -- JSON array
            weaknesses TEXT, -- JSON array
            recommendations TEXT, -- JSON array
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create Interview Details table (question-by-question log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            feedback TEXT,
            scores_json TEXT, -- JSON containing breakdown scores
            FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
        )
    """)
    
    # Create Coding History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coding_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            problem_name TEXT NOT NULL,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            score REAL,
            feedback TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

# --- User Functions ---
def register_user(username, password):
    """Register a new user. Returns user_id if successful, None otherwise."""
    conn = get_connection()
    cursor = conn.cursor()
    pwd_hash = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pwd_hash))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def login_user(username, password):
    """Log in user. Returns user dictionary (id, username) if credentials are correct, None otherwise."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row and verify_password(row['password_hash'], password):
        return {"id": row['id'], "username": row['username']}
    return None

# --- Resume Functions ---
def save_resume(user_id, file_name, extracted_text, skills, projects, experience):
    """Save extracted resume details for user. Overwrites or inserts new."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Serialize Python structures to JSON strings
    skills_json = json.dumps(skills)
    projects_json = json.dumps(projects)
    experience_json = json.dumps(experience)
    
    # Delete old resume records for simplicity
    cursor.execute("DELETE FROM resumes WHERE user_id = ?", (user_id,))
    
    cursor.execute("""
        INSERT INTO resumes (user_id, file_name, extracted_text, skills, projects, experience)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, file_name, extracted_text, skills_json, projects_json, experience_json))
    
    conn.commit()
    conn.close()

def get_resume(user_id):
    """Retrieve resume record for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data = dict(row)
        data['skills'] = json.loads(data['skills']) if data['skills'] else []
        data['projects'] = json.loads(data['projects']) if data['projects'] else []
        data['experience'] = json.loads(data['experience']) if data['experience'] else []
        return data
    return None

# --- Interview Logging Functions ---
def start_interview(user_id, interview_type):
    """Create an interview session header and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO interviews (user_id, type, date) VALUES (?, ?, ?)", 
                   (user_id, interview_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    interview_id = cursor.lastrowid
    conn.close()
    return interview_id

def log_interview_question(interview_id, question, answer, feedback, scores_dict):
    """Log individual question response evaluation."""
    conn = get_connection()
    cursor = conn.cursor()
    scores_json = json.dumps(scores_dict)
    cursor.execute("""
        INSERT INTO interview_details (interview_id, question, answer, feedback, scores_json)
        VALUES (?, ?, ?, ?, ?)
    """, (interview_id, question, answer, feedback, scores_json))
    conn.commit()
    conn.close()

def finalize_interview(interview_id, overall_score, filler_words, wpm, duration, strengths, weaknesses, recommendations):
    """Update overall scores and summary in the interview header."""
    conn = get_connection()
    cursor = conn.cursor()
    strengths_json = json.dumps(strengths)
    weaknesses_json = json.dumps(weaknesses)
    recs_json = json.dumps(recommendations)
    
    cursor.execute("""
        UPDATE interviews
        SET overall_score = ?, filler_words = ?, wpm = ?, duration = ?, strengths = ?, weaknesses = ?, recommendations = ?
        WHERE id = ?
    """, (overall_score, filler_words, wpm, duration, strengths_json, weaknesses_json, recs_json, interview_id))
    
    conn.commit()
    conn.close()

# --- Coding History Functions ---
def log_coding_round(user_id, problem_name, code, language, score, feedback):
    """Save user code review outcomes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO coding_history (user_id, problem_name, code, language, score, feedback, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, problem_name, code, language, score, feedback, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- Dashboard & Statistics Functions ---
def get_user_stats(user_id):
    """Aggregate statistics for user profile dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Basic stats
    cursor.execute("""
        SELECT COUNT(*) as total_interviews,
               AVG(overall_score) as avg_score,
               SUM(filler_words) as total_filler
        FROM interviews WHERE user_id = ? AND overall_score IS NOT NULL
    """, (user_id,))
    basic = cursor.fetchone()
    
    # 2. Performance over time (line charts)
    cursor.execute("""
        SELECT id, type, overall_score, date
        FROM interviews WHERE user_id = ? AND overall_score IS NOT NULL
        ORDER BY date ASC
    """, (user_id,))
    history = [dict(row) for row in cursor.fetchall()]
    
    # 3. Coding stats
    cursor.execute("""
        SELECT COUNT(*) as total_coding, AVG(score) as avg_coding_score
        FROM coding_history WHERE user_id = ?
    """, (user_id,))
    coding = cursor.fetchone()
    
    # 4. Compile detailed score averages (communication, technical, grammar, etc.)
    # We will average the detailed scores stored in interview_details
    cursor.execute("""
        SELECT details.scores_json
        FROM interview_details details
        JOIN interviews i ON details.interview_id = i.id
        WHERE i.user_id = ? AND details.scores_json IS NOT NULL
    """, (user_id,))
    all_scores = [json.loads(row['scores_json']) for row in cursor.fetchall()]
    
    avg_breakdown = {
        "Technical Knowledge": 0.0,
        "Communication": 0.0,
        "STAR Structure": 0.0,
        "Grammar": 0.0,
        "Relevance": 0.0
    }
    
    if all_scores:
        count = len(all_scores)
        for s in all_scores:
            avg_breakdown["Technical Knowledge"] += s.get("technical_knowledge", s.get("Technical Knowledge", 0))
            avg_breakdown["Communication"] += s.get("communication", s.get("Communication", 0))
            avg_breakdown["STAR Structure"] += s.get("star_structure", s.get("STAR Structure", 0))
            avg_breakdown["Grammar"] += s.get("grammar", s.get("Grammar", 0))
            avg_breakdown["Relevance"] += s.get("relevance", s.get("Relevance", 0))
            
        for k in avg_breakdown:
            avg_breakdown[k] = round(avg_breakdown[k] / count, 1)
    
    # 5. MCQ stats — use same open connection
    mcq_total = 0
    mcq_avg = 0.0
    try:
        # Ensure mcq_results table exists
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
        cursor.execute("""
            SELECT COUNT(*) as cnt,
                   AVG(CAST(score AS REAL) / CAST(total AS REAL) * 100) as avg_pct
            FROM mcq_results WHERE user_id = ?
        """, (user_id,))
        mcq_row = cursor.fetchone()
        if mcq_row and mcq_row['cnt']:
            mcq_total = int(mcq_row['cnt'] or 0)
            mcq_avg = round(float(mcq_row['avg_pct'] or 0.0), 1)
    except Exception as e:
        print(f"MCQ stats error: {e}")

    conn.close()  # single close at the end

    return {
        "total_interviews": basic['total_interviews'] or 0,
        "avg_score": round(basic['avg_score'], 2) if basic['avg_score'] else 0.0,
        "total_filler": basic['total_filler'] or 0,
        "total_coding": coding['total_coding'] or 0,
        "avg_coding_score": round(coding['avg_coding_score'], 2) if coding['avg_coding_score'] else 0.0,
        "mcq_total": mcq_total,
        "mcq_avg_pct": mcq_avg,
        "history": history,
        "avg_breakdown": avg_breakdown
    }

def get_past_interviews(user_id):
    """Retrieve full history of interviews for list displaying."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM interviews WHERE user_id = ? ORDER BY date DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_interview_details(interview_id):
    """Retrieve details for a single interview session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get header
    cursor.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,))
    header = cursor.fetchone()
    
    if not header:
        conn.close()
        return None
        
    # Get details
    cursor.execute("SELECT * FROM interview_details WHERE interview_id = ?", (interview_id,))
    details = cursor.fetchall()
    conn.close()
    
    h_dict = dict(header)
    h_dict['strengths'] = json.loads(h_dict['strengths']) if h_dict['strengths'] else []
    h_dict['weaknesses'] = json.loads(h_dict['weaknesses']) if h_dict['weaknesses'] else []
    h_dict['recommendations'] = json.loads(h_dict['recommendations']) if h_dict['recommendations'] else []
    
    d_list = []
    for row in details:
        d = dict(row)
        d['scores_json'] = json.loads(d['scores_json']) if d['scores_json'] else {}
        d_list.append(d)
        
    return {
        "header": h_dict,
        "details": d_list
    }

# Self-running initialization check
if __name__ == "__main__":
    print("Initializing Database...")
    init_db()
    print("Database initialized successfully.")
