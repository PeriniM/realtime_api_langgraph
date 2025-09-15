import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react';
import './VoiceStreaming.css';

const VoiceStreaming = ({ onTranscript, onError, isConnected }) => {
  const [isListening, setIsListening] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  
  const mediaRecorderRef = useRef(null);
  const audioStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const wsRef = useRef(null);

  // Initialize WebSocket connection only when needed
  useEffect(() => {
    // Don't auto-connect, wait for user to start listening
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    setConnectionStatus('connecting');
    const ws = new WebSocket('ws://localhost:8000/ws/voice');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[VoiceStreaming] Connected to voice WebSocket');
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        console.error('[VoiceStreaming] Error parsing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('[VoiceStreaming] WebSocket disconnected');
      setConnectionStatus('disconnected');
      stopListening();
    };

    ws.onerror = (error) => {
      console.error('[VoiceStreaming] WebSocket error:', error);
      setConnectionStatus('error');
      onError && onError(error);
    };
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'audio_chunk':
        // Queue audio chunk for playback
        queueAudioChunk(data.audio);
        break;
      case 'transcript':
        onTranscript && onTranscript(data.text, data.isUser);
        break;
      case 'speech_started':
        console.log('[VoiceStreaming] AI started speaking');
        break;
      case 'speech_ended':
        console.log('[VoiceStreaming] AI finished speaking');
        break;
      case 'error':
        onError && onError(new Error(data.message));
        break;
      default:
        console.log('[VoiceStreaming] Unknown message type:', data.type);
    }
  };

  const queueAudioChunk = (base64Audio) => {
    audioQueueRef.current.push(base64Audio);
    if (!isPlayingRef.current) {
      playNextAudioChunk();
    }
  };

  const playNextAudioChunk = async () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsPlaying(false);
      return;
    }

    isPlayingRef.current = true;
    setIsPlaying(true);

    try {
      const base64Audio = audioQueueRef.current.shift();
      const audioData = atob(base64Audio);
      const audioBuffer = new ArrayBuffer(audioData.length);
      const view = new Uint8Array(audioBuffer);
      
      for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i);
      }

      // Create audio context if not exists
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 24000
        });
      }

      const audioBufferSource = audioContextRef.current.createBufferSource();
      const audioBufferDecoded = await audioContextRef.current.decodeAudioData(audioBuffer);
      
      audioBufferSource.buffer = audioBufferDecoded;
      audioBufferSource.connect(audioContextRef.current.destination);
      
      audioBufferSource.onended = () => {
        // Play next chunk after a small delay
        setTimeout(() => {
          playNextAudioChunk();
        }, 10);
      };

      audioBufferSource.start();
    } catch (error) {
      console.error('[VoiceStreaming] Error playing audio chunk:', error);
      isPlayingRef.current = false;
      setIsPlaying(false);
    }
  };

  const startListening = async () => {
    if (isListening) {
      return;
    }

    // Connect to WebSocket if not already connected
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      // Wait a moment for connection to establish
      await new Promise(resolve => setTimeout(resolve, 1000));
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.error('[VoiceStreaming] Failed to establish WebSocket connection');
        onError && onError(new Error('Failed to connect to voice service'));
        return;
      }
    }

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      audioStreamRef.current = stream;

      // Create audio context for analysis
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000
      });

      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);

      // Start audio level monitoring
      monitorAudioLevel();

      // Create MediaRecorder for streaming
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          // Convert to base64 and send
          const reader = new FileReader();
          reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            wsRef.current.send(JSON.stringify({
              type: 'audio_data',
              audio: base64,
              timestamp: Date.now()
            }));
          };
          reader.readAsDataURL(event.data);
        }
      };

      mediaRecorder.start(50); // Send data every 50ms for low latency
      setIsListening(true);

      console.log('[VoiceStreaming] Started listening and streaming audio');
    } catch (error) {
      console.error('[VoiceStreaming] Error starting listening:', error);
      onError && onError(error);
    }
  };

  const stopListening = () => {
    if (!isListening) return;

    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }

    // Stop audio stream
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }

    // Stop audio level monitoring
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setIsListening(false);
    setAudioLevel(0);

    console.log('[VoiceStreaming] Stopped listening');
  };

  const monitorAudioLevel = () => {
    const updateLevel = () => {
      if (analyserRef.current && isListening) {
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        
        // Calculate average audio level
        const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
        setAudioLevel(average / 255); // Normalize to 0-1
        
        animationFrameRef.current = requestAnimationFrame(updateLevel);
      }
    };
    updateLevel();
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return '#10b981';
      case 'connecting': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'error': return 'Error';
      default: return 'Disconnected';
    }
  };

  return (
    <div className="voice-streaming">
      <div className="voice-header">
        <h3>Voice Streaming</h3>
        <div className="connection-status">
          <div 
            className="status-dot" 
            style={{ backgroundColor: getConnectionStatusColor() }}
          />
          <span>{getConnectionStatusText()}</span>
        </div>
      </div>

      <div className="voice-controls">
        <motion.button
          className={`voice-button ${isListening ? 'listening' : ''}`}
          onClick={toggleListening}
          disabled={false}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <div className="button-content">
            {isListening ? (
              <MicOff size={24} />
            ) : (
              <Mic size={24} />
            )}
            <span>
              {isListening ? 'Stop Listening' : 
               connectionStatus === 'connected' ? 'Start Listening' :
               connectionStatus === 'connecting' ? 'Connecting...' :
               'Connect & Start Listening'}
            </span>
          </div>
        </motion.button>

        {isListening && (
          <motion.div
            className="audio-level-indicator"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
          >
            <div className="level-bars">
              {[...Array(8)].map((_, i) => (
                <motion.div
                  key={i}
                  className="level-bar"
                  animate={{
                    height: `${Math.max(10, audioLevel * 100 * (1 - i * 0.1))}%`
                  }}
                  transition={{ duration: 0.1 }}
                />
              ))}
            </div>
          </motion.div>
        )}

        {isPlaying && (
          <motion.div
            className="playing-indicator"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
          >
            <Volume2 size={20} />
            <span>AI Speaking</span>
            <div className="playing-dots">
              <motion.span
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0 }}
              />
              <motion.span
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
              />
              <motion.span
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
              />
            </div>
          </motion.div>
        )}
      </div>

      <div className="voice-info">
        <p>
          {isListening 
            ? 'Listening... Speak into your microphone' 
            : 'Click the button to start voice conversation'
          }
        </p>
        {connectionStatus !== 'connected' && (
          <p className="error-text">
            Voice streaming requires a WebSocket connection
          </p>
        )}
      </div>
    </div>
  );
};

export default VoiceStreaming;
