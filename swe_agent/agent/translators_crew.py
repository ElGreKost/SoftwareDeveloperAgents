from crewai import Agent, Task, Crew, LLM, Process
from crewai.project import agent, task, crew, CrewBase

from dotenv import load_dotenv
load_dotenv()
import os
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_llm = LLM(
    model="gemini/gemini-1.5-flash-8b",
    api_key=GEMINI_API_KEY,
    temperature=0,
    max_tokens=100
)

@CrewBase
class TranslatorsCrew:
    agents_config: str | dict = "config/translator_agents.yaml"
    tasks_config: str | dict = "config/translation_tasks.yaml"

    @agent
    def translator(self) -> Agent:
        return Agent(
            config=self.agents_config["translator"],
            llm=gemini_llm,
            verbose=True,
        )

    @task
    def translator_task(self) -> Task:
        return Task(
            config=self.tasks_config["european_translations_task"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.translator()],
            tasks=[self.translator_task()],
            process=Process.sequential,
            verbose=True
        )

translators_crew = TranslatorsCrew().crew()

translators_crew_output = translators_crew.kickoff(inputs=dict(source_word="I'm cumming bitch"))