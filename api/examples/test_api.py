#!/usr/bin/env python3
"""
Simple test script to verify the API works correctly.
"""

import asyncio
import websockets
import json
import time

async def test_websocket():
    """Test WebSocket connection and message handling"""
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
                "content": "Hello, can you help me test the system?"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message")
            
            # Wait for responses
            for i in range(3):  # Expect user message, AI response, and agent update
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"📥 Received: {data['type']}")
                    
                    if data['type'] == 'new_message':
                        print(f"   Message: {data['message']['content']}")
                    elif data['type'] == 'agent_update':
                        print(f"   Agent status: {data['agent_in_loop']['status']}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print("✅ Test completed successfully")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing Agent in the Loop API...")
    asyncio.run(test_websocket())
