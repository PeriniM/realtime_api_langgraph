#!/usr/bin/env python3
"""
FastAPI server for Agent in the Loop chatbot interface.
Integrates with the existing background agent system and provides WebSocket endpoints
for real-time communication with the React frontend.
"""

import asyncio
import base64
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Import our existing background agent system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_background_agent import (
    create_background_task, 
    get_task_status, 
    cleanup_old_tasks,
    get_conversation_history
)

# Import OpenAI for real AI responses
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Import realtime service for speech-to-speech
from realtime_service import realtime_service

# Voice streaming service for frontend-to-backend voice communication
class VoiceStreamingService:
    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.openai_client = AsyncOpenAI()
        self.realtime_connection = None
        self.connection_context = None
        self.audio_buffer = []
        self.is_connected = False
        self.event_task = None
        # Message buffering for complete responses
        self.current_response_text = ""
        self.current_response_audio = []
        self.is_response_in_progress = False
        
    async def start(self):
        """Start the voice streaming service"""
        try:
            # Connect to OpenAI Realtime API using proper async context manager
            self.realtime_connection = self.openai_client.realtime.connect(model="gpt-realtime")
            self.connection_context = await self.realtime_connection.__aenter__()
            self.is_connected = True
            
            # Configure the session
            await self.connection_context.session.update(session={
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
                "instructions": "Be concise and friendly. You are from US and speak in US English. Do not say a lot of things, give some time to the user to answer.",
            })
            
            # Start listening for OpenAI events
            self.event_task = asyncio.create_task(self._handle_openai_events())
            
            print(f"[VoiceStreaming] Started voice streaming service for {self.connection_id}")
            
        except Exception as e:
            print(f"[VoiceStreaming] Error starting service: {e}")
            await self._send_error(f"Failed to start voice streaming: {str(e)}")
    
    async def handle_message(self, message_data: dict):
        """Handle incoming WebSocket messages from frontend"""
        try:
            message_type = message_data.get("type")
            
            if message_type == "audio_data":
                # Handle audio data from frontend
                await self._handle_audio_data(message_data)
            elif message_type == "keepalive":
                # Handle keepalive
                pass
            else:
                print(f"[VoiceStreaming] Unknown message type: {message_type}")
                
        except Exception as e:
            print(f"[VoiceStreaming] Error handling message: {e}")
            await self._send_error(f"Error processing message: {str(e)}")
    
    async def _handle_audio_data(self, message_data: dict):
        """Handle audio data from frontend"""
        try:
            if not self.is_connected or not self.connection_context:
                return
                
            audio_base64 = message_data.get("audio")
            if not audio_base64:
                return
            
            # Convert base64 to bytes and send to OpenAI
            audio_bytes = base64.b64decode(audio_base64)
            
            # For WebM/Opus format from frontend, we need to handle it differently
            # For now, we'll send it directly to OpenAI's input buffer
            await self.connection_context.input_audio_buffer.append(
                audio=audio_base64
            )
            
        except Exception as e:
            print(f"[VoiceStreaming] Error handling audio data: {e}")
    
    async def _handle_openai_events(self):
        """Handle events from OpenAI Realtime API"""
        try:
            async for event in self.connection_context:
                await self._process_openai_event(event)
        except Exception as e:
            print(f"[VoiceStreaming] Error in OpenAI event loop: {e}")
            await self._send_error(f"OpenAI connection error: {str(e)}")
    
    async def _process_openai_event(self, event):
        """Process individual OpenAI events"""
        try:
            event_type = event.type
            
            if event_type == "response.output_audio.delta":
                # Buffer audio chunk instead of sending immediately
                self.current_response_audio.append(event.delta)
                self.is_response_in_progress = True
                print(f"[VoiceStreaming] Buffered audio chunk, total chunks: {len(self.current_response_audio)}")
                
            elif event_type == "response.output_audio_transcript.delta":
                # Buffer transcript delta instead of sending immediately
                self.current_response_text += event.delta
                self.is_response_in_progress = True
                print(f"[VoiceStreaming] Buffered text delta: '{event.delta}', current text: '{self.current_response_text}'")
                
            elif event_type == "response.output_audio_transcript.done":
                # Send complete AI transcript
                transcript = getattr(event, 'transcript', '')
                if transcript:
                    await self._send_transcript(transcript, is_user=False, is_complete=True)
                    
            elif event_type == "conversation.item.input_audio_transcription.delta":
                # Send user transcript delta
                await self._send_transcript(event.delta, is_user=True)
                
            elif event_type == "conversation.item.input_audio_transcription.completed":
                # Send complete user transcript
                transcript = event.transcript
                await self._send_transcript(transcript, is_user=True, is_complete=True)
                
            elif event_type == "input_audio_buffer.speech_started":
                await self._send_event("speech_started", {"is_user": True})
                
            elif event_type == "input_audio_buffer.speech_stopped":
                await self._send_event("speech_ended", {"is_user": True})
                
            elif event_type == "response.started":
                await self._send_event("speech_started", {"is_user": False})
                
            elif event_type == "response.done":
                # Send complete buffered response
                await self._send_complete_response()
                self._reset_response_buffer()
                await self._send_event("speech_ended", {"is_user": False})
                
            elif event_type == "error":
                error_msg = getattr(event, 'error', str(event))
                await self._send_error(f"OpenAI error: {error_msg}")
                
        except Exception as e:
            print(f"[VoiceStreaming] Error processing OpenAI event: {e}")
    
    async def _send_audio_chunk(self, audio_delta: str):
        """Send audio chunk to frontend"""
        try:
            await self.websocket.send_text(json.dumps({
                "type": "audio_chunk",
                "audio": audio_delta,
                "timestamp": time.time()
            }))
        except Exception as e:
            print(f"[VoiceStreaming] Error sending audio chunk: {e}")
    
    async def _send_transcript(self, text: str, is_user: bool, is_complete: bool = False):
        """Send transcript to frontend"""
        try:
            await self.websocket.send_text(json.dumps({
                "type": "transcript",
                "text": text,
                "is_user": is_user,
                "is_complete": is_complete,
                "timestamp": time.time()
            }))
        except Exception as e:
            print(f"[VoiceStreaming] Error sending transcript: {e}")
    
    async def _send_event(self, event_type: str, data: dict):
        """Send event to frontend"""
        try:
            await self.websocket.send_text(json.dumps({
                "type": event_type,
                **data,
                "timestamp": time.time()
            }))
        except Exception as e:
            print(f"[VoiceStreaming] Error sending event: {e}")
    
    async def _send_error(self, error_message: str):
        """Send error to frontend"""
        try:
            await self.websocket.send_text(json.dumps({
                "type": "error",
                "message": error_message,
                "timestamp": time.time()
            }))
        except Exception as e:
            print(f"[VoiceStreaming] Error sending error message: {e}")
    
    async def _send_complete_response(self):
        """Send complete buffered response to frontend"""
        try:
            print(f"[VoiceStreaming] Sending complete response - Text: '{self.current_response_text}', Audio chunks: {len(self.current_response_audio)}")
            
            # Send complete text if available
            if self.current_response_text.strip():
                await self._send_transcript(self.current_response_text, is_user=False, is_complete=True)
            
            # Send complete audio if available
            if self.current_response_audio:
                # Combine all audio chunks into one
                combined_audio = "".join(self.current_response_audio)
                await self._send_audio_chunk(combined_audio)
                
        except Exception as e:
            print(f"[VoiceStreaming] Error sending complete response: {e}")
    
    def _reset_response_buffer(self):
        """Reset the response buffer"""
        self.current_response_text = ""
        self.current_response_audio = []
        self.is_response_in_progress = False
    
    async def cleanup(self):
        """Clean up the voice streaming service"""
        try:
            self.is_connected = False
            
            # Cancel the event task
            if self.event_task and not self.event_task.done():
                self.event_task.cancel()
                try:
                    await self.event_task
                except asyncio.CancelledError:
                    pass
            
            # Close the realtime connection
            if self.realtime_connection:
                try:
                    await self.realtime_connection.__aexit__(None, None, None)
                except Exception as e:
                    print(f"[VoiceStreaming] Error closing realtime connection: {e}")
                    
            print(f"[VoiceStreaming] Cleaned up voice streaming service for {self.connection_id}")
        except Exception as e:
            print(f"[VoiceStreaming] Error during cleanup: {e}")

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = AsyncOpenAI()

