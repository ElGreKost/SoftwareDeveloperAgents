"""CrewAI SWE Agent"""

import os
from enum import Enum
from crewai import LLM
import dotenv
import typing as t
from crewai import Agent, Crew, Process, Task
from crewai import LLM
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash-exp",
    api_key=GEMINI_API_KEY,
    temperature=0,
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
