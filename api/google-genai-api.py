import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")


client = genai.Client(api_key=gemini_key)
config = types.GenerateContentConfig(
    temperature=0.2
)
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )

    print(response.text)
except:
    raise RuntimeError