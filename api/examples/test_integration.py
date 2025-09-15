#!/usr/bin/env python3
"""
Test script to verify the API integration with background agents works correctly.
"""

import asyncio
import websockets
import json
import time

async def test_integration():
    """Test the complete integration"""
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
                "content": "Hello! Can you help me understand how the background agents work?"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message")
            
            # Wait for responses
            message_count = 0
            agent_result_received = False
            
            for i in range(10):  # Wait for up to 10 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(response)
                    message_count += 1
                    print(f"📥 Message {message_count}: {data['type']}")
                    
                    if data['type'] == 'new_message':
                        content = data['message']['content']
                        print(f"   Content: {content[:100]}...")
                        
                        if data['message']['is_agent_result']:
                            agent_result_received = True
                            print("   ✅ Agent result received!")
                    
                    elif data['type'] == 'agent_update':
                        agent_status = data['agent_in_loop']['status']
                        print(f"   Agent status: {agent_status}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"✅ Test completed. Received {message_count} messages")
            
            if agent_result_received:
                print("✅ Background agent integration working correctly!")
            else:
                print("⚠️  No agent result received - may need to check background agent")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing API integration with background agents...")
    asyncio.run(test_integration())
