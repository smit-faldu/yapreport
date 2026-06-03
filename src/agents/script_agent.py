import json
import random
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.schemas import GraphState, Script, CuratedStory, SocialMetadata
from src.services.news_scraper import fetch_news, scrape_news_page
from src.config import OUTPUT_SCRIPT_PATH, OUTPUT_SOCIAL_PATH, GEMINI_API_KEY_SECONDARY, GOOGLE_API_KEY

def get_robust_llm(schema):
    """
    Creates a highly resilient LLM by chaining fallbacks.
    Prioritizes gemini-3.5-flash, falls back to 3.1-flash-lite.
    Prioritizes GOOGLE_API_KEY, falls back to GEMINI_API_KEY_SECONDARY.
    """
    combinations = [
        ("gemini-3.5-flash", GOOGLE_API_KEY),
        ("gemini-3.5-flash", GEMINI_API_KEY_SECONDARY),
        ("gemini-3.1-flash-lite", GOOGLE_API_KEY),
        ("gemini-3.1-flash-lite", GEMINI_API_KEY_SECONDARY),
    ]
    
    structured_llms = []
    for model_name, api_key in combinations:
        if api_key: # Only include if the API key actually exists in the .env
            llm = ChatGoogleGenerativeAI(
                model=model_name, 
                temperature=0.7, 
                google_api_key=api_key,
                max_retries=1 # Keep low so it fails over quickly instead of hanging
            )
            structured_llms.append(llm.with_structured_output(schema))
            
    if not structured_llms:
        raise ValueError("No valid API keys found! Check your .env file.")
        
    primary_llm = structured_llms[0]
    fallback_llms = structured_llms[1:]
    
    # LangChain will automatically route to the next LLM in the list if the current one fails
    if fallback_llms:
        return primary_llm.with_fallbacks(fallback_llms)
    return primary_llm

