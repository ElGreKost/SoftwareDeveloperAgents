from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from composio_crewai import ComposioToolSet, Action, App
composio_toolset = ComposioToolSet()
tools = composio_toolset.get_tools(actions=['FILETOOL_GIT_CLONE', 'FILETOOL_LIST_FILES'])

# Define agent
crewai_agent = Agent(
    role="Sample Agent",
    goal="""You are an AI agent that is responsible for taking actions based on the tools you have""",
    backstory=(
        "You are AI agent that is responsible for taking actions based on the tools you have"
    ),
    verbose=True,
    tools=tools,
    llm=ChatOpenAI(model_name="gpt-3.5-turbo"),
)
task = Task(
    description="first use list-files tool to show the contents of the current working repo and then "
                "there clone this repository https://github.com/ElGreKost/Reinforcement-Learning-Library.git",
    agent=crewai_agent,
    expected_output=""
)
my_crew = Crew(agents=[crewai_agent], tasks=[task], verbose=True)

result = my_crew.kickoff()
print(result)