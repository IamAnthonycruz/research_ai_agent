
from asyncddgs import aDDGS
import asyncio

async def search_web_handler(query:str):
    formatted_results = ""
    try:
        async with aDDGS() as ddgs:
            text_results = await ddgs.text(
                keywords=query,
                region="us-en",
                safesearch="off",
                timelimit="y",
                max_results=7,
            )
            if text_results:
                for i, result in enumerate(text_results, 1):
                    formatted_results += (
                        f"[{i}] Title: {result['title']}\n"
                        f"  Snippet: {result['body']}\n"
                        f"  URL: {result['href']}\n\n"
                    )
    except Exception as e:
        return f"Search failed: {str(e)}"
    return formatted_results
        