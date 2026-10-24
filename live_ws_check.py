"""Headless check of the browser path in --live: same /ws protocol as app.js (mic_start + binary PCM + typed 'say')."""
import asyncio, json, wave, base64, time, websockets
async def main():
    async with websockets.connect("ws://127.0.0.1:8766/ws", max_size=2**24) as ws:
        evs=[]
        async def rx():
            async for m in ws:
                e=json.loads(m); evs.append(e)
                a=e.get("audio"); print(e["type"], e.get("role",""), e.get("text", e.get("message", e.get("on",""))), f"[audio {len(base64.b64decode(a))} B]" if a else "")
        r=asyncio.create_task(rx())
        await ws.send(json.dumps({"type":"answer"})); await asyncio.sleep(3)
        await ws.send(json.dumps({"type":"mic_start","sample_rate":16000}))
        w=wave.open("audio/clips/customer_SYNTHETIC_01.wav"); pcm=w.readframes(w.getnframes())+b"\0"*32000
        for i in range(0,len(pcm),1024): await ws.send(pcm[i:i+1024]); await asyncio.sleep(0.032)
        await asyncio.sleep(5)
        await ws.send(json.dumps({"type":"mic_stop"}))
        await ws.send(json.dumps({"type":"say","text":"Nahi nahi, 12 ande"})); await asyncio.sleep(5)
        await ws.send(json.dumps({"type":"hangup"})); await asyncio.sleep(1); r.cancel()
        ag=[e for e in evs if e.get("role")=="agent"]
        print("SUMMARY agent_replies",len(ag),"with_audio",sum(1 for e in ag if e.get("audio") and len(base64.b64decode(e["audio"]))>1000),"errors",[e for e in evs if e["type"]=="error"])
asyncio.run(main())
