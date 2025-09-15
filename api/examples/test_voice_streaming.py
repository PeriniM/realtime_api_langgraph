#!/usr/bin/env python3
"""
Test script to verify the voice streaming WebSocket endpoint works correctly.
"""

import asyncio
import websockets
import json
import time
import base64

async def test_voice_streaming():
    """Test the voice streaming WebSocket endpoint"""
    uri = "ws://localhost:8000/ws/voice"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Voice WebSocket")
            
            # Wait a moment for the connection to establish
            await asyncio.sleep(1)
            
            # Send a test audio data message (simulated)
            test_audio_data = {
                "type": "audio_data",
                "audio": base64.b64encode(b"fake_audio_data").decode('utf-8'),
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(test_audio_data))
            print("📤 Sent test audio data")
            
            # Listen for responses
            message_count = 0
            for i in range(10):  # Wait for up to 10 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    message_count += 1
                    print(f"📥 Message {message_count}: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'transcript':
                        print(f"   Transcript: {data.get('text', '')}")
                    elif data.get('type') == 'audio_chunk':
                        print(f"   Audio chunk received (length: {len(data.get('audio', ''))})")
                    elif data.get('type') == 'error':
                        print(f"   Error: {data.get('message', '')}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"✅ Test completed. Received {message_count} messages")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the API server is running with: python start_server.py")

if __name__ == "__main__":
    print("🧪 Testing Voice Streaming WebSocket...")
    print("📋 This test verifies:")
    print("   - Voice WebSocket connection")
    print("   - Audio data message handling")
    print("   - Response message types")
    print("")
    asyncio.run(test_voice_streaming())
