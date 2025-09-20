import streamlit as st
import pandas as pd
import sqlite3
import json
from processor import (
    init_db,
    extract_text_from_file,
    save_job_to_db
)

# --- Initialize Database ---
# This ensures the DB and tables are created when the app starts
init_db()

# --- Page Config ---
st.set_page_config(page_title="HireSight Admin", layout="wide")
st.title("HireSight — Recruiter Admin Panel")

# --- UI Layout ---
tabs = st.tabs(["Dashboard", "Upload JD", "Upload Resume (Legacy)", "Admin"])

with tabs[0]:
    st.header("Results Dashboard")
    # You can add logic here to view analysis results if needed

with tabs[1]:
    st.header("Upload Job Description (JD)")
    
    jd_file = st.file_uploader("Upload JD File (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    role_title = st.text_input("Role Title (e.g., Frontend Developer)")
    skills = st.text_input("Enter comma-separated skills (e.g., Python,React,AWS)")
    
    if st.button("Process and Save JD"):
        if jd_file and role_title and skills:
            jd_text = extract_text_from_file(jd_file)
            skills_list = [skill.strip() for skill in skills.split(',')]
            
            save_job_to_db(role_title, jd_text, skills_list)
            
            st.success("JD processed and SAVED to the live jobs database.")
            with st.expander("See JD Text"):
                # --- THIS IS THE ONLY LINE THAT CHANGED ---
                st.markdown(f"text\n{jd_text}\n")
                # --- This will display the text in a clean, scrollable box ---
        else:
            st.error("Please fill in all fields before processing.")
            
# The other tabs can be left as placeholders or built out later.
with tabs[2]:
    st.info("This is a legacy tab. Please use the main Job Seeker app for analysis.")
with tabs[3]:
    st.info("Admin functions can be added here.")