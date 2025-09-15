import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2 } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import AgentPanel from './components/AgentPanel';
import VoiceStreaming from './components/VoiceStreaming';
import websocketService from './services/websocketService';
import realtimeService from './services/realtimeService';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: 'Hello! I\'m your AI assistant. I can help you with various tasks, and I have background agents that can handle things like sending emails, updating your calendar, or fetching notes while we chat.',
      timestamp: new Date(),
      isAgentResult: false
    }
  ]);
  
  const [isListening, setIsListening] = useState(false);
  const [agentInLoop, setAgentInLoop] = useState({
    isActive: false,
    currentTask: null,
    status: 'idle' // idle, analyzing, executing
  });
  
  const [subAgents, setSubAgents] = useState([
    { id: 'email', name: 'Email Agent', status: 'idle', icon: '📧' },
    { id: 'calendar', name: 'Calendar Agent', status: 'idle', icon: '📅' },
    { id: 'notes', name: 'Notes Agent', status: 'idle', icon: '📝' },
    { id: 'research', name: 'Research Agent', status: 'idle', icon: '🔍' }
  ]);

  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [conversationMode, setConversationMode] = useState('text'); // 'text' or 'speech'
  const [realtimeConnectionStatus, setRealtimeConnectionStatus] = useState('disconnected');
  const [voiceConnectionStatus, setVoiceConnectionStatus] = useState('disconnected');

  // WebSocket connection setup - only run once on mount
  useEffect(() => {
    // Set up regular WebSocket event listeners
    const handleWebSocketConnected = () => {
      setConnectionStatus('connected');
      console.log('[App] Connected to text API');
    };

    const handleWebSocketDisconnected = () => {
      setConnectionStatus('disconnected');
      console.log('[App] Disconnected from text API');
    };

    const handleWebSocketMessageEvent = (data) => {
      handleWebSocketMessage(data);
    };

    const handleWebSocketError = (error) => {
      console.error('[App] WebSocket error:', error);
      setConnectionStatus('error');
    };

    // Set up realtime WebSocket event listeners
    const handleRealtimeConnected = () => {
      setRealtimeConnectionStatus('connected');
      console.log('[App] Connected to realtime API');
    };

    const handleRealtimeDisconnected = () => {
      setRealtimeConnectionStatus('disconnected');
      console.log('[App] Disconnected from realtime API');
    };

    const handleRealtimeMessageEvent = (data) => {
      handleRealtimeMessage(data);
    };

    const handleRealtimeError = (error) => {
      console.error('[App] Realtime WebSocket error:', error);
      setRealtimeConnectionStatus('error');
      
      // Show user-friendly error message
      if (error.message && error.message.includes('Microphone')) {
        alert(`Speech mode error: ${error.message}`);
      } else if (error.message && error.message.includes('Not connected')) {
        alert('Speech mode error: Not connected to speech service. Please try again.');
      }
    };

    const handleListeningStarted = () => {
      setIsListening(true);
    };

    const handleListeningStopped = () => {
      setIsListening(false);
    };

    // Add event listeners
    websocketService.on('connected', handleWebSocketConnected);
    websocketService.on('disconnected', handleWebSocketDisconnected);
    websocketService.on('message', handleWebSocketMessageEvent);
    websocketService.on('error', handleWebSocketError);

    realtimeService.on('connected', handleRealtimeConnected);
    realtimeService.on('disconnected', handleRealtimeDisconnected);
    realtimeService.on('message', handleRealtimeMessageEvent);
    realtimeService.on('error', handleRealtimeError);
    realtimeService.on('listening_started', handleListeningStarted);
    realtimeService.on('listening_stopped', handleListeningStopped);

    // Connect to appropriate service based on mode
    if (conversationMode === 'text' && !websocketService.isConnected) {
      websocketService.connect();
    } else if (conversationMode === 'speech' && !realtimeService.isConnected) {
      realtimeService.connect();
    }

    // Cleanup on unmount
    return () => {
      // Remove event listeners to prevent duplicates
      websocketService.off('connected', handleWebSocketConnected);
      websocketService.off('disconnected', handleWebSocketDisconnected);
      websocketService.off('message', handleWebSocketMessageEvent);
      websocketService.off('error', handleWebSocketError);

      realtimeService.off('connected', handleRealtimeConnected);
      realtimeService.off('disconnected', handleRealtimeDisconnected);
      realtimeService.off('message', handleRealtimeMessageEvent);
      realtimeService.off('error', handleRealtimeError);
      realtimeService.off('listening_started', handleListeningStarted);
      realtimeService.off('listening_stopped', handleListeningStopped);
    };
  }, []); // Empty dependency array - only run once on mount

  // Separate effect for mode switching
  useEffect(() => {
    // Connect to appropriate service based on mode
    if (conversationMode === 'text' && !websocketService.isConnected) {
      websocketService.connect();
    } else if (conversationMode === 'speech' && !realtimeService.isConnected) {
      realtimeService.connect();
    }
  }, [conversationMode]);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'new_message':
        const newMessage = {
          id: data.message.id,
          type: data.message.type,
          content: data.message.content,
          timestamp: new Date(data.message.timestamp),
          isAgentResult: data.message.is_agent_result
        };
        console.log('[App] Received new message:', newMessage);
        // Check for duplicates before adding
        setMessages(prev => {
          const exists = prev.some(msg => msg.id === newMessage.id);
          if (exists) {
            console.log('[App] Duplicate message detected, skipping:', newMessage.id);
            return prev;
          }
          return [...prev, newMessage];
        });
        break;
      
      case 'agent_update':
        setAgentInLoop(data.agent_in_loop);
        setSubAgents(data.sub_agents);
        break;
      
      default:
        console.log('[App] Unknown message type:', data.type);
    }
  };

  const handleRealtimeMessage = (data) => {
    switch (data.type) {
      case 'user_transcript_delta':
        // Handle live user transcript updates
        console.log('[App] User speaking:', data.content);
        break;
      
      case 'user_message_complete':
        // User finished speaking
        const userMessage = {
          id: `user_${Date.now()}`,
          type: 'user',
          content: data.content,
          timestamp: new Date(),
          isAgentResult: false
        };
        // Check for duplicates before adding
        setMessages(prev => {
          const exists = prev.some(msg => msg.id === userMessage.id);
          if (exists) {
            console.log('[App] Duplicate user message detected, skipping:', userMessage.id);
            return prev;
          }
          return [...prev, userMessage];
        });
        break;
      
      case 'ai_transcript_delta':
        // Handle live AI transcript updates
        console.log('[App] AI speaking:', data.content);
        break;
      
      case 'ai_response_complete':
        // AI finished speaking
        const aiMessage = {
          id: `ai_${Date.now()}`,
          type: 'ai',
          content: data.content,
          timestamp: new Date(),
          isAgentResult: false
        };
        // Check for duplicates before adding
        setMessages(prev => {
          const exists = prev.some(msg => msg.id === aiMessage.id);
          if (exists) {
            console.log('[App] Duplicate AI message detected, skipping:', aiMessage.id);
            return prev;
          }
          return [...prev, aiMessage];
        });
        break;
      
      case 'user_speaking_started':
        console.log('[App] User started speaking');
        break;
      
      case 'user_speaking_stopped':
        console.log('[App] User stopped speaking');
        break;
      
      case 'agent_result':
        // Background agent result
        const agentMessage = {
          id: `agent_${Date.now()}`,
          type: 'ai',
          content: data.content,
          timestamp: new Date(),
          isAgentResult: true
        };
        console.log('[App] Received agent result message:', agentMessage);
        // Check for duplicates before adding
        setMessages(prev => {
          const exists = prev.some(msg => msg.id === agentMessage.id);
          if (exists) {
            console.log('[App] Duplicate agent message detected, skipping:', agentMessage.id);
            return prev;
          }
          return [...prev, agentMessage];
        });
        break;
      
      case 'error':
        console.error('[App] Realtime error:', data.message);
        break;
      
      default:
        console.log('[App] Unknown realtime message type:', data.type);
    }
  };

  const handleVoiceTranscript = (text, isUser) => {
    if (!text.trim()) return;
    
    const message = {
      id: `${isUser ? 'user' : 'ai'}_${Date.now()}`,
      type: isUser ? 'user' : 'ai',
      content: text,
      timestamp: new Date(),
      isAgentResult: false
    };
    
    // Check for duplicates before adding
    setMessages(prev => {
      const exists = prev.some(msg => msg.id === message.id);
      if (exists) {
        console.log('[App] Duplicate voice message detected, skipping:', message.id);
        return prev;
      }
      return [...prev, message];
    });
  };

  const handleVoiceError = (error) => {
    console.error('[App] Voice streaming error:', error);
    // You could show a toast notification here
  };

  // Mock conversation scenarios
  const mockScenarios = [
    {
      trigger: 'email',
      userMessage: 'Can you send an email to john@example.com about the meeting?',
      aiResponse: 'I\'ll help you send that email. Let me compose it for you.',
      agentTask: 'Sending email to john@example.com about the meeting',
      agentResult: '✅ Email sent successfully to john@example.com with subject "Meeting Discussion"'
    },
    {
      trigger: 'calendar',
      userMessage: 'Schedule a meeting for tomorrow at 2 PM',
      aiResponse: 'I\'ll schedule that meeting for you right away.',
      agentTask: 'Scheduling meeting for tomorrow at 2 PM',
      agentResult: '📅 Meeting scheduled for tomorrow at 2:00 PM. Calendar invite sent to all participants.'
    },
    {
      trigger: 'notes',
      userMessage: 'Can you find my notes about the project proposal?',
      aiResponse: 'Let me search for your project proposal notes.',
      agentTask: 'Searching for project proposal notes',
      agentResult: '📝 Found 3 notes related to "project proposal". The most recent one is from last week with key points about budget and timeline.'
    },
    {
      trigger: 'research',
      userMessage: 'What\'s the latest news about AI developments?',
      aiResponse: 'I\'ll research the latest AI developments for you.',
      agentTask: 'Researching latest AI developments',
      agentResult: '🔍 Found recent articles about GPT-4 updates, new AI regulations in the EU, and breakthrough in quantum computing applications.'
    }
  ];

  const handleUserMessage = (message) => {
    if (conversationMode === 'text') {
      // Text mode - use regular WebSocket
      if (websocketService.isConnected) {
        websocketService.sendUserMessage(message);
        // Don't add message to state here - let the API response handle it
      } else {
        console.log('[App] Text WebSocket not connected, using mock behavior');
        handleMockUserMessage(message);
      }
    } else {
      // Speech mode - messages are handled automatically by realtime service
      console.log('[App] Speech mode - messages handled by realtime service');
    }
  };

  const switchConversationMode = (mode) => {
    if (mode === conversationMode) return;
    
    console.log(`[App] Switching from ${conversationMode} mode to ${mode} mode`);
    
    // Stop listening if currently listening
    if (isListening) {
      if (conversationMode === 'speech') {
        realtimeService.stopListening();
      }
      setIsListening(false);
    }
    
    // Disconnect current service
    if (conversationMode === 'text') {
      websocketService.disconnect();
    } else if (conversationMode === 'speech') {
      realtimeService.disconnect();
    }
    
    // Switch mode
    setConversationMode(mode);
    
    // Connect to new service
    if (mode === 'text') {
      websocketService.connect();
    } else if (mode === 'speech') {
      realtimeService.connect();
    }
  };

  const handleMockUserMessage = (message) => {
    // Only add user message in mock mode when not connected to API
    const newMessage = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: message,
      timestamp: new Date(),
      isAgentResult: false
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    // Check if message triggers an agent
    const scenario = mockScenarios.find(s => 
      message.toLowerCase().includes(s.trigger) || 
      message.toLowerCase().includes('email') ||
      message.toLowerCase().includes('calendar') ||
      message.toLowerCase().includes('notes') ||
      message.toLowerCase().includes('research')
    );
    
    if (scenario) {
      // Simulate AI response
      setTimeout(() => {
        const aiMessage = {
          id: `ai_${Date.now()}`,
          type: 'ai',
          content: scenario.aiResponse,
          timestamp: new Date(),
          isAgentResult: false
        };
        setMessages(prev => [...prev, aiMessage]);
        
        // Trigger agent in the loop
        triggerAgentInLoop(scenario);
      }, 1000);
    } else {
      // Regular AI response
      setTimeout(() => {
        const aiMessage = {
          id: `ai_${Date.now()}`,
          type: 'ai',
          content: 'I understand. How else can I help you today?',
          timestamp: new Date(),
          isAgentResult: false
        };
        setMessages(prev => [...prev, aiMessage]);
      }, 1000);
    }
  };

  const triggerAgentInLoop = (scenario) => {
    // Activate agent in the loop
    setAgentInLoop({
      isActive: true,
      currentTask: scenario.agentTask,
      status: 'analyzing'
    });
    
    // After 2 seconds, activate the specific sub-agent
    setTimeout(() => {
      setSubAgents(prev => prev.map(agent => 
        agent.id === scenario.trigger 
          ? { ...agent, status: 'active' }
          : agent
      ));
      
      setAgentInLoop(prev => ({ ...prev, status: 'executing' }));
      
      // After 3 more seconds, complete the task and add result to chat
      setTimeout(() => {
        setSubAgents(prev => prev.map(agent => 
          agent.id === scenario.trigger 
            ? { ...agent, status: 'completed' }
            : agent
        ));
        
        setAgentInLoop({
          isActive: false,
          currentTask: null,
          status: 'idle'
        });
        
        // Add agent result to chat
        const agentResultMessage = {
          id: `agent_${Date.now()}`,
          type: 'ai',
          content: scenario.agentResult,
          timestamp: new Date(),
          isAgentResult: true
        };
        setMessages(prev => [...prev, agentResultMessage]);
        
        // Reset sub-agent status after a delay
        setTimeout(() => {
          setSubAgents(prev => prev.map(agent => ({ ...agent, status: 'idle' })));
        }, 2000);
      }, 3000);
    }, 2000);
  };

  const handleAudioToggle = () => {
    if (conversationMode === 'speech') {
      // Already in speech mode - toggle listening
      if (!isListening) {
        realtimeService.startListening();
      } else {
        realtimeService.stopListening();
      }
    } else {
      // Currently in text mode - switch to speech mode and start listening
      console.log('[App] Switching to speech mode and starting listening');
      switchConversationMode('speech');
      
      // Start listening after a short delay to allow connection to establish
      setTimeout(() => {
        if (realtimeService.isConnected) {
          realtimeService.startListening();
        } else {
          console.log('[App] Realtime service not connected, waiting for connection...');
          // Wait for connection and then start listening
          const checkConnection = () => {
            if (realtimeService.isConnected) {
              realtimeService.startListening();
            } else {
              setTimeout(checkConnection, 100);
            }
          };
          checkConnection();
        }
      }, 500);
    }
  };

  return (
    <div className="app">
      <div className="app-container">
        {/* Full-width header */}
        <div className="app-header">
          <div className="chat-title">
            <Volume2 className="chat-icon" />
            <h2>LangGraph Realtime API Demo</h2>
          </div>
          <div className="status-indicator">
            <div className={`status-dot ${isListening ? 'listening' : connectionStatus === 'connected' ? 'connected' : 'disconnected'}`}></div>
            <span>
              {isListening ? 'Listening...' : 
               agentInLoop?.isActive ? 'Agent Processing...' :
               connectionStatus === 'connected' ? 'Connected' : 
               connectionStatus === 'error' ? 'Connection Error' : 
               'Disconnected (Mock Mode)'}
            </span>
          </div>
        </div>
        
        <div className="app-content">
          <div className="left-panel">
            <VoiceStreaming 
              onTranscript={handleVoiceTranscript}
              onError={handleVoiceError}
              isConnected={true}
            />
            <ChatInterface 
              messages={messages}
              isListening={isListening}
              onAudioToggle={handleAudioToggle}
              onSendMessage={handleUserMessage}
              connectionStatus={conversationMode === 'text' ? connectionStatus : realtimeConnectionStatus}
              conversationMode={conversationMode}
              onModeSwitch={switchConversationMode}
              agentInLoop={agentInLoop}
            />
          </div>
          <AgentPanel 
            agentInLoop={agentInLoop}
            subAgents={subAgents}
            connectionStatus={conversationMode === 'text' ? connectionStatus : realtimeConnectionStatus}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
