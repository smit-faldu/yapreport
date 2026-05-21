import subprocess
import soundfile as sf
import os

def get_audio_duration(path):
    return sf.info(path).duration

def extract_bg_to_disk(video_path, duration, fps, w, h, tmp_dir):
    print(f"🎬 Extracting BG frames to disk...")
    out = os.path.join(tmp_dir, "bg_%06d.png")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        "-r", str(fps), out,
        "-hide_banner", "-loglevel", "error"
    ], check=True)
    frames = sorted(
        os.path.join(tmp_dir, f)
        for f in os.listdir(tmp_dir) if f.startswith("bg_")
    )
    print(f"   ✅ {len(frames)} BG frames")
    return frames

def mux_audio(video, audio, output):
    print(f"🔊 Muxing audio → {output}")
    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-i", audio,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output,
        "-hide_banner", "-loglevel", "error"
    ], check=True)
