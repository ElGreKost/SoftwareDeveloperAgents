import os
from pathlib import Path
import uuid
from composio import Action
from tools import create_pr

def main() -> None:
    """Run the agent."""
    repo, issue = from_github()
    owner, repo_name = repo.split("/")
    crew, composio_toolset = get_crew(workspace_id=None)


    composio_tests_workdir = Path(Path.home(), "composio_tests")
    os.makedirs(composio_tests_workdir, exist_ok=True)

    composio_toolset.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": str(composio_tests_workdir)},
    )

    crew.kickoff(
        inputs={
            "repo": repo,
            "issue": issue,
        }
    )
    composio_toolset.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": str(Path(Path.home(), repo_name))},
    )
    response = composio_toolset.execute_action(
        action=Action.FILETOOL_GIT_PATCH,
        params={},
    )
    branch_name = "test-branch-" + str(uuid.uuid4())[:4]
    git_commands = [
        f"checkout -b {branch_name}",
        "add -u",
        "config --global user.email 'random@gmail.com'",
        "config --global user.name 'random'",
        f"commit -m '{issue}'",
        f"push --set-upstream origin {branch_name}",
    ]
    for command in git_commands:
        composio_toolset.execute_action(
            action=Action.FILETOOL_GIT_CUSTOM,
            params={"cmd": command},
        )
    composio_toolset.execute_action(
        action=create_pr,
        params={
            "owner": owner,
            "repo": repo_name,
            "head": branch_name,
            "base": "master",
            "title": "Composio generated PR",
        },
    )  

    data = response.get("data", {})
    if data.get("error") and len(data["error"]) > 0:
        print("Error:", data["error"])
    elif data.get("patch"):
        print("=== Generated Patch ===\n" + data["patch"])
    else:
        print("No output available")


if __name__ == "__main__":
    main()



