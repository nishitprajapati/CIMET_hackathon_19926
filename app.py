import base64
import os
import subprocess
import tempfile
import threading
import time
import wave

import numpy as np
import streamlit as st
from scipy.signal import resample_poly
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from src.journey.energy import ENERGY_JOURNEY
from src.journey.engine import EnergyTurnEngine
from src.voice.stt import STTEngine
from src.voice.tts import TTSEngine


# ============================================================
# CONFIG
# ============================================================

SAMPLE_RATE = 16000
LISTEN_SECONDS = 5.0
WEBRTC_KEY = "energy_voice_call"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Energy Journey",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# THREAD-SAFE MICROPHONE BUFFER
# ============================================================

class MicrophoneBuffer:

    def __init__(self):
        self.lock = threading.Lock()
        self.frames = []
        self.sample_rate = None
        self.enabled = False

    def enable(self):
        with self.lock:
            self.frames = []
            self.sample_rate = None
            self.enabled = True

    def disable(self):
        with self.lock:
            self.enabled = False

    def clear(self):
        with self.lock:
            self.frames = []
            self.sample_rate = None

    def add_frame(self, frame):

        with self.lock:

            if not self.enabled:
                return

            audio = frame.to_ndarray()

            if audio.ndim == 2:

                if audio.shape[0] > 1:
                    audio = np.mean(
                        audio,
                        axis=0,
                    )
                else:
                    audio = audio[0]

            audio = np.asarray(
                audio,
                dtype=np.float32,
            )

            self.frames.append(audio)

            if self.sample_rate is None:
                self.sample_rate = frame.sample_rate

    def duration(self):

        with self.lock:

            if (
                not self.frames
                or not self.sample_rate
            ):
                return 0.0

            total_samples = sum(
                len(frame)
                for frame in self.frames
            )

            return total_samples / self.sample_rate

    def consume(self):

        with self.lock:

            if (
                not self.frames
                or not self.sample_rate
            ):
                return None

            frames = list(self.frames)
            sample_rate = self.sample_rate

            self.frames = []
            self.sample_rate = None
            self.enabled = False

        audio = np.concatenate(frames)

        return audio, sample_rate


