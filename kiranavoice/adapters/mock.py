"""Mock adapters: zero network, zero credits."""
import io, math, struct, wave

class MockSTT:
    """Text-in: treats each incoming 'chunk' as an already-transcribed utterance."""
    async def transcribe_stream(self, chunks):
        async for c in chunks:
            yield c.decode() if isinstance(c, bytes) else c

class MockTTS:
    """Returns a short soft two-tone chime WAV (canned audio) instead of speech; UI also shows text."""
    async def synthesize(self, text: str) -> bytes:
        sr, dur = 16000, 0.25
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            frames = b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * (660 if n < sr * dur / 2 else 880) * n / sr)))
                              for n in range(int(sr * dur)))
            w.writeframes(frames)
        return buf.getvalue()
