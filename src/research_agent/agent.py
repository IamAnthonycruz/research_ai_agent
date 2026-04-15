
import asyncio
from typing import List


from google.genai import types, errors
from pydantic import ValidationError
from research_agent.RAG.embeddings import Embedder
from research_agent.RAG.storage import Storage
from research_agent.client import client, DEFAULT_CONFIG
from research_agent.tools.handlers import get_notes_handler, search_web_handler, page_fetcher_handler, save_note_handler
from research_agent.schemas.web_search_schema import WebSearchResponse
from research_agent.tools.agent_prompts import default_config_system_prompt



async def select_tool(tool_call, notes, storage):
    tool_name = tool_call.name
    res = None
    match tool_name:
        case "search_web":
            res = await search_web_handler(**tool_call.args)
        case "fetch_page":
            res = await page_fetcher_handler(**tool_call.args, storage=storage)
        case "save_note":
            res = save_note_handler(**tool_call.args, notes=notes)
        case "get_all_notes":
            res =  get_notes_handler(notes=notes)
        case _:
            res = f"Unknown tool: {tool_name}"
    return res

async def generate_content_helper(contents, config=DEFAULT_CONFIG, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config
            )
            return response
        except errors.ClientError as e:
            if e.status == 429 and attempt < max_retries - 1:
                await asyncio.sleep(12)
            else:
                raise
    
async def agent_loop(topic:str, MAX_ATTEMPT=10):
    curr_attempt = 0
    logger_arr = []
    notes = []
    storage = Storage(db_path="./research_kb", embedder=Embedder())
    contents = [
                types.Content(
                    role="user", parts=[types.Part(text=topic)]
                )
            ]
    while curr_attempt < MAX_ATTEMPT:
        try:
            tools=[]
            response_part_list = []
            
            curr_attempt+=1
            response = await generate_content_helper(contents=contents)
            await asyncio.sleep(30)
            for tool in response.candidates[0].content.parts:
                tool_call =tool.function_call
                if tool_call:
                    tools.append(tool_call)
            if len(tools) > 0:
                for tool_call in tools:
                    res = await select_tool(tool_call=tool_call, notes=notes, storage=storage)
                    function_response_part = types.Part.from_function_response(
                        name=tool_call.name,
                        response={"results":res}
                    )
                    response_part_list.append(function_response_part)
                logger_arr.append(response.candidates[0].content)
                contents.append(response.candidates[0].content)
                contents.append(types.Content(role="user", parts=response_part_list))
            else:
                break
                
        except errors.APIError as e:
            print(f"Gemini API Error: {e.status} - {e.message}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise
    print(f"KB chunk count after research: {storage.collection.count()}")
    response = await generate_content_helper(contents=contents, config=types.GenerateContentConfig(
            system_instruction=default_config_system_prompt,
            response_mime_type="application/json",
            response_schema=WebSearchResponse))
    await asyncio.sleep(10)
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