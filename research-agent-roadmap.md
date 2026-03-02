# Research Agent Roadmap
### From Zero to Multi-Agent System — Gemini 2.0 Flash

---

## Part 1: One Agent, One Tool
**Time: 6–8 hours**
**Goal:** Build a single agent that can take a research topic, call a web search tool, and return structured results.

By the end of this part, you'll have a working loop: user gives topic → model decides to search → your code executes the search → model gets results → model produces a structured answer.

---

### Subproblem 1.1: Calling the Gemini API Programmatically

**Logic Walkthrough**

Before anything else, you need to be able to send a message to Gemini and get a response back in your code. This is the foundation everything else builds on.

Here's what's actually happening under the hood: you're making an HTTP POST request to Google's API endpoint with a JSON body that contains your prompt, your model configuration, and your API key. The SDK wraps this so you don't hand-build HTTP requests, but understanding that it's just a request-response cycle matters — because when things break, they break at the HTTP level (timeouts, rate limits, malformed payloads).

The flow:
1. Install the `google-genai` Python SDK (this is the newer one, not `google-generativeai` — Google recently consolidated their SDKs).
2. Create a client by passing your API key. The key comes from Google AI Studio — you literally just click "Get API Key."
3. Build a message: you're constructing a `contents` list, where each item has a `role` ("user" or "model") and `parts` (the actual text or data).
4. Send it using `client.models.generate_content()` and specify the model string (`gemini-2.0-flash`).
5. Parse the response: the response object has `candidates`, each candidate has `content`, and inside content you get `parts` — your text is in `parts[0].text`.

Key decisions you'll make:
- **API key management**: Use environment variables or a `.env` file. Never hardcode it. `python-dotenv` is the standard pattern here.
- **Model parameters**: Temperature controls randomness (0.0 = deterministic, good for factual research; 1.0+ = creative). Start with 0.2 for a research agent.
- **Error handling on the first call**: The API can return 429 (rate limited), 500 (server error), or malformed responses. Wrap your call in a try/except from the start — don't add it later.

Gotcha: The Gemini SDK has gone through multiple versions. Make sure you're using `google-genai` (the unified SDK), not the older `google-generativeai`. The import structure and method names are different. Check the docs you're reading match the SDK you installed.

