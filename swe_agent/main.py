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


repo_name = "ntua-el19871/sample_repo"

def main() -> None:

    ############################### Load environment variables ########################################
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = "ntua-el19871/sample_repo"  # Do not change


    ############################### Initialize OpenAI model ###########################################
    ####################### now we have the client object which is our llm ############################
    client = ChatOpenAI(
        api_key=openai_api_key,  # Ensure this environment variable is set
        model="gpt-3.5-turbo",
    )

    ############################### Initialize github ###########################################
    ####################### now we have the repo and issue objects ##############################
    github_client = Github(github_token)
    repo = github_client.get_repo(repo_name)
    issue_number = int(input("Enter the GitHub issue number to process: "))
    issue = repo.get_issue(number=issue_number)


    ############################### Initialize the agents #######################################
    ####################### now we have the planner and editor ##################################  

    with open("agents/planner.yaml", 'r') as file:
        config = yaml.safe_load(file)
    planner = Agent(llm=client, **config)

    with open("agents/editor.yaml", 'r') as file:
        config = yaml.safe_load(file)
    editor = Agent(llm=client, **config)


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


    ############################### Initialize the Crew ########################################
    crew = Crew(
        agents=[planner, editor],  # Add all agents involved
        tasks=[task_1, task_2],    # Add all tasks to be executed
        process="sequential",      # Define the execution process
        verbose=True,              # Set verbosity for debugging
        cache=False,               # Optional: Enable/disable caching
        memory=True                # Enable memory for shared context
    )

    ############################### Kickoff the Crew ###########################################

    inputs = {
        "planner": {"issue_title": issue.title, "issue_body": issue.body},
        "editor": {"issue_title": issue.title, "repo_name": repo_name},
    }

    crew.kickoff(inputs)

    # Retrieve outputs
    task_1_output = task_1.output


    task_2_output = task_2.output



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
