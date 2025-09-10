import os
import requests
from flask import Flask, request, render_template, send_file

app = Flask(__name__)

GITHUB_PAT = "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"
GEMINI_API_KEY = "AIzaSyBoRJ7QhbruG_Fcfe1R6aSdE9yMylrc9OI"

GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

@app.route("/")
def index():
    
    return render_template("index.html")

@app.route("/generate_readme", methods=["POST"])
def generate_readme():
    
    repo_url = request.form.get("repo_url")

    if not repo_url:
        return render_template("index.html", message="Repository URL is required.", status="error")

    
    try:
       
        parts = repo_url.strip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
    except IndexError:
        return render_template("index.html", message="Invalid GitHub URL format.", status="error")

   
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_PAT:
        headers["Authorization"] = f"token {GITHUB_PAT}"

    try:
        github_response = requests.get(GITHUB_API_URL.format(owner=owner, repo=repo), headers=headers)
        github_response.raise_for_status()
        repo_data = github_response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching GitHub repository data: {e}"
        if github_response.status_code == 404:
            error_message = "Repository not found. Please check the URL."
        elif github_response.status_code == 401:
            error_message = "Unauthorized. Please provide a valid Personal Access Token (PAT) for this private repository."
        return render_template("index.html", message=error_message, status="error")

   
    name = repo_data.get("name", "")
    description = repo_data.get("description", "") or "A public or private project."
    language = repo_data.get("language", "Unknown")
    stargazers_count = repo_data.get("stargazers_count", 0)
    forks_count = repo_data.get("forks_count", 0)
    topics = ", ".join(repo_data.get("topics", [])) if repo_data.get("topics") else "None"
    
   
    file_list_response = requests.get(f"https://api.github.com/repos/{owner}/{repo}/contents", headers=headers)
    file_list = [item['name'] for item in file_list_response.json() if isinstance(item, dict) and 'name' in item]
    file_list_str = ", ".join(file_list)

   
    prompt = f"""
    You are a professional technical writer specializing in creating comprehensive, well-structured, and professional README.md files for software projects.
    Your task is to generate a detailed README.md file for a GitHub repository based on the provided metadata.

    ---
    Metadata:
    - Repository Name: {name}
    - Owner: {owner}
    - Description: {description}
    - Primary Language: {language}
    - Stars: {stargazers_count}
    - Forks: {forks_count}
    - Topics: {topics}
    - Top-level files: {file_list_str}

    ---
    Instructions:
    1.  Start with a prominent title and a brief introduction.
    2.  Include a "Features" section with a bulleted list based on the project's description and file list.
    3.  Add a "Getting Started" section with simple, step-by-step instructions for installation and setup. Infer dependencies from the file list (e.g., `requirements.txt` suggests Python, `package.json` suggests Node.js).
    4.  If applicable, include a "Usage" section with clear, concise code examples.
    5.  Create a "Contributing" section with general guidelines for potential contributors.
    6.  The output must be a single, complete markdown file, ready to be saved as `README.md`. Do not include any extra text before or after the markdown content.
    7.  Do not include placeholders like `[Your Project Name]`. Use the actual data provided.
    8.  Use appropriate markdown headings (e.g., #, ##, ###) and formatting (bolding, italics, code blocks).
    """

    try:
        gemini_response = requests.post(
            GEMINI_API_URL.format(api_key=GEMINI_API_KEY),
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
        )
        gemini_response.raise_for_status()
        readme_content = gemini_response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.RequestException as e:
        return render_template("index.html", message=f"Error communicating with Gemini API: {e}", status="error")
    
   
    output_dir = "generated_readmes"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{repo.lower()}-readme.md"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except IOError as e:
        return render_template("index.html", message=f"Error saving file: {e}", status="error")

if __name__ == "__main__":
    app.run(debug=True)
