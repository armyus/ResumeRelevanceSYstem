import pdfplumber
import docx
import re
import os

def parse_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            # Simple removal of potential headers/footers (e.g., page numbers)
            text += re.sub(r'^\s*Page \d+\s*|\s*-\s*Page \d+\s*$', '', page_text, flags=re.MULTILINE)
    return text.strip()

def parse_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

def parse_resume(file_path):
    if file_path.lower().endswith('.pdf'):
        return parse_pdf(file_path)
    elif file_path.lower().endswith('.docx'):
        return parse_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Use PDF or DOCX.")

def test_parsing():
    import os
    folder_path = r"C:\Projects\ResumeRelevanceSystem\Resumes"  # Folder containing resumes
    try:
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.pdf', '.docx')):
                file_path = os.path.join(folder_path, filename)
                parsed_text = parse_resume(file_path)
                print(f"\nParsed Resume Text for {filename}:")
                print(parsed_text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_parsing()