import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from github import Github
from git import Repo
import yaml
from langchain_openai import ChatOpenAI

from crewai import Agent, Crew, Task




from helpcode.build_test_tree import build_test_tree
from helpcode.build_versioning_tree import build_versioning_tree_and_snippets
from helpcode.create_virtualenv_install_dependencies import create_virtualenv, install_dependencies


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
    ####################### now we have the client object which is our llm ############################

    llm = ChatOpenAI(
        api_key=openai_api_key,  # Ensure this environment variable is set
        model="gpt-3.5-turbo",
    )

    response = llm.invoke("What is the capital of France?")
    print(f"OpenAI Response: {response}")

    ############################### Initialize GitHub ###########################################
    ####################### now we have the repo and issue objects ##############################
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
    # Clone the repository directly without wrapping in a function
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

    # ############################### Create and Activate Virtual Environment ###########################################
    # venv_name = "repo_venv"
    # venv_path = local_repo_path / venv_name

    # if venv_path.exists():
    #     print(f"Virtual environment '{venv_name}' already exists at {venv_path}")
    # else:
    #     print(f"Creating virtual environment '{venv_name}'...")
    #     create_virtualenv(venv_path)

    # ############################### Install Dependencies ###########################################
    # print("Installing dependencies from pyproject.toml...")
    # install_dependencies(venv_path, local_repo_path)

    ############################### Additional Steps ###########################################
    # Example: Running a script within the new virtual environment
    # script_path = local_repo_path / 'your_script.py'
    # if script_path.exists():
    #     subprocess.check_call([str(venv_path / 'bin' / 'python'), str(script_path)])
    # else:
    #     print(f"Script {script_path} does not exist.")

    #print("Setup complete.")



    #sys.exit(0)


    ############################### Get the repository test structure #######################################



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
