# from inputs import from_github
# import uuid
# from agent import get_crew
# from composio import Action
# from tools import create_pr

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from github import Github
import yaml
from crewai import Task, Crew, Agent
#from helpcode import gather_test_related_files
from helpcode.build_test_tree import build_test_tree
from helpcode.build_versioning_tree import build_versioning_tree
import shutil # to delete folders
from git import Repo  
from opentelemetry.trace import set_tracer_provider, NoOpTracerProvider


import sys
print(sys.path)

#github_repo_name = "ntua-el19871/sample_repo"
github_repo_name = "astropy/astropy"

def main() -> None:

    ############################### Load environment variables ########################################
    load_dotenv() if not os.getenv("OPENAI_API_KEY") or not os.getenv("GITHUB_TOKEN") else None
    openai_api_key = os.getenv("OPENAI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY is missing.")
    if not github_token:
        raise EnvironmentError("GITHUB_TOKEN is missing.")


    ############################### Initialize OpenAI model ###########################################
    ####################### now we have the client object which is our llm ############################
    set_tracer_provider(NoOpTracerProvider())   #gt rid of the warning
    llm = ChatOpenAI(
        api_key=openai_api_key,  # Ensure this environment variable is set
        model="gpt-3.5-turbo",
    )

    response = llm.invoke("What is the capital of France?")
    print(response)

    ############################### Initialize github ###########################################
    ####################### now we have the repo and issue objects ##############################
    github_client = Github(github_token)
    repo = github_client.get_repo(github_repo_name)
    repo_owner, repo_name = github_repo_name.split("/")
    issue_number = int(input("Enter the GitHub issue number to process: "))
    issue = repo.get_issue(number=issue_number)
  
    ############################### Clone the Repository ###########################################
    local_repo_path = f"./{repo_name}"  # Local directory to clone the repository
    repo_url = repo.clone_url
    # Clone the repository directly without wrapping in a function
    if os.path.exists(local_repo_path):
        print(f"Repository already cloned at {local_repo_path}")
    else:
        print(f"Cloning repository from {repo_url} to {local_repo_path}...")
        Repo.clone_from(repo_url, local_repo_path)
        print("Cloning completed successfully.")






















    # def guess_dep_and_version_commands(repo_path):
    #     """
    #     Inspect a local repo path for common dependency/versioning files 
    #     and guess which commands might be used for installing dependencies 
    #     and handling versioning.
    #     """
    #     # We’ll store findings here
    #     found_files = set()

    #     # Walk the repo to find key files
    #     for root, dirs, files in os.walk(repo_path):
    #         # Avoid hidden or irrelevant dirs (you can refine this)
    #         dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'build', 'dist')]
            
    #         for f in files:
    #             # Lowercase name for easy matching
    #             f_lower = f.lower()
    #             # Track the full path and name
    #             found_files.add(f_lower)

    #     commands = []

    #     # ---- DEPENDENCIES ----
    #     # Priority 1: environment.yml (Conda)
    #     if 'environment.yml' in found_files:
    #         commands.append("conda env create -f environment.yml")

    #     # Priority 2: Pipfile (Pipenv)
    #     if 'pipfile' in found_files:
    #         commands.append("pipenv install")

    #     # Priority 3: pyproject.toml
    #     # We can't be certain if it's Poetry or just PEP 517, 
    #     # but let's guess:
    #     if 'pyproject.toml' in found_files:
    #         # Could parse the file content to see if [tool.poetry] is present
    #         # For simplicity, let's guess both possibilities
    #         commands.append("poetry install  # if using Poetry")
    #         commands.append("pip install .   # if using PEP 517")

    #     # Priority 4: requirements.txt
    #     if 'requirements.txt' in found_files:
    #         commands.append("pip install -r requirements.txt")

    #     # Priority 5: setup.py (traditional)
    #     if 'setup.py' in found_files:
    #         commands.append("pip install .   # or python setup.py install")

    #     # If no recognized config, might guess a readme or fallback
    #     # e.g. commands.append("Check README.md or docs")

    #     # ---- VERSIONING ----
    #     # Bumpversion
    #     if '.bumpversion.cfg' in found_files:
    #         commands.append("bumpversion patch  # or minor/major if used")

    #     # Versioneer
    #     if 'versioneer.py' in found_files:
    #         commands.append("# versioneer is used. Possibly 'python setup.py version' or check docs.")
        
    #     # Summarize
    #     if not commands:
    #         commands_str = "No obvious dependency/versioning strategy detected."
    #     else:
    #         commands_str = "\n".join(commands)

    #     return commands_str


    # recommended_commands = guess_dep_and_version_commands(local_repo_path)
    # print("Potential dependency and versioning commands:\n")
    # print(recommended_commands)




































    ############################### Get the repository test structure #######################################




    versioning_tree = build_versioning_tree(local_repo_path)
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

    # inputs = {
    #     "planner": {"issue_title": issue.title, "issue_body": issue.body},
    #     "editor": {"issue_title": issue.title, "repo_name": repo_name},
    # }

    # crew_1.kickoff(inputs)

    # # Retrieve outputs
    # task_1_output = task_1.output


    # task_2_output = task_2.output

    # inputx = {
    #     "tester": {"repository structure": repo_structure_json}
    # }

    crew_2.kickoff(inputs={"test_tree": test_tree, "versioning_tree": versioning_tree})


    ############################### delete the cloned repo ###########################################
    # try:
    #     if os.path.exists(local_repo_path):
    #         print(f"Cleaning up cloned repository at {local_repo_path}...")
    #         shutil.rmtree(local_repo_path)
    #         print("Cleanup completed successfully.")
    # except Exception as e:
    #     print(f"Error during deleting the cloned repo: {e}")



    # """Run the agent."""
    # repo, issue = from_github()

    # owner, repo_name = repo.split("/")
    # crew, composio_toolset = get_crew(repo_path=f"/home/user/{repo_name}", workspace_id=None)
    # crew.kickoff(
    #     inputs={
    #         "repo": repo,
    #         "issue": issue,
    #     }
    # )
    # composio_toolset.execute_action(
    #     action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
    #     params={"path": f"/home/user/{repo_name}"},
    # )
    # response = composio_toolset.execute_action(
    #     action=Action.FILETOOL_GIT_PATCH,
    #     params={},
    # )
    # branch_name = "test-branch-" + str(uuid.uuid4())[:4]
    # git_commands = [
    #     f"checkout -b {branch_name}",
    #     "add -u",
    #     "config --global user.email 'random@gmail.com'",
    #     "config --global user.name 'random'",
    #     f"commit -m '{issue}'",
    #     f"push --set-upstream origin {branch_name}",
    # ]
    # for command in git_commands:
    #     composio_toolset.execute_action(
    #         action=Action.FILETOOL_GIT_CUSTOM,
    #         params={"cmd": command},
    #     )
    # composio_toolset.execute_action(
    #     action=create_pr,
    #     params={
    #         "owner": owner,
    #         "repo": repo_name,
    #         "head": branch_name,
    #         "base": "master",
    #         "title": "Composio generated PR",
    #     },
    # )  

    # data = response.get("data", {})
    # if data.get("error") and len(data["error"]) > 0:
    #     print("Error:", data["error"])
    # elif data.get("patch"):
    #     print("=== Generated Patch ===\n" + data["patch"])
    # else:
    #     print("No output available")


if __name__ == "__main__":
    main()
