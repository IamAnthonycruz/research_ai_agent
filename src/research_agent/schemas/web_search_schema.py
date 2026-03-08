from typing import List

from pydantic import BaseModel, HttpUrl

class Sources(BaseModel):
    title: str
    url: HttpUrl
class WebSearchResponse(BaseModel):
    title: str
    summary: str
    key_findings: List[str]
    sources: List[Sources]