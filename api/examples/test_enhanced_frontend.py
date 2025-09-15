#!/usr/bin/env python3
"""
Test script to verify the enhanced frontend works with background agent integration.
This script simulates the background agent workflow and sends appropriate WebSocket messages.
"""

import asyncio
import websockets
import json
import time

async def test_enhanced_frontend():
    """Test the enhanced frontend with background agent simulation"""
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
                "content": "Hello! Can you help me analyze this conversation and provide some insights?"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message to trigger background agent")
            
            # Monitor responses and track agent activity
            message_count = 0
            agent_updates_received = 0
            agent_result_received = False
            
            print("\n🔍 Monitoring agent activity...")
            
            for i in range(15):  # Wait for up to 15 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    print(f"\n📥 Message {message_count}: {data['type']}")
                    
                    if data['type'] == 'new_message':
                        content = data['message']['content']
                        is_agent_result = data['message'].get('is_agent_result', False)
                        
                        if is_agent_result:
                            agent_result_received = True
                            print(f"   🎉 Agent Result: {content[:100]}...")
                        else:
                            print(f"   💬 Message: {content[:50]}...")
                    
                    elif data['type'] == 'agent_update':
                        agent_updates_received += 1
                        agent_in_loop = data.get('agent_in_loop', {})
                        sub_agents = data.get('sub_agents', [])
                        
                        print(f"   🤖 Agent in Loop: {agent_in_loop.get('status', 'unknown')}")
                        if agent_in_loop.get('current_task'):
                            print(f"   📋 Current Task: {agent_in_loop['current_task']}")
                        
                        active_sub_agents = [agent for agent in sub_agents if agent.get('status') == 'active']
                        if active_sub_agents:
                            print(f"   ⚡ Active Sub-agents: {[agent['name'] for agent in active_sub_agents]}")
                        
                    elif data['type'] == 'keepalive':
                        print("   💓 Keepalive received")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"\n📊 Test Results:")
            print(f"   Total messages received: {message_count}")
            print(f"   Agent updates received: {agent_updates_received}")
            print(f"   Agent result received: {'✅ Yes' if agent_result_received else '❌ No'}")
            
            if agent_updates_received > 0 and agent_result_received:
                print("\n🎉 Enhanced frontend integration working correctly!")
                print("   - Background agent activity detected")
                print("   - Real-time status updates received")
                print("   - Agent results delivered to frontend")
            else:
                print("\n⚠️  Some issues detected:")
                if agent_updates_received == 0:
                    print("   - No agent updates received")
                if not agent_result_received:
                    print("   - No agent result received")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the API server is running with: python start_server.py")

if __name__ == "__main__":
    print("🧪 Testing Enhanced Frontend with Background Agent Integration...")
    print("📋 This test verifies:")
    print("   - Real-time agent status updates")
    print("   - Background agent processing")
    print("   - Agent result delivery")
    print("   - Interactive frontend feedback")
    print("")
    asyncio.run(test_enhanced_frontend())
