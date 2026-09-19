import tempfile

import sounddevice as sd
from scipy.io.wavfile import write

from src.voice.stt import STTEngine


SAMPLE_RATE = 16000
DURATION = 5


print("Speak now for 5 seconds...")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
)

sd.wait()

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
    audio_path = temp.name

write(audio_path, SAMPLE_RATE, audio)

print("Transcribing...")

engine = STTEngine()
result = engine.transcribe(audio_path)

print("TRANSCRIPT:", result["text"])
print("LANGUAGE:", result["language"])
print("CONFIDENCE:", result["language_probability"])
