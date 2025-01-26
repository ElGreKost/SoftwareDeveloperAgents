from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew
import os
from crewai import LLM
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_llm = LLM(
    model="gemini/gemini-1.5-pro-002",
    api_key=GEMINI_API_KEY,
    temperature=0,
)
from composio_crewai import ComposioToolSet, Action, App, WorkspaceType

composio_toolset = ComposioToolSet(
        workspace_config=WorkspaceType.Docker(),
)
tools = composio_toolset.get_tools(
    actions=['FILETOOL_GIT_CLONE'])

# Define agent
crewai_agent = Agent(
    role="Sample Agent",
    goal="Clone the repository https://github.com/ElGreKost/SoftwareDeveloperAgents using FILETOOL_GIT_CLONE.",
    backstory="I am a software developer and I work on software development projects.",
    verbose=True,
    tools=tools,
    # llm=ChatOpenAI(model_name="gpt-4")(
    #     "You are AI agent that is responsible for taking actions based on the tools you have"
    # )
    llm = gemini_llm,
)

task = Task(
    description="clone this repository  https://github.com/ElGreKost/SoftwareDeveloperAgents using FILETOOL_GIT_CLONE.",
    agent=crewai_agent,
    expected_output=""
)

my_crew = Crew(agents=[crewai_agent], tasks=[task], verbose=True)

result = my_crew.kickoff()
print(result)