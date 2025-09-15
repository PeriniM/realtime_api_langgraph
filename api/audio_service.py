#!/usr/bin/env python3
"""
Audio service for handling microphone input and speaker output.
Based on the implementation from test_bidirectional.py
"""

import asyncio
import base64
import numpy as np
import sounddevice as sd
from typing import Optional, Callable

# Audio parameters (keep them in sync for input/output)
SAMPLE_RATE = 24000  # common realtime model rate
CHANNELS = 1
DTYPE = "int16"
CHUNK_MS = 20
FRAMES_PER_CHUNK = int(SAMPLE_RATE * CHUNK_MS / 1000)

class AudioService:
    """Audio service for microphone and speaker handling"""
    
    def __init__(self):
        self.microphone: Optional[Microphone] = None
        self.speaker: Optional[Speaker] = None
        self.is_initialized = False
        
    def initialize(self):
        """Initialize audio devices"""
        try:
            self.microphone = Microphone()
            self.speaker = Speaker()
            self.is_initialized = True
            print("[AudioService] Audio devices initialized successfully")
        except Exception as e:
            print(f"[AudioService] Failed to initialize audio devices: {e}")
            self.is_initialized = False
    
    def cleanup(self):
        """Clean up audio devices"""
        if self.microphone:
            self.microphone.close()
        if self.speaker:
            self.speaker.close()
        self.is_initialized = False
        print("[AudioService] Audio devices cleaned up")

class Microphone:
    """Microphone input handler"""
    
    def __init__(self):
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=FRAMES_PER_CHUNK,
        )
        self.stream.start()
        print("[Microphone] Initialized")

    def read_chunk(self) -> bytes:
        """Read a chunk of audio data from microphone"""
        frames, _ = self.stream.read(FRAMES_PER_CHUNK)
        return frames.tobytes()

    def close(self):
        """Close microphone stream"""
        self.stream.stop()
        self.stream.close()
        print("[Microphone] Closed")

class Speaker:
    """Speaker output handler"""
    
    def __init__(self):
        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=FRAMES_PER_CHUNK,
        )
        self.stream.start()
        print("[Speaker] Initialized")

    def play_bytes(self, pcm_bytes: bytes):
        """Play PCM audio bytes through speaker"""
        # bytes(int16 little-endian) -> numpy -> write
        audio = np.frombuffer(pcm_bytes, dtype=np.int16)
        # Reshape for mono/stereo as needed
        audio = audio.reshape(-1, CHANNELS) if CHANNELS > 1 else audio
        self.stream.write(audio)

    def close(self):
        """Close speaker stream"""
        self.stream.stop()
        self.stream.close()
        print("[Speaker] Closed")

# Global audio service instance
audio_service = AudioService()
