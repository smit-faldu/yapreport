import os
import json
import gc
import torch
import re
from src.config import WHISPER_MODEL

_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

def _flush_gpu(label: str = ""):
    """Drain all async CUDA ops and release the allocator cache."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
    if label:
        print(f"🗑️  {label} unloaded — GPU memory freed.")

def transcribe(audio_path, dialogue):
    print("🎙  Transcribing with WhisperX...")
    import whisperx

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    # ── Step 1: ASR transcription ─────────────────────────────────────────────
    with torch.inference_mode():
        model = whisperx.load_model(WHISPER_MODEL, device, compute_type=compute_type)
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, batch_size=8)
    del model
    _flush_gpu("WhisperX ASR model")

    # ── Step 2: Word-level alignment ──────────────────────────────────────────
    with torch.inference_mode():
        model_a, meta = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, meta, audio, device, return_char_alignments=False)
    del model_a
    _flush_gpu("WhisperX alignment model")

    # ── Step 3: Map words → speakers from script ──────────────────────────────
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": w.get("start", 0), "end": w.get("end", 0)})

    # Script alignment mapping
    script_tokens = []
    for turn in dialogue:
        for raw_word in turn["line"].split():
            clean_word = re.sub(r'[^a-z0-9]', '', raw_word.lower())
            if clean_word:
                script_tokens.append({"text": clean_word, "speaker": turn["speaker"].lower()})

    script_idx = 0
    for w in words:
        clean_w = re.sub(r'[^a-z0-9]', '', w["word"].lower())
        if not clean_w:
            w["speaker"] = script_tokens[min(script_idx, len(script_tokens)-1)]["speaker"]
            continue

        match_found = False
        for offset in range(15):
            check_idx = script_idx + offset
            if check_idx >= len(script_tokens): break
            if script_tokens[check_idx]["text"] == clean_w:
                w["speaker"] = script_tokens[check_idx]["speaker"]
                script_idx = check_idx + 1
                match_found = True
                break

        if not match_found:
            safe_idx = min(script_idx, len(script_tokens) - 1)
            w["speaker"] = script_tokens[safe_idx]["speaker"]

    print(f"   ✅ {len(words)} words aligned.")
    return words