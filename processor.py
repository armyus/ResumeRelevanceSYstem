import sqlite3
import os
import json
import re
import tempfile

# Third-party libraries
import PyPDF2
import docx2txt
import pdfplumber
from langchain_openai import ChatOpenAI

# --- Database ---
# --- FINAL, CORRECTED PATH LOGIC ---
# This logic ensures both apps find the single database in the project's root folder.
current_dir = os.path.dirname(os.path.abspath(_file_))
# If the script is running from the 'frontend' folder, go up one level to find the root.
if os.path.basename(current_dir) == 'frontend':
    PROJECT_ROOT = os.path.dirname(current_dir)
else:
    PROJECT_ROOT = current_dir
DB_PATH = os.path.join(PROJECT_ROOT, 'results.db')
# --- END OF CHANGE ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            skills TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create results table (for analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            score INTEGER NOT NULL,
            verdict TEXT,
            missing_skills TEXT,
            suggestions TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_job_to_db(title, description, skills):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (title, description, skills) VALUES (?, ?, ?)",
        (title, description, json.dumps(skills))
    )
    conn.commit()
    conn.close()

def load_jobs_from_db():
    if not os.path.exists(DB_PATH):
        return [] # Return empty list if database doesn't exist yet
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY timestamp DESC")
    jobs = cursor.fetchall()
    conn.close()
    
    # Convert list of tuples to list of dicts for easier handling
    job_list = []
    for job in jobs:
        job_list.append({
            "id": job[0],
            "title": job[1],
            "description_full": job[2],
            "skills": json.loads(job[3]),
            "timestamp": job[4]
        })
    return job_list

# --- File Processing ---
def extract_text_from_file(file):
    """Extracts text from PDF or DOCX and cleans it."""
    try:
        if file.type == "application/pdf":
            with pdfplumber.open(file) as pdf:
                raw_text = "".join(page.extract_text() for page in pdf.pages if page.extract_text())
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raw_text = docx2txt.process(file)
        else:
            return "Unsupported file type."

        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', raw_text) 
        text = re.sub(r' +', ' ', text) 
        return text.strip()

    except Exception as e:
        return f"Error extracting text: {e}"

# --- AI Analysis ---
def analyze_resume(resume_text, jd_text):
    """Analyzes resume against job description using an LLM or returns dummy data."""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        # Fallback to dummy data if no API key is set
        return {
            "overallScore": 78,
            "scoreGoodness": "Good Match",
            "skillsMatchedCount": 4,
            "skillsMissingCount": 3,
            "relevantProjectsCount": 3,
            "matchedSkills": [
                {"skill": "React", "required": True, "score": 95},
                {"skill": "JavaScript", "required": True, "score": 90},
                {"skill": "HTML/CSS", "required": True, "score": 88},
                {"skill": "Git", "required": False, "score": 85}
            ],
            "missingSkills": [
                {"skill": "TypeScript", "importance": "High", "impact": -15},
                {"skill": "Redux", "importance": "Medium", "impact": -8},
                {"skill": "Testing (Jest)", "importance": "Medium", "impact": -6}
            ],
            "experience": {
                "required": "2-4 years",
                "match": "2.5 years",
                "level": "Good"
            },
            "education": {
                "match": "Perfect",
                "ranking": "Good"
            },
            "improvements": {
                "skills": ["Focus on TypeScript.", "Learn Redux for state management."],
                "experience": ["Contribute to larger-scale projects."],
                "resume": ["Quantify achievements in project descriptions."]
            }
        }

    # If API key exists, proceed with real analysis
    try:
        llm = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
        prompt = f"""
        Analyze the following resume against the job description.
        Provide a detailed analysis in JSON format with the following keys:
        "overallScore", "scoreGoodness", "skillsMatchedCount", "skillsMissingCount", 
        "relevantProjectsCount", "matchedSkills", "missingSkills", "experience", 
        "education", "improvements".

        Resume Text:
        ---
        {resume_text}
        ---

        Job Description Text:
        ---
        {jd_text}
        ---
        """
        response = llm.invoke(prompt)
        return json.loads(response.content)

    except Exception as e:
        return {"error": f"An error occurred during AI analysis: {e}"}