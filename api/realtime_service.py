#!/usr/bin/env python3
"""
Realtime service for OpenAI Realtime API integration.
Handles speech-to-speech conversation with background agent integration.
"""

import asyncio
import base64
import json
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

from audio_service import audio_service

load_dotenv()

class RealtimeService:
    """Service for handling OpenAI Realtime API conversations"""
    
    def __init__(self):
        self.client = AsyncOpenAI()
        self.active_connections: Dict[str, Any] = {}
        self.background_manager = None
        self.frontend_websocket = None
        
    async def start_realtime_conversation(self, websocket, connection_id: str):
        """Start a realtime conversation session"""
        try:
            # Store frontend websocket for sending messages
            self.frontend_websocket = websocket
            
            # Initialize audio service if not already done (with error handling)
            if not audio_service.is_initialized:
                try:
                    audio_service.initialize()
                    print("[RealtimeService] Audio service initialized successfully")
                except Exception as e:
                    print(f"[RealtimeService] Audio service initialization failed: {e}")
                    # Continue without audio service - frontend can still use text mode
                    await self._send_to_frontend(websocket, {
                        "type": "warning",
                        "message": "Audio service unavailable - using text-only mode"
                    })
            
            # Initialize background task manager
            self.background_manager = EnhancedBackgroundTaskManager()
            
            async with self.client.realtime.connect(model="gpt-realtime") as conn:
                # Set connection for background agent
                self.background_manager.set_connection(conn)
                
                # Configure the realtime session
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
                                "model": "gpt-4o-mini-transcribe"
                            },
                            "turn_detection": {"type": "semantic_vad"}
                        },
                        "output": {
                            "format": {
                                "type": "audio/pcm", 
                                "rate": 24000
                            },
                            "voice": "alloy"
                        }
                    },
                    "instructions": "Be concise and friendly. You are from US and speak in US English. Do not say a lot of things, give some time to the user to answer. When you are talking there are some ai subagents analyzing the conversations and they can perform actions.",
                })
                
                # Store connection info
                self.active_connections[connection_id] = {
                    "websocket": websocket,
                    "realtime_conn": conn,
                    "background_manager": self.background_manager
                }
                
                # Start audio streaming tasks
                await self._run_audio_streaming(conn, websocket, connection_id)
                
        except Exception as e:
            print(f"[RealtimeService] Error in conversation: {e}")
            await self._send_error_to_frontend(websocket, str(e))
        finally:
            # Clean up connection
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
    
    async def _run_audio_streaming(self, conn, websocket, connection_id: str):
        """Run the audio streaming tasks"""
        response_active = False
        current_user_message = None
        
        # Task A: Send microphone audio to OpenAI
        async def pump_mic():
            while connection_id in self.active_connections:
                try:
                    # Check if audio service is available
                    if not audio_service.is_initialized or not audio_service.microphone:
                        print("[RealtimeService] Audio service not available, skipping mic pump")
                        await asyncio.sleep(1)
                        continue
                    
                    pcm = audio_service.microphone.read_chunk()
                    # Cancel any active response when new audio comes in
                    if response_active:
                        try:
                            await conn.send({"type": "response.cancel"})
                        except Exception as e:
                            print(f"[RealtimeService] Cancel error: {e}")
                    
                    await conn.input_audio_buffer.append(
                        audio=base64.b64encode(pcm).decode("utf-8")
                    )
                    await asyncio.sleep(0)  # yield to event loop
                except Exception as e:
                    print(f"[RealtimeService] Mic pump error: {e}")
                    # Don't break immediately, try to continue
                    await asyncio.sleep(0.1)
                    continue
        
        # Task B: Handle OpenAI responses and play audio
        async def pump_model():
            nonlocal response_active, current_user_message
            async for event in conn:
                try:
                    t = event.type
                    
                    if t == "response.output_audio.delta":
                        # Play audio through speaker (with error handling)
                        try:
                            pcm_bytes = base64.b64decode(event.delta)
                            if audio_service.is_initialized and audio_service.speaker:
                                audio_service.speaker.play_bytes(pcm_bytes)
                        except Exception as e:
                            print(f"[RealtimeService] Audio playback error: {e}")
                            # Continue processing even if audio playback fails
                        
                    elif t == "response.output_audio_transcript.delta":
                        # Send live transcript to frontend
                        await self._send_to_frontend(websocket, {
                            "type": "ai_transcript_delta",
                            "content": event.delta
                        })
                        
                    elif t == "response.output_audio_transcript.done":
                        # AI response complete
                        ai_transcript = getattr(event, 'transcript', '')
                        if ai_transcript:
                            # Send AI message to frontend
                            await self._send_to_frontend(websocket, {
                                "type": "ai_response_complete",
                                "content": ai_transcript
                            })
                            print(f"[RealtimeService] AI said: {ai_transcript}")
                            
                            # Trigger background agent
                            if current_user_message:
                                await self.background_manager.on_conversation_turn_complete(
                                    current_user_message, ai_transcript
                                )
                                current_user_message = None
                        
                    elif t == "conversation.item.input_audio_transcription.delta":
                        # Send user transcript delta to frontend
                        await self._send_to_frontend(websocket, {
                            "type": "user_transcript_delta",
                            "content": event.delta
                        })
                        
                    elif t == "conversation.item.input_audio_transcription.completed":
                        # User message complete
                        user_message = event.transcript
                        current_user_message = user_message
                        # Send user message to frontend
                        await self._send_to_frontend(websocket, {
                            "type": "user_message_complete",
                            "content": user_message
                        })
                        print(f"[RealtimeService] User said: {user_message}")
                        
                    elif t == "input_audio_buffer.speech_started":
                        await self._send_to_frontend(websocket, {
                            "type": "user_speaking_started"
                        })
                        self.background_manager.set_user_speaking(True)
                        
                    elif t == "input_audio_buffer.speech_stopped":
                        await self._send_to_frontend(websocket, {
                            "type": "user_speaking_stopped"
                        })
                        self.background_manager.set_user_speaking(False)
                        
                    elif t == "response.done":
                        response_active = False
                        self.background_manager.response_in_progress = False
                        
                    elif t == "response.started":
                        response_active = True
                        self.background_manager.response_in_progress = True
                        
                    elif t == "response.error":
                        error_msg = getattr(event, 'error', event)
                        await self._send_error_to_frontend(websocket, f"Response error: {error_msg}")
                        response_active = False
                        
                    elif t == "error":
                        error = getattr(event, 'error', event)
                        error_msg = f"Connection error: {getattr(error, 'message', str(error))}"
                        await self._send_error_to_frontend(websocket, error_msg)
                        response_active = False
                        
                except Exception as e:
                    print(f"[RealtimeService] Event handling error: {e}")
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(pump_mic(), pump_model())
    
    async def _send_to_frontend(self, websocket, data: Dict[str, Any]):
        """Send data to frontend via WebSocket"""
        try:
            # Check if connection is still open before sending
            if websocket.client_state.name != "CONNECTED":
                print("[RealtimeService] Connection closed, not sending message")
                return False
            
            await websocket.send_text(json.dumps(data))
            return True
        except Exception as e:
            print(f"[RealtimeService] Error sending to frontend: {e}")
            return False
    
    async def _send_error_to_frontend(self, websocket, error_msg: str):
        """Send error message to frontend"""
        await self._send_to_frontend(websocket, {
            "type": "error",
            "message": error_msg
        })
    
    def stop_conversation(self, connection_id: str):
        """Stop a conversation session"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

# Enhanced Background Task Manager (adapted from test_bidirectional.py)
class EnhancedBackgroundTaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.conversation_history = []
        self.connection = None
        self.task_counter = 0
        self.pending_results = []
        self.user_speaking = False
        self.response_in_progress = False
    
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
            # Only deliver if we have a valid connection
            if realtime_service.frontend_websocket and realtime_service.frontend_websocket.client_state.name == "CONNECTED":
                asyncio.create_task(self._deliver_pending_results())
            else:
                print("[Background] No valid connection, clearing pending results")
                self.pending_results.clear()
    
    async def on_conversation_turn_complete(self, user_message: str, ai_response: str):
        """Create background task after each conversation turn"""
        # Add to conversation history
        turn = {
            "user": user_message,
            "ai": ai_response,
            "timestamp": time.time()
        }
        self.conversation_history.append(turn)
        
        # Create background task using our own system
        task_id = self._create_background_task(user_message, ai_response)
        
        self.active_tasks[task_id] = {
            "created_at": time.time(),
            "user_message": user_message,
            "ai_response": ai_response,
            "delivered": False
        }
        
        print(f"[Background] Created task {task_id} for: {user_message[:50]}...")
        
        # Start monitoring this task
        asyncio.create_task(self._monitor_task(task_id))
    
    def _create_background_task(self, user_message: str, ai_response: str) -> str:
        """Create a background task for conversation analysis"""
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Start the background task
        asyncio.create_task(self._run_background_task(task_id, user_message, ai_response))
        
        return task_id
    
    async def _run_background_task(self, task_id: str, user_message: str, ai_response: str):
        """Run the background task for conversation analysis"""
        try:
            # Simulate conversation analysis (in a real implementation, this would use an LLM)
            await asyncio.sleep(2)  # Simulate processing time
            
            # Create a simple analysis result
            analysis_result = {
                "action": "conversation_analysis",
                "message": f"Analyzed conversation turn: User said '{user_message[:50]}...' and AI responded with '{ai_response[:50]}...'. The conversation shows good engagement and natural flow.",
                "user_request": user_message,
                "timestamp": time.time(),
                "status": "success"
            }
            
            # Mark task as completed
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "completed"
                self.active_tasks[task_id]["result"] = analysis_result
                self.active_tasks[task_id]["delivered"] = False
                
        except Exception as e:
            # Mark task as error
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "error"
                self.active_tasks[task_id]["error"] = str(e)
                self.active_tasks[task_id]["delivered"] = False
    
    async def _monitor_task(self, task_id: str):
        """Monitor a specific task and deliver result when ready"""
        while task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            
            if task.get('status') == 'completed':
                await self._buffer_result(task_id, task['result'])
                break
            elif task.get('status') == 'error':
                await self._buffer_error(task_id, task['error'])
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
    
    async def _deliver_pending_results(self):
        """Deliver all pending results when user finishes speaking"""
        if not self.pending_results or self.response_in_progress:
            return
        
        print(f"[Background] Delivering {len(self.pending_results)} pending results")
        
        # Combine all pending results into a single message
        if len(self.pending_results) == 1:
            combined_message = self.pending_results[0]["message"]
        else:
            combined_message = "Here are the results from the background tasks:\n" + "\n".join([f"• {result['message']}" for result in self.pending_results])
        
        print(f"[Background] Combined message to deliver: {combined_message}")
        
        try:
            # Check if connection is still alive
            if not realtime_service.frontend_websocket or realtime_service.frontend_websocket.client_state.name != "CONNECTED":
                print("[Background] Connection is dead, not delivering pending results")
                self.pending_results.clear()
                return
            
            # Send agent result directly to frontend instead of injecting into conversation
            if realtime_service.frontend_websocket:
                success = await realtime_service._send_to_frontend(realtime_service.frontend_websocket, {
                    "type": "agent_result",
                    "content": combined_message
                })
                if success:
                    print(f"[Background] Successfully sent {len(self.pending_results)} buffered results to frontend")
                else:
                    print("[Background] Failed to send results - connection may be closed")
            else:
                print("[Background] No frontend websocket available")
            
        except Exception as e:
            print(f"[Background] Failed to deliver buffered results: {e}")
        
        # Clear the pending results
        self.pending_results.clear()
    
    def _create_completion_message(self, task_id: str, result: dict) -> str:
        """Create a completion message for the background task result"""
        message = result.get('message', 'Conversation insights gathered')
        # Truncate very long analysis messages
        if len(message) > 200:
            message = message[:200] + "..."
        return f"🧠 Conversation analysis: {message}"

# Global realtime service instance
realtime_service = RealtimeService()
