#!/usr/bin/env python3
"""
Test script to verify that duplicate messages are fixed.
"""

import asyncio
import websockets
import json
import time

async def test_duplicate_fix():
    """Test that messages are not duplicated"""
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
            
            # Wait for responses and track message IDs
            message_ids = set()
            duplicate_count = 0
            
            for i in range(10):  # Wait for up to 10 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data['type'] == 'new_message':
                        message_id = data['message']['id']
                        if message_id in message_ids:
                            duplicate_count += 1
                            print(f"⚠️  Duplicate message detected: {message_id}")
                        else:
                            message_ids.add(message_id)
                            print(f"📥 New message: {message_id} - {data['message']['content'][:50]}...")
                    else:
                        print(f"📥 Other message: {data['type']}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"✅ Test completed.")
            print(f"📊 Total unique messages: {len(message_ids)}")
            print(f"🔍 Duplicate count: {duplicate_count}")
            
            if duplicate_count == 0:
                print("✅ No duplicates detected!")
            else:
                print(f"⚠️  {duplicate_count} duplicates detected")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the API server is running with: python start_server.py")

if __name__ == "__main__":
    print("🧪 Testing Duplicate Message Fix...")
    asyncio.run(test_duplicate_fix())