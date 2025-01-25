import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from github import Github
from git import Repo
from langchain_openai import ChatOpenAI
from crewai import Agent, Crew, Task
import yaml

from helpcode.build_test_tree import build_test_tree
from helpcode.build_versioning_tree import build_versioning_tree_and_snippets
from helpcode.create_virtualenv_install_dependencies import create_virtualenv, install_dependencies

# Mapping of repository names to their respective test commands
REPO_TEST_COMMANDS = {
    "astropy/astropy": [
        ["python", "-m", "pytest"],
    ],
    "django/django": [
        ["python", "-m", "pip", "install", "-e", ".."],  # Install parent directory in editable mode
        ["python", "-m", "pip", "install", "-r", "requirements/py3.txt"],
        ["./runtests.py"],
    ],
    # Add more repositories and their commands here
}

# Example GitHub repository names:
# github_repo_name = "ntua-el19871/sample_repo"
github_repo_name = "astropy/astropy"
# github_repo_name = "django/django"

def main() -> None:
    ############################### Load environment variables ########################################
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("GITHUB_TOKEN"):
        load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY is missing.")
    if not github_token:
        raise EnvironmentError("GITHUB_TOKEN is missing.")

    ############################### Initialize OpenAI model ###########################################
    llm = ChatOpenAI(
        api_key=openai_api_key,  # Ensure this environment variable is set
        model="gpt-3.5-turbo",
    )

    response = llm.invoke("What is the capital of France?")
    print(f"OpenAI Response: {response}")

    ############################### Initialize GitHub ###########################################
    github_client = Github(github_token)
    repo = github_client.get_repo(github_repo_name)
    repo_owner, repo_name = github_repo_name.split("/")
    try:
        issue_number = int(input("Enter the GitHub issue number to process: "))
    except ValueError:
        print("Invalid input. Please enter a numeric issue number.")
        sys.exit(1)
    issue = repo.get_issue(number=issue_number)

    ############################### Clone the Repository ###########################################
    local_repo_path = Path(f"./{repo_name}")  # Local directory to clone the repository
    repo_url = repo.clone_url
    if local_repo_path.exists():
        print(f"Repository already cloned at {local_repo_path}")
    else:
        print(f"Cloning repository from {repo_url} to {local_repo_path}...")
        try:
            Repo.clone_from(repo_url, local_repo_path)
            print("Cloning completed successfully.")
        except Exception as e:
            print(f"Error cloning repository: {e}")
            sys.exit(1)

    ############################### Create Temporary Virtual Environment ###########################################
    with tempfile.TemporaryDirectory() as temp_venv_dir:
        print(f"Creating temporary virtual environment at {temp_venv_dir}...")
        try:
            # Create virtual environment
            subprocess.check_call([sys.executable, "-m", "venv", temp_venv_dir])
            print("Temporary virtual environment created.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1)

        # Define paths
        venv_python = Path(temp_venv_dir) / ("Scripts" if os.name == "nt" else "bin") / "python"
        if not venv_python.exists():
            print(f"Python executable not found in the virtual environment at {venv_python}")
            sys.exit(1)

        ############################### Install Dependencies with Extras ###########################################
        print("Installing dependencies from pyproject.toml with [test] extras...")
        try:
            # Upgrade pip in the temp venv
            subprocess.check_call([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
            
            # Navigate to the cloned repo
            repo_dir = local_repo_path.resolve()
            # Install the package in editable mode along with [test] extras
            subprocess.check_call([str(venv_python), "-m", "pip", "install", "-e", ".[test]"], cwd=str(repo_dir))
            print("Dependencies with [test] extras installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)

        ############################### Verify Pytest Installation ###########################################
        print("Verifying pytest installation...")
        try:
            subprocess.check_call([str(venv_python), "-m", "pytest", "--version"], cwd=str(repo_dir))
            print("Pytest is installed correctly.")
        except subprocess.CalledProcessError:
            print("Pytest is not installed in the virtual environment.")
            sys.exit(1)

        ############################### Run Repository-Specific Commands ###########################################
        print(f"Running test commands for repository: {github_repo_name}")
        commands = REPO_TEST_COMMANDS.get(github_repo_name)
        if not commands:
            print(f"No test commands defined for repository: {github_repo_name}")
            sys.exit(1)

        for idx, cmd in enumerate(commands, start=1):
            print(f"Executing command {idx}: {' '.join(cmd)}")
            try:
                # Determine the working directory
                if github_repo_name == "django/django" and cmd == ["./runtests.py"]:
                    # For django/django, ensure we're in the 'tests' directory before running runtests.py
                    test_dir = repo_dir / "tests"
                    if not test_dir.exists():
                        print(f"Tests directory does not exist at {test_dir}")
                        sys.exit(1)
                    subprocess.check_call(cmd, cwd=str(test_dir))
                else:
                    # For other commands, execute in the repository's root directory
                    subprocess.check_call(cmd, cwd=str(repo_dir))
                print(f"Command {idx} executed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error executing command {idx}: {' '.join(cmd)}")
                print(f"Command failed with exit code {e.returncode}")
                sys.exit(1)

        # Temporary virtual environment and all its contents will be deleted here
        print("Cleaning up temporary virtual environment...")

    ############################### Rollback is implicit by deleting the temp venv ###########################################
    print("Environment rolled back to the original state.")



    versioning_tree = build_versioning_tree_and_snippets(local_repo_path)
    print(versioning_tree)


    #sys.exit(0) 
    ############################### Get the repository test structure #######################################

    # print("Generating repository structure...")
    # repo_structure = get_repo_structure_as_text(local_repo_path)
    # print(repo_structure)
    test_tree = build_test_tree(local_repo_path)
        
    ############################### Initialize the agents #######################################
    ####################### now we have the planner and editor ##################################  

    with open("agents/planner.yaml", 'r') as file:
        config = yaml.safe_load(file)
    planner = Agent(llm=llm, **config)

    with open("agents/editor.yaml", 'r') as file:
        config = yaml.safe_load(file)
    editor = Agent(llm=llm, **config)

    with open("agents/tester.yaml", 'r') as file:
        config = yaml.safe_load(file)
    tester = Agent(llm=llm, **config)

    with open("agents/versioner.yaml", 'r') as file:
        config = yaml.safe_load(file)
    versioner = Agent(llm=llm, **config)


    ############################### Initialize the tasks #######################################
    ############################ now we have the task objects ##################################
    with open("tasks/task_1.yaml", 'r') as file:
        config = yaml.safe_load(file)
   
    config['description'] = config['description'].format(issue=issue.body, repo = repo_name)    #Replace the placeholder with the actual issue body
    task_1 = Task(agent = planner, **config)

    with open("tasks/task_2.yaml", 'r') as file:
        config = yaml.safe_load(file)
   
    config['description'] = config['description'].format(issue=issue.body, repo = repo_name)    #Replace the placeholder with the actual issue body
    task_2 = Task(agent = planner, **config)

    with open("tasks/task_3.yaml", 'r') as file:
        config = yaml.safe_load(file)
   
    task_3 = Task(agent = tester, **config)

    with open("tasks/task_4.yaml", 'r') as file:
        config = yaml.safe_load(file)
   
    task_4 = Task(agent = versioner, **config)


    ############################### Initialize the Crew ########################################
    crew_1 = Crew(
        agents=[planner, editor],  # Add all agents involved
        tasks=[task_1, task_2],    # Add all tasks to be executed
        process="sequential",      # Define the execution process
        verbose=True,              # Set verbosity for debugging
        cache=False,               # Optional: Enable/disable caching
        memory=True                # Enable memory for shared context
    )
    crew_2 = Crew(
        agents=[versioner,tester],  # Add all agents involved
        tasks=[task_4,task_3],    # Add all tasks to be executed
        process="sequential",      # Define the execution process
        verbose=True,              # Set verbosity for debugging
        cache=False,               # Optional: Enable/disable caching
        memory=True                # Enable memory for shared context
    )


    ############################### Kickoff the Crew ###########################################


    crew_2.kickoff(inputs={"test_tree": test_tree, "versioning_tree": versioning_tree})


    ############################### delete the cloned repo ###########################################
    # try:
    #     if os.path.exists(local_repo_path):
    #         print(f"Cleaning up cloned repository at {local_repo_path}...")
    #         shutil.rmtree(local_repo_path)
    #         print("Cleanup completed successfully.")
    # except Exception as e:
    #     print(f"Error during deleting the cloned repo: {e}")



if __name__ == "__main__":
    main()
