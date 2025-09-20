import os
import re
import pdfplumber
from docx import Document
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer, util
import json  # For saving results

def extract_text_from_pdf(file_path):
    """Extract raw text from a PDF file."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    """Extract raw text from a DOCX file."""
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_resume_text(resume_path):
    """Handle resume extraction based on file type and normalize."""
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume file not found: {resume_path}")
    
    ext = os.path.splitext(resume_path)[1].lower()
    if ext == '.pdf':
        text = extract_text_from_pdf(resume_path)
    elif ext == '.docx':
        text = extract_text_from_docx(resume_path)
    else:
        raise ValueError("Unsupported resume format. Use PDF or DOCX.")
    
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_jd_text(jd_path):
    """Extract text from JD (supports PDF or DOCX)."""
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"JD file not found: {jd_path}")
    
    ext = os.path.splitext(jd_path)[1].lower()
    if ext in ['.pdf', '.docx']:
        if ext == '.pdf':
            text = extract_text_from_pdf(jd_path)
        else:  # .docx
            text = extract_text_from_docx(jd_path)
    else:
        raise ValueError("Unsupported JD format. Use PDF or DOCX.")
    
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_resume_sections(resume_text):
    """Refined parsing: Extract sections like Skills, Experience, Education."""
    sections = {
        'skills': [],
        'experience': [],
        'education': [],
        'objective': ''
    }
    
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
        sections['experience'] = [exp.strip() for exp in re.split(r'\n', exp_text) if re.search(r'\w+\s+\w+', exp) and len(exp.split()) > 2][:2]  # More specific
    
    edu_match = re.search(r'Education\s*:?\s*(.*?)(?=\s*(Projects|Certifications|\Z))', resume_text, re.IGNORECASE | re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1).strip()
        sections['education'] = [edu.strip() for edu in re.split(r'\n', edu_text) if re.search(r'[A-Za-z]+\s+[A-Za-z]+', edu)][:2]
    
    return sections

def parse_jd_sections(jd_text):
    """Refined parsing: Extract role title, must-have skills, etc."""
    sections = {
        'role_title': '',
        'must_have_skills': [],
        'description': ''
    }
    
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
    """Calculate hard match score based on exact and fuzzy matching."""
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
    """Calculate soft match score using sentence embeddings."""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    jd_embedding = model.encode(jd_text, convert_to_tensor=True)
    cosine_score = util.pytorch_cos_sim(resume_embedding, jd_embedding).item()
    soft_score = (cosine_score + 1) / 2 * 50  # Normalize to 0-50
    return min(soft_score, 50)

def save_results(resume_path, jd_path, score, matched_pairs):
    """Save analysis results to a JSON file."""
    result = {
        'resume_file': os.path.basename(resume_path),
        'jd_file': os.path.basename(jd_path),
        'hard_score': score[0],
        'soft_score': soft_match_score(extract_resume_text(resume_path), extract_jd_text(jd_path)),
        'total_score': score[0] + soft_match_score(extract_resume_text(resume_path), extract_jd_text(jd_path)),
        'matched_skills': matched_pairs
    }
    with open(os.path.join('output', 'relevance_result.json'), 'w') as f:
        json.dump(result, f, indent=4)
    print("Results saved to 'output/relevance_result.json'")

def main():
    data_dir = 'data'
    if not os.path.exists(data_dir):
        print(f"Error: 'data' folder not found. Please create it and add sample files.")
        return
    
    resume_files = [f for f in os.listdir(data_dir) if f.lower().endswith(('.pdf', '.docx')) and 'resume' in f.lower()]
    jd_files = [f for f in os.listdir(data_dir) if f.lower().endswith(('.pdf', '.docx')) and 'jd' in f.lower()]
    
    if not resume_files or not jd_files:
        print("Error: No resume or JD files found in 'data' folder. Add sample files (PDFs with 'resume' or 'jd' in name).")
        return
    
    resume_path = os.path.join(data_dir, resume_files[0])
    jd_path = os.path.join(data_dir, jd_files[0])
    
    try:
        resume_text = extract_resume_text(resume_path)
        jd_text = extract_jd_text(jd_path)
        
        resume_sections = parse_resume_sections(resume_text)
        jd_sections = parse_jd_sections(jd_text)
        
        print("Parsed Resume Sections:")
        print(f"Objective: {resume_sections['objective'][:100]}...")
        print(f"Skills: {', '.join(resume_sections['skills'][:5])}")  # First 5 skills
        print(f"Experience (first 2): {resume_sections['experience'][:2]}")
        print(f"Education (first 2): {resume_sections['education'][:2]}\n")
        
        print("Parsed JD Sections:")
        print(f"Role Title: {jd_sections['role_title']}")
        print(f"Must-Have Skills: {', '.join(jd_sections['must_have_skills'][:5])}")  # First 5
        print(f"Description (first 200 chars): {jd_sections['description']}\n")
        
        # Hard Matching
        hard_score, matched_pairs = hard_match_score(resume_sections['skills'], jd_sections['must_have_skills'])
        print(f"Hard Match Score: {hard_score}/50")
        if matched_pairs:
            print(f"Matched Skills: {matched_pairs}")
        
        # Soft Matching
        soft_score = soft_match_score(resume_text, jd_text)
        print(f"Soft Match Score: {soft_score}/50")
        
        # Total Relevance Score
        total_score = hard_score + soft_score
        print(f"Total Relevance Score: {total_score}/100")
        
        # Save Results
        if not os.path.exists('output'):
            os.makedirs('output')
        save_results(resume_path, jd_path, (hard_score, soft_score), matched_pairs)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()