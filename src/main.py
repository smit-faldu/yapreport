# src/main.py (Updates)
import sys
import os
import time # Added for unique filenames
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
# NEW: Import the uploader
from src.services.supabase_uploader import upload_video

def run_pipeline():
    print("="*50)
    print(" PHASE 1: Script & Audio Generation")
    print("="*50)

    script = run_script_pipeline()
    run_tts_pipeline(script)

    print("\n✅ Phase 1 complete! Podcast saved to", OUTPUT_AUDIO_PATH)

    print("\n" + "="*50)
    print(" PHASE 2: Video Renderer — FFmpeg Filtergraph Edition")
    print("="*50)

    ensure_font()

    dialogue = json.load(open(OUTPUT_SCRIPT_PATH))["dialogue"]
    print(f"📄 {len(dialogue)} turns")

    duration = get_audio_duration(OUTPUT_AUDIO_PATH)
    words = transcribe(OUTPUT_AUDIO_PATH, dialogue)
    timeline = build_timeline(words)

    create_ass_subtitles(words, duration)
    compile_video(timeline, duration, BG_VIDEO_PATH, OUTPUT_AUDIO_PATH, OUTPUT_VIDEO_PATH)

    mb = os.path.getsize(OUTPUT_VIDEO_PATH) / 1024 / 1024
    print(f"\n🎉 Done! → {OUTPUT_VIDEO_PATH}  ({mb:.1f} MB)")

    # --- NEW: Supabase Upload ---
    # Create a unique filename based on timestamp to avoid overwriting previous videos
    timestamp = int(time.time())
    remote_filename = f"yapreport_{timestamp}.mp4"
    public_url = upload_video(OUTPUT_VIDEO_PATH, remote_filename)
    
    return public_url


app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server is up and running"}

@app.post("/generate")
def generate_video(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"status": "accepted", "message": "Pipeline execution started in the background. Check server logs for the final Supabase URL."}

@app.get("/generate-sync")
def generate_video_sync():
    video_url = run_pipeline()
    response = {
        "status": "success", 
        "message": "Pipeline execution completed successfully"
    }
    if video_url:
        response["video_url"] = video_url
        
    return response

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)