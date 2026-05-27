# src/services/supabase_uploader.py
import os
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET

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