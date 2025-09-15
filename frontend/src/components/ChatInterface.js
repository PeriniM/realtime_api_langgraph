import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Send, Loader2 } from 'lucide-react';
import AgentResultMessage from './AgentResultMessage';
import './ChatInterface.css';

const ChatInterface = ({ messages, isListening, onAudioToggle, onSendMessage, connectionStatus, conversationMode, onModeSwitch, agentInLoop }) => {
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      onSendMessage(inputMessage);
      setInputMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        <AnimatePresence>
          {messages.map((message) => {
            // Render agent results with the new collapsible component
            if (message.isAgentResult) {
              console.log('[ChatInterface] Rendering agent result message:', message);
              return (
                <div key={message.id} style={{ width: '100%', margin: '8px 0' }}>
                  <AgentResultMessage 
                    message={message} 
                  />
                </div>
              );
            }
            
            // Render regular messages
            return (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className={`message ${message.type}`}
              >
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-time">{formatTime(message.timestamp)}</div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={messagesEndRef} />
        
        {/* Agent Processing Indicator */}
        {agentInLoop?.isActive && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="agent-processing-indicator"
          >
            <div className="processing-content">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="processing-spinner"
              >
                <Loader2 size={16} />
              </motion.div>
              <span className="processing-text">
                Background agent is analyzing the conversation...
              </span>
            </div>
          </motion.div>
        )}
      </div>

      <div className="input-container">
        <form onSubmit={handleSendMessage} className="input-form">
          <div className="input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={conversationMode === 'speech' ? 'Speech mode active...' : 'Type a message...'}
              className="message-input"
              disabled={conversationMode === 'speech' || isListening}
            />
            <button
              type="submit"
              className="send-button"
              disabled={!inputMessage.trim() || conversationMode === 'speech' || isListening}
            >
              <Send size={18} />
            </button>
            {conversationMode === 'speech' ? (
              <>
                <button
                  type="button"
                  onClick={onAudioToggle}
                  className={`speech-button ${isListening ? 'listening' : ''}`}
                  title={isListening ? 'Stop listening' : 'Start listening'}
                >
                  <Mic size={16} />
                  <span>{isListening ? 'Stop Listening' : 'Start Listening'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onModeSwitch('text')}
                  className="speech-button"
                  title="Switch to Text Mode"
                  style={{ background: '#e8f0f0', color: '#4a4a4a' }}
                >
                  <span>Text Mode</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={onAudioToggle}
                className="speech-button"
                title="Switch to Speech Mode"
              >
                <Mic size={16} />
                <span>Switch to Speech</span>
              </button>
            )}
          </div>
        </form>
        
        <div className="voice-status">
          {isListening && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="listening-indicator"
            >
              <div className="pulse-ring"></div>
              <div className="pulse-ring delay-1"></div>
              <div className="pulse-ring delay-2"></div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
