import sqlite3
import os
import json
import re

# Third-party libraries
import PyPDF2
import docx2txt
import pdfplumber
from langchain_community.llms import HuggingFaceHub
from langchain_openai import ChatOpenAI

# --- Database ---
# This logic ensures the app finds the single database in the project's root folder.
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == 'pages':
    PROJECT_ROOT = os.path.dirname(os.path.dirname(current_dir))
else:
    PROJECT_ROOT = current_dir
DB_PATH = os.path.join(PROJECT_ROOT, 'results.db')


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
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY timestamp DESC")
    jobs = cursor.fetchall()
    conn.close()
    
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
    """Analyzes resume against job description using the best available free model."""
    hf_api_key = os.getenv("HUGGINGFACEHUB_API_TOKEN")

    if not hf_api_key:
        # Fallback to dummy data if no API key is set
        return {
            "overallScore": 78, "scoreGoodness": "Good Match", "skillsMatchedCount": 4,
            "skillsMissingCount": 3, "relevantProjectsCount": 3
        }

    try:
        llm = HuggingFaceHub(
            repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
            huggingfacehub_api_token=hf_api_key,
            # --- THIS IS THE FIX ---
            model_kwargs={"task": "text-generation", "temperature": 0.2, "max_new_tokens": 1024}
        )
        prompt = f"""
        [INST] You are an expert HR analyst. Analyze the following resume against the job description.
        Provide a detailed analysis ONLY in JSON format with the following keys:
        "overallScore", "scoreGoodness", "skillsMatchedCount", "skillsMissingCount", 
        "relevantProjectsCount", "matchedSkills", "missingSkills", "experience", 
        "education", "improvements". Do not provide any explanation or text outside of the JSON object.

        Resume Text:---
        {resume_text}
        ---
        Job Description Text:---
        {jd_text}
        ---
        [/INST]
        """
        response = llm.invoke(prompt)
        json_response_str = response.strip().split('{', 1)[1].rsplit('}', 1)[0]
        return json.loads('{' + json_response_str + '}')

    except Exception as e:
        return {"error": f"An error occurred during AI analysis: {e}"}

