from typing import TypedDict, List
from pydantic import BaseModel, Field

class GraphState(TypedDict):
    raw_news:     str
    curated_news: str
    target_url:   str
    scraped_text: str
    final_script: str

class DialogueLine(BaseModel):
    speaker: str = Field(description="Trump or Elon")
    line:    str = Field(description="The humorous dialogue line")

class Script(BaseModel):
    dialogue: List[DialogueLine]

class CuratedStory(BaseModel):
    headline: str = Field(description="The exact headline")
    who: str = Field(description="Specific real names of people/organizations")
    what_happened: str = Field(description="Exactly what occurred")
    url: str = Field(description="The exact URL of the story from the raw news")
