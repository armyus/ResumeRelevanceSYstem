import pdfplumber
import docx
import spacy
import nltk
from langchain import __version__ as lc_version
from sentence_transformers import SentenceTransformer

print("All imports successful!")
print(f"LangChain version: {lc_version}")
model = SentenceTransformer('all-MiniLM-L6-v2')  # Test embedding model
print("Embedding model loaded.")