#!/usr/bin/env python3
"""
Test script to verify the speech-to-speech conversation functionality.
"""

import asyncio
import websockets
import json
import time

async def test_speech_to_speech():
    """Test the speech-to-speech WebSocket endpoint"""
    uri = "ws://localhost:8000/ws/realtime"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Realtime WebSocket")
            
            # Wait for connection to be established
            await asyncio.sleep(1)
            
            # Send a test message to check if the connection is working
            test_message = {
                "type": "test",
                "message": "Testing realtime connection"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message")
            
            # Listen for responses for a few seconds
            print("🎤 Listening for realtime responses...")
            print("💡 Note: This test only verifies WebSocket connection.")
            print("💡 For full speech-to-speech testing, use the frontend with microphone access.")
            
            message_count = 0
            for i in range(10):  # Listen for up to 10 seconds
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    message_count += 1
                    print(f"📥 Message {message_count}: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'error':
                        print(f"   Error: {data.get('message', 'Unknown error')}")
                    elif data.get('type') == 'user_speaking_started':
                        print("   🎤 User started speaking")
                    elif data.get('type') == 'user_speaking_stopped':
                        print("   🔇 User stopped speaking")
                    elif data.get('type') == 'ai_transcript_delta':
                        print(f"   🤖 AI speaking: {data.get('content', '')}")
                    elif data.get('type') == 'user_transcript_delta':
                        print(f"   👤 User speaking: {data.get('content', '')}")
                        
                except asyncio.TimeoutError:
                    print("⏰ No messages received in this interval")
                    continue
            
            print(f"✅ Test completed. Received {message_count} messages")
            print("✅ Realtime WebSocket connection is working!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the API server is running with: python start_server.py")

if __name__ == "__main__":
    print("🧪 Testing Speech-to-Speech Realtime WebSocket...")
    print("📋 This test verifies the WebSocket connection.")
    print("📋 For full speech testing, use the frontend interface.")
    asyncio.run(test_speech_to_speech())