# Pydantic models for API
class Message(BaseModel):
    id: str
    type: str  # "user" or "ai"
    content: str
    timestamp: datetime
    is_agent_result: bool = False

class ConversationTurn(BaseModel):
    user_message: str
    ai_response: str
    timestamp: datetime

class TaskStatus(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float
    completed_at: Optional[float] = None
    message: str

class AgentInLoopStatus(BaseModel):
    is_active: bool
    current_task: Optional[str] = None
    status: str  # "idle", "analyzing", "executing"

class SubAgent(BaseModel):
    id: str
    name: str
    status: str  # "idle", "active", "completed", "error"
    icon: str

# FastAPI app
app = FastAPI(
    title="Agent in the Loop API",
    description="API for the Agent in the Loop chatbot interface",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.conversation_history: List[Message] = []
        self.agent_in_loop: AgentInLoopStatus = AgentInLoopStatus(
            is_active=False,
            current_task=None,
            status="idle"
        )
        self.sub_agents: List[SubAgent] = [
            SubAgent(id="email", name="Email Agent", status="idle", icon="📧"),
            SubAgent(id="calendar", name="Calendar Agent", status="idle", icon="📅"),
            SubAgent(id="notes", name="Notes Agent", status="idle", icon="📝"),
            SubAgent(id="research", name="Research Agent", status="idle", icon="🔍")
        ]
        self.active_tasks: Dict[str, str] = {}  # task_id -> agent_id mapping

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[API] Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[API] Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            # Check if connection is still open before sending
            if websocket.client_state.name != "CONNECTED":
                print("[API] Connection closed, removing from active connections")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                return False
            
            await websocket.send_text(message)
            return True
        except Exception as e:
            print(f"[API] Error sending message: {e}")
            # Remove dead connection
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            return False

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

    async def send_agent_update(self, websocket: WebSocket):
        """Send current agent status to client"""
        update = {
            "type": "agent_update",
            "agent_in_loop": self.agent_in_loop.dict(),
            "sub_agents": [agent.dict() for agent in self.sub_agents]
        }
        success = await self.send_personal_message(json.dumps(update, cls=DateTimeEncoder), websocket)
        if not success:
            print("[API] Failed to send agent update, connection may be closed")

    async def send_message(self, message: Message, websocket: WebSocket):
        """Send a new message to client"""
        message_data = {
            "type": "new_message",
            "message": message.dict()
        }
        success = await self.send_personal_message(json.dumps(message_data, cls=DateTimeEncoder), websocket)
        if not success:
            print("[API] Failed to send message, connection may be closed")

    def add_message(self, message: Message):
        """Add message to conversation history"""
        self.conversation_history.append(message)
    
    async def generate_ai_response(self, user_message: str) -> str:
        """Generate AI response using OpenAI"""
        try:
            # Build conversation context from recent messages
            recent_messages = self.conversation_history[-10:]  # Last 10 messages for context
            
            # Create messages for OpenAI API
            messages = [
                {
                    "role": "system", 
                    "content": "You are a helpful AI assistant. Be concise, friendly, and helpful. You have background agents that can help with various tasks like sending emails, updating calendars, or fetching notes."
                }
            ]
            
            # Add recent conversation history
            for msg in recent_messages:
                if msg.type == "user":
                    messages.append({"role": "user", "content": msg.content})
                elif msg.type == "ai":
                    messages.append({"role": "assistant", "content": msg.content})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI API
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[API] Error generating AI response: {e}")
            # Fallback response
            return f"I understand you said: '{user_message}'. Let me help you with that."

    async def trigger_agent_in_loop(self, user_message: str, ai_response: str, websocket: WebSocket):
        """Trigger the agent in the loop system"""
        # Activate agent in the loop
        self.agent_in_loop = AgentInLoopStatus(
            is_active=True,
            current_task="Analyzing conversation...",
            status="analyzing"
        )
        
        # Send initial update
        await self.send_agent_update(websocket)
        
        # Create background task
        task_id = create_background_task(user_message, ai_response, None)
        self.active_tasks[task_id] = "conversation_analysis"
        
        # Start monitoring task
        asyncio.create_task(self._monitor_task(task_id, websocket))

    async def _monitor_task(self, task_id: str, websocket: WebSocket):
        """Monitor a background task and update UI accordingly"""
        last_status = None
        while task_id in self.active_tasks:
            status = get_task_status(task_id)
            
            # Update agent status when task status changes to running
            if status['status'] == 'running' and last_status != 'running':
                self.agent_in_loop = AgentInLoopStatus(
                    is_active=True,
                    current_task="Running background analysis...",
                    status="executing"
                )
                await self.send_agent_update(websocket)
                print(f"[API] Updated agent status to 'executing' for task {task_id}")
            
            if status['status'] == 'completed':
                await self._handle_task_completion(task_id, status, websocket)
                break
            elif status['status'] == 'error':
                await self._handle_task_error(task_id, status, websocket)
                break
            
            last_status = status['status']
            await asyncio.sleep(0.5)  # Check every 500ms

    async def _handle_task_completion(self, task_id: str, status: Dict, websocket: WebSocket):
        """Handle successful task completion"""
        result = status.get('result', {})
        message = result.get('message', 'Task completed successfully')
        
        # Create agent result message
        agent_message = Message(
            id=f"agent_{int(time.time())}",
            type="ai",
            content=f"🧠 {message}",
            timestamp=datetime.now(),
            is_agent_result=True
        )
        
        # Send to client (don't add to history here to avoid duplicates)
        await self.send_message(agent_message, websocket)
        
        # Reset agent states
        self.agent_in_loop = AgentInLoopStatus(
            is_active=False,
            current_task=None,
            status="idle"
        )
        
        # Reset sub-agents
        for agent in self.sub_agents:
            agent.status = "idle"
        
        # Send final update
        await self.send_agent_update(websocket)
        
        # Clean up
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    async def _handle_task_error(self, task_id: str, status: Dict, websocket: WebSocket):
        """Handle task error"""
        error = status.get('error', 'Unknown error')
        
        # Create error message
        error_message = Message(
            id=f"error_{int(time.time())}",
            type="ai",
            content=f"❌ Background task failed: {error}",
            timestamp=datetime.now(),
            is_agent_result=True
        )
        
        # Send to client (don't add to history here to avoid duplicates)
        await self.send_message(error_message, websocket)
        
        # Reset agent states
        self.agent_in_loop = AgentInLoopStatus(
            is_active=False,
            current_task=None,
            status="idle"
        )
        
        # Reset sub-agents
        for agent in self.sub_agents:
            agent.status = "idle"
        
        # Send final update
        await self.send_agent_update(websocket)
        
        # Clean up
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

# Global connection manager
manager = ConnectionManager()

# Voice WebSocket endpoint for frontend-to-backend voice streaming
@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for voice streaming from frontend to backend"""
    await websocket.accept()
    connection_id = f"voice_{int(time.time())}"
    
    try:
        print(f"[API] Voice WebSocket connected: {connection_id}")
        
        # Initialize voice streaming service
        voice_service = VoiceStreamingService(websocket, connection_id)
        print(f"[API] Starting voice streaming service...")
        try:
            await voice_service.start()
            print(f"[API] Voice streaming service started successfully")
        except Exception as e:
            print(f"[API] Error starting voice streaming service: {e}")
            # Send error to frontend but don't close connection
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Failed to start voice streaming: {str(e)}"
            }))
        
        # Handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message_data = json.loads(data)
                await voice_service.handle_message(message_data)
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_text(json.dumps({
                        "type": "keepalive",
                        "timestamp": time.time()
                    }))
                except:
                    break
            except json.JSONDecodeError as e:
                print(f"[API] JSON decode error: {e}")
                continue
            except WebSocketDisconnect:
                print("[API] Voice WebSocket disconnected")
                break
            except Exception as e:
                print(f"[API] Voice WebSocket error: {e}")
                break
                
    except Exception as e:
        print(f"[API] Voice WebSocket error: {e}")
    finally:
        await voice_service.cleanup()
        print(f"[API] Voice WebSocket disconnected: {connection_id}")

# Realtime WebSocket endpoint for speech-to-speech
@app.websocket("/ws/realtime")
async def realtime_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time speech-to-speech conversation"""
    await websocket.accept()
    connection_id = f"realtime_{int(time.time())}"
    
    try:
        print(f"[API] Realtime WebSocket connected: {connection_id}")
        
        # Start keepalive task
        keepalive_task = asyncio.create_task(keepalive_ping(websocket))
        
        try:
            await realtime_service.start_realtime_conversation(websocket, connection_id)
        except Exception as e:
            print(f"[API] Realtime conversation error: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Realtime conversation failed: {str(e)}"
            }))
    except Exception as e:
        print(f"[API] Realtime WebSocket error: {e}")
    finally:
        # Cancel keepalive task
        if 'keepalive_task' in locals():
            keepalive_task.cancel()
        realtime_service.stop_conversation(connection_id)
        print(f"[API] Realtime WebSocket disconnected: {connection_id}")

