from typing import TypedDict, List
from pydantic import BaseModel, Field

class GraphState(TypedDict):
    raw_news:      str
    curated_news:  str
    target_url:    str
    scraped_text:  str
    draft_script:  str  # Raw script from write_agent (before review)
    final_script:  str  # Polished script after review_agent
    social_content: str  # To hold the generated social media copy

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

# NEW: Schema for the Social Media Agent
class SocialMetadata(BaseModel):
    universal_caption: str = Field(description="A medium-length, SEO-driven caption with hashtags for Instagram and Facebook Reels only.")
    youtube_title: str = Field(description="A short, punchy, SEO-optimized title for YouTube Shorts. Must be under 70 characters and contain high-volume keywords.")
    youtube_description: str = Field(description="A longer, highly SEO-optimized description specifically for the YouTube Shorts description box.")