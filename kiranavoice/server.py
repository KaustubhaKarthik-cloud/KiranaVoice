import asyncio, json, os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .pipeline import CallSession
from .whatsapp import get_sender

STATIC = Path(__file__).resolve().parent.parent / "static"
DEMO_SCRIPT = ["Bhaiya, 2 kilo atta, 1 litre Fortune oil aur 6 ande bhej do", "Nahi nahi, 12 ande",
               "Bas itna", "Mera naam Ramesh", "98765 43210"]

def make_app(mode="mock", sender_kind="mock"):
    app = FastAPI(title="KiranaVoice")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    def tts():
        if mode == "mock":
            from .adapters.mock import MockTTS; return MockTTS()
        from .adapters.gnani import GnaniTimbreTTS; return GnaniTimbreTTS()

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/config")
    def config():
        return {"mode": mode, "sender": sender_kind, "demo_script": DEMO_SCRIPT}

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept()
        async def emit(ev): await sock.send_text(json.dumps(ev, ensure_ascii=False))
        session = None; audio_q: asyncio.Queue | None = None; stt_task = None
        try:
            while True:
                msg = await sock.receive()
                if msg.get("bytes") is not None and audio_q is not None:
                    await audio_q.put(msg["bytes"]); continue
                if msg.get("type") == "websocket.disconnect":
                    break
                data = json.loads(msg.get("text") or "{}")
                if data.get("type") == "answer":
                    if session is None:
                        session = CallSession(tts(), get_sender(sender_kind), emit, caller_id=None)
                        await session.start()
                elif data.get("type") == "mic_start" and session and mode == "live" and stt_task is None:
                    from .adapters.gnani import GnaniPrismaSTT
                    audio_q = asyncio.Queue()
                    stt = GnaniPrismaSTT(sample_rate=int(data.get("sample_rate", 16000)))
                    stt.pace = False  # browser mic already arrives in real time
                    async def chunks(q=audio_q):
                        while (c := await q.get()) is not None: yield c
                    async def run_stt(stt=stt, chunks=chunks):
                        try:
                            async for t in stt.transcribe_stream(chunks()):
                                await session.user_text(t)
                        except Exception as e:  # surface, never include secrets
                            await emit({"type": "error", "where": "stt", "message": type(e).__name__})
                    stt_task = asyncio.create_task(run_stt())
                    await emit({"type": "mic", "on": True})
                elif data.get("type") == "mic_stop" and audio_q is not None:
                    await audio_q.put(None); audio_q = None; stt_task = None
                    await emit({"type": "mic", "on": False})
                elif data.get("type") == "say" and session:
                    await session.user_text(data["text"])  # typed input; replies voiced by Timbre in --live
                elif data.get("type") == "hangup" and session:
                    if audio_q: await audio_q.put(None)
                    await session.stop(); session = None
        except WebSocketDisconnect:
            pass
        finally:
            if stt_task: stt_task.cancel()
            if session: await session.stop()
    return app
