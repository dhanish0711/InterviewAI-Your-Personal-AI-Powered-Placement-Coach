import streamlit as st
import os
from dotenv import load_dotenv
from database import log_coding_round, get_resume
from gemini_service import evaluate_code_with_ai, generate_coding_problem

load_dotenv(override=True)

st.set_page_config(page_title="Coding Sandbox - InterviewAI", page_icon="💻", layout="wide")

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

st.markdown("<h2>💻 Coding Sandbox & <span class='accent-header'>AI Code Review</span></h2>", unsafe_allow_html=True)

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

# ─────────────────────── BUILT-IN CLASSIC PROBLEMS ───────────────────────
CLASSIC_PROBLEMS = {
    "Two Sum": {
        "difficulty": "Easy",
        "topic": "Hash Maps",
        "tags": ["arrays", "hash-map"],
        "description": """Given an array of integers `nums` and an integer `target`, return **indices** of the two numbers that add up to `target`.

**Example 1:**
- Input: `nums = [2, 7, 11, 15]`, `target = 9`
- Output: `[0, 1]` → `nums[0] + nums[1] = 9`

**Example 2:**
- Input: `nums = [3, 2, 4]`, `target = 6`
- Output: `[1, 2]`

**Constraints:** Each input has exactly one solution. You may not use the same element twice. Aim for O(N) time.""",
        "hint1": "A brute force O(N²) nested loop works but can you do better?",
        "hint2": "Think about what complement you need for each element: `target - nums[i]`.",
        "hint3": "Use a hash map to store each value's index. For each element, check if its complement already exists in the map.",
        "starter": {
            "Python": "def twoSum(nums, target):\n    \"\"\"\n    :param nums: List[int]\n    :param target: int\n    :return: List[int] — indices of the two numbers\n    \"\"\"\n    # Write your solution here\n    pass\n\n# Test cases\nprint(twoSum([2, 7, 11, 15], 9))  # Expected: [0, 1]\nprint(twoSum([3, 2, 4], 6))       # Expected: [1, 2]",
            "Java": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        // Write your solution here\n        return new int[]{};\n    }\n\n    public static void main(String[] args) {\n        Solution s = new Solution();\n        int[] res = s.twoSum(new int[]{2,7,11,15}, 9);\n        System.out.println(res[0] + \", \" + res[1]); // Expected: 0, 1\n    }\n}",
            "C++": "class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        // Write your solution here\n        return {};\n    }\n};",
        },
    },
    "Valid Parentheses": {
        "difficulty": "Easy",
        "topic": "Stack",
        "tags": ["stack", "strings"],
        "description": """Given a string `s` containing only `(`, `)`, `{`, `}`, `[`, `]`, determine if the input string is **valid**.

An input is valid if:
- Open brackets must be closed by the **same type** of brackets
- Open brackets must be closed in the **correct order**
- Every closing bracket has a corresponding open bracket

**Example 1:** `s = "()[]{}"` → `True`  
**Example 2:** `s = "(]"` → `False`  
**Example 3:** `s = "([)]"` → `False`

**Constraints:** `1 <= len(s) <= 10⁴`""",
        "hint1": "Process the string character by character.",
        "hint2": "When you see an opening bracket, you need to remember it for later. What data structure helps with 'last in, first out'?",
        "hint3": "Use a stack. Push opening brackets. When you see a closing bracket, pop the stack and check if they match.",
        "starter": {
            "Python": "def isValid(s):\n    \"\"\"\n    :param s: str\n    :return: bool\n    \"\"\"\n    # Write your solution here\n    pass\n\n# Test cases\nprint(isValid('()[]{}'))  # True\nprint(isValid('(]'))       # False\nprint(isValid('([)]'))     # False",
            "Java": "class Solution {\n    public boolean isValid(String s) {\n        // Write your solution here\n        return false;\n    }\n}",
            "C++": "class Solution {\npublic:\n    bool isValid(string s) {\n        // Write your solution here\n        return false;\n    }\n};",
        },
    },
    "Longest Substring Without Repeating": {
        "difficulty": "Medium",
        "topic": "Sliding Window",
        "tags": ["sliding-window", "hash-map", "strings"],
        "description": """Given a string `s`, find the **length** of the longest substring without repeating characters.

**Example 1:**
- Input: `s = "abcabcbb"`
- Output: `3` → "abc"

**Example 2:**
- Input: `s = "bbbbb"`
- Output: `1` → "b"

**Example 3:**
- Input: `s = "pwwkew"`
- Output: `3` → "wke"

**Constraints:** `0 <= len(s) <= 5 * 10⁴`. Aim for O(N) time.""",
        "hint1": "A brute force checks all substrings — O(N³). How can you avoid re-scanning?",
        "hint2": "Use two pointers (left, right) to define a sliding window of non-repeating characters.",
        "hint3": "Maintain a set of characters in the current window. When a duplicate is found, shrink from the left until it's gone.",
        "starter": {
            "Python": "def lengthOfLongestSubstring(s):\n    \"\"\"\n    :param s: str\n    :return: int\n    \"\"\"\n    # Write your solution here\n    return 0\n\n# Test cases\nprint(lengthOfLongestSubstring('abcabcbb'))  # 3\nprint(lengthOfLongestSubstring('bbbbb'))     # 1\nprint(lengthOfLongestSubstring('pwwkew'))    # 3",
            "Java": "class Solution {\n    public int lengthOfLongestSubstring(String s) {\n        // Write your solution here\n        return 0;\n    }\n}",
            "C++": "class Solution {\npublic:\n    int lengthOfLongestSubstring(string s) {\n        // Write your solution here\n        return 0;\n    }\n};",
        },
    },
    "Binary Search": {
        "difficulty": "Easy",
        "topic": "Binary Search",
        "tags": ["binary-search", "arrays"],
        "description": """Given a **sorted** array of integers `nums` and an integer `target`, return the **index** of target using binary search. Return `-1` if not found.

**Example 1:**
- Input: `nums = [-1, 0, 3, 5, 9, 12]`, `target = 9`
- Output: `4`

**Example 2:**
- Input: `nums = [-1, 0, 3, 5, 9, 12]`, `target = 2`
- Output: `-1`

**Constraints:** Must run in **O(log N)** time. All elements are unique.""",
        "hint1": "Don't use linear search. How can you eliminate half the array each time?",
        "hint2": "Compare the middle element to target. Is target in the left or right half?",
        "hint3": "Maintain `left` and `right` pointers. Mid = (left + right) // 2. Update pointers based on comparison.",
        "starter": {
            "Python": "def search(nums, target):\n    \"\"\"\n    :param nums: List[int] — sorted\n    :param target: int\n    :return: int — index or -1\n    \"\"\"\n    # Write your binary search here\n    pass\n\n# Test cases\nprint(search([-1, 0, 3, 5, 9, 12], 9))   # 4\nprint(search([-1, 0, 3, 5, 9, 12], 2))   # -1",
            "Java": "class Solution {\n    public int search(int[] nums, int target) {\n        // Write your solution here\n        return -1;\n    }\n}",
            "C++": "class Solution {\npublic:\n    int search(vector<int>& nums, int target) {\n        // Write your solution here\n        return -1;\n    }\n};",
        },
    },
    "Reverse Linked List": {
        "difficulty": "Easy",
        "topic": "Linked Lists",
        "tags": ["linked-list", "recursion"],
        "description": """Given the head of a singly linked list, **reverse the list** and return the reversed list.

**Example 1:**
- Input: `head = [1 → 2 → 3 → 4 → 5]`
- Output: `[5 → 4 → 3 → 2 → 1]`

**Example 2:**
- Input: `head = [1 → 2]`
- Output: `[2 → 1]`

**Constraints:** Number of nodes between 0 and 5000. Solve iteratively **and** recursively.""",
        "hint1": "You need to change the direction of each node's `next` pointer.",
        "hint2": "Use three pointers: `prev`, `curr`, `next_node`. Iterate through and reverse links.",
        "hint3": "At each step: save `curr.next`, point `curr.next = prev`, advance `prev = curr`, `curr = saved`.",
        "starter": {
            "Python": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverseList(head):\n    \"\"\"\n    :param head: Optional[ListNode]\n    :return: Optional[ListNode]\n    \"\"\"\n    # Write your solution here\n    pass",
            "Java": "class Solution {\n    public ListNode reverseList(ListNode head) {\n        // Write your solution here\n        return null;\n    }\n}",
            "C++": "class Solution {\npublic:\n    ListNode* reverseList(ListNode* head) {\n        // Write your solution here\n        return nullptr;\n    }\n};",
        },
    },
}

