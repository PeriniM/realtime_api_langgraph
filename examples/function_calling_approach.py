#!/usr/bin/env python3
"""
Alternative approach using function calling for background agent integration.
This approach uses the OpenAI Realtime API's function calling feature to
trigger background tasks and handle their results.
"""

import asyncio
import json
import time
from typing import Any, Dict
from simple_background_agent import create_background_task, get_task_status

class FunctionCallingBackgroundManager:
    def __init__(self):
        self.active_tasks = {}
        self.conversation_history = []
    
    def get_session_tools(self):
        """Define available functions for the model to call"""
        return [
            {
                "type": "function",
                "name": "send_email",
                "description": "Send an email to a recipient with a subject and body",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Email address of the recipient"
                        },
                        "subject": {
                            "type": "string", 
                            "description": "Subject line of the email"
                        },
                        "body": {
                            "type": "string",
                            "description": "Body content of the email"
                        }
                    },
                    "required": ["recipient", "subject", "body"]
                }
            },
            {
                "type": "function",
                "name": "update_calendar",
                "description": "Schedule or update a calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the calendar event"
                        },
                        "datetime": {
                            "type": "string",
                            "description": "Date and time of the event (ISO format preferred)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location of the event (optional)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the event (optional)"
                        }
                    },
                    "required": ["title", "datetime"]
                }
            },
            {
                "type": "function",
                "name": "research_topic",
                "description": "Research a specific topic and gather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The topic to research"
                        },
                        "depth": {
                            "type": "string",
                            "enum": ["quick", "detailed", "comprehensive"],
                            "description": "How thorough the research should be"
                        },
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Preferred sources to search (optional)"
                        }
                    },
                    "required": ["topic", "depth"]
                }
            },
            {
                "type": "function",
                "name": "background_processing",
                "description": "Perform general background processing or analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_type": {
                            "type": "string",
                            "description": "Type of background task to perform"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data or context for the background task"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Priority level of the task"
                        }
                    },
                    "required": ["task_type"]
                }
            }
        ]
    
    async def handle_function_call(self, connection, function_call_item):
        """Handle a function call from the model"""
        function_name = function_call_item.get("name")
        call_id = function_call_item.get("call_id")
        arguments = json.loads(function_call_item.get("arguments", "{}"))
        
        print(f"[Function Call] {function_name} called with args: {arguments}")
        
        # Create background task based on function call
        task_id = self._create_background_task_from_function(function_name, arguments)
        
        # Store the call_id for later reference
        self.active_tasks[task_id] = {
            "call_id": call_id,
            "function_name": function_name,
            "arguments": arguments,
            "created_at": time.time(),
            "completed": False
        }
        
        # Start monitoring the task
        asyncio.create_task(self._monitor_function_task(connection, task_id))
        
        # Return a temporary response to the model
        return {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps({
                    "status": "processing",
                    "message": f"Starting {function_name} task...",
                    "task_id": task_id
                })
            }
        }
    
    def _create_background_task_from_function(self, function_name: str, arguments: dict) -> str:
        """Create a background task based on function call arguments"""
        
        # Convert function call to a user message for the background agent
        if function_name == "send_email":
            user_message = f"Send email to {arguments.get('recipient')} with subject '{arguments.get('subject')}' and body '{arguments.get('body')}'"
        elif function_name == "update_calendar":
            user_message = f"Schedule calendar event '{arguments.get('title')}' for {arguments.get('datetime')} at {arguments.get('location', 'TBD')}"
        elif function_name == "research_topic":
            user_message = f"Research topic '{arguments.get('topic')}' with {arguments.get('depth')} depth"
        elif function_name == "background_processing":
            user_message = f"Perform {arguments.get('task_type')} background processing with data {arguments.get('data', {})}"
        else:
            user_message = f"Execute {function_name} with arguments {arguments}"
        
        # Create the background task
        task_id = create_background_task(
            user_message,
            f"Executing {function_name} function call",
            self.conversation_history[-3:] if self.conversation_history else []
        )
        
        return task_id
    
    async def _monitor_function_task(self, connection, task_id: str):
        """Monitor a function task and provide results when complete"""
        while task_id in self.active_tasks and not self.active_tasks[task_id]["completed"]:
            status = get_task_status(task_id)
            
            if status['status'] == 'completed':
                await self._deliver_function_result(connection, task_id, status['result'])
                break
            elif status['status'] == 'error':
                await self._deliver_function_error(connection, task_id, status['error'])
                break
            
            await asyncio.sleep(0.5)
    
    async def _deliver_function_result(self, connection, task_id: str, result: dict):
        """Deliver function call result back to the model"""
        if task_id not in self.active_tasks:
            return
        
        task_info = self.active_tasks[task_id]
        call_id = task_info["call_id"]
        function_name = task_info["function_name"]
        
        try:
            # Create function call output with the result
            await connection.conversation.item.create(
                item={
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({
                        "status": "completed",
                        "function": function_name,
                        "result": result,
                        "message": f"{function_name} completed successfully"
                    })
                }
            )
            
            # Generate a response using the function result
            await connection.response.create()
            
            self.active_tasks[task_id]["completed"] = True
            print(f"[Function Call] Delivered result for {function_name} (task {task_id})")
            
        except Exception as e:
            print(f"[Function Call] Failed to deliver result: {e}")
    
    async def _deliver_function_error(self, connection, task_id: str, error: str):
        """Deliver function call error back to the model"""
        if task_id not in self.active_tasks:
            return
        
        task_info = self.active_tasks[task_id]
        call_id = task_info["call_id"]
        function_name = task_info["function_name"]
        
        try:
            await connection.conversation.item.create(
                item={
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({
                        "status": "error",
                        "function": function_name,
                        "error": error,
                        "message": f"{function_name} failed: {error}"
                    })
                }
            )
            
            # Generate a response about the error
            await connection.response.create()
            
            self.active_tasks[task_id]["completed"] = True
            print(f"[Function Call] Delivered error for {function_name} (task {task_id})")
            
        except Exception as e:
            print(f"[Function Call] Failed to deliver error: {e}")
    
    def add_conversation_turn(self, user_message: str, ai_response: str):
        """Add a conversation turn to history"""
        self.conversation_history.append({
            "user": user_message,
            "ai": ai_response,
            "timestamp": time.time()
        })
    
    def cleanup_completed_tasks(self):
        """Clean up completed function tasks"""
        to_remove = []
        for task_id, task_info in self.active_tasks.items():
            if task_info.get("completed", False):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]

# Example usage in main function:
"""
# In your main() function, add function calling support:

# 1. Configure session with tools
await conn.session.update(session={
    "type": "realtime",
    "model": "gpt-realtime",
    "tools": function_manager.get_session_tools(),
    "tool_choice": "auto",
    # ... other session config
})

# 2. Handle function calls in your event loop
async for event in conn:
    if event.type == "response.done":
        # Check if response contains function calls
        if hasattr(event, 'response') and hasattr(event.response, 'output'):
            for output_item in event.response.output:
                if output_item.type == "function_call":
                    await function_manager.handle_function_call(conn, output_item)
"""
