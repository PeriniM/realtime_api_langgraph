#!/usr/bin/env python3
"""
Simple test to check if background agents are working.
"""

import asyncio
import websockets
import json
import time

async def test_background_agents():
    """Test if background agents are sending messages"""
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for initial agent update
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📡 Received initial update: {data['type']}")
            
            # Send a test message that should trigger background agent
            test_message = {
                "type": "user_message",
                "content": "Hello! Can you help me analyze this conversation and provide some insights about the background agent system?"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message to trigger background agent")
            
            # Monitor responses
            message_count = 0
            agent_result_received = False
            agent_updates_received = 0
            
            print("\n🔍 Monitoring for background agent messages...")
            
            for i in range(20):  # Wait for up to 20 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    print(f"\n📥 Message {message_count}: {data['type']}")
                    
                    if data['type'] == 'new_message':
                        content = data['message']['content']
                        is_agent_result = data['message'].get('is_agent_result', False)
                        
                        if is_agent_result:
                            agent_result_received = True
                            print(f"   🎉 AGENT RESULT: {content}")
                        else:
                            print(f"   💬 Regular message: {content[:100]}...")
                    
                    elif data['type'] == 'agent_update':
                        agent_updates_received += 1
                        agent_in_loop = data.get('agent_in_loop', {})
                        print(f"   🤖 Agent status: {agent_in_loop.get('status', 'unknown')}")
                        if agent_in_loop.get('current_task'):
                            print(f"   📋 Current task: {agent_in_loop['current_task']}")
                    
                    elif data['type'] == 'keepalive':
                        print("   💓 Keepalive")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"\n📊 Test Results:")
            print(f"   Total messages received: {message_count}")
            print(f"   Agent updates received: {agent_updates_received}")
            print(f"   Agent result received: {'✅ YES' if agent_result_received else '❌ NO'}")
            
            if agent_result_received:
                print("\n✅ Background agents are working correctly!")
            else:
                print("\n❌ Background agents are NOT sending messages!")
                print("   This indicates a problem with the background agent system.")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing Background Agent Message Delivery...")
    asyncio.run(test_background_agents())
