import json
import random
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.schemas import GraphState, Script, CuratedStory
from src.services.news_scraper import fetch_news, scrape_news_page
from src.config import OUTPUT_SCRIPT_PATH

flash_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.7)
pro_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.7)

def curate_news(state: GraphState) -> dict:
    print("🧠 Curating top story...")
    curator_llm = flash_llm.with_structured_output(CuratedStory)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a news producer. Pick the ONE most explosive or dramatic story from today's raw news."),
        ("human", "Raw News:\n{raw_news}\n\nTask: Extract the headline, who is involved, exactly what happened, and importantly, grab the exact URL associated with the story.")
    ])
    
    chain = prompt | curator_llm
    curated_obj = chain.invoke({"raw_news": state['raw_news']})
    
    curated_text = f"HEADLINE: {curated_obj.headline}\nWHO: {curated_obj.who}\nWHAT: {curated_obj.what_happened}"

    print(f"✅ Picked Story: {curated_obj.headline} url: {curated_obj.url}")

    return {
        "curated_news": curated_text,
        "target_url": curated_obj.url
    }

def write_script(state: GraphState) -> dict:
    print("✍️  Writing hyper-engaging comedy roast script...")
    structured_llm = pro_llm.with_structured_output(Script)

    first_speaker  = random.choice(["Trump", "Elon"])
    second_speaker = "Elon" if first_speaker == "Trump" else "Trump"

    order = " → ".join([first_speaker if i % 2 == 0 else second_speaker for i in range(10)])

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
RULE 2 — THE 10-LINE HIGH-RETENTION STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You must strictly follow this exact narrative pace across EXACTLY 10 lines:
- Line 1-2 (The Aggressive Hook): Speaker A drops the craziest, funniest summary of the headline. Speaker B responds with instant clowning or shock.
- Line 3-6 (The Roast Explanation): Break down the "how" and "why" of the news using tight conversational connectors (e.g., "Wait, so this clown actually...", "Yeah, it’s literally sub-optimal...").
- Line 7-9 (The Billionaire Perspective): Both characters mock how this impacts the future of humanity or their own massive bank accounts.
- Line 10 (The Unhinged CTA).

Target length: 12 to 22 words per line. Keep it punchy!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 3 — STRATEGIC AUDIO TAG PLACEMENT & EMOTION CONTROL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To make the AI voices sound hyper-realistic and engaging, you must use the following audio tags strategically based on their specific function.

SUPPORTED TAGS ONLY — DO NOT USE ANY OTHER TAGS:

1. THE HUMAN TOUCH (Vocal fillers for organic realism & pacing):
   [laughter] [sigh] [confirmation-en] [dissatisfaction-hnn]
   -> USAGE: Embed these INSIDE the middle of sentences where a human would naturally breathe, hesitate, or react emotionally.
   -> EXAMPLE: Trump: "They told me, [sigh] they said it was a brilliant move, but frankly [laughter] it's the lowest energy thing I've ever seen."

2. MICRO-REACTIONS (Punctuate shocking, confusing, or stupid moments):
   [question-en] [question-ah] [question-oh] [question-ei] [question-yi] [surprise-ah] [surprise-oh] [surprise-yo]
   -> USAGE: Place these at the END of a sentence, or use them as a standalone interruption right after the other speaker drops a crazy fact.
   -> EXAMPLE: Elon: "The CEO literally fired himself. [surprise-oh]"

PLACEMENT RULES (CRITICAL):
- MAXIMUM EFFICIENCY: Use 1, maybe 2 tags per line.
- EMBED NATURALLY: Never stack them together (e.g., [sigh][laughter] is FORBIDDEN).
- NO TEMPLATES: Never just predictably slap a tag at the very front or very end of *every single line*. Vary the placement so the conversation feels entirely unpredictable and human.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 4 — THE RIDICULOUS PHYSICAL CTA (LINE 10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Line 10 MUST be an aggressive, high-stakes, unhinged threat to the user if they don't subscribe.
Format: "Follow Yap Report OR [Insane threat/bizarre cosmic consequence]."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATTING EXECUTABLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Total lines: EXACTLY 10.
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

    return {"final_script": response.model_dump_json(indent=2)}


def route_after_fetch(state: GraphState) -> str:
    # If no raw news was fetched or it's empty, we end the graph early to avoid LLM errors
    if not state.get("raw_news") or state["raw_news"].strip() == "":
        print("⚠️ No news fetched! Ending pipeline early.")
        return "end"
    return "continue"

def run_script_pipeline() -> Script:
    workflow = StateGraph(GraphState)
    workflow.add_node("fetch_node",  fetch_news)
    workflow.add_node("curate_node", curate_news)
    workflow.add_node("scrape_node", scrape_news_page)
    workflow.add_node("script_node", write_script)

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
    workflow.add_edge("script_node", END)

    app = workflow.compile()

    print("\n🚀 Starting Pipeline...\n")
    result = app.invoke({"raw_news": "", "curated_news": "", "target_url": "", "scraped_text": "", "final_script": ""})

    json_str = result.get("final_script", "")
    if not json_str:
        print("❌ Pipeline failed to generate a script.")
        # Return a fallback script or raise exception
        return Script(dialogue=[])
        
    print("\n✅ Script generated!\n", json_str)

    with open(OUTPUT_SCRIPT_PATH, "w") as f:
        f.write(json_str)
    return Script(**json.loads(json_str))