MIC_BUFFER = MicrophoneBuffer()


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state():

    defaults = {
        "call_active": False,
        "call_ended": False,
        "processing": False,

        "collected": {},
        "conversation": [],

        "stt": None,
        "tts": None,
        "engine": None,

        "agent_audio": None,
        "agent_audio_id": 0,
        "rendered_audio_id": -1,

        "agent_speaking_until": 0.0,

        "error": None,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


# ============================================================
# GLOBAL CSS
# ============================================================

st.html(
    """
    <style>

    /* Main page */

    .stApp {
        background:
            radial-gradient(
                circle at 15% 10%,
                rgba(24, 105, 72, 0.20),
                transparent 32%
            ),
            radial-gradient(
                circle at 85% 85%,
                rgba(25, 80, 70, 0.14),
                transparent 35%
            ),
            #06100d;
    }

    .block-container {
        max-width: 860px;
        padding-top: 35px;
        padding-bottom: 50px;
    }


    /* Header */

    .energy-header {
        text-align: center;
        margin-bottom: 36px;
    }

    .energy-title {
        color: #f4f8f6;
        font-size: 44px;
        font-weight: 750;
        letter-spacing: -1.8px;
        line-height: 1.1;
        margin: 0;
    }

    .energy-subtitle {
        color: #8da49a;
        font-size: 16px;
        margin-top: 10px;
    }


    /* Start screen */

    .ready-card {
        text-align: center;
        padding: 52px 20px 30px 20px;
    }

    .ready-text {
        color: #b7c7c0;
        font-size: 16px;
        line-height: 1.6;
    }


    /* Status */

    .call-status {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 9px;

        width: fit-content;

        margin: 0 auto 28px auto;

        padding: 9px 16px;

        border-radius: 999px;

        background: rgba(52, 170, 111, 0.12);
        border: 1px solid rgba(84, 203, 143, 0.22);

        color: #8ee2b4;

        font-size: 13px;
        font-weight: 600;
    }

    .status-dot {
        width: 8px;
        height: 8px;

        border-radius: 50%;

        background: #55d994;

        box-shadow:
            0 0 10px rgba(85, 217, 148, 0.75);
    }


    /* Conversation */

    .conversation {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 20px;
    }

    .message-row {
        display: flex;
        width: 100%;
    }

    .message-row.agent {
        justify-content: flex-start;
    }

    .message-row.customer {
        justify-content: flex-end;
    }

    .message-container {
        max-width: 74%;
    }

    .message-label {
        color: #70877d;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 5px;
    }

    .message-row.customer .message-label {
        text-align: right;
    }

    .message-bubble {
        padding: 13px 17px;
        border-radius: 17px;
        font-size: 15px;
        line-height: 1.55;
    }

    .agent-bubble {
        color: #e7efeb;
        background: rgba(255, 255, 255, 0.065);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-bottom-left-radius: 5px;
    }

    .customer-bubble {
        color: #e7f7ee;
        background: rgba(45, 135, 94, 0.22);
        border: 1px solid rgba(80, 180, 125, 0.20);
        border-bottom-right-radius: 5px;
    }


    /* Listening */

    .listening-state {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;

        padding: 20px;

        color: #71dca1;

        font-size: 15px;
        font-weight: 600;
    }

    .listening-dot {
        width: 9px;
        height: 9px;

        border-radius: 50%;

        background: #5be69a;

        box-shadow:
            0 0 15px rgba(91, 230, 154, 0.85);

        animation: listeningPulse 1.2s infinite;
    }

    @keyframes listeningPulse {

        0% {
            transform: scale(0.8);
            opacity: 0.4;
        }

        50% {
            transform: scale(1.15);
            opacity: 1;
        }

        100% {
            transform: scale(0.8);
            opacity: 0.4;
        }
    }


    /* Speaking / processing */

    .speaking-state {
        text-align: center;

        padding: 20px;

        color: #80958c;

        font-size: 14px;
    }


    /* Start button */

    div.stButton > button {
        width: 100%;
        height: 50px;

        border-radius: 999px;

        border: 1px solid rgba(90, 215, 150, 0.35);

        background: #23895e;

        color: white;

        font-size: 15px;
        font-weight: 650;
    }

    div.stButton > button:hover {
        background: #2b9b6d;
        border-color: rgba(110, 235, 170, 0.55);
    }


    /* Hide WebRTC visual controls */

    iframe[title="streamlit_webrtc.streamlit_webrtc"] {
        height: 1px !important;
        min-height: 1px !important;
        max-height: 1px !important;

        width: 1px !important;
        min-width: 1px !important;
        max-width: 1px !important;

        opacity: 0 !important;

        position: absolute !important;
        left: -10000px !important;
        top: -10000px !important;

        pointer-events: none !important;
    }


    /* Hide Streamlit audio controls */

    audio {
        display: none !important;
    }


    /* Final data */

    .final-card {
        margin-top: 30px;
        padding: 20px;

        border-radius: 16px;

        background: rgba(255, 255, 255, 0.04);

        border: 1px solid rgba(255, 255, 255, 0.07);
    }

    .final-title {
        color: #8da49a;

        font-size: 11px;
        font-weight: 650;

        letter-spacing: 0.08em;
        text-transform: uppercase;

        margin-bottom: 12px;
    }

    </style>
    """
)


# ============================================================
# AUDIO HELPERS
# ============================================================

def get_audio_duration(audio_path):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(
        result.stdout.strip()
    )


def create_agent_audio(text):

    output_path = tempfile.mktemp(
        suffix=".mp3"
    )

    st.session_state.tts.synthesize_sync(
        text,
        output_path,
    )

    with open(
        output_path,
        "rb",
    ) as audio_file:

        audio_bytes = audio_file.read()

    duration = get_audio_duration(
        output_path
    )

    try:
        os.remove(output_path)
    except OSError:
        pass

    return audio_bytes, duration


def speak_agent(text):

    if not text:
        return

    audio_bytes, duration = create_agent_audio(
        text
    )

    st.session_state.agent_audio = audio_bytes

    st.session_state.agent_audio_id += 1

    st.session_state.agent_speaking_until = (
        time.monotonic()
        + duration
        + 0.20
    )

    MIC_BUFFER.disable()
    MIC_BUFFER.clear()


# ============================================================
# AUDIO PLAYER
# ============================================================

def render_agent_audio():

    if not st.session_state.agent_audio:
        return

    audio_b64 = base64.b64encode(
        st.session_state.agent_audio
    ).decode("utf-8")

    audio_id = (
        st.session_state.agent_audio_id
    )

    audio_html = f"""
    <!DOCTYPE html>

    <html>

    <body
        style="
            margin:0;
            padding:0;
            background:transparent;
            overflow:hidden;
        "
    >

    <audio
        id="agent_audio_{audio_id}"
        autoplay
        playsinline
    >

        <source
            src="data:audio/mpeg;base64,{audio_b64}"
            type="audio/mpeg"
        >

    </audio>

    <script>

    const audio =
        document.getElementById(
            "agent_audio_{audio_id}"
        );

    if (audio) {{

        audio.volume = 1.0;

        const playAudio = () => {{
            audio.play().catch(() => {{}});
        }};

        playAudio();

        audio.addEventListener(
            "canplaythrough",
            playAudio,
            {{ once: true }}
        );
    }}

    </script>

    </body>

    </html>
    """

    st.iframe(
        audio_html,
        height=1,
        scrolling=False,
    )


# ============================================================
# JOURNEY HELPERS
# ============================================================

def get_question_for_field(field):

    for section in ENERGY_JOURNEY["sections"]:

        if field in section["fields"]:
            return section["script"]

    return None


# ============================================================
# START CALL
# ============================================================

def start_call():

    st.session_state.stt = STTEngine()
    st.session_state.tts = TTSEngine()
    st.session_state.engine = EnergyTurnEngine()

    st.session_state.call_active = True
    st.session_state.call_ended = False
    st.session_state.processing = False

    st.session_state.collected = {}
    st.session_state.conversation = []

    st.session_state.agent_audio = None
    st.session_state.agent_audio_id = 0
    st.session_state.rendered_audio_id = -1

    st.session_state.error = None

    MIC_BUFFER.disable()
    MIC_BUFFER.clear()

    opening = (
        ENERGY_JOURNEY["opening_script"]
    )

    st.session_state.conversation.append(
        {
            "speaker": "agent",
            "text": opening,
        }
    )

    speak_agent(opening)


# ============================================================
# AUDIO -> WAV
# ============================================================

def audio_to_wav(
    audio,
    source_rate,
):

    audio = np.asarray(
        audio,
        dtype=np.float32,
    )

    if audio.ndim > 1:

        audio = np.mean(
            audio,
            axis=1,
        )

    if source_rate != SAMPLE_RATE:

        audio = resample_poly(
            audio,
            SAMPLE_RATE,
            source_rate,
        )

    audio = np.clip(
        audio,
        -32768,
        32767,
    )

    audio = audio.astype(
        np.int16
    )

    output_path = tempfile.mktemp(
        suffix=".wav"
    )

    with wave.open(
        output_path,
        "wb",
    ) as wav_file:

        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(
            SAMPLE_RATE
        )

        wav_file.writeframes(
            audio.tobytes()
        )

    return output_path


# ============================================================
# PROCESS CUSTOMER SPEECH
# ============================================================

def process_customer_audio():

    audio_data = MIC_BUFFER.consume()

    if audio_data is None:
        return

    audio, source_rate = audio_data

    wav_path = None

    st.session_state.processing = True

    try:

        wav_path = audio_to_wav(
            audio,
            source_rate,
        )

        result = (
            st.session_state.stt.transcribe(
                wav_path
            )
        )

        transcript = (
            result.get(
                "text",
                "",
            )
            .strip()
        )

        # No speech detected.
        if not transcript:

            st.session_state.processing = False

            MIC_BUFFER.clear()
            MIC_BUFFER.enable()

            return

        # Add customer message.
        st.session_state.conversation.append(
            {
                "speaker": "customer",
                "text": transcript,
            }
        )

        # Journey engine.
        turn = (
            st.session_state.engine.process(
                transcript,
                st.session_state.collected,
            )
        )

        st.session_state.collected.update(
            turn.extracted
        )

        # ----------------------------------------------------
        # COMPLETE
        # ----------------------------------------------------

        if turn.action == "complete":

            response = turn.response

            st.session_state.conversation.append(
                {
                    "speaker": "agent",
                    "text": response,
                }
            )

            speak_agent(response)

            st.session_state.call_active = False
            st.session_state.call_ended = True
            st.session_state.processing = False

            return

        # ----------------------------------------------------
        # CLOSE
        # ----------------------------------------------------

        if turn.action == "close":

            response = turn.response

            st.session_state.conversation.append(
                {
                    "speaker": "agent",
                    "text": response,
                }
            )

            speak_agent(response)

            st.session_state.call_active = False
            st.session_state.call_ended = True
            st.session_state.processing = False

            return

        # ----------------------------------------------------
        # ESCALATE
        # ----------------------------------------------------

        if turn.action == "escalate":

            response = turn.response

            st.session_state.conversation.append(
                {
                    "speaker": "agent",
                    "text": response,
                }
            )

            speak_agent(response)

            st.session_state.call_active = False
            st.session_state.call_ended = True
            st.session_state.processing = False

            return

        # ----------------------------------------------------
        # CONTINUE
        # ----------------------------------------------------

        next_question = None

        if turn.next_field:

            next_question = (
                get_question_for_field(
                    turn.next_field
                )
            )

        response = (
            next_question
            if next_question
            else turn.response
        )

        if response:

            st.session_state.conversation.append(
                {
                    "speaker": "agent",
                    "text": response,
                }
            )

            speak_agent(response)

        st.session_state.processing = False

    except Exception as exc:

        st.session_state.error = str(exc)

        st.session_state.processing = False
        st.session_state.call_active = False
        st.session_state.call_ended = True

        MIC_BUFFER.disable()

    finally:

        if wav_path:

            try:
                os.remove(wav_path)
            except OSError:
                pass


# ============================================================
# WEBRTC CALLBACK
# ============================================================

def audio_frame_callback(frame):

    try:
        MIC_BUFFER.add_frame(frame)
    except Exception:
        pass

    return frame


# ============================================================
# HEADER
# ============================================================

st.html(
    """
    <div class="energy-header">
        <div class="energy-title">
            Energy Journey
        </div>

        <div class="energy-subtitle">
            Customer recovery assistant
        </div>
    </div>
    """
)


# ============================================================
# START SCREEN
# ============================================================

if (
    not st.session_state.call_active
    and not st.session_state.call_ended
):

    st.html(
        """
        <div class="ready-card">
            <div class="ready-text">
                Ready to continue a customer's
                interrupted energy journey.
            </div>
        </div>
        """
    )

    if st.button(
        "Start Call",
        type="primary",
        use_container_width=True,
    ):

        start_call()
        st.rerun()

    st.stop()


# ============================================================
# WEBRTC MICROPHONE
# ============================================================

if st.session_state.call_active:

    webrtc_streamer(
        key=WEBRTC_KEY,
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_frame_callback,
        media_stream_constraints={
            "audio": True,
            "video": False,
        },
        desired_playing_state=True,
        async_processing=True,
    )


# ============================================================
# STATUS
# ============================================================

if st.session_state.call_active:

    st.html(
        """
        <div class="call-status">
            <span class="status-dot"></span>
            Call in progress
        </div>
        """
    )

else:

    st.html(
        """
        <div class="call-status">
            <span class="status-dot"></span>
            Call completed
        </div>
        """
    )


# ============================================================
# CONVERSATION
# ============================================================

if st.session_state.conversation:

    conversation_html = [
        '<div class="conversation">'
    ]

    for message in (
        st.session_state.conversation
    ):

        speaker = message["speaker"]
        text = message["text"]

        # Basic HTML escaping.
        text = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

        if speaker == "agent":

            conversation_html.append(
                f"""
                <div class="message-row agent">

                    <div class="message-container">

                        <div class="message-label">
                            Energy Support
                        </div>

                        <div class="message-bubble agent-bubble">
                            {text}
                        </div>

                    </div>

                </div>
                """
            )

        else:

            conversation_html.append(
                f"""
                <div class="message-row customer">

                    <div class="message-container">

                        <div class="message-label">
                            You
                        </div>

                        <div class="message-bubble customer-bubble">
                            {text}
                        </div>

                    </div>

                </div>
                """
            )

    conversation_html.append(
        "</div>"
    )

    st.html(
        "".join(conversation_html)
    )


# ============================================================
# AGENT AUDIO
# ============================================================

if (
    st.session_state.agent_audio
    and (
        st.session_state.agent_audio_id
        != st.session_state.rendered_audio_id
    )
):

    render_agent_audio()

    st.session_state.rendered_audio_id = (
        st.session_state.agent_audio_id
    )


# ============================================================
# LIVE CALL MONITOR
# ============================================================

@st.fragment(run_every=0.25)
def call_monitor():

    if not st.session_state.call_active:
        return

    now = time.monotonic()

    # --------------------------------------------------------
    # AGENT SPEAKING
    # --------------------------------------------------------

    if (
        now
        < st.session_state.agent_speaking_until
    ):

        MIC_BUFFER.disable()

        st.html(
            """
            <div class="speaking-state">
                Speaking...
            </div>
            """
        )

        return

    # --------------------------------------------------------
    # PROCESSING
    # --------------------------------------------------------

    if st.session_state.processing:

        st.html(
            """
            <div class="speaking-state">
                Processing...
            </div>
            """
        )

        return

    # --------------------------------------------------------
    # CUSTOMER TURN
    # --------------------------------------------------------

    if not MIC_BUFFER.enabled:
        MIC_BUFFER.enable()

    duration = MIC_BUFFER.duration()

    # This is shown ONLY after agent speech is finished.
    st.html(
        """
        <div class="listening-state">
            <span class="listening-dot"></span>
            Listening...
        </div>
        """
    )

    # --------------------------------------------------------
    # 5 SECOND LISTENING WINDOW
    # --------------------------------------------------------

    if duration >= LISTEN_SECONDS:

        MIC_BUFFER.disable()

        process_customer_audio()


# ============================================================
# START MONITOR
# ============================================================

if st.session_state.call_active:

    call_monitor()


# ============================================================
# FINAL DATA
# ============================================================

if st.session_state.call_ended:

    st.html(
        """
        <div class="final-card">

            <div class="final-title">
                Journey information captured
            </div>

        </div>
        """
    )

    st.json(
        st.session_state.collected
    )


# ============================================================
# ERROR
# ============================================================

if st.session_state.error:

    st.error(
        st.session_state.error
    )