import os
import urllib.request
import subprocess
import soundfile as sf
from src.config import (
    FONT_URL, FONTS_DIR, FONT_PATH,
    W, H, WORDS_PER_CAP, PHOTO_SIZE, PHOTO_X, PHOTO_Y,
    BG_VIDEO_PATH, TRUMP_IMG, ELON_IMG, OUTPUT_VIDEO_PATH, OUTPUT_AUDIO_PATH
)

def ensure_font():
    os.makedirs(FONTS_DIR, exist_ok=True)
    if not os.path.exists(FONT_PATH):
        print("⬇  Downloading Bubbly font...")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        print("   ✅ Font downloaded")

def get_audio_duration(path):
    return sf.info(path).duration

def float_to_ass_time(sec):
    """ Converts seconds to ASS timestamp format H:MM:SS.cs """
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int((sec % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def build_timeline(words):
    timeline = []
    if not words: return timeline
    current_speaker, current_start = words[0].get("speaker", "unknown"), words[0].get("start", 0)
    
    for i, w in enumerate(words):
        speaker = w.get("speaker", "unknown")
        start = w.get("start", 0)
        if speaker != current_speaker:
            timeline.append({"speaker": current_speaker, "start": current_start, "end": start})
            current_speaker, current_start = speaker, start
            
    # Cap the final turn
    if words:
        timeline.append({"speaker": current_speaker, "start": current_start, "end": words[-1].get("end", current_start) + 5.0})
    return timeline

def create_ass_subtitles(words, duration, filename="captions.ass"):
    """ Generates a hardware-accelerated subtitle file for FFmpeg with karaoke color overrides. """
    print("📝 Generating Subtitles (ASS)...")
    
    # ASS Header with Styling (Alignment 8 = Top Center. MarginV 960 pushes it to the middle)
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {W}",
        f"PlayResY: {H}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Luckiest Guy,75,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,5,0,8,10,10,960,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    last_time = 0
    for i in range(0, len(words), WORDS_PER_CAP):
        chunk = words[i:i+WORDS_PER_CAP]
        chunk_start = chunk[0].get("start", last_time)
        
        # Keep caption on screen until next chunk starts
        if i + WORDS_PER_CAP < len(words):
            chunk_end = words[i+WORDS_PER_CAP].get("start", chunk[-1].get("end", chunk_start + 1.0))
        else:
            chunk_end = chunk[-1].get("end", chunk_start + 1.0)
            
        chunk_end = min(chunk_end, duration)
        last_time = chunk_end

        # Emit an event for each word's highlight span
        for j, w in enumerate(chunk):
            w_start = w.get("start", chunk_start)
            w_end = chunk[j+1].get("start", w.get("end", w_start + 0.2)) if j + 1 < len(chunk) else chunk_end
            if w_end < w_start: w_end = w_start + 0.1

            text_parts = []
            for k, cw in enumerate(chunk):
                raw_text = cw["word"].replace("{", "").replace("}", "").upper()
                if k == j:
                    # &H00FF00& = Green, &HFFFFFF& = White
                    text_parts.append(f"{{\\c&H00FF00&}}{raw_text}{{\\c&HFFFFFF&}}")
                else:
                    text_parts.append(raw_text)

            line_text = " ".join(text_parts)
            ass_lines.append(f"Dialogue: 0,{float_to_ass_time(w_start)},{float_to_ass_time(w_end)},Default,,0,0,0,,{line_text}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_lines))

def check_nvenc_support():
    """ Probes FFmpeg to see if NVIDIA H.264 NVENC encoder is supported. """
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False

def compile_video(timeline, duration, bg_video_path=None, audio_path=None, output_path=None):
    if bg_video_path is None: bg_video_path = BG_VIDEO_PATH
    if audio_path is None: audio_path = OUTPUT_AUDIO_PATH
    if output_path is None: output_path = OUTPUT_VIDEO_PATH
    
    print("🎬 Rendering video natively with FFmpeg Engine...")
    
    def get_enable_expr(target):
        exprs = [f"between(t,{t['start']},{t['end']})" for t in timeline if t["speaker"] == target]
        return "+".join(exprs) if exprs else "0"

    trump_enable = get_enable_expr("trump")
    elon_enable = get_enable_expr("elon")

    fonts_dir_ffmpeg = FONTS_DIR.replace('\\', '/')
    
    filter_str = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[bg]; "
        f"[2:v]scale={PHOTO_SIZE}:{PHOTO_SIZE}[trump]; "
        f"[3:v]scale={PHOTO_SIZE}:{PHOTO_SIZE}[elon]; "
        f"[bg][trump]overlay=x={PHOTO_X}:y={PHOTO_Y}:enable='{trump_enable}'[v1]; "
        f"[v1][elon]overlay=x={PHOTO_X}:y={PHOTO_Y}:enable='{elon_enable}'[v2]; "
        f"[v2]subtitles=captions.ass:fontsdir='{fonts_dir_ffmpeg}'[outv]"
    )

    has_nvenc = check_nvenc_support()
    if has_nvenc:
        print("💡 GPU encoding detected! Using NVIDIA NVENC Hardware Acceleration...")
        # FIX: Changed from -cq 18 (massive files) to a capped 5Mbps bitrate
        encoder_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "5M", "-maxrate", "6M", "-bufsize", "10M"]
    else:
        print("⚠️ GPU encoding not supported. Using CPU fallback (libx264)...")
        encoder_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_video_path,
        "-i", audio_path,
        "-i", TRUMP_IMG,
        "-i", ELON_IMG,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-map", "1:a",           
        "-t", str(duration),     
    ] + encoder_args + [
        "-c:a", "aac", 
        "-ac", "2",               # FIX: Convert Mono to Stereo
        "-b:a", "128k",           # FIX: Lower bitrate to prevent "Too many bits" AAC clamping error
        "-shortest",              # FIX: Ensures absolute hard-cut when audio finishes
        "-hide_banner", "-loglevel", "warning",
        output_path
    ]
    
    subprocess.run(cmd, check=True)