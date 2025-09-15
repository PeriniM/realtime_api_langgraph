import asyncio
import base64
import json
import os
import time
from typing import Any

import numpy as np
import sounddevice as sd  # Mic + speaker
from openai import AsyncOpenAI
from langsmith import traceable, Client
from dotenv import load_dotenv

# Import our simple background agent
from simple_background_agent import create_background_task, get_task_status, cleanup_old_tasks

load_dotenv(override=True)

# ---- LangSmith setup ----
langsmith_client = Client()

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

# ---- Enhanced Background Task Manager with Out-of-Band Responses ----
class EnhancedBackgroundTaskManager:
    def __init__(self):
        self.active_tasks = {}  # task_id -> task_info
        self.conversation_history = []
        self.connection = None
        self.task_counter = 0
        self.pending_results = []  # Buffer for completed results waiting to be delivered
        self.user_speaking = False  # Track if user is currently speaking
        self.response_in_progress = False  # Track if a response is being generated
    
    def set_connection(self, connection):
        """Set the realtime connection for out-of-band responses"""
        self.connection = connection
    
    def set_user_speaking(self, speaking: bool):
        """Track whether user is currently speaking"""
        self.user_speaking = speaking
        print(f"[Background] User speaking state changed to: {speaking}")
        if not speaking:
            # User finished speaking, deliver any pending results
            print(f"[Background] User finished speaking, checking for pending results...")
            self.print_pending_results()
            asyncio.create_task(self._deliver_pending_results())
    
    async def on_conversation_turn_complete(self, user_message: str, ai_response: str):
        """Create background task after each conversation turn"""
        # Add to conversation history
        turn = {
            "user": user_message,
            "ai": ai_response,
            "timestamp": time.time()
        }
        self.conversation_history.append(turn)
        
        # Create background task
        # Note: No need to pass conversation context as the agent now has full memory via checkpointer
        task_id = create_background_task(
            user_message, 
            ai_response, 
            None  # Agent has full conversation memory
        )
        
        self.active_tasks[task_id] = {
            "created_at": time.time(),
            "user_message": user_message,
            "ai_response": ai_response,
            "delivered": False
        }
        
        print(f"[Background] Created task {task_id} for: {user_message[:50]}...")
        
        # Start monitoring this task
        asyncio.create_task(self._monitor_task(task_id))
    
    async def _monitor_task(self, task_id: str):
        """Monitor a specific task and deliver result when ready"""
        while task_id in self.active_tasks:
            status = get_task_status(task_id)
            
            if status['status'] == 'completed':
                await self._buffer_result(task_id, status['result'])
                break
            elif status['status'] == 'error':
                await self._buffer_error(task_id, status['error'])
                break
            
            await asyncio.sleep(0.5)  # Check every 500ms
    
    async def _buffer_result(self, task_id: str, result: dict):
        """Buffer a completed result instead of delivering immediately"""
        completion_message = self._create_completion_message(task_id, result)
        buffered_item = {
            "type": "success",
            "task_id": task_id,
            "message": completion_message
        }
        self.pending_results.append(buffered_item)
        self.active_tasks[task_id]["delivered"] = True
        print(f"[Background] Buffered result for task {task_id}")
        print(f"[Background] Buffered content: {completion_message}")
        print(f"[Background] Full result data: {result}")
    
    async def _buffer_error(self, task_id: str, error: str):
        """Buffer an error result instead of delivering immediately"""
        error_message = f"❌ Background task failed: {error}. The main conversation can continue normally."
        buffered_item = {
            "type": "error",
            "task_id": task_id,
            "message": error_message
        }
        self.pending_results.append(buffered_item)
        self.active_tasks[task_id]["delivered"] = True
        print(f"[Background] Buffered error for task {task_id}")
        print(f"[Background] Buffered error content: {error_message}")
    
    async def _deliver_pending_results(self):
        """Deliver all pending results when user finishes speaking"""
        if not self.pending_results or not self.connection or self.response_in_progress:
            return
        
        print(f"[Background] Delivering {len(self.pending_results)} pending results")
        print(f"[Background] Pending results details:")
        for i, result in enumerate(self.pending_results):
            print(f"  [{i+1}] Type: {result['type']}, Task: {result['task_id']}")
            print(f"      Message: {result['message']}")
        
        # Combine all pending results into a single message
        if len(self.pending_results) == 1:
            combined_message = self.pending_results[0]["message"]
        else:
            combined_message = "Here are the results from the background tasks:\n" + "\n".join([f"• {result['message']}" for result in self.pending_results])
        
        print(f"[Background] Combined message to deliver: {combined_message}")
        
        try:
            # Add the combined result as a conversation item to the main conversation
            await self.connection.conversation.item.create(
                item={
                    "type": "message",
                    "role": "assistant",
                    "content": [{
                        "type": "output_text",
                        "text": combined_message
                    }]
                }
            )
            
            # Don't generate a response automatically - let the user speak first
            print(f"[Background] Successfully delivered {len(self.pending_results)} buffered results to conversation")
            
        except Exception as e:
            print(f"[Background] Failed to deliver buffered results: {e}")
        
        # Clear the pending results
        self.pending_results.clear()
    
    async def _deliver_result_out_of_band(self, task_id: str, result: dict):
        """Deliver background task result by injecting into main conversation"""
        if not self.connection or task_id not in self.active_tasks:
            return
        
        try:
            # Create a message about the background task completion
            completion_message = self._create_completion_message(task_id, result)
            
            # Add the background result as a conversation item to the main conversation
            await self.connection.conversation.item.create(
                item={
                    "type": "message",
                    "role": "assistant",
                    "content": [{
                        "type": "input_text",
                        "text": completion_message
                    }]
                }
            )
            
            # Generate a response to this new conversation item
            await self.connection.response.create()
            
            self.active_tasks[task_id]["delivered"] = True
            print(f"[Background] Delivered result to main conversation for task {task_id}")
            
        except Exception as e:
            print(f"[Background] Failed to deliver result: {e}")
    
    def _create_completion_message(self, task_id: str, result: dict) -> str:
        """Create a completion message for the background task result"""
        # For conversation analysis, show a summary instead of the full message
        message = result.get('message', 'Conversation insights gathered')
        # Truncate very long analysis messages
        if len(message) > 200:
            message = message[:200] + "..."
        return f"🧠 Conversation analysis: {message}"
    
    def _create_context_prompt(self, task_id: str, result: dict) -> str:
        """Create a context-aware prompt for the out-of-band response"""
        user_message = self.active_tasks[task_id]["user_message"]
        
        return f"""
I've completed a background analysis of the conversation related to the user's request: "{user_message}".
The analysis provides insights about the conversation quality, tone, and suggestions for improvement.
Please inform the user about the background analysis and provide any relevant insights in a conversational way.
Be natural and helpful in your response.
"""
    
    async def _deliver_error_result(self, task_id: str, error: str):
        """Deliver error result by injecting into main conversation"""
        if not self.connection or task_id not in self.active_tasks:
            return
        
        try:
            # Create an error message
            error_message = f"❌ Background task failed: {error}. The main conversation can continue normally."
            
            # Add the error as a conversation item to the main conversation
            await self.connection.conversation.item.create(
                item={
                    "type": "message",
                    "role": "assistant",
                    "content": [{
                        "type": "input_text",
                        "text": error_message
                    }]
                }
            )
            
            # Generate a response to this new conversation item
            await self.connection.response.create()
            
            print(f"[Background] Delivered error result to main conversation for task {task_id}")
            
        except Exception as e:
            print(f"[Background] Failed to deliver error result: {e}")
    
    def cleanup_completed_tasks(self):
        """Clean up delivered tasks"""
        to_remove = []
        for task_id, task_info in self.active_tasks.items():
            if task_info.get("delivered", False):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]
    
    def print_pending_results(self):
        """Print current pending results for debugging"""
        print(f"[Background] Current pending results: {len(self.pending_results)}")
        if self.pending_results:
            for i, result in enumerate(self.pending_results):
                print(f"  [{i+1}] Type: {result['type']}, Task: {result['task_id']}")
                print(f"      Message: {result['message']}")
        else:
            print("  No pending results")

