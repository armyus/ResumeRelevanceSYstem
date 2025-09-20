import streamlit as st
import time
import json
from processor import load_jobs_from_db, extract_text_from_file, analyze_resume

# --- PAGE CONFIG ---
st.set_page_config(page_title="HireSight Job Seeker", layout="wide")


# --- STATE MANAGEMENT ---
# This dictionary holds the state of our multi-page app.
if "page" not in st.session_state:
    st.session_state.page = "login"
    st.session_state.username = ""
    st.session_state.selected_job = None
    st.session_state.analysis_result = None

# --- STYLING ---
def load_css():
    """Loads the stylesheet from the main directory."""
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Stylesheet not found. Make sure style.css is in the main project directory.")


# --- UI RENDERING FUNCTIONS (VIEWS) ---

def render_login():
    """Renders the login form."""
    st.title("Welcome Back")
    st.write("Sign in to your account")
    
    with st.form(key='login_form'):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button(label='Sign In')

        if submit_button:
            if username: # Simplified login for prototype
                st.session_state.username = username
                st.session_state.page = "dashboard"
                st.rerun() # Use the updated st.rerun()
            else:
                st.error("Please enter a username.")

def render_dashboard():
    """Renders the main job dashboard."""
    st.title(f"Welcome back, {st.session_state.username}!")
    st.write("Discover your next opportunity with AI-powered job matching.")
    
    # --- Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Applications Sent", "12")
    col2.metric("Average Score", "78%", "4%")
    col3.metric("Shortlisted", "4")
    col4.metric("Interviews", "2")
    
    st.markdown("---", unsafe_allow_html=True)

    # --- Main Layout (2 columns) ---
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.header("Find Your Perfect Job")
        JOBS = load_jobs_from_db()

        if not JOBS:
            st.warning("No jobs have been posted yet. Please check back later.")
        else:
            for job in JOBS:
                with st.container():
                    st.subheader(job['title'])
                    
                    # Create a dummy company email/name for display
                    company_info = job['title'].replace(' ', '') + "@example.com"
                    st.write(f"**{company_info}**")
                    
                    st.markdown(
                        f"""
                        <p>{job['description_full'][:100]}...</p>
                        """, unsafe_allow_html=True
                    )

                    skills_html = "".join([f"<span class='skill-tag'>{skill}</span>" for skill in job['skills']])
                    st.markdown(skills_html, unsafe_allow_html=True)
                    
                    uploaded_file = st.file_uploader(
                        "Upload your resume",
                        type=["pdf", "docx"],
                        key=f"uploader_{job['id']}"
                    )
                    
                    if uploaded_file:
                        if st.button("Analyze with AI", key=f"button_{job['id']}"):
                            st.session_state.selected_job = job
                            with st.spinner("Analyzing your resume..."):
                                resume_text = extract_text_from_file(uploaded_file)
                                jd_text = job['description_full']
                                st.session_state.analysis_result = analyze_resume(resume_text, jd_text)
                                st.session_state.page = "results"
                                st.rerun()

                    st.markdown('<hr class="job-divider">', unsafe_allow_html=True)

    with right_col:
        st.header("Recent Applications")
        st.info("Feature coming soon!")
        
        st.header("AI Tips")
        st.success("Add 'React' to your skills to match 23 more jobs!")

def render_results():
    """Renders the detailed analysis results page."""
    result = st.session_state.analysis_result
    job = st.session_state.selected_job
    
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.title("Analysis Results")
    st.subheader(f"For the role of **{job['title']}**")
    
    # --- NEW: ERROR HANDLING BLOCK ---
    # Check if the result dictionary contains an 'error' key first.
    if 'error' in result:
        st.error(f"An error occurred during the AI analysis:")
        st.error(result['error'])
        st.warning("This is often caused by an invalid or expired API key, or a billing issue with your OpenAI account. Please check your key in the Streamlit Cloud secrets.")
        return # Stop rendering the rest of the page
    # --- END OF NEW BLOCK ---

    # --- Metrics for Results ---
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Overall Score", f"{result.get('overallScore', 'N/A')}%")
    res_col2.metric("Skills Matched", result.get('skillsMatchedCount', 'N/A'))
    res_col3.metric("Skills Missing", result.get('skillsMissingCount', 'N/A'))
    res_col4.metric("Relevant Projects", result.get('relevantProjectsCount', 'N/A'))

    # --- Tabbed Interface for Details ---
    tab1, tab2, tab3, tab4 = st.tabs(["✅ Skills Analysis", "Experience", "Education", "💡 Improvements"])
    
    with tab1:
        st.subheader("Matched Skills")
        for skill in result.get('matchedSkills', []):
            st.progress(skill.get('score', 0), text=f"{skill.get('skill', 'Unknown')} {'(Required)' if skill.get('required') else ''}")
        
        st.subheader("Missing Skills")
        for skill in result.get('missingSkills', []):
            st.warning(f"**{skill.get('skill', 'Unknown')}** (Importance: {skill.get('importance', 'N/A')})")

    with tab2:
        exp = result.get('experience', {})
        st.metric("Required Experience", exp.get('required', 'N/A'))
        st.metric("Your Experience Match", exp.get('match', 'N/A'), delta=exp.get('level', ''))

    with tab3:
        edu = result.get('education', {})
        st.metric("Education Match", edu.get('match', 'N/A'))
        st.metric("Institution Ranking", edu.get('ranking', 'N/A'))

    with tab4:
        st.subheader("Resume Suggestions")
        improvements = result.get('improvements', {})
        for suggestion in improvements.get('resume', []):
            st.info(suggestion)
            
# --- MAIN APP LOGIC (ROUTER) ---
def main():
    load_css()
    if st.session_state.page == "login":
        render_login()
    elif st.session_state.page == "dashboard":
        render_dashboard()
    elif st.session_state.page == "results":
        render_results()

if __name__ == "__main__":
    main()
