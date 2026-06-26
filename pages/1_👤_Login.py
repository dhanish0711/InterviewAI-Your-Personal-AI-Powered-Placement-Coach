import streamlit as st
import os
import time
from database import login_user, register_user

# Page Configuration
st.set_page_config(page_title="Authentication - InterviewAI", page_icon="👤", layout="centered")

# Load CSS styling
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center;'><span class='accent-header'>👤 Account Gateway</span></h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8;'>Sign in to log mock interviews, save resumes, and view analytics.</p>", unsafe_allow_html=True)

# Main Container
with st.container():
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### Sign In to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    user = login_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success(f"Welcome back, {username}! Redirecting to Home...")
                        time.sleep(1) # Brief pause for user to read success message
                        st.switch_page("app.py")
                    else:
                        st.error("Invalid username or password.")
        
        # Judge/Examiner Bypass Section
        st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B;'>Evaluation Mode</p>", unsafe_allow_html=True)
        if st.button("🚀 Quick Demo Login (Skip Registration)", use_container_width=True):
            # Try to register demo user if not exists
            register_user("Demo_User", "demo123")
            user = login_user("Demo_User", "demo123")
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success("Logged in as Demo_User! Redirecting to Home...")
                time.sleep(1)
                st.switch_page("app.py")
            else:
                st.error("Bypass login failed. Please register manually.")
                
    with tab2:
        st.markdown("### Create an Account")
        with st.form("register_form"):
            new_username = st.text_input("Choose Username", placeholder="Enter new username")
            new_password = st.text_input("Create Password", type="password", placeholder="Enter secure password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            register_submitted = st.form_submit_button("Register Account", use_container_width=True)
            
            if register_submitted:
                if not new_username or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    user_id = register_user(new_username, new_password)
                    if user_id:
                        # Auto login
                        user = login_user(new_username, new_password)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user = user
                            st.success("Registration successful! Redirecting to Home...")
                            time.sleep(1)
                            st.switch_page("app.py")
                    else:
                        st.error("Username already exists. Please choose a different one.")

# Back to home link
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'><a href='/' target='_self' style='color: #818CF8; text-decoration: none;'>← Back to Home Page</a></p>", unsafe_allow_html=True)
