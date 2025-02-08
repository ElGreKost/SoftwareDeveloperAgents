import os
from langchain_openai import ChatOpenAI
from langchain.llms.base import LLM
import requests
from typing import Optional

def get_llm():
    """
    Initialize and return the LLM.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

    # Return a basic LLM setup
    #return ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    return ChatOpenAI(api_key=api_key, model="gpt-4o-mini")



class OllamaLLM(LLM):
    """
    A custom LLM wrapper for Ollama to use with LangChain.
    """

    model: str  # The name of the Ollama model to use (e.g., "deepseek-r1:1.5b")
    api_url: str = "http://localhost:11434/api"  # Ollama server endpoint

    def _call(self, prompt: str, stop: Optional[list[str]] = None) -> str:
        """
        Make a call to the Ollama model with the given prompt.
        """
        # Build the request payload
        payload = {"prompt": prompt}
        headers = {"Content-Type": "application/json"}

        # Make the POST request to the Ollama server
        response = requests.post(f"{self.api_url}/{self.model}", json=payload, headers=headers)
        response.raise_for_status()

        # Extract and return the model's response
        return response.json().get("response", "").strip()

    @property
    def _identifying_params(self):
        """
        Return model identifying parameters.
        """
        return {"model": self.model}

    @property
    def _llm_type(self):
        """
        Return the type of the LLM.
        """
        return "ollama"
