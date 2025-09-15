#!/usr/bin/env python3
"""
ReAct-based background agent that uses an LLM to analyze conversations and provide feedback.
Stores task results in memory for polling by the main application.
"""

import asyncio
import json
import random
import time
from typing import Dict, Any
from dataclasses import dataclass, asdict
import threading
from pathlib import Path
from datetime import datetime
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TaskResult:
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    result: Any = None
    error: str = None
    created_at: float = 0.0
    completed_at: float = 0.0
    message: str = ""

# ---- Background Agent Tools ----
# No tools needed - just conversation analysis

class ReActBackgroundAgent:
    def __init__(self):
        self.tasks: Dict[str, TaskResult] = {}
        self.task_counter = 0
        self.lock = threading.Lock()
        
        # Create checkpointer for conversation memory
        self.checkpointer = InMemorySaver()
        
        # Create the ReAct agent without tools - just for conversation analysis
        system_prompt = """You are a background conversation analyst. Your role is to analyze conversation turns and provide insights about the conversation quality, flow, and patterns.

For each conversation turn you receive, analyze:

1. **Tone and Sentiment**: How does this turn affect the overall conversation mood?
2. **Topic Evolution**: How are topics developing or changing throughout the conversation?
3. **User Intent**: What is the user trying to achieve in this turn?
4. **Response Quality**: How well does the AI's response address the user's needs?
5. **Conversation Flow**: How does this turn contribute to the overall conversation flow?
6. **Patterns**: Any emerging patterns or trends across the full conversation?
7. **Improvement Suggestions**: What could be done better based on the full context?

You have access to the full conversation history through your memory. Use this context to provide comprehensive analysis that considers both the current turn and the broader conversation patterns.

Provide thoughtful, constructive feedback that helps improve the conversation experience."""
        
        self.agent = create_react_agent(
            model="openai:gpt-4o-mini",
            tools=[],  # No tools - just analysis
            name="background_agent",
            checkpointer=self.checkpointer,
            prompt=system_prompt
        )
        
        # Configuration for the agent (thread_id for conversation memory)
        self.config = {"configurable": {"thread_id": "conversation_analysis"}}
    
    def create_task(self, user_message: str, ai_response: str, conversation_context: list = None) -> str:
        """Create a new background task and return task ID"""
        with self.lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{int(time.time())}"
            
            task = TaskResult(
                task_id=task_id,
                status="pending",
                created_at=time.time(),
                message=f"Processing: {user_message[:50]}..."
            )
            
            self.tasks[task_id] = task
            
            # Start background task in thread
            thread = threading.Thread(
                target=self._run_background_task,
                args=(task_id, user_message, ai_response, conversation_context),
                daemon=True
            )
            thread.start()
            
            print(f"[Background Agent] Created task {task_id}")
            return task_id
    
    def _run_background_task(self, task_id: str, user_message: str, ai_response: str, conversation_context: list):
        """Run the actual background task using ReAct agent"""
        try:
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = "running"
                    self.tasks[task_id].message = "Task is running..."
            
            print(f"[Background Agent] Task {task_id} starting ReAct processing")
            
            # Create context for the ReAct agent
            context = self._create_agent_context(user_message, ai_response, conversation_context)
            
            # Run the ReAct agent with checkpointer to maintain conversation memory
            response = self.agent.invoke(
                {"messages": [{"role": "user", "content": context}]},
                config=self.config
            )
            
            # Extract the final result
            final_message = response["messages"][-1].content
            
            # Parse the result to extract structured data
            result = self._parse_agent_result(final_message, user_message)
            
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = "completed"
                    self.tasks[task_id].result = result
                    self.tasks[task_id].completed_at = time.time()
                    self.tasks[task_id].message = "Task completed successfully"
            
            print(f"[Background Agent] Task {task_id} completed")
            
        except Exception as e:
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = "error"
                    self.tasks[task_id].error = str(e)
                    self.tasks[task_id].completed_at = time.time()
                    self.tasks[task_id].message = f"Task failed: {str(e)}"
            
            print(f"[Background Agent] Task {task_id} failed: {e}")
    
    def _create_agent_context(self, user_message: str, ai_response: str, conversation_context: list) -> str:
        """Create context for the ReAct agent"""
        # Since the agent has a system prompt and full conversation memory,
        # we just need to provide the current turn
        context = f"""New conversation turn:
User: "{user_message}"
AI: "{ai_response}"

Please analyze this turn."""
        return context
    
    def _parse_agent_result(self, agent_response: str, user_message: str) -> Dict[str, Any]:
        """Parse the agent response to extract structured result data"""
        # Since we're only doing conversation analysis, always return analysis result
        return {
            "action": "conversation_analysis",
            "message": agent_response,
            "user_request": user_message,
            "timestamp": time.time(),
            "status": "success"
        }
    
    def get_task_status(self, task_id: str) -> TaskResult:
        """Get the status of a specific task"""
        with self.lock:
            return self.tasks.get(task_id, TaskResult(
                task_id=task_id,
                status="not_found",
                error="Task not found"
            ))
    
    def get_all_tasks(self) -> Dict[str, TaskResult]:
        """Get all tasks (for debugging)"""
        with self.lock:
            return self.tasks.copy()
    
    def cleanup_old_tasks(self, max_age_seconds: int = 300):
        """Clean up tasks older than max_age_seconds"""
        current_time = time.time()
        with self.lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if current_time - task.created_at > max_age_seconds:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
                print(f"[Background Agent] Cleaned up old task {task_id}")
    
    def get_conversation_history(self):
        """Get the conversation history from the checkpointer"""
        try:
            # Get the current state from the checkpointer
            state = self.checkpointer.get(self.config)
            if state and 'messages' in state.values:
                messages = state.values['messages']
                print(f"[Background Agent] Conversation history has {len(messages)} messages")
                return messages
            else:
                print("[Background Agent] No conversation history found")
                return []
        except Exception as e:
            print(f"[Background Agent] Error getting conversation history: {e}")
            return []

