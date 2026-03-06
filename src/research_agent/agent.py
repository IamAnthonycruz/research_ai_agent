
from google.genai import types, errors
from research_agent.client import client, DEFAULT_CONFIG


try:
    
    prompt = "placeholder"
    contents = [
        types.Content(
            role="user", parts=[types.Part(text=prompt )]
        )
    ]
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=contents, 
        config=DEFAULT_CONFIG
    )
    parts =  response.candidates[0].content.parts[0]
    if parts.function_call:
        pass
    else:
        print(parts.text)
        
except errors.APIError as e:
    print(f"Gemini API Error: {e.status} - {e.message}")
    raise
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    raise