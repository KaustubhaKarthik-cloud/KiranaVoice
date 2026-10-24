import asyncio, json, os, time, wave
import websockets
from kiranavoice.envload import load_env_local; load_env_local()
async def main(fn):
    w=wave.open(fn); pcm=w.readframes(w.getnframes()); sr=w.getframerate()
    h={"x-api-key-id":os.environ["GNANI_API_KEY"],"lang_code":"hi-IN","x-sample-rate":str(sr)}
    async with websockets.connect("wss://api.vachana.ai/stt/v3/stream",additional_headers=h) as ws:
        async def send():
            for i in range(0,len(pcm),1024):
                await ws.send(pcm[i:i+1024]); await asyncio.sleep(512/sr)
            await ws.send(b"\x00"*sr*2)  # 1 s silence to close VAD segment
        t=asyncio.create_task(send()); t0=time.perf_counter()
        try:
            while True:
                m=await asyncio.wait_for(ws.recv(),timeout=8)
                print(round(time.perf_counter()-t0,2), m if isinstance(m,str) and len(m)<400 else type(m))
        except Exception as e: print("end:",type(e).__name__, str(e)[:150])
asyncio.run(main("audio/clips/customer_SYNTHETIC_02.wav"))
