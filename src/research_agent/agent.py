
import asyncio


from google.genai import types, errors
from pydantic import ValidationError
from research_agent.client import build_structured_output_config, client, DEFAULT_CONFIG
from research_agent.tools.handlers import search_web_handler
from research_agent.schemas.web_search_schema import WebSearchResponse


async def select_tool(tool_call):
    tool_name = tool_call.name
    res = None
    match tool_name:
        case "search_web":
            res = await search_web_handler(**tool_call.args)
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
        
        prompt = "Give me the latest developments in nuclear fusion energy"
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
            response = generate_content_helper(contents=contents, config=build_structured_output_config(WebSearchResponse))
            try:
                result = WebSearchResponse.model_validate_json(response.text)
                print(result)
            except ValidationError as e:
                print(f"An unexpected error occured: {e}")
                raise
        else:
            print(response.text)
    except errors.APIError as e:
        print(f"Gemini API Error: {e.status} - {e.message}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise
asyncio.run(main())