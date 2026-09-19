import os
import tempfile

import sounddevice as sd
from scipy.io.wavfile import write

from src.journey.engine import EnergyTurnEngine
from src.journey.energy import ENERGY_JOURNEY
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


def get_question_for_field(field):
    for section in ENERGY_JOURNEY["sections"]:
        if field in section["fields"]:
            return section["script"]

    return None


def main():
    stt = STTEngine()
    tts = TTSEngine()
    engine = EnergyTurnEngine()

    collected = {}

    opening = ENERGY_JOURNEY["opening_script"]

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

            # Terminal actions use the engine's response.
            if turn.action in {
                "complete",
                "close",
                "escalate",
            }:
                if turn.response:
                    print("AGENT:", turn.response)

                    speak(
                        tts,
                        turn.response,
                        "agent_response.mp3",
                    )

                print("\nCALL ENDED")
                print("FINAL COLLECTED DATA:", collected)
                break

            # For normal journey progression, use the exact
            # question defined by the Energy journey.
            if turn.next_field:
                next_question = get_question_for_field(
                    turn.next_field
                )

                if next_question:
                    print("AGENT:", next_question)

                    speak(
                        tts,
                        next_question,
                        "agent_question.mp3",
                    )
                else:
                    print("AGENT:", turn.response)

                    speak(
                        tts,
                        turn.response,
                        "agent_response.mp3",
                    )

            elif turn.response:
                print("AGENT:", turn.response)

                speak(
                    tts,
                    turn.response,
                    "agent_response.mp3",
                )

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)


if __name__ == "__main__":
    main()
