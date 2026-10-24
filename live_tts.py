"""Live Timbre v2.5: synthesize demo lines, record time-to-first-audio. Key never printed."""
import asyncio, json, time, sys
from kiranavoice.envload import load_env_local; load_env_local()
from kiranavoice.adapters.gnani import GnaniTimbreTTS
AGENT=["Namaste! Sharma Kirana se bol rahe hain. Bataiye, kya bhejna hai?",
 "Theek hai, do kilo atta, ek litre Fortune oil, chhe ande. Sahi hai?",
 "Done, baarah ande. Aur kuch?","Aapka naam bata dijiye?","Aur phone number?",
 "Shukriya Ramesh ji! Order note ho gaya, thodi der mein bhej denge."]
CUST=["Bhaiya, do kilo atta, ek litre Fortune oil aur chhe ande bhej do","Nahi nahi, baarah ande","Mera naam Ramesh"]
async def main():
    t=GnaniTimbreTTS(voice="Nalini", language="hi-en"); res=[]; errs=0
    for kind,lines,voice in (("agent",AGENT,"Nalini"),("customer_SYNTHETIC",CUST,"Deepak")):
        t.voice=voice
        for i,txt in enumerate(lines,1):
            try:
                wav=await t.synthesize(txt)
            except Exception as e:
                errs+=1; print("ERR",kind,i,type(e).__name__,str(e)[:200]); 
                if errs>=2: sys.exit("stopping: repeated errors")
                continue
            d="audio/timbre" if kind=="agent" else "audio/clips"
            fn=f"{d}/{kind}_{i:02d}.wav"; open(fn,"wb").write(wav)
            ttfb=(t.first_audio_at-t.sent_at)*1000 if t.first_audio_at else None
            r={"file":fn,"text":txt,"voice":voice,"ttfb_ms":round(ttfb) if ttfb else None,"secs":round((len(wav)-44)/32000,2)}; res.append(r); print(r)
    json.dump(res,open("audio/tts_results.json","w"),indent=1,ensure_ascii=False)
asyncio.run(main())
