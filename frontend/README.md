# Agent in the Loop - Frontend Mockup

This is a React-based mockup frontend for the innovative "Agent in the Loop" chatbot interface. It demonstrates how a real-time audio conversation system can integrate with background AI agents that monitor conversations and trigger appropriate actions.

## Features

### 🎙️ Real-time Chat Interface (Left Side)
- **Audio Input**: Voice recording button with visual feedback
- **Text Input**: Traditional text input as fallback
- **Message History**: Scrollable conversation with timestamps
- **Agent Results**: Special styling for messages from background agents
- **Responsive Design**: Adapts to different screen sizes

### 🤖 Agent Monitoring Panel (Right Side)
- **Agent in the Loop Card**: Shows the main monitoring agent status
- **Sub-Agent Grid**: Displays available specialized agents (Email, Calendar, Notes, Research)
- **Real-time Status Updates**: Visual indicators for agent states (idle, active, completed)
- **Activity Log**: Shows recent agent activities
- **Smooth Animations**: Framer Motion animations for state transitions

## Mock Interactions

The interface includes pre-programmed scenarios that demonstrate the agent system:

### 📧 Email Agent
- **Trigger**: Messages containing "email" or "send"
- **Example**: "Can you send an email to john@example.com about the meeting?"
- **Result**: Shows email agent activation and completion

### 📅 Calendar Agent
- **Trigger**: Messages containing "calendar", "schedule", or "meeting"
- **Example**: "Schedule a meeting for tomorrow at 2 PM"
- **Result**: Shows calendar agent activation and completion

### 📝 Notes Agent
- **Trigger**: Messages containing "notes" or "find"
- **Example**: "Can you find my notes about the project proposal?"
- **Result**: Shows notes agent activation and completion

### 🔍 Research Agent
- **Trigger**: Messages containing "research", "news", or "latest"
- **Example**: "What's the latest news about AI developments?"
- **Result**: Shows research agent activation and completion

## How It Works

1. **User Input**: User types or speaks a message
2. **Agent Detection**: The system detects if the message triggers a specific agent
3. **Agent in the Loop Activation**: The main monitoring agent becomes active
4. **Sub-Agent Trigger**: The appropriate sub-agent is highlighted and activated
5. **Task Execution**: Visual feedback shows the agent working
6. **Result Delivery**: The agent result is added to the chat with special styling

## Getting Started

### Prerequisites
- Node.js (version 14 or higher)
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Open your browser and navigate to `http://localhost:3000`

### Available Scripts

- `npm start` - Runs the app in development mode
- `npm build` - Builds the app for production
- `npm test` - Launches the test runner
- `npm eject` - Ejects from Create React App (one-way operation)

## Architecture

### Components

- **App.js**: Main application component with state management
- **ChatInterface.js**: Left-side chat interface with audio controls
- **AgentPanel.js**: Right-side agent monitoring panel
- **CSS Modules**: Styled components with modern design

### State Management

The app uses React hooks for state management:
- `messages`: Chat message history
- `agentInLoop`: Main agent status and current task
- `subAgents`: Array of sub-agent states
- `isListening`: Audio recording state

### Animations

Uses Framer Motion for smooth animations:
- Message appearance/disappearance
- Agent state transitions
- Card hover effects
- Loading indicators

## Design Philosophy

This mockup demonstrates the concept of "Agent in the Loop" where:

1. **Seamless Integration**: Background agents work invisibly during normal conversation
2. **Visual Feedback**: Users can see when agents are working
3. **Contextual Results**: Agent results are delivered naturally in the conversation
4. **Non-Intrusive**: The main conversation flow is never interrupted

## Future Enhancements

- Real WebSocket integration with the Python backend
- Actual audio recording and playback
- More sophisticated agent detection
- Custom agent configuration
- Real-time collaboration features
- Advanced analytics and monitoring

## Technical Stack

- **React 18**: Modern React with hooks
- **Framer Motion**: Animation library
- **Lucide React**: Icon library
- **CSS3**: Modern styling with gradients and animations
- **Create React App**: Development environment

This mockup serves as a proof-of-concept for the innovative "Agent in the Loop" architecture, demonstrating how background AI agents can enhance real-time conversations without disrupting the user experience.
