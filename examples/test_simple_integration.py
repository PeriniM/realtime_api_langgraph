#!/usr/bin/env python3
"""
Simple test script to demonstrate the background agent integration
without needing the full audio setup.
"""

import asyncio
import time
from simple_background_agent import create_background_task, get_task_status, cleanup_old_tasks

async def test_background_agent():
    """Test the background agent with simulated conversation turns"""
    
    print("🧪 Testing Simple Background Agent Integration")
    print("=" * 50)
    
    # Simulate conversation turns
    test_conversations = [
        {
            "user": "Please send an email to John about the meeting tomorrow",
            "ai": "I'll help you send that email to John about tomorrow's meeting."
        },
        {
            "user": "Can you check my calendar for next week?",
            "ai": "I'll check your calendar for next week and let you know what's scheduled."
        },
        {
            "user": "Research the latest AI developments",
            "ai": "I'll research the latest AI developments for you."
        },
        {
            "user": "Hello, how are you today?",
            "ai": "Hello! I'm doing well, thank you for asking. How can I help you today?"
        }
    ]
    
    # Create tasks for each conversation turn
    task_ids = []
    for i, conv in enumerate(test_conversations):
        print(f"\n📝 Conversation Turn {i+1}:")
        print(f"   User: {conv['user']}")
        print(f"   AI: {conv['ai']}")
        
        task_id = create_background_task(
            conv['user'], 
            conv['ai'], 
            test_conversations[:i+1]  # Full history up to this point
        )
        task_ids.append(task_id)
        print(f"   ✅ Created background task: {task_id}")
    
    print(f"\n⏳ Polling {len(task_ids)} background tasks...")
    print("=" * 50)
    
    # Poll for completion
    completed_tasks = set()
    start_time = time.time()
    
    while len(completed_tasks) < len(task_ids):
        for task_id in task_ids:
            if task_id in completed_tasks:
                continue
                
            status = get_task_status(task_id)
            elapsed = time.time() - start_time
            
            if status['status'] == 'completed':
                print(f"✅ Task {task_id} completed after {elapsed:.1f}s")
                print(f"   Result: {status['result']}")
                completed_tasks.add(task_id)
                
            elif status['status'] == 'error':
                print(f"❌ Task {task_id} failed: {status['error']}")
                completed_tasks.add(task_id)
                
            elif status['status'] == 'running':
                print(f"🔄 Task {task_id} is running... ({elapsed:.1f}s)")
        
        if len(completed_tasks) < len(task_ids):
            await asyncio.sleep(1)
    
    print("\n🎉 All background tasks completed!")
    print("=" * 50)
    
    # Show final results
    print("\n📊 Final Results:")
    for task_id in task_ids:
        status = get_task_status(task_id)
        if status['status'] == 'completed':
            result = status['result']
            action = result.get('action', 'unknown')
            print(f"   {task_id}: {action} - {result.get('message', 'No message')}")
    
    # Cleanup
    cleanup_old_tasks()
    print("\n🧹 Cleaned up old tasks")

if __name__ == "__main__":
    asyncio.run(test_background_agent())
