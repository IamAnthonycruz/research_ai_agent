from google.genai import types
search_web_declaration = types.FunctionDeclaration(
    name="search_web",
    description="This tool searches the web for current information. You MUST use this for recent news, recent events, or to verify facts or for information past your cutoff date.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "query": types.Schema(
                type="STRING",
                description="A concise web search query, 3-8 words. Focus on the key information need"
            )
        },
        required=["query"]
    )
)

page_fetcher_declaration = types.FunctionDeclaration(
    name="fetch_page",
    description="This tool extracts the full text content of a web page through its URL. Use this after using the search_web tool to read the complete content of a promising result",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "url": types.Schema(
                type="STRING",
                description="A valid URL to read the full contents. This URL will be obtained from search results which will come from the search_web tool call"
            )
        },
        required=["url"]
    )
    
)