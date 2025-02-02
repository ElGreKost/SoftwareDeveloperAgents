# writer_crew.py
from dotenv import load_dotenv
load_dotenv()

import os
from crewai import Agent, Crew, Process, Task
from crewai.project import agent, task, CrewBase, crew
from crewai import LLM

# Load LLM with environment-configured API keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash-exp",
    api_key=GEMINI_API_KEY,
    temperature=0,
)


@CrewBase
class StorytellingCrew:
    agents_config: str | dict = "config/writer_agent.yaml"
    tasks_config: str | dict = "config/writer_tasks.yaml"

    @agent
    def writer(self) -> Agent:
        return Agent(config=self.agents_config["writer"], llm=gemini_llm)

    @task
    def select_nature_and_animals(self) -> Task:
        return Task(config=self.tasks_config["select_nature_and_animals"])

    @task
    def plan_story_structure(self) -> Task:
        return Task(config=self.tasks_config["plan_story_structure"])

    @task
    def write_story(self) -> Task:
        return Task(config=self.tasks_config["write_story"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.writer()],
            tasks=[
                self.select_nature_and_animals(),
                self.plan_story_structure(),
                self.write_story()
            ],
            process=Process.sequential,  # Tasks will be executed one after the other
            verbose=True
        )


if __name__ == "__main__":
    storytelling_crew = StorytellingCrew().crew()
    result = storytelling_crew.kickoff()
    print(result)