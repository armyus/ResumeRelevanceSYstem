import streamlit as st
import os
from processor import extract_text, parse_jd_sections, analyze_resume, save_to_db, init_db
import pandas as pd
import sqlite3
import json
import io

# Initialize DB (run once)
init_db()

st.title("Resume Relevance Check System")
st.markdown("A tool to evaluate resume relevance against job descriptions. Built for Innomatics Research Labs.")

# Sidebar for uploads
st.sidebar.header("Upload Files")
jd_file = st.sidebar.file_uploader("Upload Job Description (PDF/DOCX)", type=["pdf", "docx"])
resume_files = st.sidebar.file_uploader("Upload Resumes (PDF/DOCX)", type=["pdf", "docx"], accept_multiple_files=True)

# Process button
if st.sidebar.button("Analyze Resumes"):
    if jd_file and resume_files:
        with st.spinner("Processing..."):
            # Save uploaded files temporarily
            jd_path = os.path.join("temp", jd_file.name)
            os.makedirs("temp", exist_ok=True)
            with open(jd_path, "wb") as f:
                f.write(jd_file.getbuffer())

            resume_paths = []
            for resume_file in resume_files:
                resume_path = os.path.join("temp", resume_file.name)
                with open(resume_path, "wb") as f:
                    f.write(resume_file.getbuffer())
                resume_paths.append(resume_path)

            # Process JD
            jd_text = extract_text(jd_path)
            jd_sections = parse_jd_sections(jd_text)

            # Analyze each resume
            results = []
            for resume_path in resume_paths:
                result = analyze_resume(resume_path, jd_text, jd_sections)
                results.append(result)

            # Save to DB
            save_to_db(jd_file.name, results)

            # Display results
            st.header("Analysis Results")
            df = pd.DataFrame(results)
            df = df[['resume_file', 'total_score', 'verdict', 'matched_skills', 'missing_skills', 'suggestions', 'objective']]
            st.dataframe(df.style.format({'total_score': '{:.2f}'}).set_properties(**{'text-align': 'left'}))

            # Filter by verdict
            verdict_filter = st.selectbox("Filter by Verdict", ["All", "High", "Medium", "Low"])
            if verdict_filter != "All":
                df = df[df['verdict'] == verdict_filter]
            st.dataframe(df.style.format({'total_score': '{:.2f}'}).set_properties(**{'text-align': 'left'}))

            # Download results
            csv = df.to_csv(index=False)
            st.download_button(label="Download Results as CSV", data=csv, file_name="relevance_results.csv", mime="text/csv")

            # Clean up temp files
            for path in [jd_path] + resume_paths:
                if os.path.exists(path):
                    os.remove(path)

        st.success("Analysis complete!")
    else:
        st.error("Please upload both a JD and at least one resume.")

# Display stored results
st.header("Previous Evaluations")
conn = sqlite3.connect('results.db')
query = "SELECT jd_file, resume_file, score, verdict, matched_skills, missing_skills, suggestions FROM evaluations"
stored_df = pd.read_sql_query(query, conn)
conn.close()
if not stored_df.empty:
    stored_df['matched_skills'] = stored_df['matched_skills'].apply(json.loads)
    stored_df['missing_skills'] = stored_df['missing_skills'].apply(json.loads)
    st.dataframe(stored_df.style.format({'score': '{:.2f}'}).set_properties(**{'text-align': 'left'}))
else:
    st.write("No previous evaluations found.")

# Footer
st.sidebar.text("Built by [Your Team Name] for Innomatics Research Labs")