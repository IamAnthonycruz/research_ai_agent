
from http.client import HTTPException

from asyncddgs import aDDGS
import asyncio

from pydantic import HttpUrl
import requests
import trafilatura

from research_agent.RAG.chunk import Chunk
from research_agent.RAG.storage import Storage

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

async def page_fetcher_handler(url: str, storage: Storage):
    try:
        print(f"[fetch] attempting {url}")
        fetched_page = trafilatura.fetch_url(url)
        if not fetched_page:
            print(f"[fetch] fetch_url returned None for {url}")
            return f"Failed to fetch {url}"

        print(f"[fetch] got page, extracting...")
        extracted = trafilatura.bare_extraction(fetched_page)
        if not extracted or not extracted.text:
            print(f"[fetch] bare_extraction failed or no text for {url}")
            return f"Fetched url but failed to extract content from {url}"

        text = extracted.text
        title = extracted.title or url
        print(f"[fetch] extracted '{title}' ({len(text.split())} words)")

        chunks = Chunk.chunk_note(text=text, source_url=url, source_title=title)
        print(f"[fetch] chunked into {len(chunks)} pieces")
        if chunks:
            storage.write(chunks)
            print(f"[fetch] wrote to storage")

        result_arr = text.split()[:3000]
        return " ".join(result_arr)

    except Exception as e:
        print(f"[fetch] exception: {e}")
        return f"Error fetching {url}: {str(e)}"


def save_note_handler(key: str, content:str, notes:list):
    if not key or not content:
        return "Key or content are missing"
    my_dict = {
        "key": key,
        "content":content
    }
    notes.append(my_dict)
    return f"Added note {key}: {content}"
    
def get_notes_handler(notes:list):
    note_arr = []
    if not notes:
        return "No stored notes found"
    for index, note in enumerate(notes,start=1):
        note_str = f"Note: [{index}] Key:{note['key']} Content: {note['content']}"
        note_arr.append(note_str)
    return "\n ".join(note_arr)
        
        