# Global agent instance
background_agent = ReActBackgroundAgent()

def create_background_task(user_message: str, ai_response: str, conversation_context: list = None) -> str:
    """Create a background task and return task ID"""
    return background_agent.create_task(user_message, ai_response, conversation_context)

def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get task status as dictionary"""
    task = background_agent.get_task_status(task_id)
    return asdict(task)

def cleanup_old_tasks():
    """Clean up old tasks"""
    background_agent.cleanup_old_tasks()

def get_conversation_history():
    """Get the conversation history from the background agent's memory"""
    return background_agent.get_conversation_history()

if __name__ == "__main__":
    # Test the conversation analysis background agent with memory
    print("Testing Conversation Analysis Background Agent with Memory...")
    
    # Simulate a conversation with multiple turns
    conversation_turns = [
        ("Hey, how are you doing?", "I'm doing great, thanks for asking! How about you?"),
        ("I'm good too! What's the weather like?", "I don't have access to real-time weather data, but I'd be happy to help you find weather information if you'd like!"),
        ("That's okay, thanks anyway!", "You're welcome! Is there anything else I can help you with today?")
    ]
    
    for i, (user_msg, ai_msg) in enumerate(conversation_turns, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {user_msg}")
        print(f"AI: {ai_msg}")
        
        # Create background task
        task_id = create_background_task(user_msg, ai_msg, None)
        print(f"Created task: {task_id}")
        
        # Poll for completion
        while True:
            status = get_task_status(task_id)
            if status['status'] in ['completed', 'error']:
                print(f"Analysis completed!")
                break
            time.sleep(0.5)
        
        # Show conversation history after each turn
        history = get_conversation_history()
        print(f"Conversation history now has {len(history)} messages")
    
    print("\n--- Final Conversation History ---")
    history = get_conversation_history()
    for i, msg in enumerate(history):
        print(f"{i+1}. {msg}")
