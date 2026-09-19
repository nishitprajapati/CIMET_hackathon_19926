from src.voice.tts import TTSEngine

engine = TTSEngine()

engine.synthesize_sync(
    "Hello, this is the energy support team. Is now a good time?",
    "tts_test.mp3",
)

print("TTS audio generated successfully")
