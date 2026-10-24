from typing import AsyncIterator, Protocol

class STTAdapter(Protocol):
    async def transcribe_stream(self, pcm_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]: ...

class TTSAdapter(Protocol):
    async def synthesize(self, text: str) -> bytes: ...  # WAV bytes
