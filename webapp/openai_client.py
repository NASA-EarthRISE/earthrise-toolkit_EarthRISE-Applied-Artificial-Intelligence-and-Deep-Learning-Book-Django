import os
from openai import OpenAI

api_key  = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

# OpenAI client pointed at the LiteLLM proxy
client = OpenAI(api_key=api_key, base_url=base_url)

CHAT_MODEL      = os.getenv("MODEL", "gemini-2.5-pro")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