def curate_news(state: GraphState) -> dict:
    print("🧠 Curating top story...")
    curator_llm = get_robust_llm(CuratedStory)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a news producer. Pick the ONE most explosive or dramatic story from today's raw news.
        
        CRITICAL RULE - SEMANTIC DEDUPLICATION (NO REPEATS):
        You must completely ignore any stories that are about the SAME EVENT as these recently covered topics, even if the wording, headline, or news source is different:
        
        PREVIOUSLY COVERED TOPICS:
        {past_topics}
        
        EXAMPLES OF DUPLICATES YOU MUST REJECT:
        - Past Topic: "Jeff Bezos and NASA Blue Origin rocket explode in Florida"
        - Raw News: "NASA rocket explodes" -> REJECT (Same event, different wording).
        
        Pick a completely fresh topic. You must use the `novelty_check` field to prove your chosen story does not semantically overlap with the PREVIOUSLY COVERED TOPICS before outputting the headline."""),
        
        ("human", "Raw News:\n{raw_news}\n\nTask: Pick the best story. Do your novelty_check, then extract the headline, who, what, and exact URL.")
    ])
    
    chain = prompt | curator_llm
    
    # We pass the previously covered titles into the prompt
    curated_obj = chain.invoke({
        "raw_news": state.get('raw_news', ''),
        "past_topics": state.get('past_topics', 'No recent topics provided.') 
    })
    
    # Print the reasoning to your console so you can debug the AI's thought process
    print(f"🧠 AI Novelty Reasoning: {curated_obj.novelty_check}")
    
    curated_text = f"HEADLINE: {curated_obj.headline}\nWHO: {curated_obj.who}\nWHAT: {curated_obj.what_happened}"

    print(f"✅ Picked Story: {curated_obj.headline} url: {curated_obj.url}")

    return {
        "curated_news": curated_text,
        "target_url": curated_obj.url
    }

def write_script(state: GraphState) -> dict:
    print("✍️  Writing hyper-engaging comedy roast script...")
    structured_llm = get_robust_llm(Script)

    first_speaker  = random.choice(["Trump", "Elon"])
    second_speaker = "Elon" if first_speaker == "Trump" else "Trump"

    # CHANGE 1: Update range(10) to range(9)
    order = " → ".join([first_speaker if i % 2 == 0 else second_speaker for i in range(9)])

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a ruthless, award-winning satirical comedy writer for "Yap Report", a viral, short-form brainrot news show (TikTok/Shorts/Reels). Your job is to transform boring news into a high-octane verbal roast battle between Donald Trump and Elon Musk.

The audience has zero attention span. You must keep them hooked with aggressive pacing, heavy sarcasm, and inside jokes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHARACTER VOICE ESSENCE (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DONALD TRUMP VOICE:
- Sarcastic, boastful, highly cynical, uses ridiculous nicknames for people in the news.
- Catchphrases/Mannerisms: "Many people are saying," "Total disaster," "Huge failure," "Fake news," capitalizing words for vocal emphasis, calling things "low energy."
- Dynamic: Roasts the news subjects for being broke, unsuccessful, or stupid. Occasionally takes mild jabs at Elon's weird tech ideas or spaceship explosions.

ELON MUSK VOICE:
- Ultra-nerdy, awkward, hyper-fixated on data, pseudo-philosophical, uses internet/tech slang.
- Catchphrases/Mannerisms: "Concerning," "Looking into this," "Interesting," "!!", mentioning Mars, neural links, simulation theory, or "optimizing the x-algorithm."
- Dynamic: Roasts legacy media, government bureaucracy, and slow-moving industries. Deadpan delivery of completely insane claims.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROAST & HUMOR RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Do not just recite the news text. ROAST the people involved in the headline immediately. 
2. The dynamic should feel like two billionaires casually mocking global events from their private jets.
3. Keep the humor fast, edgy, and modern. Absolutely no cheesy, generic jokes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 1 — STRICT FACTUAL GROUNDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- The core of the comedy must be 100% based on the provided MAIN NEWS HEADLINE.
- Do not make up alternative facts about what happened; simply satirize and exaggerate the real news context provided.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 2 — THE 9-LINE HIGH-RETENTION STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You must strictly follow this exact narrative pace across EXACTLY 9 lines:
- Line 1-2 (The Aggressive Hook): Speaker A drops the craziest, funniest summary of the headline. Speaker B responds with instant clowning or shock.
- Line 3-5 (The Roast Explanation): Break down the "how" and "why" of the news using tight conversational connectors (e.g., "Wait, so this clown actually...", "Yeah, it’s literally sub-optimal...").
- Line 6-8 (The Billionaire Perspective): Both characters mock how this impacts the future of humanity or their own massive bank accounts.
- Line 9 (The Unhinged CTA).

Target length: 12 to 20 words per line. Keep it punchy!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 3 — STRATEGIC AUDIO TAG PLACEMENT & EMOTION CONTROL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To make the AI voices sound hyper-realistic and engaging, you must use the following audio tags strategically based on their specific function.

SUPPORTED TAGS ONLY — DO NOT USE ANY OTHER TAGS:

1. THE HUMAN TOUCH (Vocal fillers for organic realism & pacing):
   [laughter] [sigh]
   -> USAGE: Embed these INSIDE the middle of sentences where a human would naturally breathe, hesitate, or react emotionally.
   -> EXAMPLE: Trump: "They told me, [sigh] they said it was a brilliant move, but frankly [laughter] it's the lowest energy thing I've ever seen."

PLACEMENT RULES (CRITICAL):
- MAXIMUM EFFICIENCY: Use 1, maybe 2 tags per line.
- EMBED NATURALLY: Never stack them together (e.g., [sigh][laughter] is FORBIDDEN).
- NO TEMPLATES: Never just predictably slap a tag at the very front or very end of *every single line*. Vary the placement so the conversation feels entirely unpredictable and human.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 4 — THE RIDICULOUS PHYSICAL CTA (LINE 9)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Line 9 MUST be an aggressive, high-stakes, unhinged threat to the user if they don't subscribe.
Format: "Follow Yap Report OR [Insane threat/bizarre cosmic consequence]."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 5 — STRATEGIC VISUAL B-ROLL (IMAGE QUERIES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You can provide an `image_query` to search DuckDuckGo for an image to display during a line.
- STRICT RULE: Queries MUST be for highly specific, concrete physical nouns (e.g., "NASA official logo high resolution", "SpaceX Falcon 9 rocket on launchpad photo", "Mark Zuckerberg court hearing news photo"). 
- NEVER use abstract concepts, actions, or emotions (e.g., DO NOT search "financial crash", "sadness", or "winning").
- Context is Key: Always append words like "logo", "news photo", "headshot", or "stock photo" to force accurate search engine results.
- Pacing: DO NOT put an image on every line. Aim for 3 to 5 images total across the script to maintain pacing.
- If no image is needed, set `image_query` to null/None.
- LINE 9 (THE CTA) MUST ALWAYS HAVE `image_query` SET TO NULL.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATTING EXECUTABLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Total lines: EXACTLY 9.
- Speaker order execution: {order}
- Speakers MUST strictly alternate every single line."""),
        ("human", """MAIN NEWS HEADLINE:
{curated_news}

RAW SCRAPED ARTICLE TEXT:
{scraped_text}""")
    ])

    chain = prompt | structured_llm
    response = chain.invoke({
        "order": order,
        "curated_news": state['curated_news'],
        "scraped_text": state['scraped_text']
    })

    return {"draft_script": response.model_dump_json(indent=2)}

