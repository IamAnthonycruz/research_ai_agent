
from http.client import HTTPException

from asyncddgs import aDDGS
import asyncio

from pydantic import HttpUrl
import requests
import trafilatura

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

async def page_fetcher_handler(url: str):
    try:
        fetched_page = trafilatura.fetch_url(url)
        if not fetched_page:
            return f"Failed to fetch {url}"
        result = trafilatura.extract(fetched_page)
        if not result:
            return f"Fetched url but failed to extract content from {url}"
        result_arr = result.split()
        result_arr = result_arr[:3000]
        return " ".join(result_arr)
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"
