import os
import requests
from pathlib import Path
import zipfile
import shutil
from datetime import datetime, timedelta

# def get_repo_and_issue(repo_name, issue_number):
#     """
#     Downloads a GitHub repository at the state when the specified issue was created
#     (or slightly earlier, to capture the buggy version) and saves it as 'repo'
#     (e.g., 'astropy'), without the commit SHA in the directory name.
    
#     Parameters:
#       repo_name (str): The GitHub repository name in the format "owner/repo".
#       issue_number (str or int): The issue number.
      
#     Returns:
#       tuple: (issue_title, issue_body, absolute_repo_path)
#     """
#     # Validate repository name format
#     if "/" not in repo_name:
#         raise ValueError("Invalid repository name format. Use 'owner/repo'.")
    
#     issue_number = str(issue_number).strip()
#     if not issue_number.isdigit():
#         raise ValueError("Invalid issue number. It must be a numeric value.")
    
#     github_token = os.getenv("GITHUB_ACCESS_TOKEN")
#     if not github_token:
#         raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set.")
    
#     headers = {"Authorization": f"token {github_token}"}
    
#     # Get issue details
#     issue_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}"
#     response = requests.get(issue_url, headers=headers)
#     if response.status_code != 200:
#         raise ValueError(f"Failed to fetch issue #{issue_number} from {repo_name}. HTTP Status: {response.status_code}")
    
#     issue_data = response.json()
#     issue_title = issue_data.get("title", "No title provided")
#     issue_body = issue_data.get("body", "No description provided")
#     issue_created_at = issue_data.get("created_at")
    
#     if not issue_created_at:
#         raise ValueError(f"Issue #{issue_number} does not have a creation date.")
    
#     # Convert the issue creation date to a datetime object
#     issue_created_at_dt = datetime.fromisoformat(issue_created_at.replace("Z", "+00:00"))
    
#     # Subtract a time delta to get an earlier commit (e.g., 5 minutes earlier)
#     adjusted_time = issue_created_at_dt - timedelta(minutes=5)
    
#     # Get repository commits and find the closest commit before the adjusted time
#     repo_owner, repo = repo_name.split("/")
#     commits_url = f"https://api.github.com/repos/{repo_owner}/{repo}/commits"
#     params = {"until": adjusted_time.isoformat()}
    
#     response = requests.get(commits_url, headers=headers, params=params)
#     if response.status_code != 200:
#         raise ValueError(f"Failed to fetch commits from {repo_name}. HTTP Status: {response.status_code}")
    
#     commits_data = response.json()
#     if not commits_data:
#         raise ValueError(f"No commits found in {repo_name} before the adjusted time.")
    
#     # Get the SHA of the most recent commit before the adjusted time
#     closest_commit_sha = commits_data[0]["sha"]
    
#     # Download the repository at the specific commit
#     zip_url = f"https://github.com/{repo_owner}/{repo}/archive/{closest_commit_sha}.zip"
#     zip_path = Path(f"{repo}.zip")
#     extract_dir = Path(f"./{repo}")  # Repository folder path without commit SHA

#     if not extract_dir.exists():
#         print(f"Downloading repository {repo_name} at commit {closest_commit_sha} (state when issue was found)...")
#         response = requests.get(zip_url, stream=True)
#         if response.status_code == 200:
#             with open(zip_path, "wb") as f:
#                 f.write(response.content)
#         else:
#             raise ValueError(f"Failed to download repository ZIP. HTTP Status: {response.status_code}")

#         with zipfile.ZipFile(zip_path, "r") as zip_ref:
#             zip_ref.extractall(".")
        
#         extracted_folder = next(
#             (folder for folder in Path(".").iterdir() if folder.is_dir() and folder.name.startswith(f"{repo}-")),
#             None
#         )
        
#         if extracted_folder and extracted_folder.exists():
#             shutil.move(str(extracted_folder), str(extract_dir))
#         else:
#             raise ValueError(f"Extracted folder for {repo} not found.")
#     else:
#         print(f"Repository {repo_name} already exists locally.")
    
#     if zip_path.exists():
#         zip_path.unlink()

#     absolute_path = str(extract_dir.resolve())
#     return issue_title, issue_body, absolute_path

def get_repo_and_issue(repo_name: str, issue_number: str, base_commit: str) -> tuple:
    """
    Downloads a GitHub repository at the specified commit (base_commit) and saves it as 'repo'
    (e.g., 'astropy'), without including the commit SHA in the directory name.
    
    Parameters:
      repo_name (str): The GitHub repository name in the format "owner/repo".
      issue_number (str or int): The issue number.
      base_commit (str): The commit SHA to use for downloading the repository.
      
    Returns:
      tuple: (issue_title, issue_body, absolute_repo_path)
    """
    # Validate repository name format
    if "/" not in repo_name:
        raise ValueError("Invalid repository name format. Use 'owner/repo'.")
    
    issue_number = str(issue_number).strip()
    if not issue_number.isdigit():
        raise ValueError("Invalid issue number. It must be a numeric value.")
    
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set.")
    
    headers = {"Authorization": f"token {github_token}"}
    
    # Get issue details from GitHub
    issue_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}"
    response = requests.get(issue_url, headers=headers)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch issue #{issue_number} from {repo_name}. HTTP Status: {response.status_code}")
    
    issue_data = response.json()
    issue_title = issue_data.get("title", "No title provided")
    issue_body = issue_data.get("body", "No description provided")
    
    # Use the provided base_commit directly
    closest_commit_sha = base_commit
    
    # Download the repository at the specified commit
    repo_owner, repo = repo_name.split("/")
    zip_url = f"https://github.com/{repo_owner}/{repo}/archive/{closest_commit_sha}.zip"
    zip_path = Path(f"{repo}.zip")
    extract_dir = Path(f"./{repo}")  # Repository folder path without commit SHA

    if not extract_dir.exists():
        print(f"Downloading repository {repo_name} at commit {closest_commit_sha}...")
        response = requests.get(zip_url, stream=True)
        if response.status_code == 200:
            with open(zip_path, "wb") as f:
                f.write(response.content)
        else:
            raise ValueError(f"Failed to download repository ZIP. HTTP Status: {response.status_code}")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(".")

        extracted_folder = next(
            (folder for folder in Path(".").iterdir() if folder.is_dir() and folder.name.startswith(f"{repo}-")),
            None
        )

        if extracted_folder and extracted_folder.exists():
            shutil.move(str(extracted_folder), str(extract_dir))
        else:
            raise ValueError(f"Extracted folder for {repo} not found.")
    else:
        print(f"Repository {repo_name} already exists locally.")

    if zip_path.exists():
        zip_path.unlink()

    absolute_path = str(extract_dir.resolve())
    return issue_title, issue_body, absolute_path