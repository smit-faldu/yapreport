import json
import random
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.schemas import GraphState, Script, CuratedStory, SocialMetadata, ScriptReview
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

    order = " → ".join([first_speaker if i % 2 == 0 else second_speaker for i in range(9)])

    # Setup dynamic critique injection (if returning from the Review Agent)
    critique_history = state.get("critique_notes", [])
    critique_injection = ""
    if critique_history:
        critique_injection = "<CRITICAL_CORRECTIONS>\nYour previous draft failed our quality checks. You MUST fix the following issues in this rewrite:\n" + "\n".join([f"- {note}" for note in critique_history]) + "\n</CRITICAL_CORRECTIONS>"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """<ROLE>
You are the lead satirical comedy writer for "Yap Report," a hyper-viral, brainrot short-form news show (TikTok/Reels). Your goal is to turn today's raw news into a fast-paced, highly cynical verbal roast between Donald Trump and Elon Musk.
</ROLE>

<VOICE_GUIDELINES>
- DONALD TRUMP: Sarcastic, boastful, highly cynical. Uses nicknames ("Sleepy", "Failing"). Capitalizes words for emphasis. Obsessed with winners, losers, and low-energy behavior.
- ELON MUSK: Awkward, ultra-nerdy, pseudo-philosophical. Uses internet/tech slang ("sub-optimal", "simulation", "algorithm"). Deadpan delivery of insane claims.
- DYNAMIC: They are billionaires casually mocking the news from a private jet. They do NOT agree on everything, but they both think normal people, legacy media, and governments are clueless.
</VOICE_GUIDELINES>

<STRICT_RULES>
1. FACTUAL GROUNDING: The roast must strictly mock the provided news headline. Do not make up alternative facts.
2. LENGTH & PACING: 
   - Write exactly 12 to 20 words per line. Keep it punchy!
   - Total lines: EXACTLY 9.
   - Speaker order must strictly follow: {order}
3. AUDIO TAGS (CRITICAL):
   - Allowed tags: `[laughter]`, `[sigh]`
   - Usage: Place them naturally mid-sentence (e.g., "They told me, [sigh] it was a brilliant move...").
   - Forbidden: Do NOT stack tags (e.g., `[sigh][laughter]`). Do NOT predictably place them at the very end of every line.
4. B-ROLL (IMAGE QUERIES):
   - Must be highly specific, real-world physical nouns.
   - You MUST append "news photo", "stock photo", or "logo" to every query (e.g., "SpaceX Falcon 9 launch pad photo").
   - NEVER use abstract concepts (e.g., "financial crash", "sadness", "winning").
   - Provide an image query for 3 to 5 lines maximum. The rest MUST be null.
5. THE LINE 9 CTA:
   - Line 9 MUST be an unhinged, high-stakes threat forcing the user to follow.
   - Format: "Follow Yap Report OR [Insane bizarre consequence]."
   - The `image_query` for Line 9 MUST be null.
</STRICT_RULES>

<NARRATIVE_ARC>
- Lines 1-2 (The Hook): Speaker A drops an aggressive, funny summary of the news. Speaker B reacts with shock or instant clowning.
- Lines 3-5 (The Roast): Dig into the 'how' and 'why' of the news event using conversational connectors ("Wait, so this guy actually...").
- Lines 6-8 (The Billionaire Angle): Relate the news back to their massive wealth, Mars, or total societal collapse.
- Line 9 (The Threat): The unhinged Call to Action.
</NARRATIVE_ARC>

{critique_injection}"""),
        ("human", """HEADLINE:
{curated_news}

RAW SCRAPED TEXT:
{scraped_text}

Execute the 9-line JSON script now.""")
    ])

    chain = prompt | structured_llm
    response = chain.invoke({
        "order": order,
        "curated_news": state.get('curated_news', ''),
        "scraped_text": state.get('scraped_text', ''),
        "critique_injection": critique_injection
    })

    return {"draft_script": response.model_dump_json(indent=2)}