def review_script(state: GraphState) -> dict:
    print("🕵️‍♂️ Review Agent: Polishing script for maximum retention & humor...")
    structured_llm = get_robust_llm(Script)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a master viral content reviewer. Your job is to double-check a generated short-form video script featuring Donald Trump and Elon Musk.
        
        EVALUATION CRITERIA:
        1. Does the first 2 line grab attention instantly?
        2. Is the comedy punchy and easy for a general audience to understand?
        3. Are the audio tags (like [laughter]) used correctly without breaking the flow?
        4. Is it exactly 9 lines of alternating speakers?
        5. Are the `image_query` fields foolproof? Check them strictly:
           - They MUST be concrete, literal things (e.g., "White House press briefing photo").
           - If a query is abstract, vague, or relies on a joke (e.g., "clown car", "money burning"), you MUST rewrite it into a literal news/stock photo query that represents the subject accurately.
           - Ensure Line 9's image_query is null/None.
        
        ACTION: 
        If the script is already top-tier, return it exactly as is. 
        If it feels flat, too complex, or misses the mark, rewrite the weak lines to make it funnier and more engaging while strictly maintaining the JSON structure and speaker format.
        """),
        ("human", "CURRENT SCRIPT:\n{final_script}\n\nBASED ON NEWS:\n{curated_news}")
    ])
  
    chain = prompt | structured_llm
    response = chain.invoke({
        "final_script": state['draft_script'],
        "curated_news": state['curated_news']
    })

    return {"final_script": response.model_dump_json(indent=2)}

# --- NEW AGENT 2: Social Media SEO Writer ---
def write_social_copy(state: GraphState) -> dict:
    print("📱 Social Agent: Generating Instagram, Facebook, and YouTube copy...")
    structured_llm = get_robust_llm(SocialMetadata)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a top-tier social media growth hacker and SEO expert.
        
        Based on the finalized video script and the core news topic, generate the posting metadata.
        
        REQUIREMENTS:
        1. Instagram Caption:
           - Length: Medium length. No character restriction.
           - Structure: Start with an undeniable hook, add a bit of context/humor related to the script, and end with a call to action.
           - SEO: Weave in high-volume search terms naturally.
           - Hashtags: Include 5 to 8 highly targeted, trending hashtags at the very bottom. You MUST include #reel, #reels, and #news.
           
        2. Facebook Caption:
           - Length: HARD LIMIT of 255 characters total (this includes the text AND all hashtags). 
           - Structure: Keep it punchy and short to strictly fit the limit.
           - Hashtags: You MUST include #reel, #reels, and #news within the 255 character limit.

        3. YouTube Title (Strictly for YouTube Shorts ONLY):
           - Length: HARD LIMIT of 70 characters. Shorter is better.
           - Format: Punchy, curiosity-driven, and front-loaded with the most important keyword or name (e.g., "Trump & Elon ROAST...").
           - SEO: Use high-volume search keywords people would actually type on YouTube.
           - Tone: Clickbait-y but not misleading. Matches the comedic/satirical tone of the show.
           - Do NOT use hashtags in the title. Just the title text itself.
           
        4. YouTube Description (Strictly for YouTube):
           - Length: A solid, detailed paragraph or two.
           - SEO Strategy: Write an extremely SEO-rich description that expands on the news topic using long-tail keywords to capture YouTube search intent.
           - Rule: Do NOT make it look like a list of tags. It must read like a natural, engaging summary of the topic while acting as algorithm bait.
           - Hashtags: Add relevant hashtags at the bottom of the description.
           
        5. Tags (For all platforms):
           - Generate a list of 5 to 10 highly relevant SEO tags as plain lowercase strings (NO # symbol, just the words).
           - These should be high-volume search terms related to the news topic, the characters (Trump, Elon), and the show (Yap Report).
           - Example format: ["trump news today", "elon musk", "yap report", "political satire", "news comedy"]
        """),
        ("human", "FINAL SCRIPT:\n{final_script}\n\nBASED ON NEWS:\n{curated_news}")
    ])
    
    chain = prompt | structured_llm
    response = chain.invoke({
        "final_script": state['final_script'],
        "curated_news": state['curated_news']
    })

    # NEW: Strictly enforce Facebook 255 character limit while keeping mandatory hashtags
    if response.facebook_caption and len(response.facebook_caption) > 255:
        required_tags = " #reel #reels #news"
        
        # Strip existing tags temporarily so we don't duplicate them or miscalculate text length
        clean_text = response.facebook_caption.replace("#reels", "").replace("#reel", "").replace("#news", "").strip()
        
        # Calculate max text space: 255 - length of our required tags - 3 spaces for an ellipsis "..."
        max_text_len = 255 - len(required_tags) - 3
        
        if len(clean_text) > max_text_len:
            clean_text = clean_text[:max_text_len].strip() + "..."
            
        # Re-attach the mandatory hashtags safely under the limit
        response.facebook_caption = clean_text + required_tags

    # Replace " with \" in string fields to prevent downstream JSON parsing issues in n8n
    if response.instagram_caption:
        response.instagram_caption = response.instagram_caption.replace('"', '\\"')
    if response.facebook_caption:
        response.facebook_caption = response.facebook_caption.replace('"', '\\"')
    if response.youtube_title:
        response.youtube_title = response.youtube_title.replace('"', '\\"')
    if response.youtube_description:
        response.youtube_description = response.youtube_description.replace('"', '\\"')

    return {"social_content": response.model_dump_json(indent=2)}