# ---- LangSmith instrumentation functions ----
@traceable(client=langsmith_client, run_type="chain", name="User Message")
def log_user_message(message: str, timestamp: float) -> dict:
    """Log user message to LangSmith."""
    return {
        "message": message,
        "timestamp": timestamp,
        "message_type": "user_input"
    }

@traceable(client=langsmith_client, run_type="chain", name="AI Response")
def log_ai_response(message: str, timestamp: float) -> dict:
    """Log AI response to LangSmith."""
    return {
        "message": message,
        "timestamp": timestamp,
        "message_type": "ai_response"
    }

@traceable(client=langsmith_client, run_type="chain", name="Conversation Session")
async def main() -> None:
    # 1) Create client and open a realtime session (WebSocket)
    client = AsyncOpenAI()  # reads OPENAI_API_KEY
    speaker = Speaker()
    mic = Microphone()
    
    # Initialize enhanced background task manager
    background_manager = EnhancedBackgroundTaskManager()

    try:
        async with client.realtime.connect(model="gpt-realtime") as conn:
            # Set connection for out-of-band responses
            background_manager.set_connection(conn)
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
                        "turn_detection": {"type": "semantic_vad"}  # try semantic_vad
                    },
                    "output": {
                        "format": {
                            "type": "audio/pcm", 
                            "rate": 24000
                        },
                        "voice": "alloy"  # 'alloy', 'ash', 'ballad', 'coral', 'echo', 'sage', 'shimmer', 'verse', 'marin', and 'cedar'
                    }
                },
                "instructions": "Be concise and friendly. You are from US and speak in US English. Do not say a lot of things, give some time to the user to answer. When you are talking there are some ai subagents analyzing the conversations and they can perform actions.",
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
            current_user_message = None
            
            async def pump_model() -> None:
                nonlocal response_active, current_user_message
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
                        # Log AI response to LangSmith
                        ai_transcript = getattr(event, 'transcript', '')
                        if ai_transcript:
                            log_ai_response(ai_transcript, time.time())
                            # Create background task after AI response is complete
                            # Always trigger background agent after AI responds
                            if current_user_message:
                                await background_manager.on_conversation_turn_complete(
                                    current_user_message, ai_transcript
                                )
                                current_user_message = None
                        print()
                    elif t == "conversation.item.input_audio_transcription.delta":
                        # Print live transcript of user input
                        # print(f"[User] {event.delta}", end="", flush=True)
                        continue
                    elif t == "conversation.item.input_audio_transcription.completed":
                        # Print completed user transcript and log to LangSmith
                        user_message = event.transcript
                        print(f"[User] {user_message}")
                        log_user_message(user_message, time.time())
                        current_user_message = user_message
                    elif t == "input_audio_buffer.speech_started":
                        print("\n[User speaking...]")
                        background_manager.set_user_speaking(True)
                    elif t == "input_audio_buffer.speech_stopped":
                        print("[User finished speaking]")
                        background_manager.set_user_speaking(False)
                    elif t == "response.done":
                        response_active = False
                        background_manager.response_in_progress = False
                    elif t == "response.started":
                        response_active = True
                        background_manager.response_in_progress = True
                    elif t == "response.error":
                        print(f"[model error] {getattr(event, 'error', event)}")
                        response_active = False
                        background_manager.response_in_progress = False
                    elif t == "error":
                        # Improved error handling based on OpenAI documentation
                        error = getattr(event, 'error', event)
                        print(f"[conn error] Type: {getattr(error, 'type', 'unknown')}")
                        print(f"[conn error] Code: {getattr(error, 'code', 'unknown')}")
                        print(f"[conn error] Event ID: {getattr(error, 'event_id', 'unknown')}")
                        print(f"[conn error] Message: {getattr(error, 'message', str(error))}")
                        response_active = False

            # 5) Run both main tasks until Ctrl+C
            await asyncio.gather(pump_mic(), pump_model())

    except KeyboardInterrupt:
        pass
    finally:
        mic.close()
        speaker.close()
        # Clean up background tasks
        background_manager.cleanup_completed_tasks()
        cleanup_old_tasks()
        # Ensure all LangSmith traces are submitted before exiting
        langsmith_client.flush()

if __name__ == "__main__":
    # On macOS, you may need: brew install portaudio ffmpeg
    # Also grant mic permission to your terminal.
    asyncio.run(main())