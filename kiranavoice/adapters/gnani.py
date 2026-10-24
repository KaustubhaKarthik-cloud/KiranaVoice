"""Gnani Prisma v2.5 (STT realtime) and Timbre v2.5 (TTS realtime) adapters.

Written from public docs; message formats VERIFIED live on 2026-10-22 (realtime WS for both):
  STT: https://docs.gnani.ai/api/STT/stt-websocket   wss://api.vachana.ai/stt/v3/stream
  TTS: https://docs.gnani.ai/api/TTS/tts-websocket   wss://api.vachana.ai/api/v1/tts
Evon is deliberately NOT used (weights-only, not on the API).
"""
import asyncio, base64, io, json, os, time, wave
import websockets

STT_URL = os.getenv("GNANI_STT_URL", "wss://api.vachana.ai/stt/v3/stream")
TTS_URL = os.getenv("GNANI_TTS_URL", "wss://api.vachana.ai/api/v1/tts")

def _key():
    k = os.getenv("GNANI_API_KEY")
    if not k:
        raise RuntimeError("GNANI_API_KEY not set; use --mock")
    return k

class GnaniPrismaSTT:
    def __init__(self, lang="hi-IN", sample_rate=16000, telephony=True):
        self.headers = {"x-api-key-id": _key(), "lang_code": lang, "x-sample-rate": str(sample_rate),
                        "x-format": "transcribe"}
        if telephony:  # docs' telephony guidance
            self.headers.update({"x-vad-threshold": "0.7", "x-min-silence-ms": "500"})
        self.sr, self.pace, self.trailing_silence, self.close_after_s = sample_rate, True, True, 2.5
        self.last_audio_at = self.transcript_at = None
        self.bias = ["atta", "chawal", "cheeni", "dal", "fortune", "ande", "maggi", "kilo", "litre", "packet"]
        self.headers.update({"x-bias-list": json.dumps(self.bias), "x-bias-score": "1.0"})

    async def transcribe_stream(self, pcm_chunks):
        """pcm_chunks: 16-bit mono PCM; docs say send 1024-byte frames at real-time cadence."""
        async with websockets.connect(STT_URL, additional_headers=self.headers) as ws:
            q: asyncio.Queue = asyncio.Queue()

            async def sender():
                async for chunk in pcm_chunks:
                    for i in range(0, len(chunk), 1024):
                        await ws.send(chunk[i:i + 1024])
                        if self.pace:
                            await asyncio.sleep(512 / self.sr)  # real-time cadence per docs
                    self.last_audio_at = time.perf_counter()
                if self.trailing_silence:
                    await ws.send(b"\x00" * self.sr * 2)  # 1 s silence closes the VAD segment
                await asyncio.sleep(self.close_after_s)
                await ws.close()

            async def receiver():
                try:
                    async for msg in ws:
                        if not isinstance(msg, str):
                            continue
                        ev = json.loads(msg)
                        # verified live 2026-10-22: connected -> speech_start -> {"type":"transcript","text",...,"is_final":true,"latency"}
                        if ev.get("type") == "transcript" and ev.get("is_final") and ev.get("text"):
                            self.last_event = {k: ev.get(k) for k in ("latency", "audio_duration_ms")}
                            self.transcript_at = time.perf_counter()
                            await q.put(ev["text"])
                        elif ev.get("type") == "error":
                            raise RuntimeError(f"Prisma error: {ev.get('message')}")
                except websockets.ConnectionClosed:
                    pass
                finally:
                    await q.put(None)

            tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
            while (t := await q.get()) is not None:
                yield t
            for x in tasks:
                x.cancel()

class GnaniTimbreTTS:
    def __init__(self, voice="Nalini", language="hi-en", sample_rate=16000):
        self.voice, self.language, self.sr = voice, language, sample_rate

    async def synthesize(self, text: str) -> bytes:
        req = {"text": text, "voice": self.voice, "model": "timbre-v2.5", "language": self.language, "speed": 1.0,
               "audio_config": {"sample_rate": self.sr, "num_channels": 1, "sample_width": 2,
                                "encoding": "linear_pcm", "container": "raw"}}
        pcm = bytearray(); self.first_audio_at = None; self.sent_at = time.perf_counter()
        async with websockets.connect(TTS_URL, additional_headers={"X-API-Key-ID": _key()}) as ws:
            await ws.send(json.dumps(req))
            async for msg in ws:
                ev = json.loads(msg)
                # verified live 2026-10-22: {"type":"start"} then {"type":"audio","data":{"chunk_index","audio":<b64 PCM>}}
                if ev.get("type") == "audio" and isinstance(ev.get("data"), dict) and ev["data"].get("audio"):
                    if self.first_audio_at is None:
                        self.first_audio_at = time.perf_counter()
                    pcm += base64.b64decode(ev["data"]["audio"])
                elif ev.get("type") == "error":
                    raise RuntimeError(f"Timbre error: {ev.get('message')}")
                if ev.get("is_final") or ev.get("type") in ("end", "complete", "done") or (isinstance(ev.get("data"), dict) and ev["data"].get("is_final")):
                    break
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(self.sr); w.writeframes(bytes(pcm))
        return buf.getvalue()
