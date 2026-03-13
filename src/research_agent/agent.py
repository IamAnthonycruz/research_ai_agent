
import asyncio
from typing import List


from google.genai import types, errors
from pydantic import ValidationError
from research_agent.client import client, DEFAULT_CONFIG
from research_agent.tools.handlers import search_web_handler, page_fetcher_handler
from research_agent.schemas.web_search_schema import WebSearchResponse
from research_agent.tools.agent_prompts import default_config_system_prompt

async def select_tool(tool_call):
    tool_name = tool_call.name
    res = None
    match tool_name:
        case "search_web":
            res = await search_web_handler(**tool_call.args)
        case "fetch_page":
            res = await page_fetcher_handler(**tool_call.args)
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

    
async def agent_loop(topic:str, MAX_ATTEMPT=10):
    curr_attempt = 0
    logger_arr = []
    contents = [
                types.Content(
                    role="user", parts=[types.Part(text=topic)]
                )
            ]
    while curr_attempt < MAX_ATTEMPT:
        try:
            curr_attempt+=1
            response = generate_content_helper(contents=contents)
            tool_call =  response.candidates[0].content.parts[0].function_call
            
            if tool_call:
                res = await select_tool(tool_call=tool_call)
                function_response_part = types.Part.from_function_response(
                    name=tool_call.name,
                    response={"results":res}
                )
                logger_arr.append(response.candidates[0].content)
                
                contents.append(response.candidates[0].content)
                contents.append(types.Content(role="user", parts=[function_response_part]))
                
            else:
                break
                
        except errors.APIError as e:
            print(f"Gemini API Error: {e.status} - {e.message}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise
    response = generate_content_helper(contents=contents, config=types.GenerateContentConfig(
            system_instruction=default_config_system_prompt,
            response_mime_type="application/json",
            response_schema=WebSearchResponse))
    try:
        response = WebSearchResponse.model_validate_json(response.text)
        return response, logger_arr
    except ValidationError as e:
            print(f"An unexpected error occured: {e}")
            raise
async def main():
    topic = "What are the latest developments in nuclear fusion energy?"
    res,log = await agent_loop(topic=topic)
    print(res)
asyncio.run(main())