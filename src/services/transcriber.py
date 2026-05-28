import os
import json
import gc
import torch
import re
import difflib  # <-- NEW IMPORT
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

    # ── Step 3: Map words → speakers from script (ROBUST GLOBAL ALIGNMENT) ────
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": w.get("start", 0), "end": w.get("end", 0)})

    script_tokens = []
    for turn in dialogue:
        for raw_word in turn["line"].split():
            clean_word = re.sub(r'[^a-z0-9]', '', raw_word.lower())
            if clean_word:
                script_tokens.append({"text": clean_word, "speaker": turn["speaker"].lower()})

    if not words or not script_tokens:
        return words

    # Extract clean text lists for diffing
    whisper_text = [re.sub(r'[^a-z0-9]', '', w["word"].lower()) for w in words]
    script_text = [t["text"] for t in script_tokens]

    # Initialize all words with no speaker
    for w in words:
        w["speaker"] = None

    # Use difflib to find global matching blocks (bypasses skipped/mumbled lines gracefully)
    sm = difflib.SequenceMatcher(None, whisper_text, script_text)
    
    for match in sm.get_matching_blocks():
        for i in range(match.size):
            w_idx = match.a + i
            s_idx = match.b + i
            words[w_idx]["speaker"] = script_tokens[s_idx]["speaker"]

    # Forward/Backward fill for words that Whisper mispronounced and weren't exact matches
    last_speaker = script_tokens[0]["speaker"] 
    for w in words:
        if w["speaker"] is not None:
            last_speaker = w["speaker"]
        else:
            w["speaker"] = last_speaker
            
    # Quick backward pass to catch any unmatched words at the very beginning
    last_speaker = words[-1]["speaker"] if words[-1]["speaker"] else script_tokens[-1]["speaker"]
    for w in reversed(words):
        if w["speaker"] is not None:
            last_speaker = w["speaker"]
        else:
            w["speaker"] = last_speaker

    print(f"   ✅ {len(words)} words aligned.")
    return words