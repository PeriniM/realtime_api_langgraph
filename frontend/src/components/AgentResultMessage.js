import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, Bot, Sparkles, Zap } from 'lucide-react';
import './AgentResultMessage.css';

const AgentResultMessage = ({ message }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSparkles, setShowSparkles] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  // Show sparkles animation when message first appears
  useEffect(() => {
    setShowSparkles(true);
    const timer = setTimeout(() => setShowSparkles(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="agent-result-message"
    >
      <div className="agent-result-header" onClick={toggleExpanded}>
        <motion.div 
          className="agent-result-icon"
          animate={showSparkles ? { 
            scale: [1, 1.2, 1],
            rotate: [0, 5, -5, 0]
          } : {}}
          transition={{ duration: 0.6 }}
        >
          {showSparkles ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Sparkles size={16} />
            </motion.div>
          ) : (
            <Bot size={16} />
          )}
        </motion.div>
        <div className="agent-result-title">
          <span className="agent-badge">
            {showSparkles ? "✨ New Result" : "🤖 Agent Result"}
          </span>
          {!isExpanded && (
            <span className="agent-preview">
              {message.content.length > 60 
                ? `${message.content.substring(0, 60)}...` 
                : message.content}
            </span>
          )}
          <span className="agent-time">{formatTime(message.timestamp)}</span>
        </div>
        <div className="agent-result-toggle">
          {isExpanded ? (
            <ChevronDown size={16} className="toggle-icon" />
          ) : (
            <ChevronRight size={16} className="toggle-icon" />
          )}
        </div>
      </div>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="agent-result-content"
          >
            <div className="agent-result-text">
              {message.content}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AgentResultMessage;
