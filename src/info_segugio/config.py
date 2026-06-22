import os


class Config:
    LLM_MODEL = "gpt-4o"
    LLM_MODEL_LOW = "gpt-4o-mini"
    AI_API_URL = "https://api.openai.com/v1/"
    AI_API_KEY = os.environ.get("OPENAI_API_KEY")
    TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

