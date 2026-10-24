"""One live end-to-end run: SYNTHETIC customer clips -> Prisma -> Pipecat OrderFlow -> Timbre -> WhatsApp (wa.me)."""
import asyncio, base64, json, os, time, wave
from kiranavoice.envload import load_env_local; load_env_local()
from kiranavoice.adapters.gnani import GnaniPrismaSTT, GnaniTimbreTTS
from kiranavoice.pipeline import CallSession
from kiranavoice.whatsapp import WaMeSender
async def main():
    if not os.path.exists("audio/clips/customer_SYNTHETIC_04.wav"):
        t=GnaniTimbreTTS(voice="Deepak"); open("audio/clips/customer_SYNTHETIC_04.wav","wb").write(await t.synthesize("Bas itna"))
    evs=[]; os.makedirs("audio/e2e",exist_ok=True)
    async def emit(e):
        evs.append(e)
        if e["type"]=="transcript":
            print(e["role"].upper()+":", e["text"])
            if e.get("audio"): open(f"audio/e2e/agent_{sum(1 for x in evs if x.get('audio')):02d}.wav","wb").write(base64.b64decode(e["audio"]))
        elif e["type"]=="order": print("ORDER:", json.dumps(e["order"],ensure_ascii=False)); print("SEND:", e["send"]["sender"], e["send"]["ok"])
    s=CallSession(GnaniTimbreTTS(), WaMeSender(), emit, caller_id="9876543210")
    t0=time.perf_counter(); await s.start()
    for n in (1,2,4,3):
        w=wave.open(f"audio/clips/customer_SYNTHETIC_{n:02d}.wav"); pcm=w.readframes(w.getnframes())
        async def src(): yield pcm
        stt=GnaniPrismaSTT(sample_rate=w.getframerate())
        got=[t async for t in stt.transcribe_stream(src())]
        for t in got: await s.user_text(t)
        await asyncio.sleep(4)  # let Timbre reply finish
    await s.stop(); await asyncio.sleep(1)
    print("total_s", round(time.perf_counter()-t0,1), "order_ok", any(e["type"]=="order" for e in evs))
    json.dump([{k:v for k,v in e.items() if k!="audio"} for e in evs],open("audio/e2e/events.json","w"),ensure_ascii=False,indent=1)
asyncio.run(main())
