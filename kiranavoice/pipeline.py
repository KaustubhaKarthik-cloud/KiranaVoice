"""Pipecat pipeline: STT transcripts -> OrderFlow -> TTS -> UI/audio out -> WhatsApp on close."""
import asyncio, base64
from pipecat.frames.frames import Frame, TranscriptionFrame, TextFrame, EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from .flow import OrderFlow
from .whatsapp import format_summary

class AgentReplyFrame(TextFrame):
    pass

class OrderFlowProcessor(FrameProcessor):
    def __init__(self, flow: OrderFlow, emit):
        super().__init__(); self.flow, self.emit = flow, emit
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            await self.emit({"type": "transcript", "role": "customer", "text": frame.text})
            reply = self.flow.handle(frame.text)
            await self.emit({"type": "items", "items": [vars(i) for i in self.flow.items], "state": self.flow.state})
            await self.push_frame(AgentReplyFrame(text=reply), direction)
        else:
            await self.push_frame(frame, direction)

class TTSOutProcessor(FrameProcessor):
    def __init__(self, tts, emit, flow, sender, shop):
        super().__init__(); self.tts, self.emit, self.flow, self.sender, self.shop = tts, emit, flow, sender, shop
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, AgentReplyFrame):
            try:
                wav = await self.tts.synthesize(frame.text)
            except Exception as e:
                wav = b''; await self.emit({"type": "error", "where": "tts", "message": type(e).__name__})
            await self.emit({"type": "transcript", "role": "agent", "text": frame.text,
                             "audio": base64.b64encode(wav).decode() if wav else None})
            if self.flow.state == "done" and self.flow.order:
                summary = format_summary(self.flow.order, self.shop)
                res = await asyncio.to_thread(self.sender.send, summary)
                await self.emit({"type": "order", "order": self.flow.order, "summary": summary, "send": res})
        else:
            await self.push_frame(frame, direction)

class CallSession:
    def __init__(self, tts, sender, emit, shop="Sharma Kirana", caller_id=None):
        self.flow = OrderFlow(shop, caller_id)
        self.pipeline = Pipeline([OrderFlowProcessor(self.flow, emit), TTSOutProcessor(tts, emit, self.flow, sender, shop)])
        self.task = PipelineTask(self.pipeline)
        self.emit, self.tts = emit, tts
    async def start(self):
        self.runner_task = asyncio.create_task(PipelineRunner(handle_sigint=False).run(self.task))
        greet = self.flow.greet()
        wav = await self.tts.synthesize(greet)
        await self.emit({"type": "transcript", "role": "agent", "text": greet, "audio": base64.b64encode(wav).decode()})
    async def user_text(self, text: str):
        await self.task.queue_frame(TranscriptionFrame(text=text, user_id="caller", timestamp=""))
    async def stop(self):
        await self.task.queue_frame(EndFrame())
