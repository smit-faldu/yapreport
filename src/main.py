import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from src.agents.script_agent import run_script_pipeline
from src.services.tts_service import run_tts_pipeline
from src.services.transcriber import transcribe
from src.video.renderer import (
    ensure_font, get_audio_duration, build_timeline, 
    create_ass_subtitles, compile_video
)
from src.config import (
    OUTPUT_SCRIPT_PATH, OUTPUT_AUDIO_PATH, OUTPUT_VIDEO_PATH,
    BG_VIDEO_PATH
)

def run_pipeline():
    print("="*50)
    print(" PHASE 1: Script & Audio Generation")
    print("="*50)

    # Step 1: Generate script via LangGraph
    script = run_script_pipeline()

    # Step 2: Convert script to audio via Qwen TTS (OmniVoice)
    run_tts_pipeline(script)

    print("\n✅ Phase 1 complete! Podcast saved to", OUTPUT_AUDIO_PATH)


    print("\n" + "="*50)
    print(" PHASE 2: Video Renderer — FFmpeg Filtergraph Edition")
    print("="*50)

    ensure_font()

    # Load the script dictionary for dialogue mapping
    dialogue = json.load(open(OUTPUT_SCRIPT_PATH))["dialogue"]
    print(f"📄 {len(dialogue)} turns")

    duration = get_audio_duration(OUTPUT_AUDIO_PATH)
    words = transcribe(OUTPUT_AUDIO_PATH, dialogue)
    timeline = build_timeline(words)

    print("\n📋 Speaker timeline:")
    for t in timeline:
        print(f"   [{t['start']:.2f}–{t['end']:.2f}s]  {t['speaker'].upper()}")

    create_ass_subtitles(words, duration)
    compile_video(timeline, duration, BG_VIDEO_PATH, OUTPUT_AUDIO_PATH, OUTPUT_VIDEO_PATH)

    mb = os.path.getsize(OUTPUT_VIDEO_PATH) / 1024 / 1024
    print(f"\n🎉 Done! → {OUTPUT_VIDEO_PATH}  ({mb:.1f} MB)")


app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server is up and running"}

@app.post("/generate")
def generate_video(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"status": "accepted", "message": "Pipeline execution started in the background"}

@app.get("/generate-sync")
def generate_video_sync():
    run_pipeline()
    return {"status": "success", "message": "Pipeline execution completed successfully"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
