import asyncio
from http.client import HTTPException

from pydantic import HttpUrl
import trafilatura


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

async def main():
    res = await page_fetcher_handler("https://en.wikipedia.org/wiki/Fallout_(franchise)")
    #print(res)
    
asyncio.run(main())