async def keepalive_ping(websocket: WebSocket):
    """Send periodic keepalive messages to keep WebSocket connection alive"""
    try:
        while True:
            await asyncio.sleep(30)  # Send keepalive every 30 seconds
            try:
                # Send a keepalive message instead of ping (more compatible)
                await websocket.send_text(json.dumps({
                    "type": "keepalive",
                    "timestamp": time.time()
                }))
                print("[API] Sent keepalive message to realtime WebSocket")
            except Exception as e:
                print(f"[API] Keepalive message failed: {e}")
                break
    except asyncio.CancelledError:
        print("[API] Keepalive task cancelled")

# Regular WebSocket endpoint for text-based conversation
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state
        await manager.send_agent_update(websocket)
        
        while True:
            try:
                # Check if connection is still open
                if websocket.client_state.name != "CONNECTED":
                    print("[API] WebSocket connection closed, breaking loop")
                    break
                
                # Receive message from client with timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    message_data = json.loads(data)
                except asyncio.TimeoutError:
                    print("[API] WebSocket receive timeout, sending keepalive")
                    # Send a keepalive message to check if connection is still alive
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "keepalive",
                            "timestamp": time.time()
                        }))
                        continue
                    except:
                        print("[API] Keepalive failed, connection is dead")
                        break
                
                if message_data["type"] == "user_message":
                    user_message = message_data["content"]
                    
                    # Create user message
                    user_msg = Message(
                        id=f"user_{int(time.time())}",
                        type="user",
                        content=user_message,
                        timestamp=datetime.now(),
                        is_agent_result=False
                    )
                    
                    # Add user message to conversation history
                    manager.add_message(user_msg)
                    
                    # Send user message to client
                    await manager.send_message(user_msg, websocket)
                    
                    # Generate real AI response using OpenAI
                    ai_response = await manager.generate_ai_response(user_message)
                    
                    # Create AI message
                    ai_msg = Message(
                        id=f"ai_{int(time.time())}",
                        type="ai",
                        content=ai_response,
                        timestamp=datetime.now(),
                        is_agent_result=False
                    )
                    
                    # Add AI message to conversation history
                    manager.add_message(ai_msg)
                    
                    # Send AI message to client
                    await manager.send_message(ai_msg, websocket)
                    
                    # Trigger agent in the loop
                    await manager.trigger_agent_in_loop(user_message, ai_response, websocket)
                    
                elif message_data["type"] == "get_status":
                    # Send current status
                    await manager.send_agent_update(websocket)
                    
            except json.JSONDecodeError as e:
                print(f"[API] JSON decode error: {e}")
                continue
            except WebSocketDisconnect:
                print("[API] WebSocket disconnected during message processing")
                break
            except Exception as e:
                print(f"[API] Error processing message: {e}")
                # Check if it's a disconnect-related error
                if "disconnect" in str(e).lower() or "closed" in str(e).lower():
                    print("[API] Connection closed, breaking loop")
                    break
                continue
                
    except WebSocketDisconnect:
        print("[API] WebSocket disconnected")
    except Exception as e:
        print(f"[API] WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

# REST API endpoints
@app.get("/")
async def root():
    return {"message": "Agent in the Loop API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/conversation/history")
async def get_conversation_history():
    """Get conversation history"""
    return {
        "messages": [msg.dict() for msg in manager.conversation_history],
        "total": len(manager.conversation_history)
    }

@app.get("/agents/status")
async def get_agent_status():
    """Get current agent status"""
    return {
        "agent_in_loop": manager.agent_in_loop.dict(),
        "sub_agents": [agent.dict() for agent in manager.sub_agents],
        "active_tasks": len(manager.active_tasks)
    }

@app.post("/conversation/clear")
async def clear_conversation():
    """Clear conversation history"""
    manager.conversation_history.clear()
    return {"message": "Conversation cleared"}

@app.post("/agents/reset")
async def reset_agents():
    """Reset all agents to idle state"""
    manager.agent_in_loop = AgentInLoopStatus(
        is_active=False,
        current_task=None,
        status="idle"
    )
    
    for agent in manager.sub_agents:
        agent.status = "idle"
    
    manager.active_tasks.clear()
    
    return {"message": "Agents reset"}

@app.get("/tasks/{task_id}")
async def get_task_status_endpoint(task_id: str):
    """Get status of a specific task"""
    try:
        status = get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.post("/tasks/cleanup")
async def cleanup_tasks():
    """Clean up old tasks"""
    cleanup_old_tasks()
    return {"message": "Old tasks cleaned up"}

# Serve static files (for production)
# app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
