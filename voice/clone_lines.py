#!/workspace/video/clone/venv/bin/python
"""XTTS-v2 clone of Karthik's voice (consented; keep local). Usage: clone_lines.py jobs.json
jobs: [{id, text, expect, lang, out}] -> out wav + out.json (transcript, score, dur). Best of N seeds by whisper score."""
import json, os, re, sys, difflib
os.environ.setdefault("COQUI_TOS_AGREED", "1")
import numpy as np, torch, soundfile as sf
from num2words import num2words
torch.set_num_threads(os.cpu_count() or 4)
TRIES = int(os.environ.get("TRIES", 3))
def norm(s):
    if any("\u0900" <= ch <= "\u097f" for ch in s): return re.sub(r"[^\u0900-\u097f]", "", s)
    s = s.lower().replace("₹", " rupees ").replace("–", " to ")
    s = re.sub(r"\d+", lambda m: " " + num2words(int(m.group())) + " ", s)
    return re.sub(r"[^a-z]", "", s)
def score(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
cfg = json.load(open(sys.argv[1]))
from TTS.api import TTS
from faster_whisper import WhisperModel
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False); M = tts.synthesizer.tts_model
lat, emb = M.get_conditioning_latents(audio_path=cfg["ref"], gpt_cond_len=30, max_ref_length=30)
wm = WhisperModel("small", device="cpu", compute_type="int8")
for j in cfg["jobs"]:
    if os.path.exists(j["out"] + ".json") and not os.environ.get("FORCE"): continue
    best = None
    for k in range(TRIES):
        torch.manual_seed(1000 + 31 * k)
        o = M.inference(j["text"], j["lang"], lat, emb, temperature=0.65 if k == 0 else 0.55, repetition_penalty=5.0,
                        top_p=0.85, top_k=50, speed=j.get("speed", 1.0), enable_text_splitting=False)
        w = np.asarray(o["wav"], np.float32); tmp = f"{j['out']}.t{k}.wav"
        sf.write(tmp, np.concatenate([np.zeros(7200, np.float32), w]), 24000)
        segs, _ = wm.transcribe(tmp, language=j.get("wlang", "en"), beam_size=5, condition_on_previous_text=False)
        got = " ".join(s.text for s in segs).strip(); sc = score(j["expect"], got); d = len(w) / 24000
        cps = len(norm(j["expect"])) / d
        if cps < 5 or cps > 20: sc -= .15
        print(f"{j['id']} [{j['lang']}] take{k} {sc:.3f} {d:.2f}s | {got}", flush=True)
        if best is None or sc > best[0]: best = (sc, w, got, d)
        os.remove(tmp)
        if sc >= .95: break
    sc, w, got, d = best; sf.write(j["out"], w, 24000)
    json.dump(dict(transcript=got, score=round(sc, 3), dur=round(d, 2), lang=j["lang"], text=j["text"]), open(j["out"] + ".json", "w"))
