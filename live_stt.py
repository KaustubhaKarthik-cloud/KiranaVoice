"""Live Prisma v2.5 realtime STT on 3 SYNTHETIC (Timbre-generated) clips. WER vs hand-written Devanagari refs."""
import asyncio, json, re, sys, time, wave
from kiranavoice.envload import load_env_local; load_env_local()
from kiranavoice.adapters.gnani import GnaniPrismaSTT
CLIPS=[("audio/clips/customer_SYNTHETIC_01.wav","भैया दो किलो आटा एक लीटर फॉर्च्यून ऑयल और छह अंडे भेज दो"),
       ("audio/clips/customer_SYNTHETIC_02.wav","नहीं नहीं बारह अंडे"),
       ("audio/clips/customer_SYNTHETIC_03.wav","मेरा नाम रमेश")]
NUM={"1":"एक","2":"दो","6":"छह","12":"बारह","१":"एक","२":"दो","६":"छह","१२":"बारह"}
def toks(s): return [NUM.get(t,t) for t in re.sub(r"[।,.!?]"," ",s).split()]
def wer(r,h):
    r,h=toks(r),toks(h); d=list(range(len(h)+1))
    for i in range(1,len(r)+1):
        p,d[0]=d[0],i
        for j in range(1,len(h)+1): p,d[j]=d[j],min(d[j]+1,d[j-1]+1,p+(r[i-1]!=h[j-1]))
    return d[len(h)]/len(r), len(r)
async def one(fn,ref):
    w=wave.open(fn); pcm=w.readframes(w.getnframes())
    stt=GnaniPrismaSTT(lang="hi-IN",sample_rate=w.getframerate())
    async def src(): yield pcm
    out=[]
    async def run():
        async for t in stt.transcribe_stream(src()): out.append(t)
    try: await asyncio.wait_for(run(), timeout=20)
    except asyncio.TimeoutError: pass
    hyp=" ".join(out); e,n=wer(ref,hyp)
    lat=round((stt.transcript_at-stt.last_audio_at)*1000) if stt.transcript_at and stt.last_audio_at else None
    return {"file":fn,"ref":ref,"hyp":hyp,"wer":round(e,3),"ref_words":n,"ms_end_of_audio_to_final":lat,"server_latency_ms":(stt.last_event or {}).get("latency") if hasattr(stt,"last_event") else None}
async def main():
    res=[]
    for fn,ref in CLIPS:
        try: r=await one(fn,ref)
        except Exception as e: print("ERR",fn,type(e).__name__,str(e)[:200]); sys.exit("stopping on error")
        print(json.dumps(r,ensure_ascii=False)); res.append(r)
    json.dump(res,open("audio/stt_results.json","w"),indent=1,ensure_ascii=False)
asyncio.run(main())