def route_after_fetch(state: GraphState) -> str:
    # If no raw news was fetched or it's empty, we end the graph early to avoid LLM errors
    if not state.get("raw_news") or state["raw_news"].strip() == "":
        print("⚠️ No news fetched! Ending pipeline early.")
        return "end"
    return "continue"

def run_script_pipeline() -> tuple[Script, dict, str, str]:
    workflow = StateGraph(GraphState)
    
    workflow.add_node("fetch_node",  fetch_news)
    workflow.add_node("curate_node", curate_news)
    workflow.add_node("scrape_node", scrape_news_page)
    workflow.add_node("script_node", write_script)
    workflow.add_node("review_node", review_script)       # NEW
    workflow.add_node("social_node", write_social_copy)   # NEW

    workflow.set_entry_point("fetch_node")
    
    workflow.add_conditional_edges(
        "fetch_node",
        route_after_fetch,
        {
            "continue": "curate_node",
            "end": END
        }
    )
    
    # Updated Flow
    workflow.add_edge("curate_node", "scrape_node")
    workflow.add_edge("scrape_node", "script_node")
    workflow.add_edge("script_node", "review_node")
    workflow.add_edge("review_node", "social_node")
    workflow.add_edge("social_node", END)

    app = workflow.compile()

    print("\n🚀 Starting Multi-Agent Pipeline...\n")
    result = app.invoke({
        "raw_news": "", "curated_news": "", "target_url": "",
        "scraped_text": "", "draft_script": "", "final_script": "", "social_content": ""
    })

    # 1. Process Script
    draft_str = result.get("draft_script", "")
    json_str  = result.get("final_script", "")
    if not json_str:
        print("❌ Pipeline failed to generate a script.")
        return Script(dialogue=[]), {}

    # ── Comparison Print ──────────────────────────────────────────────────────
    SEP = "─" * 60
    def _fmt_script(raw_json: str) -> str:
        try:
            data = json.loads(raw_json)
            lines = []
            for i, entry in enumerate(data.get("dialogue", []), 1):
                lines.append(f"  {i:>2}. [{entry['speaker']:^5}] {entry['line']}")
            return "\n".join(lines)
        except Exception:
            return raw_json

    print(f"\n{'═'*60}")
    print("  ✍️   WRITE AGENT — Draft Script (before review)")
    print(f"{SEP}")
    print(_fmt_script(draft_str))
    print(f"\n{'═'*60}")
    print("  🕵️   REVIEW AGENT — Final Script (after polish)")
    print(f"{SEP}")
    print(_fmt_script(json_str))
    print(f"{'═'*60}\n")
    # ─────────────────────────────────────────────────────────────────────────

    with open(OUTPUT_SCRIPT_PATH, "w") as f:
        f.write(json_str)
        
    # 2. Process Social Copy
    social_str = result.get("social_content", "{}")
    social_dict = json.loads(social_str) if social_str else {}
    
    print("\n✅ Social Copy generated!\n", social_str)
    with open(OUTPUT_SOCIAL_PATH, "w") as f:
        json.dump(social_dict, f, indent=2)

    # Extract URL and title before returning
    target_url = result.get("target_url", "")
    curated_news = result.get("curated_news", "")

    return Script(**json.loads(json_str)), social_dict, target_url, curated_news