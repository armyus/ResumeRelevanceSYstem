import os
import re
import pdfplumber
from docx import Document
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer, util
import sqlite3
import json

# Model for soft matching (load once)
MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported format. Use PDF or DOCX.")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_resume_sections(resume_text):
    sections = {'skills': [], 'experience': [], 'education': [], 'objective': ''}
    # [Same as before - copy the parse_resume_sections from main.py]
    obj_match = re.search(r'Objective\s*:?\s*(.*?)(?=\s*(Skills|Experience|Education|\Z))', resume_text, re.IGNORECASE | re.DOTALL)
    if obj_match:
        sections['objective'] = obj_match.group(1).strip()
    
    skills_match = re.search(r'Skills\s*:?\s*(.*?)(?=\s*(Experience|Education|\Z))', resume_text, re.IGNORECASE | re.DOTALL)
    if skills_match:
        skills_text = re.sub(r'[\w\s&]+(?=:)', '', skills_match.group(1)).strip()
        sections['skills'] = [skill.strip() for skill in re.split(r',|\n', skills_text) if skill.strip() and any(c.isalpha() for c in skill)][:10]
    else:
        tech_skills = re.findall(r'(Python|SQL|Matplotlib|Seaborn|Power BI|Pandas|NumPy|Scikit-learn|BeautifulSoup)', resume_text, re.IGNORECASE)
        sections['skills'] = list(dict.fromkeys(tech_skills))
    
    exp_match = re.search(r'Experience\s*:?\s*(.*?)(?=\s*(Education|\Z))', resume_text, re.IGNORECASE | re.DOTALL)
    if exp_match:
        exp_text = exp_match.group(1).strip()
        sections['experience'] = [exp.strip() for exp in re.split(r'\n', exp_text) if re.search(r'\w+\s+\w+', exp) and len(exp.split()) > 2][:2]
    
    edu_match = re.search(r'Education\s*:?\s*(.*?)(?=\s*(Projects|Certifications|\Z))', resume_text, re.IGNORECASE | re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1).strip()
        sections['education'] = [edu.strip() for edu in re.split(r'\n', edu_text) if re.search(r'[A-Za-z]+\s+[A-Za-z]+', edu)][:2]
    
    return sections

def parse_jd_sections(jd_text):
    sections = {'role_title': '', 'must_have_skills': [], 'description': ''}
    # [Same as before - copy parse_jd_sections from main.py]
    title_match = re.search(r'^(.+?)(?=\n)|Job\s+Title\s*:\s*(.+?)(?=\n)', jd_text, re.IGNORECASE)
    if title_match:
        sections['role_title'] = title_match.group(1) if title_match.group(1) else title_match.group(2)
        sections['role_title'] = sections['role_title'].strip() if sections['role_title'] else ''
    else:
        role_match = re.search(r'(?:Role|Position)\s*:\s*(.+?)(?=\n)', jd_text, re.IGNORECASE)
        sections['role_title'] = role_match.group(1).strip() if role_match else ''
    
    skills_match = re.search(r'(?:Skills\s+(?:Required|Must-have)|Qualifications):\s*(.*?)(?=\s*(Experience|\Z))', jd_text, re.IGNORECASE | re.DOTALL)
    if skills_match:
        skills_text = skills_match.group(1).strip()
        sections['must_have_skills'] = [skill.strip() for skill in re.split(r',|\n', skills_text) if skill.strip() and not skill.isspace()]
    else:
        tech_skills = re.findall(r'(Python|R|Excel|Pandas|Mechanical|Manufacturing)', jd_text, re.IGNORECASE)
        sections['must_have_skills'] = list(dict.fromkeys(tech_skills))
    
    sections['description'] = jd_text[:200].strip()
    return sections

def hard_match_score(resume_skills, jd_skills):
    if not jd_skills or not resume_skills:
        return 0, []
    matches = 0
    matched_pairs = []
    total_jd_skills = len(jd_skills)
    for jd_skill in jd_skills:
        for resume_skill in resume_skills:
            if jd_skill.lower() in resume_skill.lower() or fuzz.partial_ratio(jd_skill.lower(), resume_skill.lower()) > 80:
                matches += 1
                matched_pairs.append((jd_skill, resume_skill))
                break
    score = (matches / total_jd_skills) * 50
    return min(score, 50), matched_pairs

def soft_match_score(resume_text, jd_text):
    resume_embedding = MODEL.encode(resume_text, convert_to_tensor=True)
    jd_embedding = MODEL.encode(jd_text, convert_to_tensor=True)
    cosine_score = util.pytorch_cos_sim(resume_embedding, jd_embedding).item()
    return min(((cosine_score + 1) / 2 * 50), 50)

def analyze_resume(resume_path, jd_text, jd_sections):
    resume_text = extract_text(resume_path)
    resume_sections = parse_resume_sections(resume_text)
    hard_score, matched_pairs = hard_match_score(resume_sections['skills'], jd_sections['must_have_skills'])
    soft_score = soft_match_score(resume_text, jd_text)
    total_score = hard_score + soft_score

    # Verdict
    if total_score >= 80:
        verdict = "High"
    elif total_score >= 50:
        verdict = "Medium"
    else:
        verdict = "Low"

    # Missing skills
    jd_skills = set(s.lower() for s in jd_sections['must_have_skills'])
    resume_skills_lower = set(s.lower() for s in resume_sections['skills'])
    missing_skills = jd_skills - resume_skills_lower

    # Suggestions
    suggestions = f"To improve, focus on {', '.join(missing_skills)} if relevant to {jd_sections['role_title'] or 'the role'}."

    return {
        'resume_file': os.path.basename(resume_path),
        'total_score': total_score,
        'verdict': verdict,
        'matched_skills': matched_pairs,
        'missing_skills': list(missing_skills),
        'suggestions': suggestions,
        'objective': resume_sections['objective'][:100] + '...'
    }

def init_db():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations
                 (id INTEGER PRIMARY KEY, jd_file TEXT, resume_file TEXT, score REAL, verdict TEXT, matched_skills TEXT, missing_skills TEXT, suggestions TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(jd_file, results):
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    for result in results:
        c.execute("INSERT INTO evaluations (jd_file, resume_file, score, verdict, matched_skills, missing_skills, suggestions) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (jd_file, result['resume_file'], result['total_score'], result['verdict'], json.dumps(result['matched_skills']), json.dumps(result['missing_skills']), result['suggestions']))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DB initialized.")