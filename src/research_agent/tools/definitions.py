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