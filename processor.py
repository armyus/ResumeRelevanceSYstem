import sqlite3
import os
import json
import re

# Third-party libraries
import PyPDF2
import docx2txt
import pdfplumber
# --- We are using the stable, reliable class ---
from langchain_community.llms import HuggingFaceHub

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
        return {"error": "Hugging Face API Token not found. Please check the secret name in your Streamlit settings. It must be exactly HUGGINGFACEHUB_API_TOKEN."}

    try:
        llm = HuggingFaceHub(
            repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
            huggingfacehub_api_token=hf_api_key, 
            model_kwargs={"task": "text-generation", "temperature": 0.1, "max_new_tokens": 1500}
        )
        
        prompt = f"""
        [INST] You are an expert HR analyst. Analyze the resume against the job description.
        Provide a detailed analysis ONLY in a valid JSON format. Do not provide any text or explanation before or after the JSON object.
        The JSON should have these exact keys: "overallScore", "scoreGoodness", "skillsMatchedCount", "skillsMissingCount", "relevantProjectsCount", "matchedSkills", "missingSkills", "experience", "education", "improvements".
        
        For "matchedSkills" and "missingSkills", create a list of JSON objects, each with a "skill" key.
        For "experience" and "education", create a JSON object with keys like "match" and "level".
        For "improvements", create a JSON object with a key "resume" which is a list of suggestion strings.

        Resume: {resume_text}
        Job Description: {jd_text}
        [/INST]
        """
        response = llm.invoke(prompt)
        
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_response_str = match.group(0)
            return json.loads(json_response_str)
        else:
            return {"error": "The AI model returned an invalid response. The free model may be temporarily overloaded. Please try again in a few moments."}

    except Exception as e:
        return {"error": f"An error occurred during AI analysis: {e}"}

