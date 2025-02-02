"""CrewAI SWE Agent"""

import os
from enum import Enum
import dotenv
import typing as t
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import agent, task, CrewBase, crew
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash-exp",
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
from langchain_aws import ChatBedrock
from prompts import PLANNER_BACKSTORY, PLANNER_DESCRIPTION, PLANNER_EXPECTED_OUTPUT, PLANNER_GOAL, PLANNER_ROLE
from prompts import EDITOR_BACKSTORY, EDITOR_DESCRIPTION, EDITOR_EXPECTED_OUTPUT, EDITOR_GOAL, EDITOR_ROLE

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

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            llm=gemini_llm,
        )
    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm=gemini_llm,
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
    def crew(self) -> Crew:
        return Crew(
            agents=[self.planner(), self.editor()],
            tasks=[self.planner_task(), self.editor_task()],
            process=Process.sequential,
            verbose=True
        )

def get_crew(workspace_id: str):

    composio_toolset = ComposioToolSet(
        # workspace_config=WorkspaceType.Docker(),
    )
    if workspace_id:
        composio_toolset.set_workspace_id(workspace_id)

    # Get required tools
    tools = [
        *composio_toolset.get_tools(
            apps=[
                App.FILETOOL,
                App.SHELLTOOL,
                # App.CODE_ANALYSIS_TOOL,
            ]
        ),
    ]

    # Define agent
    # Define agent
    planner = Agent(
        role=PLANNER_ROLE,
        goal=PLANNER_GOAL,
        backstory=PLANNER_BACKSTORY,
        llm=gemini_llm,
        tools=tools,
        verbose=True,
    )

    editor = Agent(
        role=EDITOR_ROLE,
        goal=EDITOR_GOAL,
        backstory=EDITOR_BACKSTORY,
        llm=gemini_llm,
        tools=tools,
        verbose=True,
    )

    planner_task = Task(
        description=PLANNER_DESCRIPTION,
        expected_output=PLANNER_EXPECTED_OUTPUT,
        agent=planner,
    )

    editor_task = Task(
        description=EDITOR_DESCRIPTION,
        expected_output=EDITOR_EXPECTED_OUTPUT,
        agent=editor,
    )

    crew = Crew(
        agents=[planner, editor],
        tasks=[planner_task, editor_task],
        process=Process.sequential,
        verbose=True,
        cache=False,
        memory=True,
    )
    return crew, composio_toolset


if __name__ == '__main__':
    crew = ProblemSolversCrew().crew()
    crew_output = crew.kickoff()
    print(crew_output)