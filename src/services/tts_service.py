import gc
import torch
import numpy as np
import soundfile as sf
from omnivoice import OmniVoice
from src.models.schemas import Script
import subprocess
import os
from src.config import (
    TRUMP_REF_AUDIO, TRUMP_REF_TEXT,
    ELON_REF_AUDIO, ELON_REF_TEXT,
    PAUSE_SEC, OMNIVOICE_SR, OUTPUT_AUDIO_PATH
)

def _unload_model(model, label: str = "model"):
    """
    Aggressively release a PyTorch model from GPU/CPU memory.
    Moves weights to CPU first (avoids CUDA ref-count leaks), then deletes
    the object, runs the GC, and flushes the CUDA allocator cache.
    """
    try:
        model.cpu()          # move tensors off GPU before deletion
    except Exception:
        pass
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    print(f"🗑️  {label} unloaded — GPU memory freed.")

def load_tts_model():
    """
    Load OmniVoice model ONCE and reuse it for all lines.
    """
    print("🔊 Loading OmniVoice TTS model...")
    if torch.cuda.is_available():
        print("💡 CUDA detected. Loading OmniVoice in FP16 on GPU...")
        device_map = "cuda:0"
        dtype = torch.float16
    else:
        print("⚠️ CUDA not available. Loading OmniVoice in FP32 on CPU (slow)...")
        device_map = "cpu"
        dtype = torch.float32

    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map=device_map,
        dtype=dtype
    )
    print("✅ TTS model loaded.\n")
    return model

def make_silence(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Return a numpy array of silence at the given sample rate."""
    n_samples = int(sample_rate * duration_sec)
    return np.zeros(n_samples, dtype=np.float32)

def run_tts_pipeline(script: Script):
    # ── Load model ONCE ──────────────────────────────────────────────────────
    model = load_tts_model()

    all_audio: list[np.ndarray] = []
    total = len(script.dialogue)

    for idx, item in enumerate(script.dialogue):
        speaker = item.speaker.strip()
        text    = item.line.strip()

        # Route to correct voice clone
        if "trump" in speaker.lower():
            ref_audio = TRUMP_REF_AUDIO
            ref_text  = TRUMP_REF_TEXT
        else:
            ref_audio = ELON_REF_AUDIO
            ref_text  = ELON_REF_TEXT

        print(f"[{idx+1}/{total}] 🎙️  {speaker}: {text[:90]}{'...' if len(text)>90 else ''}")

        try:
            # OmniVoice generation
            with torch.inference_mode():
                audio_segments = model.generate(
                    text=text,
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                )
        except Exception as e:
            print(f"  ❌ TTS failed for line {idx+1}: {e}")
            continue

        audio = np.array(audio_segments[0], dtype=np.float32)
        all_audio.append(audio)
        print(f"  ✅ Done — {len(audio)/OMNIVOICE_SR:.1f}s of audio")

        # Add silence gap between lines (not after last)
        if idx < total - 1:
            silence = make_silence(OMNIVOICE_SR, PAUSE_SEC)
            all_audio.append(silence)

    # ── Unload TTS model — free GPU VRAM before WhisperX loads ───────────────
    _unload_model(model, "OmniVoice TTS")

    if not all_audio:
        print("❌ No audio generated. Check your ref WAVs and GPU.")
        return

    final_audio = np.concatenate(all_audio, axis=0)
    sf.write(OUTPUT_AUDIO_PATH, final_audio, OMNIVOICE_SR)
    duration = len(final_audio) / OMNIVOICE_SR
    print(f"\n🎉 Podcast saved → {OUTPUT_AUDIO_PATH}  ({duration:.1f}s total)")

    # ── SPEED-UP LOGIC ───────────────────────────────────────────────────────
    print("\n⏩ Speeding up audio to 1.2x using SoX...")
    temp_output = "temp_podcast_1_2x.wav"
    try:
        # Use 'tempo' to speed up without changing the pitch of the voices
        subprocess.run(["sox", OUTPUT_AUDIO_PATH, temp_output, "tempo", "1.2"], check=True)

        # Replace original file with the sped-up version
        os.replace(temp_output, OUTPUT_AUDIO_PATH)

        print(f"✅ Audio successfully sped up to 1.2x! Overwrote {OUTPUT_AUDIO_PATH}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to speed up audio using SoX: {e}")
    except Exception as e:
        print(f"❌ Error during audio speed up: {e}")