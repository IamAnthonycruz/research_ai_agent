import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from research_agent.tools.definitions import search_web_declaration
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
if not gemini_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")


client = genai.Client(api_key=gemini_key)
tools = types.Tool(function_declarations=[search_web_declaration])
if not tools:
    raise ValueError("Tools not found")
DEFAULT_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    tools=[tools],
    system_instruction="You are a research agent. You must use the search_web tool to find current information before answering any question. Never answer from your own knowledge alone — always search first."
)
def build_structured_output_config(schema):
    STRUCTURED_CONFIG = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema
    )
    return STRUCTURED_CONFIG
