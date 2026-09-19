import asyncio

import edge_tts


class TTSEngine:
    def __init__(self, voice="en-US-AriaNeural"):
        self.voice = voice

    async def synthesize(self, text, output_path):
        communicate = edge_tts.Communicate(
            text,
            self.voice,
        )

        await communicate.save(output_path)

    def synthesize_sync(self, text, output_path):
        asyncio.run(self.synthesize(text, output_path))
