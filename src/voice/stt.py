from faster_whisper import WhisperModel


class STTEngine:
    def __init__(self, model_size="base.en"):
        self.model = WhisperModel(
            model_size,
            device="cuda",
            compute_type="float16",
        )

    def transcribe(self, audio_path):
        segments, info = self.model.transcribe(audio_path)

        text = " ".join(segment.text.strip() for segment in segments).strip()

        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
        }
