# Agent in the Loop API

FastAPI server that integrates the React frontend with the Python background agent system.

## Features

- **WebSocket Communication**: Real-time bidirectional communication with the frontend
- **Background Agent Integration**: Connects to the existing ReAct-based background agent system
- **REST API Endpoints**: For status monitoring and task management
- **CORS Support**: Configured for frontend integration
- **Automatic Reconnection**: WebSocket clients automatically reconnect on connection loss

## API Endpoints

### WebSocket
- `ws://localhost:8000/ws` - Main WebSocket endpoint for real-time communication

### REST API
- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `GET /conversation/history` - Get conversation history
- `GET /agents/status` - Get current agent status
- `POST /conversation/clear` - Clear conversation history
- `POST /agents/reset` - Reset all agents to idle state
- `GET /tasks/{task_id}` - Get status of a specific task
- `POST /tasks/cleanup` - Clean up old tasks

### API Documentation
- `http://localhost:8000/docs` - Interactive API documentation (Swagger UI)
- `http://localhost:8000/redoc` - Alternative API documentation

## WebSocket Message Types

### Client to Server
```json
{
  "type": "user_message",
  "content": "Hello, can you help me?"
}
```

```json
{
  "type": "get_status"
}
```

### Server to Client
```json
{
  "type": "new_message",
  "message": {
    "id": "msg_123",
    "type": "ai",
    "content": "I'd be happy to help!",
    "timestamp": "2024-01-01T12:00:00Z",
    "is_agent_result": false
  }
}
```

```json
{
  "type": "agent_update",
  "agent_in_loop": {
    "is_active": true,
    "current_task": "Analyzing conversation...",
    "status": "analyzing"
  },
  "sub_agents": [
    {
      "id": "email",
      "name": "Email Agent",
      "status": "idle",
      "icon": "📧"
    }
  ]
}
```

## Installation

1. Install dependencies:
```bash
cd api
pip install -r requirements.txt
```

2. Make sure you have a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Running the Server

### Option 1: Using the startup script
```bash
cd api
python start_server.py
```

### Option 2: Using uvicorn directly
```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Using the main module
```bash
cd api
python main.py
```

## Integration with Frontend

The API is designed to work seamlessly with the React frontend:

1. **Start the API server** (port 8000)
2. **Start the React frontend** (port 3000)
3. **The frontend automatically connects** to the WebSocket endpoint
4. **Real-time communication** enables live agent monitoring

## Background Agent Integration

The API integrates with the existing background agent system:

- **Automatic Task Creation**: Every conversation turn triggers background analysis
- **Real-time Monitoring**: WebSocket updates show agent status changes
- **Result Delivery**: Agent results are pushed back to the frontend
- **Error Handling**: Graceful handling of agent failures

## Development

### Hot Reload
The server runs with hot reload enabled, so changes to the code will automatically restart the server.

### Logging
The server provides detailed logging for:
- WebSocket connections and disconnections
- Message handling
- Agent task creation and completion
- Error conditions

### Testing
You can test the API using:
- The interactive documentation at `/docs`
- WebSocket clients like `wscat`
- The integrated React frontend

## Architecture

```
Frontend (React) ←→ WebSocket ←→ FastAPI Server ←→ Background Agent System
     ↓                    ↓              ↓                    ↓
  Port 3000          Port 8000      Python Process      LangGraph Agent
```

The API acts as a bridge between the React frontend and the Python background agent system, providing real-time communication and state management.
