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
    model="gemini/gemini-1.5-flash-8b",
    api_key=GEMINI_API_KEY,
    temperature=0,
)
# to get the api base link, you have to activate the inference endpoint from
# https://endpoints.huggingface.co/kkakkavas/endpoints/swe-llama-7b-ugn
swe_llm = LLM(
    model="huggingface/princeton-nlp/SWE-Llama-7b",
    max_tokens=100,
    api_base="https://a2w1zm7lm6u7def9.us-east-1.aws.endpoints.huggingface.cloud",
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
            verbose=True
        )

if __name__ == '__main__':
    from pathlib import Path
    from datasets import load_dataset
    swe_bench_test_dataset = load_dataset("princeton-nlp/SWE-bench", split="test")

    # from inputs import from_github; repo, issue = from_github() # for cli tests
    def extract_owner_repo_issue_num(instance_id):
        owner__repo, issue_num = instance_id.split("-")
        return owner__repo.split("__")[0], owner__repo.split("__")[1], issue_num
    for row in swe_bench_test_dataset:
        print(extract_owner_repo_issue_num(row["instance_id"]), row["base_commit"])
        owner, repo, issue_num = extract_owner_repo_issue_num(row["instance_id"])
        break
    # owner, repo, issue_num = "ElGreKost", "SoftwareDeveloperAgents", "1"
    composio_tool_set = ComposioToolSet()
    print("getting issue")
    issue = composio_tool_set.execute_action(
        action=Action.GITHUB_GET_AN_ISSUE,
        params=dict(owner=owner, repo=repo, issue_number=int(issue_num)),
    ).get("data", {}).get("body", None)

    faulty_repos_dir = Path(Path.home(), "faulty_repos")
    os.makedirs(faulty_repos_dir, exist_ok=True)

    print("changing dir")
    composio_tool_set.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": str(faulty_repos_dir)},
    )

    print("cloning")
    # clone the repo in the faulty_repos_dir
    composio_tool_set.execute_action(
        action=Action.FILETOOL_GIT_CLONE,
        params={"repo_name": f"{owner}/{repo}"},
    )


    print("changing dir")
    composio_tool_set.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": str(faulty_repos_dir / repo)},
    )

    def get_commit_hash(owner, repo, issue_num):
        return swe_bench_test_dataset.filter(lambda x: x['instance_id'] == f"{owner}__{repo}-{issue_num}")["base_commit"][0]


    print("checkout")
    # get the error commit as the current codebase
    composio_tool_set.execute_action(
        action=Action.FILETOOL_GIT_CUSTOM,
        params={"cmd": f"checkout {get_commit_hash(owner, repo, issue_num)}^"},
    )
    # crew = ProblemSolversCrew().crew()
    # crew_output = crew.kickoff(inputs=dict(repo=owner+"/"+repo, issue=issue))
    # print(crew_output)
