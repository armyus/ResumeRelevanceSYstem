import streamlit as st
import time
import os

# We need to make sure the app can find the processor.py file
# To do this, we add the parent directory to Python's path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processor import (
    load_jobs_from_db,
    extract_text_from_file,
    analyze_resume
)

# --- PAGE CONFIG ---
st.set_page_config(page_title="HireSight", layout="wide", initial_sidebar_state="collapsed")

# --- STATE MANAGEMENT ---
# This dictionary holds the current state of the app
if "page" not in st.session_state:
    st.session_state.page = "login"
    st.session_state.logged_in = False
    st.session_state.selected_job_id = None
    st.session_state.analysis_result = None
    st.session_state.username = ""

# --- FAKE AUTHENTICATION ---
def login(username, password):
    # In a real app, you'd check this against a database
    if username and password:
        st.session_state.logged_in = True
        st.session_state.page = "dashboard"
        st.session_state.username = username
        st.rerun()
    else:
        st.error("Please enter both a username and password.")

# --- UI RENDERING FUNCTIONS ---
def render_login():
    st.header("Welcome Back")
    st.markdown("Sign in to your account")
    
    with st.form("login_form"):
        username = st.text_input("Username", value="abcd")
        password = st.text_input("Password", type="password", value="1234")
        submitted = st.form_submit_button("Sign In")
        
        if submitted:
            login(username, password)

def render_dashboard():
    # --- HEADER ---
    st.markdown(f"## Welcome back, {st.session_state.username}!")
    st.markdown("Discover your next opportunity with AI-powered job matching.")
    
    # --- METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Applications Sent", "12")
    col2.metric("Average Score", "78%", "4%")
    col3.metric("Shortlisted", "4")
    col4.metric("Interviews", "2")
    st.markdown("---")

    # --- MAIN LAYOUT ---
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("Find Your Perfect Job")
        JOBS = load_jobs_from_db()

        if not JOBS:
            st.warning("No jobs have been posted yet. Please check back later.")
            return

        for job in JOBS:
            with st.container():
                st.markdown(f"### {job['title']}")
                st.markdown(f"{job['description_full'].split('.')[0]}...") # Show first sentence
                
                skills_html = "".join([f"<span class='skill-tag'>{skill}</span>" for skill in job['skills']])
                st.markdown(skills_html, unsafe_allow_html=True)
                
                uploaded_file = st.file_uploader(
                    "Upload your resume",
                    type=["pdf", "docx"],
                    key=f"uploader_{job['id']}"
                )

                if uploaded_file:
                    if st.button("Analyze with AI", key=f"button_{job['id']}"):
                        with st.spinner("Analyzing Your Resume..."):
                            resume_text = extract_text_from_file(uploaded_file)
                            jd_text = job['description_full']
                            
                            # Store result and switch page
                            st.session_state.analysis_result = analyze_resume(resume_text, jd_text)
                            st.session_state.selected_job_id = job['id']
                            st.session_state.page = "results"
                            st.rerun()

                st.markdown("<hr class='job-divider'>", unsafe_allow_html=True)

    with right_col:
        st.subheader("Recent Applications")
        st.info("Feature coming soon!")
        
        st.subheader("AI Tips")
        st.success("Add 'React' to your skills to match 23 more jobs!")

def render_results():
    if not st.session_state.analysis_result:
        st.error("No analysis result found.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        return

    result = st.session_state.analysis_result
    
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.session_state.analysis_result = None
        st.session_state.selected_job_id = None
        st.rerun()
        
    st.header("Analysis Results")
    
    # --- METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Score", f"{result['overallScore']}%")
    c2.metric("Skills Matched", result['skillsMatchedCount'])
    c3.metric("Skills Missing", result['skillsMissingCount'])
    c4.metric("Relevant Projects", result['relevantProjectsCount'])
    
    st.markdown("---")

    # --- TABS ---
    t1, t2, t3, t4 = st.tabs(["✅ Skills Analysis", "📈 Experience", "🎓 Education", "💡 Improvements"])
    
    with t1:
        st.subheader("Matched Skills")
        for skill in result['matchedSkills']:
            st.progress(skill['score'], text=f"{skill['skill']} {'(Required)' if skill['required'] else ''}")
        
        st.subheader("Missing Skills")
        for skill in result['missingSkills']:
            st.warning(f"{skill['skill']}** (Importance: {skill['importance']}) - Score Impact: {skill['impact']}%")
    
    with t2:
        st.subheader("Experience Breakdown")
        st.info(f"Required Experience: *{result['experience']['required']}*")
        st.success(f"Your Experience: *{result['experience']['match']}*")
        
    with t3:
        st.subheader("Education & Qualifications")
        st.success(f"Degree Match: *{result['education']['match']}*")

    with t4:
        st.subheader("Personalized Suggestions")
        for suggestion in result['improvements']['resume']:
            st.markdown(f"- {suggestion}")


# --- MAIN APP ROUTER ---
def main():
    # Load CSS
    # --- THIS IS THE ONLY LINE THAT CHANGED ---
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Simple router
    if st.session_state.page == "login":
        render_login()
    elif st.session_state.page == "dashboard":
        render_dashboard()
    elif st.session_state.page == "results":
        render_results()

if __name__ == "__main__":
    main()