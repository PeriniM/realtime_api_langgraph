#!/usr/bin/env python3
"""
Test script to verify that the supervisor agent status changes from 'analyzing' to 'running'.
"""

import asyncio
import websockets
import json
import time

async def test_supervisor_status():
    """Test that supervisor agent status changes correctly"""
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
            
            # Monitor agent status changes
            status_changes = []
            message_count = 0
            
            print("\n🔍 Monitoring supervisor agent status changes...")
            
            for i in range(20):  # Wait for up to 20 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    if data['type'] == 'agent_update':
                        agent_in_loop = data.get('agent_in_loop', {})
                        status = agent_in_loop.get('status', 'unknown')
                        current_task = agent_in_loop.get('current_task', 'No task')
                        is_active = agent_in_loop.get('is_active', False)
                        
                        status_changes.append({
                            'status': status,
                            'current_task': current_task,
                            'is_active': is_active,
                            'timestamp': time.time()
                        })
                        
                        print(f"📥 Agent Update {len(status_changes)}: Status='{status}', Task='{current_task}', Active={is_active}")
                        
                        # Check if we've seen the expected status progression
                        if len(status_changes) >= 2:
                            if (status_changes[-2]['status'] == 'analyzing' and 
                                status_changes[-1]['status'] == 'executing'):
                                print("✅ SUCCESS: Status changed from 'analyzing' to 'executing'!")
                                break
                    
                    elif data['type'] == 'new_message':
                        content = data['message']['content']
                        is_agent_result = data['message'].get('is_agent_result', False)
                        
                        if is_agent_result:
                            print(f"🎉 Agent Result: {content[:100]}...")
                        else:
                            print(f"💬 Message: {content[:50]}...")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            print(f"\n📊 Test Results:")
            print(f"   Total messages received: {message_count}")
            print(f"   Agent status changes: {len(status_changes)}")
            
            # Analyze status progression
            statuses = [change['status'] for change in status_changes]
            print(f"   Status progression: {' -> '.join(statuses)}")
            
            # Check if we saw the expected progression
            if 'analyzing' in statuses and 'executing' in statuses:
                analyzing_index = statuses.index('analyzing')
                executing_index = statuses.index('executing')
                
                if executing_index > analyzing_index:
                    print("✅ SUCCESS: Supervisor agent status correctly changed from 'analyzing' to 'executing'!")
                    print("   - This means the background task is now properly showing as 'Running' in the frontend")
                else:
                    print("⚠️  Status progression was not in expected order")
            else:
                print("⚠️  Did not see expected status progression (analyzing -> executing)")
                if 'analyzing' not in statuses:
                    print("   - Missing 'analyzing' status")
                if 'executing' not in statuses:
                    print("   - Missing 'executing' status")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the API server is running with: python start_server.py")

if __name__ == "__main__":
    print("🧪 Testing Supervisor Agent Status Changes...")
    print("📋 This test verifies:")
    print("   - Agent status starts as 'analyzing'")
    print("   - Agent status changes to 'executing' when background task is running")
    print("   - Frontend will show 'Running' instead of 'Analyzing'")
    print("")
    asyncio.run(test_supervisor_status())
