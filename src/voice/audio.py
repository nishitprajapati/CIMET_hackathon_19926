import subprocess


def play_audio(audio_path):
    subprocess.run(
        [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            audio_path,
        ],
        check=True,
    )


if __name__ == "__main__":
    print("Testing synchronous audio playback...")
    play_audio("tts_test.mp3")
    print("Playback finished")
