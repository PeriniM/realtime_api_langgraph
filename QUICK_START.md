# Quick Start Guide

## 🚀 Getting Started

### 1. Start the API Server
```bash
cd api
pip install -r requirements.txt
python start_server.py
```

You should see:
```
🚀 Starting Agent in the Loop API server...
📡 WebSocket endpoint: ws://localhost:8000/ws
🌐 API documentation: http://localhost:8000/docs
🔗 Frontend should connect to: http://localhost:3000
```

### 2. Start the React Frontend
```bash
# In a new terminal
cd frontend
npm install
npm start
```

### 3. Test the Integration
1. Open `http://localhost:3000` in your browser
2. You should see "Connected to API" in the status indicator
3. Try typing a message or clicking the audio button

## 🔧 Troubleshooting

### If you see "Disconnected (Mock Mode)"
- Make sure the API server is running on port 8000
- Check the browser console for WebSocket connection errors
- Verify the API server logs for any errors

### If the audio button doesn't work
- The audio button is currently a mock implementation
- It will simulate recording for 3 seconds then send a test message
- In a real implementation, this would integrate with the browser's microphone API

### If you get JSON serialization errors
- The API has been updated to handle datetime objects properly
- Make sure you're using the latest version of the API code

## 🧪 Testing the API

You can test the API directly:
```bash
cd api
python test_api.py
```

This will:
- Connect to the WebSocket
- Send a test message
- Verify the response flow

## 📡 API Endpoints

- **WebSocket**: `ws://localhost:8000/ws`
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

## 🎯 Expected Behavior

1. **Text Messages**: Type a message → See it in chat → Get AI response → See agent analysis
2. **Audio Button**: Click → See "Listening..." → Wait 3 seconds → Get mock voice message
3. **Agent Panel**: Watch agents light up when triggered by specific keywords

## 🔍 Debugging

### Check API Logs
Look for these messages in the API server terminal:
- `[API] Client connected. Total connections: X`
- `[API] Client disconnected. Total connections: X`
- `[Background Agent] Task X completed`

### Check Browser Console
Open Developer Tools (F12) and look for:
- WebSocket connection messages
- Any JavaScript errors
- Network tab for WebSocket traffic

## 🎉 Success Indicators

- ✅ Frontend shows "Connected to API"
- ✅ Agent panel shows "🟢 Live"
- ✅ Messages appear in chat
- ✅ Agent cards light up when triggered
- ✅ Agent results appear with green styling

If you see all of these, the integration is working perfectly!
