# Agent in the Loop - Complete Integration

This document explains how to run the complete integrated system with the React frontend connected to the Python backend via FastAPI.

## 🏗️ System Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐    Python    ┌─────────────────┐
│   React Frontend │ ←─────────────→ │   FastAPI Server │ ←─────────→ │ Background Agent │
│   (Port 3000)    │                 │   (Port 8000)    │             │   (LangGraph)   │
└─────────────────┘                 └─────────────────┘             └─────────────────┘
```

## 🚀 Quick Start

### Option 1: Automated Startup (Recommended)
```bash
# From the project root
python start_system.py
```

This will:
- Check system requirements
- Start the FastAPI server
- Provide instructions for starting the frontend

### Option 2: Manual Startup

#### 1. Start the API Server
```bash
cd api
pip install -r requirements.txt
python start_server.py
```

#### 2. Start the React Frontend
```bash
# In a new terminal
cd frontend
npm install
npm start
```

## 🔧 Prerequisites

### Required Files
- `.env` file in project root with: `OPENAI_API_KEY=your_key_here`
- Python 3.8+ with pip
- Node.js 14+ with npm

### Dependencies
- **Backend**: FastAPI, WebSockets, LangGraph, OpenAI
- **Frontend**: React, Framer Motion, Lucide React

## 📡 Communication Flow

### 1. User Input
- User types message in React frontend
- Frontend sends message via WebSocket to FastAPI server
- Server receives message and creates user message in conversation

### 2. AI Response
- Server generates AI response (currently mock, can be integrated with OpenAI)
- Server sends AI response back to frontend via WebSocket
- Frontend displays AI response in chat

### 3. Background Agent Activation
- Server triggers background agent analysis
- Agent in the Loop becomes active
- Appropriate sub-agent is highlighted
- Real-time status updates sent to frontend

### 4. Agent Result Delivery
- Background agent completes analysis
- Result is sent to frontend as special agent message
- Agent states reset to idle
- User sees agent result in chat with special styling

## 🎯 Features

### Real-time Communication
- **WebSocket Connection**: Bidirectional real-time communication
- **Automatic Reconnection**: Frontend reconnects if connection is lost
- **Status Indicators**: Visual feedback for connection status

### Agent Monitoring
- **Live Status Updates**: Real-time agent state changes
- **Visual Feedback**: Animated agent cards and status indicators
- **Activity Log**: Recent agent activities displayed

### Fallback Mode
- **Mock Mode**: If API server is not running, frontend falls back to mock behavior
- **Seamless Transition**: Users can switch between live and mock modes

## 🔍 Testing the Integration

### 1. Check Connection Status
- Look for "Connected to API" in the chat header
- Agent panel should show "🟢 Live" status

### 2. Test Agent Triggers
Try these messages to trigger different agents:
- **Email**: "Can you send an email to john@example.com?"
- **Calendar**: "Schedule a meeting for tomorrow at 2 PM"
- **Notes**: "Find my notes about the project proposal"
- **Research**: "What's the latest news about AI?"

### 3. Observe Agent Behavior
- Agent in the Loop card should light up
- Appropriate sub-agent should become active
- Agent result should appear in chat with green styling

## 🛠️ Development

### API Development
- **Hot Reload**: API server restarts automatically on code changes
- **Logging**: Detailed logs for WebSocket connections and agent activities
- **Documentation**: Available at `http://localhost:8000/docs`

### Frontend Development
- **Hot Reload**: React app updates automatically on code changes
- **WebSocket Service**: Centralized WebSocket communication
- **State Management**: React hooks for real-time state updates

### Adding New Agents
1. **Backend**: Add new agent to `sub_agents` list in `main.py`
2. **Frontend**: Add new agent to `subAgents` state in `App.js`
3. **Integration**: Update trigger logic in both frontend and backend

## 🐛 Troubleshooting

### Common Issues

#### Frontend shows "Disconnected (Mock Mode)"
- **Cause**: API server not running or connection failed
- **Solution**: Start the API server with `python start_server.py`

#### WebSocket connection errors
- **Cause**: Port conflicts or firewall issues
- **Solution**: Check that port 8000 is available and not blocked

#### Agent not triggering
- **Cause**: Message doesn't match trigger patterns
- **Solution**: Check trigger keywords in both frontend and backend code

#### Import errors in API
- **Cause**: Missing dependencies or path issues
- **Solution**: Install requirements with `pip install -r requirements.txt`

### Debug Mode
- **API Logs**: Check terminal where API server is running
- **Frontend Logs**: Open browser developer console
- **WebSocket**: Use browser dev tools Network tab to monitor WebSocket messages

## 📊 Monitoring

### API Endpoints for Monitoring
- `GET /health` - Server health check
- `GET /agents/status` - Current agent status
- `GET /conversation/history` - Conversation history
- `GET /tasks/{task_id}` - Specific task status

### WebSocket Message Types
- `user_message` - User input from frontend
- `new_message` - New message to display
- `agent_update` - Agent status changes
- `get_status` - Request current status

## 🔮 Future Enhancements

### Planned Features
- **Real OpenAI Integration**: Replace mock AI responses with actual OpenAI API calls
- **Audio Support**: Integrate with the existing audio pipeline
- **Advanced Agents**: Add more sophisticated agent capabilities
- **Persistence**: Save conversation history and agent states
- **Analytics**: Track agent performance and usage patterns

### Integration Opportunities
- **Real-time Audio**: Connect with the existing `test_bidirectional.py` audio system
- **Function Calling**: Implement the function calling approach from `function_calling_approach.py`
- **Advanced Monitoring**: Add metrics and performance monitoring

## 📝 API Reference

### WebSocket Messages

#### Client → Server
```json
{
  "type": "user_message",
  "content": "Hello, can you help me?"
}
```

#### Server → Client
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

### REST Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /conversation/history` - Get messages
- `GET /agents/status` - Get agent status
- `POST /conversation/clear` - Clear history
- `POST /agents/reset` - Reset agents

This integrated system demonstrates the complete "Agent in the Loop" concept with real-time communication between the React frontend and Python backend, providing a foundation for building more sophisticated AI-powered applications.
