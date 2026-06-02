# src/services/supabase_uploader.py
import os
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET
import datetime

def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_video(file_path: str, filename: str) -> str:
    """Uploads the generated video to Supabase Storage and returns the public URL."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase credentials missing. Skipping upload.")
        return None
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        with open(file_path, "rb") as f:
            print(f"☁️ Uploading {filename} to Supabase bucket '{SUPABASE_BUCKET}'...")
            
            # The upload method requires the file bytes, the destination path, and file options
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                file=f,
                path=filename,
                file_options={"content-type": "video/mp4"}
            )
        
        # Retrieve the public URL for sharing
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        print(f"✅ Video uploaded successfully! Public URL: {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"❌ Failed to upload to Supabase: {e}")
        return None
def get_covered_urls() -> set:
    """Fetch all URLs that have already been covered."""
    supabase = get_supabase_client()
    if not supabase: return set()
    try:
        response = supabase.table("covered_news").select("url").execute()
        return {row["url"] for row in response.data}
    except Exception as e:
        print(f"❌ Failed to fetch covered news: {e}")
        return set()

def get_covered_titles() -> set:
    """Fetch all titles that have already been covered."""
    supabase = get_supabase_client()
    if not supabase: return set()
    try:
        response = supabase.table("covered_news").select("title").execute()
        return {row["title"] for row in response.data}
    except Exception as e:
        print(f"❌ Failed to fetch covered news: {e}")
        return set()

def save_covered_news(url: str, title: str, video_link: str = None, social_metadata: dict = None):
    """Save the successfully generated news to the database."""
    supabase = get_supabase_client()
    if not supabase or not url: return
    try:
        supabase.table("covered_news").insert({
            "url": url,
            "title": title,
            "video_link": video_link,
            "social_metadata": social_metadata
        }).execute()
        print(f"✅ Stored news in DB to prevent repeats: {title[:50]}...")
    except Exception as e:
        print(f"❌ Failed to save covered news: {e}")

def cleanup_old_news():
    """Delete news records older than 2 days."""
    supabase = get_supabase_client()
    if not supabase: return
    try:
        # Calculate the timestamp for 3 days ago
        three_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)).isoformat()
        
        response = supabase.table("covered_news").delete().lt("created_at", three_days_ago).execute()
        deleted_count = len(response.data) if response.data else 0
        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} old news records (>2 days old).")
    except Exception as e:
        print(f"❌ Failed to cleanup old news: {e}")