# ─────────────────────── SIDEBAR ───────────────────────
with st.sidebar:
    st.markdown("### 🎯 Problem Mode")
    mode = st.radio(
        "Choose problem source:",
        ["🤖 AI Personalized (from Resume)", "📚 Classic Problems"],
        index=0 if resume else 1
    )
    st.markdown("<hr style='border-color:rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

    language = st.selectbox("🖥️ Language:", ["Python", "Java", "C++"])

    if mode == "🤖 AI Personalized (from Resume)":
        difficulty = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"], index=1)
    else:
        selected_classic = st.selectbox("Choose Problem:", list(CLASSIC_PROBLEMS.keys()))

# ─────────────────────── MAIN LAYOUT ───────────────────────
if mode == "🤖 AI Personalized (from Resume)":
    # ── PERSONALIZED SECTION ──
    if not resume:
        st.markdown("""
        <div class='glass-card' style='text-align:center; padding:50px; border-left:4px solid #F59E0B;'>
            <div style='font-size:3rem;'>📄</div>
            <h3 style='color:#F59E0B;'>Resume Not Found</h3>
            <p style='color:#94A3B8;'>Upload your resume first so the AI can personalize coding problems based on your skills, projects, and technologies.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📄 Upload Resume Now", use_container_width=True):
            st.switch_page("pages/2_📄_Resume_&_ATS.py")
        st.stop()

    # Show resume skills summary
    skills = resume.get("skills", [])
    projects = resume.get("projects", [])

    skills_preview = " • ".join(skills[:8]) if skills else "No skills found"
    st.markdown(f"""
    <div class='glass-card' style='padding:14px 20px; border-left:4px solid #818CF8; margin-bottom:10px;'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <strong style='color:#818CF8;'>🎯 Personalizing based on your resume</strong>
                <div style='color:#94A3B8; font-size:0.85rem; margin-top:4px;'>Skills: {skills_preview}</div>
            </div>
            <span class='badge' style='background:rgba(129,140,248,0.15);color:#818CF8;'>{difficulty}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Generate or load personalized problem
    prob_key = f"ai_problem_{difficulty}_{language}"

    col_gen, col_new = st.columns([3, 1])
    with col_gen:
        gen_btn = st.button(
            f"🤖 Generate {difficulty} Problem from My Resume",
            use_container_width=True,
            type="primary"
        )
    with col_new:
        new_btn = st.button("🔄 New Problem", use_container_width=True)

    if new_btn and prob_key in st.session_state:
        del st.session_state[prob_key]
        if f"code_ai_{difficulty}_{language}" in st.session_state:
            del st.session_state[f"code_ai_{difficulty}_{language}"]
        st.rerun()

    if gen_btn or prob_key not in st.session_state:
        if gen_btn or prob_key not in st.session_state:
            with st.spinner(f"🧠 AI is crafting a {difficulty} {language} problem based on your resume skills and projects..."):
                problem = generate_coding_problem(
                    resume_text=resume["extracted_text"],
                    difficulty=difficulty,
                    language=language,
                    api_key=ibm_key,
                    project_id=project_id
                )
            if problem:
                st.session_state[prob_key] = problem
                # Clear old code when new problem generated
                if f"code_ai_{difficulty}_{language}" in st.session_state:
                    del st.session_state[f"code_ai_{difficulty}_{language}"]
                st.rerun()
            else:
                st.error("❌ Failed to generate problem. Please check your API key or try again.")
                st.stop()

    if prob_key not in st.session_state:
        st.info("👆 Click **Generate Problem** to get a personalized coding challenge from your resume.")
        st.stop()

    prob = st.session_state[prob_key]

    # ── PROBLEM + CODE EDITOR ──
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        diff_colors = {"Easy": "#10B981", "Medium": "#F59E0B", "Hard": "#EF4444"}
        diff_color = diff_colors.get(prob.get("difficulty", difficulty), "#818CF8")
        tags_html = "".join([
            f"<span style='background:rgba(129,140,248,0.1);color:#818CF8;padding:2px 8px;border-radius:20px;font-size:0.75rem;margin-right:5px;'>{t}</span>"
            for t in prob.get("tags", [])
        ])

        st.markdown(f"""
        <div class='glass-card' style='padding:20px;'>
            <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;'>
                <div>
                    <h3 style='margin:0 0 6px;'>{prob.get('title','AI Problem')}</h3>
                    <div>{tags_html}</div>
                </div>
                <div style='text-align:right;'>
                    <span style='background:{diff_color}22;color:{diff_color};padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;'>{prob.get('difficulty', difficulty)}</span>
                    <div style='color:#94A3B8;font-size:0.8rem;margin-top:4px;'>Topic: {prob.get('topic','DSA')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(prob.get("description", ""))

        # Hints — progressive reveal
        st.markdown("#### 💡 Hints (reveal one at a time)")
        hint1_col, hint2_col, hint3_col = st.columns(3)
        with hint1_col:
            with st.expander("Hint 1 — Direction"):
                st.info(prob.get("hint1", "Think carefully about the data structure."))
        with hint2_col:
            with st.expander("Hint 2 — Algorithm"):
                st.warning(prob.get("hint2", "Consider the time complexity target."))
        with hint3_col:
            with st.expander("Hint 3 — Near Solution"):
                st.error(prob.get("hint3", "Check if a greedy or DP approach fits."))

    with col2:
        st.markdown("### ✍️ Your Solution")

        editor_key = f"code_ai_{difficulty}_{language}"
        starter = prob.get("starter_code", f"# Write your {language} solution here\ndef solution():\n    pass")
        if editor_key not in st.session_state:
            st.session_state[editor_key] = starter

        code_input = st.text_area(
            f"Code ({language}):",
            value=st.session_state[editor_key],
            height=300,
            key=f"editor_ai_{difficulty}_{language}"
        )
        st.session_state[editor_key] = code_input

        eval_btn = st.button("🚀 Evaluate My Solution", use_container_width=True, type="primary")

        if eval_btn:
            if len(code_input.strip()) < 30:
                st.error("Please write a more complete solution before evaluating.")
            else:
                with st.spinner("AI is analysing your code — checking correctness, complexity, and style..."):
                    results = evaluate_code_with_ai(
                        problem_name=prob.get("title", "AI Problem"),
                        code=code_input,
                        language=language,
                        api_key=ibm_key,
                        project_id=project_id
                    )
                    log_coding_round(
                        user_id, prob.get("title", "AI Problem"),
                        code_input, language,
                        results.get("score", 0), results.get("feedback", "")
                    )
                    st.session_state["coding_results"] = results
                    st.success("✅ Analysis complete!")

        # ── RESULTS ──
        if "coding_results" in st.session_state:
            res = st.session_state.coding_results
            score = res.get("score", 0)
            score_color = "#10B981" if score >= 75 else "#F59E0B" if score >= 50 else "#EF4444"
            syntax_ok = res.get("syntax_correct", True)

            st.markdown(f"""
            <div class='glass-card' style='padding:18px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;'>
                    <span class='badge {"badge-success" if syntax_ok else "badge-danger"}'>
                        {"✅ Syntax Valid" if syntax_ok else "❌ Syntax Error"}
                    </span>
                    <span style='font-size:2rem;font-weight:800;color:{score_color};'>{score}/100</span>
                </div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;'>
                    <div class='custom-metric'>
                        <div class='custom-metric-value' style='font-size:1.1rem;'>{res.get('time_complexity','O(?)')}</div>
                        <div class='custom-metric-label'>Time Complexity</div>
                    </div>
                    <div class='custom-metric'>
                        <div class='custom-metric-value' style='font-size:1.1rem;'>{res.get('space_complexity','O(?)')}</div>
                        <div class='custom-metric-label'>Space Complexity</div>
                    </div>
                </div>
                <hr style='border-color:rgba(255,255,255,0.05);margin:10px 0;'>
                <h4>📝 Feedback</h4>
                <p style='font-size:0.9rem;line-height:1.6;'>{res.get('feedback','')}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### 🌟 Optimized Solution")
            lang_map = {"Python": "python", "Java": "java", "C++": "cpp"}
            st.code(res.get("optimized_code", ""), language=lang_map.get(language, "python"))

else:
    # ── CLASSIC PROBLEMS SECTION ──
    prob = CLASSIC_PROBLEMS[selected_classic]

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        diff_colors = {"Easy": "#10B981", "Medium": "#F59E0B", "Hard": "#EF4444"}
        diff_color = diff_colors.get(prob["difficulty"], "#818CF8")
        tags_html = "".join([
            f"<span style='background:rgba(129,140,248,0.1);color:#818CF8;padding:2px 8px;border-radius:20px;font-size:0.75rem;margin-right:5px;'>{t}</span>"
            for t in prob.get("tags", [])
        ])

        st.markdown(f"""
        <div class='glass-card' style='padding:20px;'>
            <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;'>
                <div>
                    <h3 style='margin:0 0 6px;'>{selected_classic}</h3>
                    <div>{tags_html}</div>
                </div>
                <div style='text-align:right;'>
                    <span style='background:{diff_color}22;color:{diff_color};padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;'>{prob['difficulty']}</span>
                    <div style='color:#94A3B8;font-size:0.8rem;margin-top:4px;'>Topic: {prob.get('topic','DSA')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(prob["description"])

        st.markdown("#### 💡 Hints (reveal one at a time)")
        h1, h2, h3 = st.columns(3)
        with h1:
            with st.expander("Hint 1"):
                st.info(prob.get("hint1", ""))
        with h2:
            with st.expander("Hint 2"):
                st.warning(prob.get("hint2", ""))
        with h3:
            with st.expander("Hint 3"):
                st.error(prob.get("hint3", ""))

    with col2:
        st.markdown("### ✍️ Your Solution")

        editor_key = f"code_classic_{selected_classic}_{language}"
        starter_code = prob["starter"].get(language, "")
        if editor_key not in st.session_state:
            st.session_state[editor_key] = starter_code

        code_input = st.text_area(
            f"Code ({language}):",
            value=st.session_state[editor_key],
            height=300,
            key=f"editor_classic_{selected_classic}_{language}"
        )
        st.session_state[editor_key] = code_input

        eval_btn = st.button("🚀 Evaluate My Solution", use_container_width=True, type="primary")

        if eval_btn:
            if len(code_input.strip()) < 20:
                st.error("Please write a more complete solution.")
            else:
                with st.spinner("Analysing complexity and correctness..."):
                    results = evaluate_code_with_ai(
                        selected_classic, code_input, language, api_key=ibm_key,
                        project_id=project_id
                    )
                    log_coding_round(user_id, selected_classic, code_input, language,
                                     results.get("score", 0), results.get("feedback", ""))
                    st.session_state["coding_results"] = results
                    st.success("✅ Analysis complete!")

        if "coding_results" in st.session_state:
            res = st.session_state.coding_results
            score = res.get("score", 0)
            score_color = "#10B981" if score >= 75 else "#F59E0B" if score >= 50 else "#EF4444"
            syntax_ok = res.get("syntax_correct", True)

            st.markdown(f"""
            <div class='glass-card' style='padding:18px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;'>
                    <span class='badge {"badge-success" if syntax_ok else "badge-danger"}'>
                        {"✅ Syntax Valid" if syntax_ok else "❌ Syntax Error"}
                    </span>
                    <span style='font-size:2rem;font-weight:800;color:{score_color};'>{score}/100</span>
                </div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;'>
                    <div class='custom-metric'>
                        <div class='custom-metric-value' style='font-size:1.1rem;'>{res.get('time_complexity','O(?)')}</div>
                        <div class='custom-metric-label'>Time Complexity</div>
                    </div>
                    <div class='custom-metric'>
                        <div class='custom-metric-value' style='font-size:1.1rem;'>{res.get('space_complexity','O(?)')}</div>
                        <div class='custom-metric-label'>Space Complexity</div>
                    </div>
                </div>
                <hr style='border-color:rgba(255,255,255,0.05);margin:10px 0;'>
                <h4>📝 Feedback</h4>
                <p style='font-size:0.9rem;line-height:1.6;'>{res.get('feedback','')}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### 🌟 Optimized Solution")
            lang_map = {"Python": "python", "Java": "java", "C++": "cpp"}
            st.code(res.get("optimized_code", ""), language=lang_map.get(language, "python"))

        # Nudge to try personalized
        if resume:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class='glass-card' style='text-align:center;border-left:4px solid #818CF8;padding:14px;'>
                <strong>💡 Tip:</strong> Switch to <strong>AI Personalized</strong> mode in the sidebar to get problems
                tailored to <em>your specific resume skills</em>!
            </div>
            """, unsafe_allow_html=True)
