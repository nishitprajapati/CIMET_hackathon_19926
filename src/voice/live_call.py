import os
import tempfile

import sounddevice as sd
from scipy.io.wavfile import write

from src.journey.engine import EnergyTurnEngine
from src.voice.audio import play_audio
from src.voice.stt import STTEngine
from src.voice.tts import TTSEngine


SAMPLE_RATE = 16000
RECORD_SECONDS = 5


def record_audio():
    print("\nListening...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )

    sd.wait()

    path = tempfile.mktemp(suffix=".wav")
    write(path, SAMPLE_RATE, audio)

    return path


def speak(tts, text, output_path):
    tts.synthesize_sync(text, output_path)
    play_audio(output_path)


def main():
    stt = STTEngine()
    tts = TTSEngine()
    engine = EnergyTurnEngine()

    collected = {}

    opening = (
        "Hello, this is the energy support team. "
        "You recently started comparing energy options but did not complete "
        "the process. I can help finish it with you. Is now a good time?"
    )

    print("\nAGENT:", opening)

    speak(
        tts,
        opening,
        "agent_opening.mp3",
    )

    while True:
        audio_path = record_audio()

        try:
            result = stt.transcribe(audio_path)
            transcript = result["text"]

            print("CUSTOMER:", transcript)

            if not transcript:
                print("No speech detected.")
                continue

            turn = engine.process(
                transcript,
                collected,
            )

            collected.update(turn.extracted)

            print("ACTION:", turn.action)
            print("EXTRACTED:", turn.extracted)
            print("NEXT FIELD:", turn.next_field)
            print("ESCALATION:", turn.escalation_reason)
            print("CONFIDENCE:", turn.confidence)

            if turn.response:
                print("AGENT:", turn.response)

                speak(
                    tts,
                    turn.response,
                    "agent_response.mp3",
                )

            if turn.action in {
                "complete",
                "close",
                "escalate",
            }:
                print("\nCALL ENDED")
                print("FINAL COLLECTED DATA:", collected)
                break

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)


if __name__ == "__main__":
    main()
