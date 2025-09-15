# Voice Streaming Implementation

This document describes the new voice streaming feature that enables real-time voice conversation between the frontend and backend using WebSocket communication.

## Architecture Overview

```
Frontend Microphone → WebSocket → Backend → OpenAI Realtime API
                                                      ↓
Frontend Speakers ← WebSocket ← Backend ← OpenAI Realtime API
```

## Components

### Frontend Components

#### 1. VoiceStreaming Component (`frontend/src/components/VoiceStreaming.js`)
- **Purpose**: Handles continuous audio capture and playback
- **Features**:
  - Real-time microphone access with audio level monitoring
  - WebSocket connection to `/ws/voice` endpoint
  - Audio streaming in 50ms chunks for low latency
  - Real-time audio playback from AI responses
  - Visual feedback for listening/speaking states

#### 2. Audio Processing
- **Input**: WebM/Opus format from browser microphone
- **Output**: PCM audio chunks for AI responses
- **Sample Rate**: 24kHz (optimized for OpenAI Realtime API)
- **Latency**: ~50ms chunks for real-time streaming

### Backend Components

#### 1. Voice WebSocket Endpoint (`/ws/voice`)
- **Purpose**: Handles bidirectional voice communication
- **Features**:
  - Accepts audio data from frontend
  - Forwards audio to OpenAI Realtime API
  - Streams AI responses back to frontend
  - Real-time transcript forwarding

#### 2. VoiceStreamingService Class
- **Purpose**: Manages the voice streaming session
- **Features**:
  - OpenAI Realtime API integration
  - Audio data processing and forwarding
  - Event handling and transcript management
  - Error handling and cleanup

## Message Types

### Frontend → Backend
```json
{
  "type": "audio_data",
  "audio": "base64_encoded_audio",
  "timestamp": 1234567890
}
```

### Backend → Frontend
```json
{
  "type": "audio_chunk",
  "audio": "base64_encoded_audio",
  "timestamp": 1234567890
}
```

```json
{
  "type": "transcript",
  "text": "Hello, how are you?",
  "is_user": true,
  "is_complete": true,
  "timestamp": 1234567890
}
```

```json
{
  "type": "speech_started",
  "is_user": false,
  "timestamp": 1234567890
}
```

## Usage

### Starting the System

1. **Start the Backend**:
   ```bash
   cd api
   python start_server.py
   ```

2. **Start the Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Access the Application**:
   - Open `http://localhost:3000`
   - The VoiceStreaming component will be visible at the top of the left panel

### Using Voice Streaming

1. **Grant Microphone Permission**: Click "Start Listening" and allow microphone access
2. **Speak**: The system will capture your voice and stream it to the backend
3. **Listen**: AI responses will be played through your speakers
4. **View Transcripts**: Both user and AI speech will appear as text in the chat

## Technical Details

### Audio Format Handling
- **Frontend**: Captures WebM/Opus, converts to base64 for transmission
- **Backend**: Receives base64 audio, forwards to OpenAI Realtime API
- **OpenAI**: Processes PCM audio at 24kHz sample rate
- **Response**: AI generates PCM audio, sent back as base64 chunks

### Latency Optimization
- **Audio Chunks**: 50ms chunks for minimal latency
- **WebSocket**: Real-time bidirectional communication
- **Buffering**: Minimal buffering for immediate playback
- **Processing**: Asynchronous audio processing

### Error Handling
- **Connection Issues**: Automatic reconnection attempts
- **Audio Failures**: Graceful fallback to text mode
- **Permission Denied**: User-friendly error messages
- **API Errors**: Error forwarding to frontend

## Testing

### Manual Testing
1. Start both frontend and backend
2. Open browser console to monitor WebSocket messages
3. Test microphone access and audio playback
4. Verify transcript accuracy

### Automated Testing
```bash
cd api
python examples/test_voice_streaming.py
```

## Configuration

### Audio Settings
- **Sample Rate**: 24,000 Hz
- **Channels**: 1 (mono)
- **Format**: PCM for OpenAI, WebM/Opus for browser
- **Chunk Size**: 50ms for frontend, 20ms for backend

### WebSocket Settings
- **Endpoint**: `ws://localhost:8000/ws/voice`
- **Keepalive**: 30-second intervals
- **Reconnection**: Automatic with exponential backoff

## Troubleshooting

### Common Issues

1. **Microphone Not Working**:
   - Check browser permissions
   - Verify microphone is not in use by other applications
   - Check browser console for errors

2. **No Audio Playback**:
   - Check browser audio settings
   - Verify WebSocket connection is established
   - Check backend logs for OpenAI API errors

3. **High Latency**:
   - Check network connection
   - Verify audio chunk sizes are optimal
   - Monitor WebSocket message timing

### Debug Mode
Enable debug logging by setting:
```javascript
localStorage.setItem('debug', 'voice-streaming');
```

## Future Enhancements

1. **Audio Quality Settings**: Configurable sample rates and bitrates
2. **Noise Cancellation**: Advanced audio processing
3. **Multiple Languages**: Support for different languages
4. **Voice Cloning**: Custom voice options
5. **Offline Mode**: Local speech processing fallback

## Security Considerations

1. **Audio Data**: Transmitted over WebSocket (consider HTTPS in production)
2. **Permissions**: Microphone access requires user consent
3. **Data Storage**: Audio data is not stored permanently
4. **API Keys**: OpenAI API key should be kept secure

This voice streaming implementation provides a foundation for real-time voice conversations with AI, enabling natural and responsive voice interactions.
