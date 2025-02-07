"""CrewAI SWE Agent"""

from pathlib import Path
import os
from enum import Enum
import dotenv
import typing as t
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import agent, task, CrewBase, crew

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash-001",
    api_key=GEMINI_API_KEY,
    temperature=0.2,
)
# to get the api base link, you have to activate the inference endpoint from
# https://endpoints.huggingface.co/kkakkavas/endpoints/swe-llama-7b-ugn
swe_llm = LLM(
    model="huggingface/princeton-nlp/SWE-Llama-7b",
    max_tokens=1000,
    base_url="https://a2w1zm7lm6u7def9.us-east-1.aws.endpoints.huggingface.cloud",
)
from langchain_openai import ChatOpenAI

from composio_crewai import Action, App, ComposioToolSet, WorkspaceType

# Load environment variables from .env
dotenv.load_dotenv()


class Model(str, Enum):
    OPENAI = "openai"


model = Model.OPENAI

# Initialize tool.
if model == Model.OPENAI:
    client = ChatOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],  # type: ignore
        model="gpt-3.5-turbo",
    )
else:
    raise ValueError(f"Invalid model: {model}")


@CrewBase
class ProblemSolversCrew:
    agents_config: str | dict = "config/agents.yaml"
    tasks_config: str | dict = "config/tasks.yaml"

    toolset = ComposioToolSet(api_key="jhelsrsn9a8shezjwi0ssc")
    projects_root = Path(Path.home() / "repos")
    os.makedirs(projects_root, exist_ok=True)
    toolset.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": str(projects_root)},
    )
    tools = [*toolset.get_tools(apps=[App.FILETOOL, App.SHELLTOOL])]

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            llm=gemini_llm,
            tools=self.tools,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm=gemini_llm,
            tools=self.tools,
        )

    @task
    def planner_task(self) -> Task:
        return Task(
            config=self.tasks_config["planner_task"],
        )

    @task
    def editor_task(self) -> Task:
        return Task(
            config=self.tasks_config["editor_task"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.planner(), self.editor()],
            tasks=[self.planner_task(), self.editor_task()],
            process=Process.sequential,
            verbose=True,
            # planning=True,
        )

if __name__ == '__main__':
    import re
    from pathlib import Path
    from datasets import load_dataset
    swe_bench_test_dataset = load_dataset("princeton-nlp/SWE-bench", split="test")

    # from inputs import from_github; repo, issue = from_github() # for cli tests
    def extract_owner_repo_issue_num(instance_id):
        pattern = r'^(?P<owner_repo>.+)-(?P<issue_num>[^-]+)$'
        match = re.match(pattern, instance_id)
        if not match:
            raise ValueError("Invalid instance_id format")

        owner__repo = match.group("owner_repo")
        issue_num = match.group("issue_num")

        return owner__repo.split("__")[0], owner__repo.split("__")[1], issue_num
    for issue_data in swe_bench_test_dataset:
        import re
        gold_file_path = re.findall(r"(?<=diff --git a)\S+", issue_data["patch"])[0]
        hints_text = issue_data["hints_text"]
        # print(extract_owner_repo_issue_num(issue_data["instance_id"]), issue_data["base_commit"], gold_file_path, issue_data["hints_text"])
        issue = issue_data["problem_statement"]
        owner, repo, issue_num = extract_owner_repo_issue_num(issue_data["instance_id"])
        commit_hash = issue_data["base_commit"]
        # if repo == 'django' and issue_num == 109: # django-10914, django-12708, django-14382, django-13230
        if repo == "requests" and issue_num == "863":
            break
    print(issue_data["instance_id"])
    # owner, repo, issue_num = "ElGreKost", "SoftwareDeveloperAgents", "1"
    composio_tool_set = ComposioToolSet()

    import subprocess
    faulty_repos_dir = Path(Path.home(), "repos")
    faulty_repos_dir.mkdir(exist_ok=True, parents=True)

    repo_url = f"https://github.com/{owner}/{repo}.git"
    clone_command = ["git", "clone", repo_url]
    print(f"Running {' '.join(clone_command)}")
    subprocess.run(clone_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=faulty_repos_dir)

    repo_path = Path(faulty_repos_dir, Path(repo_url).stem).absolute()
    checkout_command = ["git", "checkout", commit_hash]
    print(f"Running  {' '.join(checkout_command)} and moving to error checkpoint")
    subprocess.run(checkout_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                   cwd=repo_path)

    print(f"changing composio working directory to {repo_path}")
    composio_tool_set.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": str(repo_path)},
    )

    crew = ProblemSolversCrew().crew()
    crew_output = crew.kickoff(inputs=dict(
        repo=str(repo_path),
        repo_name=repo,
        repo_parent=str(repo_path.parent),
        issue=issue,
        gold_file_path=str(repo_path) + str(gold_file_path)
    ))

    print(crew_output.raw)


