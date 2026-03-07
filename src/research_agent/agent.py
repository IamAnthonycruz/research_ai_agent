
import asyncio


from google.genai import types, errors
from research_agent.client import client, DEFAULT_CONFIG
from research_agent.tools.handlers import search_web_handler



async def select_tool(tool_call):
    tool_name = tool_call.name
    res = None
    match tool_name:
        case "search_web":
            res = await search_web_handler(**tool_call.args)
            print("Handler:", res)
        case _:
            res = f"Unknown tool: {tool_name}"
    return res

def generate_content_helper(contents, config=DEFAULT_CONFIG):
    response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=contents, 
            config=config
        )
    return response


async def main():
    try:
        
        prompt = "What happened in the news today?"
        contents = [
            types.Content(
                role="user", parts=[types.Part(text=prompt )]
            )
        ]
        response = generate_content_helper(contents=contents)
        tool_call =  response.candidates[0].content.parts[0].function_call
        if tool_call:
            
            res = await select_tool(tool_call=tool_call)
            function_response_part = types.Part.from_function_response(
                name=tool_call.name,
                response={"results":res}
            )
            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=[function_response_part]))
            response = generate_content_helper(contents=contents)
            print(response.text)
        else:
            print(response.text)
    except errors.APIError as e:
        print(f"Gemini API Error: {e.status} - {e.message}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise
asyncio.run(main())