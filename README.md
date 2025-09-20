HireSight - AI-Powered Resume Relevance System
HireSight is a modern, full-stack web application designed to automate and streamline the resume screening process. It uses a Large Language Model (LLM) to analyze job descriptions and resumes, providing an instant relevance score and detailed feedback for both recruiters and job seekers.

<!-- It's highly recommended to replace this with a real screenshot of your app! -->

✨ Key Features
This application is composed of two main portals, combined into a single, elegant multi-page Streamlit app:

recruiter-admin-panel-icon.png Recruiter Admin Panel
Upload Job Descriptions: Easily upload new job postings in PDF or DOCX format.

Centralized Database: All job postings are saved to a central SQLite database.

View Analysis Results: (Future enhancement) A dashboard to view all submitted applications and their scores.

job-seeker-portal-icon.png Job Seeker Portal
User-Friendly Interface: A beautiful, modern UI built to match a professional Figma design.

Dynamic Job Listings: View a live list of all available jobs posted by recruiters.

Instant AI Analysis: Upload a resume for a specific job and receive an instant, detailed analysis.

In-Depth Feedback: The analysis includes an overall match score, a breakdown of matched and missing skills, and actionable suggestions for improvement.

🛠️ Tech Stack
Frontend: Streamlit for creating a beautiful, interactive multi-page web application.

AI Orchestration: LangChain for structuring prompts and interacting with the LLM.

Language Model: OpenAI GPT-3.5-turbo (or newer) for the core analysis.

File Processing: PyPDF2, python-docx, and pdfplumber for text extraction.

Database: SQLite for simple, file-based data storage.

Core Language: Python

🚀 Getting Started
Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

Prerequisites
Python 3.8+

An OpenAI API Key

Installation & Setup
Clone the Repository:

git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
cd your-repository-name

Create and Activate a Virtual Environment:

# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

Install Dependencies:
All the required packages are listed in requirements.txt.

pip install -r requirements.txt

Set Up Your OpenAI API Key:
The application needs your OpenAI API key to function. The best way to do this is by setting it as an environment variable.

On Windows (Command Prompt):

set OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"

On macOS/Linux:

export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"

Note: You will need to set this variable every time you open a new terminal. For deployment, you will set this as a "Secret" in Streamlit Community Cloud.

Usage
The application must be run in a specific order the first time to ensure the database is created correctly.

Run the App:
Start the Streamlit application from your main project directory.

streamlit run app.py

Add a Job (as a Recruiter):

A browser tab will open to the app's homepage.

In the sidebar on the left, navigate to the Recruiter Admin Panel.

Fill in the details for a new job posting and click "Process and Save JD". This will create and populate the results.db database file.

Analyze a Resume (as a Job Seeker):

In the sidebar, navigate to the Job Seeker Portal.

You will now see the job you just created.

Upload your resume for that job and click "Analyze with AI" to see the full, multi-tab analysis.