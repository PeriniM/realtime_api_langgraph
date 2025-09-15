import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Activity, CheckCircle, Clock, AlertCircle, Zap, Loader2, Sparkles, Plus } from 'lucide-react';
import './AgentPanel.css';

const AgentPanel = ({ agentInLoop, subAgents, connectionStatus }) => {
  const [processingSteps, setProcessingSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  // Define processing steps for background agent
  const backgroundSteps = [
    "Initializing task...",
    "Processing conversation context...",
    "Analyzing user intent...",
    "Generating insights...",
    "Finalizing results..."
  ];

  // Simulate processing steps when agent is active
  useEffect(() => {
    if (agentInLoop.isActive && (agentInLoop.status === 'analyzing' || agentInLoop.status === 'executing')) {
      setIsAnimating(true);
      setProcessingSteps(backgroundSteps);
      setCurrentStep(0);
      
      const interval = setInterval(() => {
        setCurrentStep(prev => {
          if (prev < backgroundSteps.length - 1) {
            return prev + 1;
          } else {
            clearInterval(interval);
            setIsAnimating(false);
            return prev;
          }
        });
      }, 800);

      return () => clearInterval(interval);
    } else {
      setProcessingSteps([]);
      setCurrentStep(0);
      setIsAnimating(false);
    }
  }, [agentInLoop.isActive, agentInLoop.status]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'idle':
        return <Clock size={16} className="status-icon idle" />;
      case 'active':
        return <Activity size={16} className="status-icon active" />;
      case 'completed':
        return <CheckCircle size={16} className="status-icon completed" />;
      case 'error':
        return <AlertCircle size={16} className="status-icon error" />;
      default:
        return <Clock size={16} className="status-icon idle" />;
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'idle':
        return 'Ready';
      case 'active':
        return 'Working...';
      case 'completed':
        return 'Completed';
      case 'error':
        return 'Error';
      default:
        return 'Ready';
    }
  };

  const getAgentInLoopStatus = () => {
    if (!agentInLoop.isActive) {
      return { status: 'idle', text: 'Monitoring conversation...' };
    }
    
    switch (agentInLoop.status) {
      case 'analyzing':
        return { status: 'active', text: 'Analyzing conversation...' };
      case 'executing':
        return { status: 'active', text: 'Running background task...' };
      default:
        return { status: 'idle', text: 'Monitoring conversation...' };
    }
  };

  const agentInLoopStatus = getAgentInLoopStatus();

  return (
    <div className="agent-panel">

      <div className="agent-panel-content">
        {/* Agents-in-the-Loop Section */}
        <div className="sub-agents-section">
          <div className="section-header">
            <h4>Agents-in-the-Loop</h4>
            <button className="add-button" title="Add new agent">
              <Plus size={16} />
            </button>
          </div>
        </div>

        {/* Main Agent Status Card */}
        <motion.div
          layout
          className={`agent-status-card ${agentInLoop.isActive ? 'active' : ''}`}
          initial={{ scale: 1 }}
          animate={{ 
            scale: agentInLoop.isActive ? 1.02 : 1,
            boxShadow: agentInLoop.isActive 
              ? '0 4px 16px rgba(0, 0, 0, 0.1)' 
              : '0 2px 8px rgba(0, 0, 0, 0.05)'
          }}
          transition={{ duration: 0.3 }}
        >
          <div className="agent-status-header">
            <motion.div 
              className="agent-status-icon"
              animate={agentInLoop.isActive ? { 
                rotate: [0, 5, -5, 0],
                scale: [1, 1.1, 1]
              } : {}}
              transition={{ 
                duration: 2, 
                repeat: agentInLoop.isActive ? Infinity : 0,
                ease: "easeInOut"
              }}
            >
              {agentInLoop.isActive ? (
                <Loader2 size={20} className="spinning-icon" />
              ) : (
                <Brain size={20} />
              )}
            </motion.div>
            <div className="agent-status-content">
              <div className="agent-status-title">Supervisor Agent</div>
              <div className="agent-status-subtitle">Monitoring the conversation</div>
              <div className="agent-status-label">
                <span className={`status-badge ${agentInLoop.isActive ? 'running' : 'idle'}`}>
                  Status: {agentInLoop.isActive ? (agentInLoop.status === 'executing' ? 'Running' : 'Analyzing') : 'Idle'}
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Sub-Agents Section */}
        <div className="sub-agents-section">
          <div className="section-header">
            <h4>Sub-Agents</h4>
            <button className="add-button" title="Add new sub-agent">
              <Plus size={16} />
            </button>
          </div>
          <div className="sub-agents-grid">
            <AnimatePresence>
              {subAgents.map((agent) => (
                <motion.div
                  key={agent.id}
                  layout
                  className={`sub-agent-card ${agent.status}`}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ 
                    opacity: 1, 
                    scale: 1,
                    boxShadow: agent.status === 'active' 
                      ? '0 8px 32px rgba(16, 185, 129, 0.3)' 
                      : agent.status === 'completed'
                      ? '0 8px 32px rgba(34, 197, 94, 0.3)'
                      : '0 4px 16px rgba(0, 0, 0, 0.1)'
                  }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.3 }}
                  whileHover={{ scale: 1.02 }}
                >
                  <div className="sub-agent-header">
                    <div className="sub-agent-icon">
                      <span className="emoji-icon">{agent.icon}</span>
                    </div>
                    <div className="sub-agent-info">
                      <h5>{agent.name}</h5>
                      <div className="sub-agent-status">
                        {getStatusIcon(agent.status)}
                        <span>{getStatusText(agent.status)}</span>
                      </div>
                    </div>
                  </div>
                  
                  {agent.status === 'active' && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="working-indicator"
                    >
                      <div className="working-dots">
                        <motion.span
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                        ></motion.span>
                        <motion.span
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                        ></motion.span>
                        <motion.span
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                        ></motion.span>
                      </div>
                      <div className="working-text">Processing...</div>
                    </motion.div>
                  )}
                  
                  {agent.status === 'completed' && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="completion-indicator"
                    >
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                        className="completion-check"
                      >
                        <CheckCircle size={16} className="completion-icon" />
                      </motion.div>
                      <span className="completion-text">Completed</span>
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>

      </div>
    </div>
  );
};

export default AgentPanel;