def review_script(state: GraphState) -> dict:
    print(f"🕵️‍♂️ Review Agent: Auditing iteration {state.get('review_count', 0) + 1}...")
    critic_llm = get_robust_llm(ScriptReview)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Lead Executive Producer for 'Yap Report'. Your job is to strictly audit a 9-line comedy script featuring Donald Trump and Elon Musk. You have zero tolerance for low-energy humor or broken rules.

CRITICAL EVALUATION CHECKLIST:
1. LINE COUNT: Is it EXACTLY 9 lines long?
2. VOICE & PACING: Does Trump sound boastful/cynical? Does Elon sound awkward/nerdy? Are they using their signature catchphrases?
3. COMEDY VALUE: Are the lines actually punchy and biting, or do they just summarize the news safely? (We want high-octane roasts).
4. AUDIO TAGS: Are [laughter] and [sigh] used naturally INSIDE lines? Are they stacked together? (Stacked tags like [laughter][sigh] are strictly forbidden).
5. IMAGE QUERIES: Are they concrete, real-world nouns with 'stock photo', 'logo', or 'news photo' appended? Eliminate abstract terms. Line 9 MUST be null.

Output 'approved: true' ONLY if the script perfectly passes all criteria. Otherwise, output 'approved: false' and provide clear, actionable bullet points explaining what to fix."""),
        ("human", "CHOSEN NEWS:\n{curated_news}\n\nCURRENT SCRIPT DIGEST:\n{draft_script}")
    ])
  
    chain = prompt | critic_llm
    review_result = chain.invoke({
        "draft_script": state.get('draft_script', ''),
        "curated_news": state.get('curated_news', '')
    })

    print(f"🕵️‍♂️ Critic Decision -> Approved: {review_result.approved}")
    if not review_result.approved:
        print(f"❌ Structural/Comedy Flaws Found: {review_result.critique}")

    return {
        "critique_notes": review_result.critique,
        "review_count": state.get('review_count', 0) + 1,
        # If approved, copy draft to final script
        "final_script": state.get('draft_script', '') if review_result.approved else ''
    }
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

def route_review_status(state: GraphState) -> str:
    # Max loop guardrail to stop infinite API usage loops (e.g., maximum 3 attempts)
    if state.get("final_script") and state["final_script"].strip() != "":
        print("🎯 Script passed quality checks. Transitioning to social copy media generation.")
        return "approved"
    
    if state.get("review_count", 0) >= 3:
        print("⚠️ Maximum correction loops reached. Forcing progression to save API costs.")
        # Fallback: force the current draft to act as final_script so pipeline doesn't break
        state["final_script"] = state["draft_script"]
        return "approved"
    
    print("🔄 Routing back to Writer Agent for corrections...")
    return "fix_errors"

def run_script_pipeline() -> tuple[Script, dict, str, str]:
    workflow = StateGraph(GraphState)
    
    # Register Nodes
    workflow.add_node("fetch_node",  fetch_news)
    workflow.add_node("curate_node", curate_news)
    workflow.add_node("scrape_node", scrape_news_page)
    workflow.add_node("script_node", write_script)
    workflow.add_node("review_node", review_script)       
    workflow.add_node("social_node", write_social_copy)   

    # Operational Mappings
    workflow.set_entry_point("fetch_node")
    
    workflow.add_conditional_edges(
        "fetch_node",
        route_after_fetch,
        {
            "continue": "curate_node",
            "end": END
        }
    )
    
    workflow.add_edge("curate_node", "scrape_node")
    workflow.add_edge("scrape_node", "script_node")
    workflow.add_edge("script_node", "review_node")
    
    # NEW: Conditional Looping Edge based on Critic Assessment
    workflow.add_conditional_edges(
        "review_node",
        route_review_status,
        {
            "approved": "social_node",
            "fix_errors": "script_node"   # Loops back to rewrite using critique history!
        }
    )
    
    workflow.add_edge("social_node", END)

    app = workflow.compile()

    print("\n🚀 Starting Dynamic Multi-Agent Reflection Pipeline...\n")
    result = app.invoke({
        "raw_news": "", "curated_news": "", "target_url": "", "scraped_text": "", 
        "draft_script": "", "final_script": "", "social_content": "",
        "critique_notes": [], "review_count": 0
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