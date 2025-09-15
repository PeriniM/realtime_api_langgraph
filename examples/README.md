# Realtime API with Background Agent Integration

This project demonstrates a real-time bidirectional audio communication system that integrates OpenAI's Realtime API with background AI agents for complex task processing.

## Architecture Overview

### Approach 1: Out-of-Band Responses (Current Implementation)

```mermaid
graph TB
    subgraph "Client Side (test_bidirectional.py)"
        A[User Voice Input] --> B[Microphone Class]
        B --> C[Audio Chunks 20ms]
        C --> D[OpenAI Realtime API]
        
        D --> E[AI Audio Response]
        E --> F[Speaker Class]
        F --> G[User Hears Response]
        
        D --> H[Live Transcription]
        H --> I[User Message Complete]
        H --> J[AI Response Complete]
        
        I --> K[Enhanced Background Manager]
        J --> K
        
        K --> L[Create Background Task]
        L --> M[Monitor Task Completion]
        M --> N[Out-of-Band Response]
        
        N --> O[Custom Context + Instructions]
        O --> P[AI Generates Contextual Response]
        P --> Q[User Hears Agent Result]
    end
    
    subgraph "Background Processing"
        L --> R[Simple Background Agent]
        R --> S[Thread-based Tasks]
        S --> T[Random Delay 1-5s]
        T --> U[Simulated Work Results]
        U --> M
    end
    
    subgraph "Out-of-Band Response Flow"
        N --> V[conversation: none]
        V --> W[Custom Input Context]
        W --> X[Context-Aware Instructions]
        X --> Y[AI Response with Background Context]
        Y --> Q
    end
    
    style A fill:#e1f5fe
    style G fill:#e8f5e8
    style Q fill:#fff3e0
    style R fill:#f3e5f5
    style U fill:#e0f2f1
```

### Approach 2: Function Calling (Alternative)

```mermaid
graph TB
    subgraph "Function Calling Flow"
        A[User Request] --> B[AI Determines Function Needed]
        B --> C[Function Call Generated]
        C --> D[Background Task Created]
        D --> E[Function Call Output]
        E --> F[AI Response with Results]
        F --> G[User Hears Complete Response]
    end
    
    subgraph "Available Functions"
        H[send_email]
        I[update_calendar]
        J[research_topic]
        K[background_processing]
    end
    
    B --> H
    B --> I
    B --> J
    B --> K
    
    style A fill:#e1f5fe
    style G fill:#e8f5e8
    style H fill:#f3e5f5
    style I fill:#f3e5f5
    style J fill:#f3e5f5
    style K fill:#f3e5f5
```

## Key Components

### 1. Real-time Audio Pipeline
- **Microphone**: Captures 24kHz PCM audio in 20ms chunks
- **Speaker**: Plays AI responses with <20ms latency
- **Interruption Handling**: User can interrupt AI mid-response

### 2. Background Agent Integration (Two Approaches)

#### Approach 1: Out-of-Band Responses (Current)
- **Always Invokes**: Every conversation turn triggers background processing
- **Out-of-Band Delivery**: Results delivered via `conversation: "none"` responses
- **Context Preservation**: Full conversation context maintained in custom input
- **Natural Integration**: AI generates contextual responses about background results

#### Approach 2: Function Calling (Alternative)
- **AI-Driven**: Model determines when to call background functions
- **Structured Functions**: Predefined functions for email, calendar, research
- **Automatic Handling**: Function calls automatically trigger background tasks
- **Seamless Flow**: Results integrated into natural conversation flow

### 3. Conversation Management
- **Turn-based Processing**: Complete user→AI pairs before agent invocation
- **Context Awareness**: Background results provide additional context
- **Error Recovery**: Graceful handling of agent failures
- **Memory Management**: Automatic cleanup of completed tasks

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# On macOS, install audio dependencies
brew install portaudio ffmpeg

# Grant microphone permissions to terminal
# Run the application
python test_bidirectional.py
```

## Background Agent Endpoint

The system expects a background agent at `http://localhost:8000/api/process` that:

1. Receives full conversation history
2. Performs background tasks (email, calendar, research)
3. Returns structured results
4. Handles timeouts gracefully

## Example Agent Response

```json
{
  "conversation_id": "conv_1234567890",
  "turn_id": "turn_5",
  "status": "completed",
  "results": [
    {
      "action": "email_sent",
      "recipient": "user@example.com",
      "subject": "Background task completed"
    },
    {
      "action": "calendar_updated",
      "summary": "Meeting scheduled",
      "time": "2024-01-15 14:00"
    }
  ],
  "timestamp": 1704067200.0
}
```

## Features

- ✅ Real-time bidirectional audio communication
- ✅ Background agent integration on every turn
- ✅ Complete conversation context preservation
- ✅ Automatic response delivery to user
- ✅ Robust error handling and timeouts
- ✅ LangSmith conversation tracking
- ✅ Interruption handling
- ✅ Live transcription display

## Architecture Benefits

1. **No Token Mixing**: Turn-based processing prevents user/AI token confusion
2. **Complete Context**: Background agents receive full conversation history
3. **Responsive UX**: Users get real-time feedback on background tasks
4. **Scalable**: Handles multiple concurrent conversations
5. **Fault Tolerant**: Graceful degradation on agent failures
