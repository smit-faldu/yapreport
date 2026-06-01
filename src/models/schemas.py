from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

class GraphState(TypedDict):
    raw_news:      str
    past_topics:   str
    curated_news:  str
    target_url:    str
    scraped_text:  str
    draft_script:  str  # Raw script from write_agent (before review)
    final_script:  str  # Polished script after review_agent
    social_content: str  # To hold the generated social media copy

class DialogueLine(BaseModel):
    speaker: str = Field(description="Trump or Elon")
    line:    str = Field(description="The humorous dialogue line")
    image_query: Optional[str] = Field(description="A highly specific 2-4 word DuckDuckGo image search query to visually represent the joke in this line. E.g., 'nasa roket crash', 'starit of hormoz', 'mark zuckerberg alien'. Use None if no image is needed.")

class Script(BaseModel):
    dialogue: List[DialogueLine]

class CuratedStory(BaseModel):
    headline: str = Field(description="The exact headline")
    who: str = Field(description="Specific real names of people/organizations")
    what_happened: str = Field(description="Exactly what occurred")
    url: str = Field(description="The exact URL of the story from the raw news")

# NEW: Schema for the Social Media Agent
# NEW: Schema for the Social Media Agent
class SocialMetadata(BaseModel):
    instagram_caption: str = Field(description="A medium-length, SEO-driven caption for Instagram including hashtags. No character limit. Must include #reel, #reels, and #news.")
    facebook_caption: str = Field(description="A short caption for Facebook. The ENTIRE string including text and hashtags MUST strictly be 255 characters or less. Must include #reel, #reels, and #news.")
    youtube_title: str = Field(description="A short, punchy, SEO-optimized title for YouTube Shorts. Must be under 70 characters and contain high-volume keywords.")
    youtube_description: str = Field(description="A longer, highly SEO-optimized description specifically for the YouTube Shorts description box, including hashtags at the end.")
    tags: List[str] = Field(description="A list of 5 to 10 highly relevant SEO tags (plain strings, no # prefix) for the video. E.g. ['trump news', 'elon musk', 'yap report'].")