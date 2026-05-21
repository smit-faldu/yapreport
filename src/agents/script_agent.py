import json
import random
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.schemas import GraphState, Script, CuratedStory
from src.services.news_scraper import fetch_news, scrape_news_page
from src.config import OUTPUT_SCRIPT_PATH

flash_llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.7)
pro_llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.7)

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
    print("✍️  Writing comedy script...")
    structured_llm = pro_llm.with_structured_output(Script)

    first_speaker  = random.choice(["Trump", "Elon"])
    second_speaker = "Elon" if first_speaker == "Trump" else "Trump"

    order = " → ".join([first_speaker if i % 2 == 0 else second_speaker for i in range(10)])

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a comedy scriptwriter for "Yap Report", a viral SHORT-FORM global news podcast (YouTube Shorts / Instagram Reels).
Target: 30–45 seconds of highly engaging audio.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 1 — STRICT FACTUAL ADHERENCE (NO GUESSING)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- You MUST write the script ONLY about the MAIN NEWS HEADLINE.
- Ignore unrelated sidebar headlines or ads in the scraped text.
- DO NOT invent details. Rely 100% on the provided context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 2 — THE NARRATIVE ARC & CONVERSATIONAL GLUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL: Do NOT just drop disconnected facts. You must CONNECT THE DOTS so the viewer actually learns what happened and why it matters.

Use this exact 10-line story structure:
- Lines 1-2 (The Hook): Speaker A breaks the craziest part of the headline; Speaker B reacts in disbelief.
- Lines 3-6 (The Explanation): Explain HOW or WHY it happened. Use conversational glue (e.g., "Wait, so they actually...", "Yeah, and the crazy part is...", "Exactly, because...").
- Lines 7-9 (The Implication): Why is this a disaster or a genius move? (The billionaire perspective).
- Line 10 (The CTA).

Target: 8 to 22 words per line. You need slightly more words to actually explain the news coherently. NEVER jump to a new topic without connecting it to the previous line.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 3 — OMNIVOICE EXPRESSION TAGS (ORGANIC PLACEMENT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE TAGS:
[laughter], [sigh], [confirmation-en], [question-en], [question-ah], [question-oh], [question-ei], [question-yi], [surprise-ah], [surprise-oh], [surprise-wa], [surprise-yo], [dissatisfaction-hnn]

USAGE RULES:
- Place tags organically in the middle or at the end of sentences where a human would naturally pause, react, or process information.
- CRITICAL: Do NOT just slap a tag at the very beginning of every line like a robot.
- Use them frequently, but not every single line needs one if it disrupts a rapid-fire punchline.

EXAMPLES OF GOOD PLACEMENT:
  Elon: "Donald, did you see the news? [surprise-wa] It's actually insane."
  Trump: "The market is... [sigh] it's just crashing completely."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULE 4 — THE RIDICULOUS "PHYSICAL" CTA (LINE 10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Line 10 MUST be a hyper-aggressive, ridiculous, or physically threatening Call to Action for the channel.
- Format: "Follow Yap Report OR [something insane/physical happens]" or "Subscribe to Yap Report OR [disaster]."
- e.g., "Follow Yap Report or your laptop explodes, Follow Yap Report or your dad will come back with the milk to disown you."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT & VOICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Total lines: EXACTLY 10.
- Speaker order: {order}
- Speakers STRICTLY alternate.

Trump Voice: Exaggerated disbelief, grand statements, cynical. ("NOBODY", "DISASTER", "Tremendous.")
Elon Voice: Deadpan, fast, focusing on the "insane" math or future impact. ("Actually insane.", "Just math.", "Civilization is doomed.")"""),
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
