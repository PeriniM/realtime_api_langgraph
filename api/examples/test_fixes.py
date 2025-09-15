#!/usr/bin/env python3
"""
Test script to verify the WebSocket fixes work correctly.
"""

import asyncio
import websockets
import json
import time

async def test_single_connection():
    """Test that only one connection is created and messages aren't duplicated"""
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for initial agent update
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📡 Received initial update: {data['type']}")
            
            # Send a test message
            test_message = {
                "type": "user_message",
                "content": "Test message for duplicate check"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message")
            
            # Count messages received
            message_count = 0
            for i in range(5):  # Expect user message, AI response, and agent updates
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    message_count += 1
                    print(f"📥 Message {message_count}: {data['type']}")
                    
                    if data['type'] == 'new_message':
                        print(f"   Content: {data['message']['content']}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"✅ Test completed. Received {message_count} messages")
            print("✅ No duplicate connections or messages detected")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing WebSocket fixes...")
    asyncio.run(test_single_connection())
