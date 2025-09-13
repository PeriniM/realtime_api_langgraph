import asyncio
import base64
import os
from typing import Any

import numpy as np
import sounddevice as sd  # Mic + speaker
from openai import AsyncOpenAI

from dotenv import load_dotenv

load_dotenv(override=True)


# ---- Audio params (keep them in sync for input/output) ----
SAMPLE_RATE = 24000  # common realtime model rate
CHANNELS = 1
DTYPE = "int16"
CHUNK_MS = 20
FRAMES_PER_CHUNK = int(SAMPLE_RATE * CHUNK_MS / 1000)

# ---- Playback sink ----
class Speaker:
    def __init__(self) -> None:
        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=FRAMES_PER_CHUNK,
        )
        self.stream.start()

    def play_bytes(self, pcm_bytes: bytes) -> None:
        # bytes(int16 little-endian) -> numpy -> write
        audio = np.frombuffer(pcm_bytes, dtype=np.int16)
        # Reshape for mono/stereo as needed
        audio = audio.reshape(-1, CHANNELS) if CHANNELS > 1 else audio
        self.stream.write(audio)

    def close(self) -> None:
        self.stream.stop(); self.stream.close()

# ---- Microphone source ----
class Microphone:
    def __init__(self) -> None:
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=FRAMES_PER_CHUNK,
        )
        self.stream.start()

    def read_chunk(self) -> bytes:
        frames, _ = self.stream.read(FRAMES_PER_CHUNK)
        return frames.tobytes()

    def close(self) -> None:
        self.stream.stop(); self.stream.close()

async def main() -> None:
    # 1) Create client and open a realtime session (WebSocket)
    client = AsyncOpenAI()  # reads OPENAI_API_KEY
    speaker = Speaker()
    mic = Microphone()

    try:
        async with client.realtime.connect(model="gpt-realtime") as conn:
            # 2) Configure session: audio in, audio out, server-side VAD
            await conn.session.update(session={
                "type": "realtime",
                "model": "gpt-realtime",
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000
                        },
                        "transcription": {
                            "model": "gpt-4o-mini-transcribe" # gpt-4o-transcribe, gpt-4o-mini-transcribe, and whisper-1
                        },
                        "turn_detection": {"type": "server_vad"}  # model finds end-of-speech
                    },
                    "output": {
                        "format": {
                            "type": "audio/pcm", 
                            "rate": 24000
                        },
                        "voice": "alloy"  # Voice configuration in output section
                    }
                },
                "instructions": "Be concise and friendly. You are Italian and speak in Italian. Do not say a lot of things, give some time to the user to answer.",
            })

            # 3) Task A: send mic audio chunks to the model continuously
            async def pump_mic() -> None:
                while True:
                    pcm = mic.read_chunk()
                    # Cancel any active response when new audio comes in (prevents overlap)
                    if response_active:
                        try:
                            await conn.send({"type": "response.cancel"})
                        except Exception as e:
                            print(f"[cancel error] {e}")
                    await conn.input_audio_buffer.append(
                        audio=base64.b64encode(pcm).decode("utf-8")
                    )
                    await asyncio.sleep(0)  # yield to event loop

            # 4) Task B: play model audio as it streams back
            response_active = False
            async def pump_model() -> None:
                nonlocal response_active
                async for event in conn:
                    t = event.type
                    if t == "response.output_audio.delta":
                        # Base64 -> bytes -> speaker
                        pcm_bytes = base64.b64decode(event.delta)
                        speaker.play_bytes(pcm_bytes)
                    elif t == "response.output_audio_transcript.delta":
                        # Print live transcript of audio output
                        print(event.delta, end="", flush=True)
                    elif t == "response.output_audio_transcript.done":
                        print()
                    elif t == "conversation.item.input_audio_transcription.delta":
                        # Print live transcript of user input
                        # print(f"[User] {event.delta}", end="", flush=True)
                        continue
                    elif t == "conversation.item.input_audio_transcription.completed":
                        # Print completed user transcript
                        print(f"[User] {event.transcript}")
                    elif t == "input_audio_buffer.speech_started":
                        print("\n[User speaking...]")
                    elif t == "input_audio_buffer.speech_stopped":
                        print("[User finished speaking]")
                    elif t == "response.done":
                        response_active = False
                    elif t == "response.started":
                        response_active = True
                    elif t == "response.error":
                        print(f"[model error] {getattr(event, 'error', event)}")
                        response_active = False
                    elif t == "error":
                        # Improved error handling based on OpenAI documentation
                        error = getattr(event, 'error', event)
                        print(f"[conn error] Type: {getattr(error, 'type', 'unknown')}")
                        print(f"[conn error] Code: {getattr(error, 'code', 'unknown')}")
                        print(f"[conn error] Event ID: {getattr(error, 'event_id', 'unknown')}")
                        print(f"[conn error] Message: {getattr(error, 'message', str(error))}")
                        response_active = False

            # 5) Run both pipes until Ctrl+C
            await asyncio.gather(pump_mic(), pump_model())

    except KeyboardInterrupt:
        pass
    finally:
        mic.close()
        speaker.close()

if __name__ == "__main__":
    # On macOS, you may need: brew install portaudio ffmpeg
    # Also grant mic permission to your terminal.
    asyncio.run(main())