**Resources**
- Reading: [Gemini API Quickstart — Google AI for Developers](https://ai.google.dev/gemini-api/docs/quickstart?lang=python)
- YouTube search: `"Gemini API Python quickstart tutorial 2025"`

**Where You'll See This Again**
1. Every LLM-powered application starts with this exact pattern — OpenAI's SDK, Anthropic's SDK, and Mistral's SDK all follow the same client → message → response structure with minor syntax differences.
2. When you build internal tools at work (like what you did at the Fed), wrapping an LLM call behind a function with retry logic is how teams make AI features production-stable.
3. Chatbot backends (customer service, coding assistants) are fundamentally this same request-response loop, just with conversation history appended to `contents` each turn.

This subproblem matters because every single thing you build in this project is a layer on top of this API call. If you don't understand the shape of the request and response objects at this level, debugging anything above it becomes guesswork. You also need this mental model to understand what the SDK is abstracting away when you start adding tools and structured output.

---

### Subproblem 1.2: Defining a Tool for the Model (Function Declarations)

**Logic Walkthrough**

Now you need to teach the model that it has the *ability* to search the web. You're not giving it code to execute — you're giving it a menu of capabilities and letting it decide when to use them.

This is called **function calling** (or tool use). Here's how it conceptually works:

You describe a function to the model using a JSON schema: the function's name, what it does (a plain-English description), and what parameters it accepts (with types and descriptions for each). You send this schema alongside your prompt. The model doesn't execute anything — it reads your description and, if it decides the function would help answer the query, it responds not with text but with a structured "please call this function with these arguments" message.

The flow:
1. Define your tool as a dictionary/object with `name`, `description`, and `parameters`. For a search tool, you'd have one parameter: `query` (string) — the search query the model wants to run.
2. Pass this tool definition into your API call under the `tools` config.
3. When the model responds, check the response type. Instead of `parts[0].text`, you'll get a `function_call` object in the parts — this contains the function name and the arguments the model chose.

Key decisions you'll make:
- **Tool description quality**: This is where most people mess up. The description isn't a formality — it's the model's *only* information about what the tool does and when to use it. A vague description like "searches stuff" leads to bad tool selection. A good one: "Searches the web for current information on a given topic. Use this when the user asks about recent events, factual claims, or topics that require up-to-date data."
- **Parameter descriptions**: Same principle. `query: "the search query"` is weak. `query: "A concise web search query, 3-8 words, focused on the key information needed"` steers the model toward writing better queries.
- **Required vs. optional parameters**: For your search tool, `query` is required. Later when you add more complex tools, you'll have optional params. Mark them correctly in the schema.

Gotcha: The model can decide NOT to use your tool. If you ask "what's 2+2?" and you only have a web search tool, a well-behaved model will just answer directly. Your code needs to handle both paths — tool call responses AND regular text responses. Don't assume every response will be a function call.

**Resources**
- Reading: [Gemini API Function Calling documentation](https://ai.google.dev/gemini-api/docs/function-calling)
- YouTube search: `"LLM function calling explained how it works"`

**Where You'll See This Again**
1. OpenAI's "function calling" and Anthropic's "tool use" are the exact same pattern with slightly different JSON schemas — the concept is universal across all major LLM APIs.
2. Plugin systems (like ChatGPT plugins or MCP servers) are just this pattern scaled up: hundreds of tool definitions that the model routes between.
3. Every enterprise AI agent (customer service bots that can look up orders, coding agents that can run tests) uses function declarations as the interface between "what the model wants to do" and "what your code actually executes."

This matters because function calling is the fundamental mechanism that turns a language model from a text generator into an agent. Without this, the model can only talk about searching — with it, the model can request a search and get real data back. Understanding the declaration pattern deeply also sets you up for Step 2, where you'll have multiple tools competing for selection.

---

### Subproblem 1.3: Executing the Tool and Returning Results

**Logic Walkthrough**

The model has asked you to call a function. Now your code has to actually do it and feed the results back.

Here's the critical mental model: you are the runtime. The model is the brain that decides what to do, but your Python code is the hands and legs. The model says "search for X" — you go search for X, get the results, and hand them back. This is called "closing the loop."

The flow:
1. Parse the `function_call` from the model's response: extract the function name and the arguments dictionary.
2. Route to the right handler: for now you only have one tool, but build this as an if/elif or dictionary dispatch (`{"web_search": do_search}`) from the start. You'll thank yourself in Step 2.
3. Execute the actual search: For the web search itself, you have a few options. The simplest is the `googlesearch-python` library or `duckduckgo-search` (no API key needed). These return a list of URLs, titles, and snippets. Start with snippets — don't try to scrape full pages yet.
4. Format the results into a string or structured object that makes sense for the model to read. The model will receive this as the "function response" — it needs enough information to synthesize an answer but not so much that it's drowning in noise. 5-10 search results with title + snippet is a good starting point.
5. Send the results back by appending to the conversation: the original user message, the model's function call, and now a `function_response` part containing your results. Then call the API again — the model now has the search results in context and can write its final answer.

Key decisions you'll make:
- **Which search provider**: `duckduckgo-search` is the zero-friction option — no API key, no billing. It's good enough for learning. SerpAPI or Google Custom Search give better results but add setup complexity.
- **How many results to return**: Start with 5. More than 10 fills the context window with marginal information. The model needs signal, not noise.
- **Result formatting**: Give the model clean, parseable text. Something like `[1] Title: ... \n Snippet: ... \n URL: ...` per result. Don't dump raw HTML or giant JSON blobs.
- **The full conversation structure**: This is the part people find tricky. After the tool execution, you're sending the API a conversation that looks like: user message → model function_call → function_response with results → (API call) → model final answer. This multi-turn structure is how the model "remembers" what it asked for and what it got back.

Gotcha: Rate limiting on free search APIs. DuckDuckGo will throttle you if you hammer it. Add a simple `time.sleep(1)` between searches. Also, search results can contain garbage — empty snippets, irrelevant results, error pages. Basic filtering (skip results with empty snippets) saves you from confusing the model.

**Resources**
- Reading: [DuckDuckGo Search Python library documentation](https://pypi.org/project/duckduckgo-search/)
- YouTube search: `"building LLM agent tool execution loop Python"`

**Where You'll See This Again**
1. Every agent framework (LangChain, CrewAI, AutoGen) has a tool executor that does exactly this: parse the model's requested action, dispatch to the right function, format results, feed them back. You're building the core of what those frameworks abstract away.
2. CI/CD pipelines follow a similar pattern — a controller (like Jenkins or GitHub Actions) receives a command, dispatches it to a runner, captures the output, and decides what to do next.
3. Robotic process automation (RPA) tools like UiPath use the same loop: AI decides what to do → automation executes it → results feed back for next decision.

This matters because the execution layer is where the agent stops being theoretical and starts being real. The model can reason all day, but if your tool execution is unreliable, slow, or returns garbage data, the entire agent fails. Getting this right also teaches you the "function call → function response" conversation pattern that is identical across all LLM providers — it's the universal protocol for giving models capabilities.

---

### Subproblem 1.4: Structured Output from the Final Response

**Logic Walkthrough**

Your agent has searched the web, gotten results, and the model has synthesized an answer. But right now that answer is just a blob of text. For a research agent, you want structured output: a title, a summary, key findings, sources used. Something your code can parse and work with programmatically.

There are two approaches to getting structured output from an LLM:

**Approach A — Prompt-based**: You tell the model in the system prompt or user message: "Return your response as JSON with the following fields: title, summary, findings (list), sources (list)." This works decently but the model can still go off-script — it might add extra fields, forget to close a bracket, or wrap the JSON in markdown code fences.

**Approach B — Schema-enforced (recommended)**: Gemini supports a `response_schema` config where you pass a JSON schema or a Pydantic model, and the API constrains the output to match that structure. This is more reliable because the model is forced to conform.

The flow:
1. Define your output structure. A Pydantic model works cleanly here: a class with `title: str`, `summary: str`, `findings: list[str]`, `sources: list[str]`.
2. Pass this schema in your API call config under `response_mime_type: "application/json"` and `response_schema`.
3. Parse the response: since you've told the API to return JSON, `response.text` will be a JSON string. Parse it with `json.loads()` or validate it with your Pydantic model.

Key decisions you'll make:
- **What fields to include in the schema**: Start minimal — title, summary, key_findings (list of strings), sources (list of objects with title and URL). You can always expand later. Overengineering the schema now creates parsing headaches.
- **How strict to make the schema**: Pydantic models with `response_schema` give you type enforcement. This is better than prompt-only approaches for a research agent where you want consistent, parseable output.
- **Fallback handling**: Even with schema enforcement, things can occasionally fail (malformed JSON, empty fields). Parse inside a try/except and have a sensible fallback.

Gotcha: When you combine tool use AND structured output in the same workflow, the structured output constraint applies to the model's *final* response — not the intermediate tool-call responses. The model should still be able to freely make function calls. Make sure your config reflects this: apply the response schema on the final generation step, not on every API call in the loop. You might end up making two types of calls — one for tool use (no schema constraint) and a final one for the structured answer.

**Resources**
- Reading: [Gemini API Structured Output documentation](https://ai.google.dev/gemini-api/docs/structured-output)
- YouTube search: `"Pydantic structured output LLM API tutorial"`

**Where You'll See This Again**
1. Every production AI feature that feeds into a UI or database needs structured output — recommendation engines, content moderation systems, and automated report generators all parse LLM responses into typed objects.
2. API contract design in general follows this same principle: define a schema, validate inputs/outputs against it, handle edge cases when the real world doesn't match the contract.
3. Data pipelines that use LLMs for extraction (pulling structured data from unstructured text — invoices, medical records, legal documents) rely entirely on structured output to feed into downstream systems.

This matters because without structured output, your agent is a chatbot. With it, your agent becomes a component — something that can plug into other systems, feed into a database, populate a UI, or pass clean data to the next agent in the pipeline. This is the difference between a demo and a tool, and it's the foundation for everything in Steps 5 and 6 where agents need to pass structured context to each other.

---

### Subproblem 1.5: The Agent Loop — Putting It All Together

**Logic Walkthrough**

Now you wire everything together into a single coherent loop. This is where you step back and think about the *flow* as a whole, not just individual pieces.

The agent loop is conceptually simple:

```
1. User provides a research topic
2. Build the initial prompt (system instructions + user query)
3. Call the API with tool definitions
4. Check the response:
   a. If it's a function call → execute the tool → append results → go to step 3
   b. If it's a text response → you're done (or apply structured output)
5. Parse and return the structured result
```

This is a **ReAct-style loop** (Reason + Act): the model reasons about what to do, takes an action (tool call), observes the result, and repeats until it has enough information to answer.

Key decisions you'll make:
- **Max iterations**: The model could theoretically keep calling tools forever (search → search again → search again). Set a limit — 3-5 iterations is reasonable for a single-tool agent. If the model hasn't converged by then, force a final answer.
- **System prompt design**: This is your single biggest lever for agent quality. Your system prompt should tell the model: (1) what it is ("You are a research agent"), (2) what its goal is ("provide thorough, sourced answers to research questions"), (3) how it should use tools ("search when you need current or factual information"), and (4) what its output should look like ("provide a structured response with title, summary, findings, and sources"). Iterate on this — it's prompt engineering, and it matters more than any code decision you'll make.
- **Conversation history management**: Each iteration appends to the conversation. User → model function call → function response → model function call → function response → model final answer. You're building this list as you loop. Make sure you're appending correctly — a missing or mis-ordered message will confuse the model.
- **Separating the tool-use calls from the final structured call**: As noted in 1.4, you may want to run the loop with tools enabled and no schema constraint, then once the model gives a text response (indicating it's ready to answer), make one final call with the schema constraint to get clean structured output. Or you can apply the schema from the start and see if the model handles both — test this yourself.

Gotcha: Debugging agent loops is harder than debugging linear code. When something goes wrong, you need to see the full conversation history — every message in every role. Build a simple logging function from the start that prints the entire `contents` list in a readable format. This will save you hours.

**Resources**
- Reading: [ReAct: Synergizing Reasoning and Acting in Language Models (paper)](https://arxiv.org/abs/2210.03629) — Read the abstract and Section 2 for the conceptual framework. You don't need the full paper.
- YouTube search: `"ReAct agent loop explained step by step"`

**Where You'll See This Again**
1. Claude's tool use, ChatGPT's function calling, and every major AI assistant all run variations of this exact loop — reason, act, observe, repeat.
2. Game AI uses a similar observe-decide-act loop — NPCs evaluate their environment, choose an action, execute it, observe the result, and repeat.
3. Control systems in robotics and automation follow the same feedback loop pattern: sense → plan → act → sense again.

This matters because the agent loop is the core architectural pattern of AI engineering right now. Everything you build in Steps 2-6 is an extension of this loop — more tools, better retrieval, evaluation layers, multiple agents running their own loops and coordinating. If you understand this loop deeply — where the model's reasoning happens, where your code takes over, where errors propagate — you can build any agent system.

---
---

## Part 2: One Agent, Multiple Tools
**Time: 6–8 hours**
**Goal:** Extend your agent to choose between multiple tools — web search, page fetching, and note-taking — and route between them intelligently.

By the end of this part, your agent will take a research topic, decide which tools to use and in what order, fetch full content from relevant pages, and produce a more thorough research report.

---

### Subproblem 2.1: Adding a Page Fetcher Tool

**Logic Walkthrough**

Your search tool returns snippets — short previews of what's on a page. But real research requires reading the full content. You need a tool that takes a URL and returns the actual text content of that page.

The flow:
1. Define a new tool declaration: `fetch_page` with one parameter, `url` (string). The description should make clear to the model when this is useful vs. search: "Fetches the full text content of a web page given its URL. Use this after searching to read the complete content of a promising result."
2. Implement the handler: Use the `requests` library to GET the URL, then extract readable text. Raw HTML is useless to the model — you need to strip tags and pull out the article body. `BeautifulSoup` with a simple heuristic (grab all `<p>` tags) works for a v1, or use a library like `trafilatura` which is specifically designed for web article extraction.
3. Handle the content size problem: A full web page can be 10,000+ words. Gemini 2.0 Flash has a 1M token context window so you *can* shove it all in, but you *shouldn't*. Truncate to a reasonable length (first 3000-5000 words) — the important information in an article is almost always near the top. Alternatively, you can chunk and summarize, but that's adding complexity you don't need yet.

Key decisions you'll make:
- **Text extraction approach**: `trafilatura` gives you cleaner output (it's designed for this exact use case) but is a heavier dependency. `BeautifulSoup` + grabbing `<p>` tags is simpler but noisier. Start with whichever you're more comfortable debugging.
- **Timeout and error handling**: Web pages can hang, return 403s, require JavaScript rendering, or redirect infinitely. Set a 10-second timeout on `requests.get()`. Return a clean error message to the model when a page fails ("Could not fetch page: connection timed out") so it can adapt.
- **Content truncation strategy**: First N characters is crude but effective. A slightly better approach is first N words, which avoids cutting mid-sentence.

Gotcha: Many modern websites are JavaScript-rendered SPAs — the HTML you get from `requests.get()` is an empty shell. For this project, just skip those pages and move on. Solving JS rendering (with Playwright/Selenium) is a rabbit hole that isn't worth it for learning agent architecture.

**Resources**
- Reading: [Trafilatura documentation — Web content extraction](https://trafilatura.readthedocs.io/en/latest/)
- YouTube search: `"web scraping article text extraction Python beautifulsoup"`

**Where You'll See This Again**
1. Search engines themselves do this at massive scale — Googlebot fetches pages, extracts content, and indexes it. Your fetch tool is a tiny version of a web crawler.
2. RAG pipelines in production (Step 3 preview) all have a document loading stage where raw content gets fetched, cleaned, and prepared for embedding — your extraction logic here carries directly forward.
3. Data journalism tools that aggregate and analyze news articles from multiple sources use the exact same fetch → extract → clean pipeline.

This matters because an agent that can only read search snippets is like a researcher who only reads headlines. The page fetcher gives your agent the ability to go deep on a source, which dramatically improves the quality and accuracy of its research output. It also introduces you to the real-world messiness of web data — something every production system has to deal with.

---

### Subproblem 2.2: Adding a Scratchpad / Note-Taking Tool

**Logic Walkthrough**

Here's a problem you'll notice quickly once your agent has search and fetch: the conversation history gets long, and the model starts losing track of what it's already learned. A scratchpad tool lets the model explicitly save important findings as it goes, creating a working memory it can reference.

The concept is simple: the model calls a `save_note` tool with a key (like "main_findings" or "source_1_summary") and a value (the text to save). Your code stores these in a Python dictionary. At any point, the model can call a `get_notes` tool to retrieve everything it's saved.

The flow:
1. Define two new tools: `save_note(key: str, content: str)` and `get_notes()` (no parameters — returns everything saved so far).
2. Implement both handlers: `save_note` writes to a dictionary and returns a confirmation. `get_notes` serializes the dictionary into a readable format and returns it.
3. Update your system prompt to tell the model about the scratchpad strategy: "As you research, save key findings using the save_note tool. Before writing your final answer, call get_notes to review everything you've collected."

Key decisions you'll make:
- **Simple dictionary vs. more structured storage**: A plain `dict[str, str]` is perfect for now. Don't build a database.
- **Whether to auto-inject notes into context**: You could automatically append all notes to every API call, or let the model explicitly request them via `get_notes`. Letting the model control when to retrieve keeps things simpler and teaches you about model-driven workflows.
- **Note size limits**: If the model tries to save an entire fetched article as a note, that defeats the purpose. Add a soft limit in your tool description: "Save concise summaries, not full text. Keep each note under 500 words."

Gotcha: This is your first tool where state persists across the loop. Search and fetch are stateless — each call is independent. The scratchpad introduces state management. Make sure your notes dictionary is initialized outside the loop and persists across iterations. This is trivial in a single-run script but matters when you start thinking about multi-agent systems in Step 5.

**Resources**
- Reading: [Building AI Agents with Memory — Lilian Weng's Blog](https://lilianweng.github.io/posts/2023-06-23-agent/) — Focus on the "Memory" section.
- YouTube search: `"AI agent memory scratchpad working memory explained"`

**Where You'll See This Again**
1. ChatGPT's "memory" feature and Claude's memory system are production versions of this pattern — the model deciding what's worth saving from a conversation for future reference.
2. In software engineering, this is the same concept as a cache or memo — intermediate results saved to avoid recomputation and maintain state across operations.
3. Research tools like Notion or Obsidian serve as human scratchpads in exactly this way — you save key findings as you read, then synthesize from your notes rather than re-reading everything.

This matters because agent memory is what separates a simple Q&A tool from a system that can do extended research. Without a scratchpad, your agent's "working memory" is just the context window, which gets noisy fast. The scratchpad lets the model curate what it's learned, which directly improves the quality of the final output. It also introduces you to stateful tools, which is a key concept for multi-agent coordination later.

---

### Subproblem 2.3: Multi-Tool Routing and Prompt Engineering

**Logic Walkthrough**

Now you have 3+ tools. The model has to decide, on each turn: should I search? Fetch a page? Save a note? Just respond? This is the **tool selection** problem, and most of the solution lives in your prompt, not your code.

Here's what's actually happening: when you provide multiple tool definitions, the model reads all of their descriptions and, based on the current conversation context and its instructions, picks the most appropriate one (or none). The quality of this routing depends almost entirely on two things: (1) how clearly your tool descriptions differentiate from each other, and (2) how well your system prompt defines the research *workflow*.

The flow:
1. Review all your tool descriptions for clarity and distinctness. The model should never be confused about which tool to use when. Search is for *finding* sources. Fetch is for *reading* specific sources. Save note is for *remembering* key information. Each description should make its role unambiguous.
2. Design a research workflow in your system prompt. Don't just list capabilities — describe a strategy: "First, search to find relevant sources. Then, fetch the most promising 2-3 pages to read their full content. Save key findings as notes as you go. When you have enough information, retrieve your notes and produce a structured report."
3. Test with multiple research queries and observe: Does the model follow the workflow? Does it use all the tools or over-rely on one? Does it search multiple times or stop after one query? Adjust your prompt based on what you observe.

Key decisions you'll make:
- **How prescriptive to be in the system prompt**: There's a spectrum from "here are your tools, figure it out" (too loose — the model may search once and give a shallow answer) to "Step 1: search, Step 2: fetch the top 3 results, Step 3: save notes on each" (too rigid — the model can't adapt to different query types). Aim for the middle: describe the general strategy but let the model decide the specifics.
- **Handling parallel vs. sequential tool calls**: Gemini can request multiple function calls in a single response (e.g., "fetch these 3 URLs at once"). Your code needs to handle this — execute all of them and return all results. This is a meaningful efficiency gain.
- **Iterating on the prompt**: This is an empirical process, not a theoretical one. Try 5-10 different research queries, see where the agent makes bad decisions, and adjust. Prompt engineering is testing, not writing.

Gotcha: The model might get into a loop — searching, then searching again with a slightly different query, then searching again, never fetching or synthesizing. This usually means your system prompt doesn't clearly signal when to move from the "gathering" phase to the "synthesizing" phase. Add explicit guidance: "After 2-3 searches, you should have enough sources. Move on to fetching and reading the most relevant ones."

**Resources**
- Reading: [Google's Prompt Engineering Guide for Gemini](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- YouTube search: `"prompt engineering for AI agents tool selection"`

**Where You'll See This Again**
1. Virtual assistants (Siri, Alexa, Google Assistant) face this exact routing problem — should I search the web, play music, set a timer, or control a smart device? The routing logic is the core of the product.
2. API gateways in microservice architectures do the same thing — an incoming request needs to be routed to the right service based on its content and the available endpoints.
3. Triage systems in customer service (automated and human) route incoming requests to the right department or tool based on the nature of the problem — same pattern, different domain.

This matters because tool selection is the agent's decision-making ability. An agent with tools it can't use effectively is worse than an agent with one tool it uses well. The prompt engineering work you do here is also the most transferable skill in AI engineering — every system you build will require you to steer model behavior through well-designed prompts. This is where you develop your intuition for what models are good at, where they need guardrails, and how instructions translate into behavior.

---
---

## Part 3: Add RAG (Retrieval-Augmented Generation)
**Time: 10–12 hours**
**Goal:** Instead of re-searching every time, store and retrieve from a local knowledge base of content your agent has already gathered. Learn embeddings, vector search, and retrieval pipelines.

By the end of this part, your agent can build up a knowledge base during research and retrieve relevant information from it using semantic similarity — not just keyword matching.

---

### Subproblem 3.1: Understanding Embeddings — What They Are and How to Generate Them

**Logic Walkthrough**

An embedding is a list of numbers (a vector) that represents the *meaning* of a piece of text. Two pieces of text that mean similar things will have vectors that are close together in space; unrelated texts will be far apart. This is what makes semantic search possible — you're not matching keywords, you're matching meaning.

Here's the concrete mechanics:
1. You take a string of text (a sentence, paragraph, or chunk of an article).
2. You send it to an embedding model (Gemini has one: `text-embedding-004`).
3. You get back a list of 768 floating-point numbers. That's your embedding.
4. You do this for every chunk of text you want to be searchable.
5. Later, when you have a query, you embed the query the same way and find which stored embeddings are closest to it.

The flow for generating:
1. Use the Gemini API's `embed_content` method. You pass in your text, specify the model (`text-embedding-004`), and optionally a `task_type` (like `RETRIEVAL_DOCUMENT` for content you're storing, `RETRIEVAL_QUERY` for the search query).
2. The response contains a list of floats — your embedding vector.
3. Store this vector alongside the original text and any metadata (source URL, title, date fetched).

Key decisions you'll make:
- **What "task_type" to use**: Gemini's embedding model supports task types that optimize the embedding for different use cases. Use `RETRIEVAL_DOCUMENT` when embedding content for storage and `RETRIEVAL_QUERY` when embedding a search query. This asymmetry actually improves retrieval quality.
- **Batch vs. single embedding**: If you're embedding many chunks, send them in batches rather than one at a time. The API supports batched requests, which is faster and uses fewer API calls.

Gotcha: Embeddings are model-specific. A vector from Gemini's model and a vector from OpenAI's model are incompatible — you can't compare them or mix them in the same search index. If you ever switch embedding models, you need to re-embed everything. Choose one and stick with it for this project.

**Resources**
- Reading: [Gemini API Embeddings Guide](https://ai.google.dev/gemini-api/docs/embeddings)
- YouTube search: `"what are embeddings explained visually machine learning"`

**Where You'll See This Again**
1. Every recommendation system (Netflix, Spotify, Amazon) uses embeddings to represent items and user preferences in the same vector space, then finds "close" matches — same core math.
2. Semantic code search tools (like GitHub's code search, Sourcegraph) embed code snippets and let you search by describing what the code does rather than remembering exact function names.
3. Fraud detection systems embed transaction patterns and flag new transactions whose embeddings are far from the "normal" cluster — anomaly detection via embedding distance.

This matters because embeddings are the bridge between human language and math. Without them, computers can only match exact strings or keywords. With them, your agent can find information based on meaning, which is how humans actually think about relevance. This is the foundational concept that makes RAG work — and RAG is arguably the most widely-deployed LLM pattern in production today.

---

### Subproblem 3.2: Text Chunking — Preparing Content for Embedding

**Logic Walkthrough**

You can't just embed an entire 5,000-word article as one vector. The embedding would capture the overall theme but lose specific details. You need to break text into smaller pieces — chunks — each of which captures a focused idea or piece of information.

Chunking seems simple ("just split by paragraphs") but is actually one of the most consequential decisions in a RAG pipeline. Bad chunking = bad retrieval = bad answers.

The flow:
1. Take a fetched article's text content.
2. Split it into chunks of roughly 200-500 words each.
3. Each chunk should be semantically coherent — it should make sense on its own without needing the chunks around it.
4. Optionally overlap chunks (e.g., each chunk includes the last 1-2 sentences of the previous chunk) to avoid losing information at boundaries.

Key decisions you'll make:
- **Chunk size**: Smaller chunks (200 words) are more precise for retrieval — a query about a specific fact is more likely to find the right chunk. Larger chunks (500+ words) preserve more context but may dilute the signal. For a research agent, start with ~300-400 words and adjust based on retrieval quality.
- **Chunking strategy**: The simplest is fixed-size with word count. A step better is splitting on paragraph boundaries, then merging small paragraphs and splitting large ones to stay near your target size. Splitting mid-sentence is bad — always split at sentence boundaries at minimum.
- **Overlap**: 10-15% overlap between consecutive chunks helps ensure that information spanning a chunk boundary isn't lost. E.g., if your chunks are 300 words, let the last 40-50 words of chunk N also appear at the start of chunk N+1.
- **Metadata**: Attach metadata to each chunk — source URL, article title, chunk index (position in original document). You'll need this for citations in the final report.

Gotcha: The quality of your RAG system is bounded by the quality of your chunking. If a key fact gets split across two chunks, neither chunk will rank highly for a query about that fact. If chunks are too large, irrelevant content dilutes the embedding. Spend time looking at your chunks manually — print them out, read them, ask "if I searched for X, would this chunk contain the answer?"

**Resources**
- Reading: [Chunking Strategies for LLM Applications — Pinecone Guide](https://www.pinecone.io/learn/chunking-strategies/)
- YouTube search: `"RAG text chunking strategies explained comparison"`

**Where You'll See This Again**
1. Search engines segment and index web pages at the passage level (not full-page) for the same reason — Google's passage-based indexing improved search quality by matching queries to specific sections of pages.
2. Document processing in legal tech and compliance (contract analysis, regulatory review) chunks documents to find specific clauses or provisions relevant to a query.
3. Audio and video transcription systems chunk transcripts into segments for searchable video — same problem, different medium.

This matters because chunking determines the "resolution" of your retrieval system. Too coarse and you can't find specific information; too fine and you lose context. This is one of those decisions that seems minor but accounts for a huge share of RAG system quality in practice. Getting an intuition for good chunking here will serve you in any system that deals with unstructured text.

---

### Subproblem 3.3: Vector Storage and Similarity Search

**Logic Walkthrough**

You've generated embeddings for all your chunks. Now you need to store them and search them. This is the "database" part of RAG.

The core operation is: given a query embedding (a list of 768 floats), find the K stored embeddings that are most similar to it. "Similar" is measured by **cosine similarity** — the cosine of the angle between two vectors. A cosine similarity of 1.0 means identical direction (same meaning), 0.0 means orthogonal (unrelated), -1.0 means opposite.

For this project, you don't need a vector database. Here's why:

Vector databases (Pinecone, Weaviate, Qdrant, ChromaDB) are designed for millions or billions of vectors where brute-force comparison is too slow. Your research agent will have hundreds to maybe a few thousand chunks. At that scale, brute-force cosine similarity on NumPy arrays is instant (milliseconds). Adding a vector database adds dependency complexity with zero performance benefit.

The flow:
1. Store your chunks in a simple data structure: a list of dictionaries, each with `text`, `embedding` (the vector), and `metadata` (source, title, etc.).
2. When you need to retrieve: embed the query, then compute cosine similarity between the query vector and every stored vector.
3. Sort by similarity score, return the top K (start with K=5).
4. Feed those top K chunks into the model's context as retrieved information.

Implementing cosine similarity:
- With NumPy: `similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))` for a single pair. For computing against all stored vectors at once, stack them into a matrix and use vectorized operations.
- Or use `sklearn.metrics.pairwise.cosine_similarity` if you want a one-liner.

Key decisions you'll make:
- **K (number of results to retrieve)**: Start with 5. Too few and you miss relevant info; too many and you inject noise into the model's context. You can also use a similarity threshold (only return chunks above 0.7 similarity) instead of a fixed K.
- **Storage format**: For persistence between runs, save your chunks + embeddings to a JSON file (convert numpy arrays to lists for serialization). For a learning project, this is more than adequate.
- **Whether to use ChromaDB**: If you want a slightly more structured approach without going full cloud database, ChromaDB is an in-process vector store that runs locally. It handles storage and similarity search for you. It's a reasonable middle ground — but understand that it's doing the same math described above, just wrapped in an API.

Gotcha: Make sure your embeddings are normalized (unit length). Gemini's embedding model returns normalized vectors, but if you ever switch to another provider or compute your own, un-normalized vectors give misleading cosine similarity scores. You can normalize with `v / np.linalg.norm(v)`.

**Resources**
- Reading: [What is a Vector Database? — Pinecone Learning Center](https://www.pinecone.io/learn/vector-database/) — Read this for conceptual understanding, then deliberately don't use one for this step.
- YouTube search: `"cosine similarity vector search explained visual"`

**Where You'll See This Again**
1. Spotify's "Discover Weekly" and similar recommendation engines compute similarity between user preference vectors and song vectors to find matches — exact same math at massive scale.
2. Image search (Google Image Search, reverse image search) embeds images into vectors and does the same nearest-neighbor search to find visually similar images.
3. Plagiarism detection tools embed text passages and flag pairs with high cosine similarity — the concept applies to content deduplication at large media companies and academic institutions.

This matters because vector similarity search is the retrieval mechanism that powers most modern AI applications. Understanding that it's just dot products and sorting — not magic — demystifies a huge category of "AI-powered" products. It also grounds your RAG implementation: you know exactly what's happening when your agent "finds relevant context," which means you can debug and improve it systematically rather than treating it as a black box.

---

### Subproblem 3.4: The Retrieval Pipeline — Integrating RAG into Your Agent

**Logic Walkthrough**

Now you connect the pieces: your agent researches a topic, the fetched content gets chunked and embedded into the knowledge base, and when the model needs information, it retrieves from the knowledge base instead of (or in addition to) re-searching the web.

This changes your agent's architecture. You're adding a new tool — `search_knowledge_base(query: str)` — that searches your local vector store instead of the web. The model now has a choice: search the web for new information, or search the knowledge base for information it's already gathered.

The flow:
1. Modify your `fetch_page` handler: after fetching and extracting text, also chunk the text, embed the chunks, and store them in your vector store. The fetch tool now has a side effect — it populates the knowledge base.
2. Create a new tool: `search_knowledge_base` that takes a query string, embeds it, runs similarity search against stored vectors, and returns the top K chunks with their metadata.
3. Update your system prompt: tell the model about the knowledge base and when to use it vs. web search. Web search is for finding new sources; knowledge base search is for finding specific information within sources you've already read.
4. Let the agent run: it should now naturally search the web → fetch promising pages (which populates the KB) → search the KB for specific details → synthesize its answer.

Key decisions you'll make:
- **When to use KB vs. web search**: This is a prompt engineering decision. Guide the model: "Search the knowledge base first for information you may have already collected. Use web search to find new sources on aspects you haven't covered yet."
- **Context injection format**: When returning KB results to the model, include the chunk text plus metadata (source title, URL). Format it clearly so the model can cite sources properly: `[Source: "Article Title" - URL]\nContent: ...`
- **KB persistence**: Should the knowledge base persist across different research sessions? For a single research query, it resets each time. For a multi-session research tool, you'd save to disk. Start with per-session (in-memory only) for simplicity.

Gotcha: The model might over-rely on the knowledge base and under-search the web, or vice versa. This is an empirical tuning problem. Watch the tool call patterns across several queries and adjust your prompts. You might need to be more explicit: "Always start with 2-3 web searches to find sources. After fetching and reading at least 3 pages, use the knowledge base for follow-up details."

**Resources**
- Reading: [Retrieval-Augmented Generation for Knowledge-Intensive Tasks (original RAG paper)](https://arxiv.org/abs/2005.11401) — Read the abstract and introduction for the conceptual framework.
- YouTube search: `"RAG pipeline tutorial from scratch Python"`

**Where You'll See This Again**
1. Enterprise knowledge assistants (Glean, Guru, internal corporate search) are production RAG systems — they ingest company documents, chunk and embed them, and retrieve relevant context when employees ask questions.
2. Coding assistants like Cursor and GitHub Copilot use RAG to pull relevant code from your codebase into the model's context so it can write code that fits your project, not just generic code.
3. Medical diagnosis support tools retrieve from medical literature databases using the same embed-search-inject-generate pipeline, helping clinicians find relevant research for specific patient presentations.

This matters because RAG is the most practically important pattern in AI engineering today. It solves the core limitation of LLMs — they can only work with what's in their context window. By giving your agent a retrieval system, you've turned it from a model that only knows what it was trained on into a system that can learn and recall information dynamically. This is the architecture behind most real AI products being built right now.

---
---

## Part 4: Add Evals
**Time: 6–8 hours**
**Goal:** Build a system to measure whether your agent's research output is actually good. Learn how to define quality, create test cases, and use LLMs to judge LLM output.

By the end of this part, you'll have an evaluation suite that can score your agent's reports on multiple dimensions and catch regressions when you change the prompt or architecture.

---

### Subproblem 4.1: Defining Evaluation Criteria

**Logic Walkthrough**

Before you can measure quality, you need to define what "good" means for your research agent. This is harder than it sounds because research quality is multi-dimensional — a report can be well-sourced but poorly organized, or comprehensive but inaccurate.

Here's how to approach this systematically:
1. Generate 5-10 test reports from your agent across different topics (some factual, some opinion-heavy, some current events).
2. Read each one yourself and write down what's good and bad about it. Be specific: "It cited 3 sources but two were outdated" or "The summary was accurate but missed the main controversy."
3. From your notes, identify recurring dimensions of quality. For a research agent, these typically include:

   - **Relevance**: Does the report actually address the research topic? (Not as obvious as it sounds — agents drift.)
   - **Factual accuracy**: Are the claims supported by the cited sources?
   - **Source quality**: Are the sources credible? Recent? Diverse (not all from the same site)?
   - **Completeness**: Does the report cover the key aspects of the topic, or is it shallow?
   - **Coherence**: Is the report well-structured and readable?

4. For each dimension, define a rubric: what does a 1 look like? A 3? A 5? Be concrete.

Key decisions you'll make:
- **How many dimensions**: Start with 3-4. More than 5 becomes unwieldy and the evaluations get noisy. You can always add more later.
- **Scoring scale**: 1-5 is standard. Binary (pass/fail) is too coarse. 1-10 leads to inconsistent scoring (what's the difference between a 6 and a 7?).
- **Rubric specificity**: "1 = bad, 5 = good" is useless. "1 = report doesn't address the topic at all, 3 = addresses the topic but misses major aspects, 5 = thoroughly covers all key aspects with appropriate depth" — that's actionable.

Gotcha: The most common mistake is evaluating only the final output. You should also evaluate intermediate decisions — did the agent search for the right things? Did it fetch relevant pages? Did it save useful notes? These process evaluations help you debug *where* things go wrong, not just *that* they went wrong.

**Resources**
- Reading: [A Survey on Evaluation of Large Language Models (paper)](https://arxiv.org/abs/2307.03109) — Skim Sections 1-3 for the taxonomy of evaluation approaches.
- YouTube search: `"how to evaluate LLM output quality metrics"`

**Where You'll See This Again**
1. ML teams at every major company have evaluation frameworks — Anthropic has evals that run before every model release to check for capability regressions and safety properties.
2. Software testing in general follows this same pattern: define what correct behavior looks like (spec), create test cases, measure pass rates. Evals are just the LLM version of unit tests.
3. Peer review in academic publishing is the human version of this — reviewers evaluate papers against criteria (novelty, methodology, clarity) with rubrics. Your LLM-as-judge approach automates this.

This matters because without evaluation, you're flying blind. Every change you make to your agent — a prompt tweak, a new tool, different chunking — might help or hurt, and you won't know which unless you measure. Evals are what turn agent development from "vibes-based" into engineering. The discipline of defining quality criteria also forces you to think clearly about what your agent is actually supposed to do, which often reveals ambiguities in your original design.

---

### Subproblem 4.2: Building Test Cases and Running LLM-as-Judge Evaluations

**Logic Walkthrough**

Now you need test cases and an automated way to score them. The key insight: you can use an LLM to evaluate another LLM's output. This is called **LLM-as-judge**, and it's the standard approach for evaluating open-ended generation where there's no single "correct" answer.

The flow:
1. **Create a test suite**: 10-15 research queries spanning different types — factual ("What caused the 2008 financial crisis?"), current ("What is the current state of quantum computing?"), comparative ("How do React and Vue compare for large applications?"), controversial ("What are the arguments for and against universal basic income?"). Write these queries down with brief notes on what a good answer would cover.
2. **Run your agent on each query**: Save the full output — the structured report from your agent.
3. **Build the judge prompt**: This is a separate LLM call (use the same Gemini API) where you ask the model to evaluate the report. Your judge prompt includes: the original research query, the agent's report, your evaluation criteria and rubric, and instructions to output a score for each dimension with a brief justification.
4. **Parse the judge's response**: Use structured output (Pydantic/JSON schema) for the judge too — you want machine-readable scores, not a free-text essay about the report.
5. **Aggregate and analyze**: Compute average scores across your test suite. Look for patterns — maybe your agent consistently scores low on source diversity, or high on relevance but low on completeness.

Key decisions you'll make:
- **Judge model**: Ideally, the judge should be a stronger model than the one being evaluated. Since you're using Gemini 2.0 Flash for the agent, you could use the same model for judging (it works, just be aware of biases) or use a different model. For a learning project, same model is fine.
- **Judge prompt engineering**: The judge prompt is at least as important as your agent's prompt. Include your full rubric, give examples of what each score level looks like, and ask for justification (this improves scoring consistency). The justification also helps *you* understand why a report scored the way it did.
- **Reference answers vs. reference-free evaluation**: Reference answers (gold-standard reports you write yourself) improve evaluation accuracy but are expensive to create. Reference-free (just the query and the agent's output) is easier to scale. Start reference-free, consider adding 3-5 reference answers for your most important test cases.

Gotcha: LLM judges have biases — they tend to give higher scores to longer responses, more polished language, and responses that resemble their own generation style. Mitigate this by (1) asking the judge to evaluate each dimension independently rather than giving an overall score, (2) including calibration examples in the judge prompt, and (3) running the judge multiple times (3 runs per report) and averaging the scores to reduce variance. Also watch out for position bias: if the judge evaluates multiple reports at once, it may prefer whichever it sees first or last. Evaluate one report at a time.

**Resources**
- Reading: [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (paper)](https://arxiv.org/abs/2306.05685) — Focus on sections about judge agreement and bias.
- YouTube search: `"LLM as judge evaluation tutorial practical"`

**Where You'll See This Again**
1. AI model red-teaming uses LLM judges to automatically evaluate whether a model's responses violate safety policies — it's how companies scale safety testing across millions of prompts.
2. Content moderation at scale (YouTube, TikTok) increasingly uses LLM-based classifiers that are essentially judges — evaluating whether content violates guidelines using criteria-based prompts.
3. Automated code review tools (like AI-powered PR reviewers) are LLM judges applied to code — they evaluate pull requests against quality criteria and provide scored feedback.

This matters because evaluation is how you make your agent reliable enough to actually use. Running evals after every change is what separates "I think this works" from "I know this works." The LLM-as-judge pattern is also one of the most versatile tools in AI engineering — you'll use it for evaluating RAG quality, agent behavior, content generation, and basically any task where the output is too complex for rule-based checking. Building this now gives you a capability you'll apply to every AI project going forward.

---
---

## Part 5: Two Agents + Orchestrator
**Time: 8–10 hours**
**Goal:** Split your monolithic agent into a Researcher agent and a Synthesizer agent, coordinated by an Orchestrator. Learn multi-agent coordination and context passing.

By the end of this part, your system has specialized agents that are better at their individual tasks than one generalist agent, and an orchestrator that manages the workflow.

---

### Subproblem 5.1: Agent Abstraction — Making Agents Modular

**Logic Walkthrough**

Right now your agent is one big script — the API call, the tool loop, the prompt, the tool handlers are all tangled together. Before you can have multiple agents, you need a clean abstraction: an Agent class (or function) that encapsulates everything an agent needs and exposes a simple interface.

Think of an agent as a self-contained worker. It has:
- **Identity**: a system prompt that defines who it is and what it does.
- **Capabilities**: a set of tools it can use.
- **A run method**: takes an input (a task/query), runs its internal loop, and returns an output (a result).

The flow:
1. Refactor your existing code into an `Agent` class. Constructor takes: system prompt, list of tool definitions, list of tool handlers (or a mapping from tool name to handler function), and model config (temperature, etc.).
2. The `run(input: str) -> str` (or `-> dict`) method encapsulates the entire agent loop from Part 1 — send message, check for tool calls, execute tools, loop until done, return final response.
3. Create your first two agents by instantiation:
   - **Researcher**: has web search, page fetch, save notes, search KB tools. System prompt focuses on finding and gathering information.
   - **Synthesizer**: has search KB and get notes tools (read-only access to the knowledge base). System prompt focuses on organizing information into a structured report. No web search — it only works with what the Researcher found.

Key decisions you'll make:
- **Shared state vs. isolated state**: The Researcher populates the knowledge base; the Synthesizer reads from it. This is shared state. The simplest approach: both agents reference the same knowledge base object passed in at construction. No databases, no message queues — just a shared Python object.
- **Input/output format**: What does the Researcher return? What does the Synthesizer accept? Define a clear contract. The Researcher might return a summary of what it found + the populated KB. The Synthesizer receives the research topic + access to the KB and returns the final structured report.
- **How much tool overlap**: The Synthesizer should NOT have search or fetch tools — its job is synthesis, not research. Limiting tools forces specialization, which improves output quality. This is a design choice: constraining what an agent can do makes it better at what it should do.

Gotcha: The refactoring itself is the hardest part of this step. You'll discover that your original code had implicit assumptions — maybe the notes dictionary was a global variable, maybe the system prompt was hardcoded. The act of making it modular will expose these and force you to clean them up. This is normal and valuable.

**Resources**
- Reading: [The Architecture of AI Agents — Harrison Chase (LangChain)](https://blog.langchain.dev/what-is-an-agent/) — Read for the conceptual framework of agent components, then build your own.
- YouTube search: `"multi agent system architecture design patterns AI"`

**Where You'll See This Again**
1. Microservices architecture in software engineering follows the same principle — break a monolith into specialized services with clear interfaces that communicate through defined contracts.
2. Assembly lines in manufacturing: each station (agent) does one thing well and passes the work product to the next station. Specialization improves quality and throughput.
3. Engineering teams themselves operate this way — designers, developers, QA testers each have their role and tools, coordinated by a project manager (the orchestrator).

This matters because clean abstractions are what make systems extensible. With a well-designed Agent class, adding a new agent in Step 6 is trivial — you just instantiate with a different prompt and tools. Without it, every new agent means copy-pasting and modifying a tangled script. This is also the moment where your project goes from "a script that calls an API" to "a system with architecture" — and that's the difference between a demo and something you'd put on a resume.

---

### Subproblem 5.2: The Orchestrator — Coordinating Multiple Agents

**Logic Walkthrough**

The orchestrator is the conductor of the orchestra. It doesn't do research or write reports — it decides who works when, passes context between agents, and manages the overall workflow.

For a two-agent system, the orchestrator can be simple — essentially a sequential pipeline:

```
1. Receive research topic from user
2. Send topic to Researcher agent
3. Researcher runs its tool loop, gathers information, populates knowledge base
4. Receive Researcher's output (summary of what was found)
5. Send topic + Researcher's summary to Synthesizer agent
6. Synthesizer queries the knowledge base, produces structured report
7. Return final report to user
```

But even this simple orchestration involves real decisions:

The flow:
1. Build the orchestrator as a function (or class) that takes the user's research query and returns the final report.
2. It creates the shared knowledge base, initializes both agents with access to it, runs them in sequence, and returns the Synthesizer's output.
3. Add error handling: if the Researcher fails or finds nothing, the orchestrator should handle that — maybe retry with a different search strategy, or return a message saying the topic couldn't be adequately researched.

Key decisions you'll make:
- **What context to pass between agents**: The Researcher's full output (including all notes) might be too large or noisy. You could pass a condensed summary. Or you could rely entirely on the shared knowledge base and just tell the Synthesizer "research has been completed, use the knowledge base." Test both approaches.
- **Should the orchestrator be an LLM or deterministic code?** For a two-agent sequential pipeline, deterministic code (just Python functions) is the right choice. The overhead of using an LLM for orchestration only pays off when the workflow requires dynamic decisions — like deciding whether more research is needed or whether to adjust the plan. You'll explore LLM-as-orchestrator in Step 6.
- **Researcher output validation**: Before passing to the Synthesizer, check if the Researcher actually found meaningful content. If the KB has fewer than 3 chunks, maybe the research wasn't sufficient. This is a simple quality gate that prevents the Synthesizer from trying to write a report with no data.

Gotcha: The biggest failure mode in multi-agent systems is "context loss" — information that one agent found doesn't make it to the next agent. This usually happens when the context passing is too compressed (you summarized away the important details) or when the knowledge base isn't properly shared (each agent got its own copy). Test by verifying that the Synthesizer's report contains specific facts that only exist in pages the Researcher fetched.

**Resources**
- Reading: [Multi-Agent Systems for LLM Applications — Microsoft AutoGen docs](https://microsoft.github.io/autogen/stable/) — Read the "Concepts" section for orchestration patterns. Then build your own — don't use AutoGen itself.
- YouTube search: `"multi agent orchestration pattern LLM explained"`

**Where You'll See This Again**
1. CI/CD pipelines are orchestrators — they coordinate a sequence of agents (build, test, deploy) where each step's output feeds into the next, with quality gates between stages.
2. MapReduce and similar distributed computing frameworks follow the same pattern: an orchestrator distributes work to mappers (researchers), collects results, then passes them to reducers (synthesizers).
3. Movie production has a producer (orchestrator) who coordinates specialized teams (writing, filming, editing, scoring) — each team does their part and hands off to the next.

This matters because orchestration is what turns individual agents into a system. A Researcher alone is just your old single agent with a different prompt. A Synthesizer alone has nothing to synthesize. The orchestrator is what creates the workflow where 1 + 1 > 2 — specialized agents coordinated well outperform a single generalist agent. Learning to design orchestration flows is also directly applicable to your work — any automated workflow you build (at the Fed or elsewhere) is fundamentally an orchestration problem.

---

### Subproblem 5.3: Error Handling and Reliability in Multi-Agent Systems

**Logic Walkthrough**

In a single-agent system, an error means one thing broke. In a multi-agent system, errors cascade — the Researcher fails, the KB is empty, the Synthesizer hallucinates a report from nothing, and the user gets confident-sounding garbage. You need to design for failure at every handoff point.

The flow:
1. **Identify failure points**: Researcher fails to find relevant results. Researcher fetches pages that are empty/garbage. KB has content but it's irrelevant to the query. Synthesizer produces a report that doesn't cite sources. Any API call can timeout or error.
2. **Add validation at each handoff**: After the Researcher runs, verify the KB has sufficient content (check chunk count and maybe run a quick relevance check — embed the original query and check similarity against stored chunks). After the Synthesizer runs, verify the output has the required structure (title, findings, sources).
3. **Build retry logic**: If the Researcher's first pass is insufficient, have the orchestrator retry with a modified search strategy (e.g., rephrase the topic, add subtopics). Limit retries to 2-3 attempts.
4. **Graceful degradation**: If after retries the research is still insufficient, return a partial report with a notice that the topic couldn't be fully covered, rather than returning nothing or hallucinating.

Key decisions you'll make:
- **How to detect "insufficient research"**: Chunk count is a rough proxy. A better approach: embed the research query, compute average similarity against KB chunks, and require a minimum threshold. If the KB has 50 chunks but none are above 0.5 similarity to the query, the research went off-track.
- **Timeout budgets**: Set an overall timeout for the full pipeline (e.g., 2 minutes). Allocate sub-budgets: Researcher gets 90 seconds, Synthesizer gets 30 seconds. If the Researcher times out, pass whatever it has to the Synthesizer rather than failing entirely.
- **Logging**: Log every agent call, tool call, and handoff with timestamps and payload summaries. When something goes wrong (and it will), you need to reconstruct what happened. This isn't just debugging — it's observability, and it's critical for any system with multiple moving parts.

Gotcha: The sneakiest failure mode is "silent degradation" — the system produces a complete, well-formatted report that contains subtly wrong or irrelevant information. No error is thrown; the output looks fine. This is why you built evals in Step 4. Run your eval suite after adding multi-agent to check if report quality improved, stayed the same, or degraded. If the multi-agent version scores worse, that's a signal that context is being lost in the handoffs.

**Resources**
- Reading: [Designing Fault-Tolerant AI Systems — Netflix Tech Blog](https://netflixtechblog.com/) — Search for their posts on resilience patterns. The principles apply directly to agent systems.
- YouTube search: `"error handling retry patterns distributed systems"`

**Where You'll See This Again**
1. Distributed microservice systems (Netflix, Uber, Amazon) all have to handle cascading failures — a single service going down can't take down the whole platform. Circuit breakers, retries, and fallbacks are standard patterns.
2. Self-driving cars have redundant systems specifically because single-point failures in a multi-component pipeline are dangerous — if LIDAR fails, the system falls back to cameras and radar rather than stopping.
3. Financial trading systems have multi-layer validation before executing trades — a bad input from one component can't cause a catastrophic trade. Same principle as your quality gates.

This matters because reliability is what separates a learning project from something useful. Anyone can build a multi-agent system that works on the happy path. The engineering challenge — and the skill that employers value — is building one that handles failure gracefully. The observability practices you build here (logging, validation, quality gates) are also industry-standard skills that apply to any production system.

---
---

## Part 6: Full Multi-Agent System
**Time: 10–14 hours**
**Goal:** Build the complete research agent: Planner → Researcher(s) → Synthesizer → Reviewer, with an LLM-powered orchestrator that can adapt the workflow dynamically.

By the end of this part, you'll have a system where an LLM plans the research approach, multiple research tasks execute (potentially in parallel), results are synthesized into a report, and a reviewer agent evaluates and suggests improvements.

---

### Subproblem 6.1: The Planner Agent

**Logic Walkthrough**

The Planner's job is to take a research topic and break it into specific research tasks. Instead of sending one vague query to the Researcher, the Planner analyzes the topic and generates a research plan.

For example, given "What is the current state of nuclear fusion energy?", the Planner might produce:
- Task 1: Search for the latest breakthroughs in nuclear fusion (2024-2025)
- Task 2: Research the major fusion companies and their approaches (Commonwealth Fusion, TAE, etc.)
- Task 3: Find current government funding and policy for fusion energy
- Task 4: Look for expert assessments on timeline to commercial fusion

This decomposition means each Researcher invocation has a focused, specific goal — which produces better results than one Researcher trying to cover everything at once.

The flow:
1. The Planner is an agent with no tools — it's pure reasoning. It receives the user's topic and returns a structured plan: a list of research tasks, each with a focused query and a description of what to look for.
2. Use structured output to force the plan into a parseable format: a list of task objects, each with `query`, `description`, and `priority`.
3. The system prompt instructs the Planner to: decompose the topic into 3-5 non-overlapping subtopics, prioritize tasks by importance, and write search queries that are specific enough to yield good results.

Key decisions you'll make:
- **Number of subtasks**: 3-5 is the sweet spot. Fewer than 3 means you haven't really decomposed the topic. More than 5 means the subtasks are probably too granular and will produce overlapping research.
- **Plan quality control**: The Planner might produce bad plans — overlapping tasks, irrelevant subtopics, or tasks that are too broad. You can add a quick validation step: check that the tasks are distinct (low embedding similarity between task queries) and relevant (high similarity to the original topic).
- **Static vs. dynamic planning**: A static plan is created once and executed. A dynamic plan can be revised as research progresses — if the Researcher finds that Task 2 is a dead end, the Planner can revise. Start with static (much simpler). Dynamic planning is a meaningful upgrade but adds complexity.

Gotcha: LLMs are decent at decomposing familiar topics but can produce shallow or formulaic plans for niche topics. "What are the key facts? What are the different perspectives? What are the implications?" is a generic plan that works for anything but isn't actually useful. Your system prompt needs to push for specificity: "Each task should target different sources of information, not just different angles on the same search results."

**Resources**
- Reading: [Plan-and-Solve Prompting for LLMs (paper)](https://arxiv.org/abs/2305.04091) — Read abstract and method section for how planning improves complex task performance.
- YouTube search: `"AI agent planning task decomposition strategy"`

**Where You'll See This Again**
1. Project management tools (Jira, Linear, Asana) formalize the same pattern — a project manager breaks a large initiative into epics and stories before assigning to developers. The Planner is the AI project manager.
2. Divide-and-conquer algorithms in CS are the computational version — merge sort splits the problem, solves sub-problems independently, then combines. Your Planner splits, Researchers solve, Synthesizer combines.
3. Military operations planning decomposes a mission into phases and objectives, assigns specialized units to each, and coordinates execution — the stakes are higher but the pattern is identical.

This matters because planning is what separates a sophisticated agent system from a brute-force one. Without planning, you're relying on a single model call to cover all aspects of a complex topic — which it inevitably does poorly. Planning distributes cognitive load the same way good software architecture distributes computational load. It's also a deeply transferable concept: any complex task (building software, managing a project, writing a thesis) benefits from explicit decomposition before execution.

---

### Subproblem 6.2: Parallel Research Execution

**Logic Walkthrough**

The Planner has produced 4 research tasks. You could run them sequentially — Task 1, then Task 2, then Task 3, then Task 4. But each task involves API calls (search, fetch) that spend most of their time waiting for network responses. Running them in parallel can cut your research time by 3-4x.

Python's `asyncio` is the right tool here. You're not doing CPU-intensive work — you're waiting for API responses. This is the classic use case for async/concurrent execution.

The flow:
1. Make your agent's `run` method async. This means making your API calls and HTTP requests async as well (use `aiohttp` for web requests, and the async versions of the Gemini SDK calls if available, or run sync calls in an executor).
2. In the orchestrator, instead of calling Researcher agents sequentially, use `asyncio.gather()` to run multiple Researcher instances concurrently.
3. Each Researcher runs independently but writes to the shared knowledge base. Since they're running concurrently, you need basic thread safety — use a lock around KB writes. At the scale you're operating (4-5 concurrent agents), a simple `asyncio.Lock` is sufficient.
4. After all Researchers complete, the KB contains all gathered information, and the Synthesizer can proceed.

Key decisions you'll make:
- **Full async rewrite vs. threading**: Pure `asyncio` is cleaner but requires async versions of all your library calls. An alternative is `concurrent.futures.ThreadPoolExecutor` — wrap each Researcher call in a thread. This works with synchronous code (no rewrite needed) and is perfectly fine at this scale. Start here if async feels like too much refactoring.
- **Concurrent KB writes**: Multiple Researchers writing to the same knowledge base simultaneously. The simplest safe approach: each Researcher accumulates its chunks locally, then writes them all to the KB in a single batch after completing. This avoids concurrent write issues entirely.
- **Error isolation**: If one Researcher fails, the others should continue. Use `asyncio.gather(return_exceptions=True)` or wrap each call in a try/except. A failed research task reduces coverage but shouldn't crash the pipeline.

Gotcha: Rate limiting. If 4 Researchers are all making API calls concurrently, you'll hit the Gemini free tier rate limit much faster. Add a simple semaphore or rate limiter that limits concurrent API calls to 2-3 across all agents. This slightly reduces parallelism but keeps you within API limits.

**Resources**
- Reading: [Python asyncio documentation — Tasks and Coroutines](https://docs.python.org/3/library/asyncio-task.html)
- YouTube search: `"Python asyncio gather concurrent tasks tutorial"`

**Where You'll See This Again**
1. Web scrapers and crawlers (Scrapy, etc.) parallelize HTTP requests for the same reason — most time is spent waiting for servers, so concurrent requests dramatically improve throughput.
2. MapReduce (Hadoop, Spark) distributes work across many workers processing in parallel — your parallel Researchers are a mini MapReduce where each Researcher is a mapper.
3. Modern CI/CD pipelines run independent test suites in parallel (unit tests, integration tests, linting) — same pattern of independent tasks that can execute concurrently and whose results are aggregated afterward.

This matters because real-world agent systems need to be fast enough to be useful. A research agent that takes 10 minutes because it serially runs 5 research tasks is a demo; one that completes in 2-3 minutes because it parallelizes is a tool. Understanding concurrent execution also prepares you for production AI systems where latency directly impacts user experience and cost.

---

### Subproblem 6.3: The Reviewer Agent — Critique and Improvement Loop

**Logic Walkthrough**

The Reviewer reads the Synthesizer's report and evaluates it — finding gaps, flagging unsupported claims, and suggesting improvements. This is essentially your eval system from Step 4 built into the agent pipeline itself.

The conceptual shift: in Step 4, you ran evals after the fact to measure quality. Now the evaluation happens *during* the pipeline, and the system can self-correct based on the feedback.

The flow:
1. The Reviewer agent receives: the original research topic, the Synthesizer's report, and the research plan from the Planner.
2. It evaluates the report against criteria similar to your evals: Does it address all subtopics from the plan? Are claims supported by cited sources? Are there obvious gaps?
3. It returns structured feedback: a list of issues found, each with a severity (minor/major) and a suggested improvement.
4. The orchestrator decides what to do with the feedback:
   - If all issues are minor or there are no issues → return the report as final.
   - If there are major issues → send the feedback to the Synthesizer for revision, OR send specific gaps back to the Researcher for more investigation.

Key decisions you'll make:
- **How many review cycles**: The Reviewer could generate feedback, the Synthesizer could revise, the Reviewer could review again, and so on. Cap this at 1-2 revision cycles — diminishing returns hit fast, and each cycle costs API calls and time.
- **Reviewer tools**: The Reviewer should have access to the KB (to verify that claims in the report actually have support in the gathered content) but NOT to web search or fetch. The Reviewer reviews what was found, not finds new things. If the Reviewer identifies a gap that requires more research, that goes back to the orchestrator, which dispatches a new Researcher task.
- **Structured feedback format**: The Reviewer's output should be structured (JSON/Pydantic): a list of issues, each with `type` (gap, unsupported_claim, factual_concern), `description`, `severity`, and `suggestion`. This makes the orchestrator's routing logic clean — if any issue has severity "major", trigger a revision cycle.

Gotcha: The Reviewer might be too harsh or too lenient. Too harsh and you get infinite revision loops that never converge. Too lenient and the review step adds latency without improving quality. Calibrate by testing: run 10 reports through the Reviewer and check whether its feedback is actionable and accurate. Your eval system from Step 4 should be your ground truth — if the Reviewer says a report is good but your evals say it's bad, your Reviewer needs recalibration.

**Resources**
- Reading: [Constitutional AI: Harmlessness from AI Feedback (paper)](https://arxiv.org/abs/2212.08073) — Read the introduction for the concept of AI self-critique and iterative refinement. The approach of having models critique and revise their own output originates here.
- YouTube search: `"AI agent self-critique feedback loop pattern"`

**Where You'll See This Again**
1. Code review workflows in software engineering are exactly this pattern — a reviewer (human or AI) reads the output, provides structured feedback, and the author revises. GitHub's PR review process is a review-revise loop.
2. Editorial processes at publications: a writer submits, an editor reviews, the writer revises, the editor approves. Your Reviewer → Synthesizer loop mirrors this.
3. Reinforcement Learning from Human Feedback (RLHF) uses a critique model to evaluate and improve another model's outputs — the fundamental training approach behind ChatGPT, Claude, and other aligned models uses this review pattern.

This matters because the ability to self-evaluate and improve is what makes an agent system robust. Without review, errors in the research or synthesis go undetected and land in the final report. The review loop is also your agent's quality guarantee — and it connects directly back to the eval criteria you defined in Step 4. From a systems perspective, you've just built a feedback loop, which is the most powerful pattern in both engineering and biology. Systems without feedback loops can't improve; systems with them converge toward quality.

---

### Subproblem 6.4: LLM-Powered Orchestration — Dynamic Workflow Control

**Logic Walkthrough**

In Step 5, your orchestrator was deterministic code: always run Researcher then Synthesizer. Now you upgrade to an LLM-powered orchestrator that can make dynamic decisions about the workflow.

The LLM orchestrator is itself an agent — it has tools, but its tools are "run the Planner," "run a Researcher," "run the Synthesizer," "run the Reviewer." It decides which agent to call next based on the current state of the research.

This allows workflows like:
- Planner creates tasks → Researchers execute → Orchestrator notices Task 3 failed → Orchestrator creates an alternative task → One more Researcher runs → Synthesizer produces report → Reviewer finds a gap → Orchestrator sends gap to a Researcher → Researcher finds more info → Synthesizer revises → Reviewer approves → Done.

That workflow was never hardcoded — the LLM decided each step based on what it observed.

The flow:
1. Define "meta-tools" for the orchestrator: `run_planner(topic) -> plan`, `run_researcher(task) -> summary`, `run_synthesizer(topic, plan) -> report`, `run_reviewer(topic, report, plan) -> feedback`.
2. The orchestrator's system prompt describes the available agents and the general research workflow, but allows flexibility: "You coordinate a research team. Typically you plan first, then research, then synthesize, then review. But you can adapt — if research is insufficient, research more. If the review finds gaps, either research more or ask the synthesizer to revise."
3. The orchestrator runs in a tool-use loop just like any agent. But its "tools" spawn and run other agents. It's agents all the way down.
4. Set a hard limit on total agent calls (e.g., 15-20) to prevent infinite loops.

Key decisions you'll make:
- **How much autonomy to give the orchestrator**: More autonomy means more dynamic workflows but also more potential for waste (unnecessary agent calls, circular loops). Start with a semi-structured approach: the system prompt defines a default workflow but allows deviations when justified.
- **State management**: The orchestrator needs to track what's been done — which tasks have been researched, what the current report looks like, what feedback was given. Pass this as a growing context in the conversation history. This is where context window management becomes important.
- **When to use LLM orchestration vs. code orchestration**: Not every workflow decision needs an LLM. "Run Planner first" is always the right first step — no LLM needed. "Should we research more or synthesize now?" — that's judgment, and an LLM adds value. Use deterministic code for decisions that are always the same, and LLM calls for decisions that depend on context.

Gotcha: The meta-orchestrator pattern (LLM that calls agents that are also LLMs) can get expensive fast. Each orchestrator decision is an API call. Each agent it spawns makes multiple API calls. A single research query could trigger 30-50 API calls across the whole system. On Gemini's free tier, this might hit rate limits. Be strategic about where LLM decisions add value vs. where simple if/else logic works fine.

**Resources**
- Reading: [Orchestrating Agents: Routines and Handoffs — OpenAI Cookbook](https://cookbook.openai.com/examples/orchestrating_agentic_loops) — Adapt the concepts to your own system.
- YouTube search: `"LLM orchestrator multi agent coordination dynamic workflow"`

**Where You'll See This Again**
1. Kubernetes is an orchestrator for containers the same way your LLM orchestrator manages agents — it monitors health, makes scaling decisions, handles failures, and routes traffic dynamically.
2. Air traffic control dynamically orchestrates aircraft (agents with independent goals) in shared airspace, adjusting plans in real-time based on conditions — same principle of dynamic coordination.
3. Operating systems are orchestrators for processes — scheduling, resource allocation, interrupts, and context switching are all dynamic orchestration decisions.

This matters because dynamic orchestration is the cutting edge of AI agent development. Static pipelines work for predictable workflows, but real research is unpredictable — some topics require more investigation, some sources are dead ends, some subtopics turn out to be more important than expected. An LLM orchestrator that can adapt the workflow based on what's actually happening produces significantly better results than a rigid pipeline. This is also the architectural pattern behind the most advanced agent systems being built today — it's exactly what companies are hiring AI engineers to build.

---
---

## Summary: The Completed System

After all 6 parts, your system looks like this:

```
User
  │
  ▼
Orchestrator (LLM-powered)
  │
  ├──→ Planner Agent
  │     └── Decomposes topic into research tasks
  │
  ├──→ Researcher Agents (parallel)
  │     ├── Web search tool
  │     ├── Page fetch tool
  │     ├── Note-taking tool
  │     └── Populate shared Knowledge Base
  │
  ├──→ Synthesizer Agent
  │     ├── Query Knowledge Base
  │     └── Produce structured report
  │
  └──→ Reviewer Agent
        ├── Evaluate report quality
        └── Flag gaps and issues
              │
              └──→ (back to Orchestrator for revision cycle)
```

**Total estimated time: 50–70 hours**

Each part builds on the last. Each subproblem introduces exactly one new concept. No step requires knowledge from a future step. You can stop at any part and have a working, useful system — Part 1 alone is a functional research agent. Each subsequent part makes it better.
