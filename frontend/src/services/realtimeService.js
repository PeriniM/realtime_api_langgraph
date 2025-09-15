/**
 * Realtime WebSocket service for speech-to-speech conversation
 */

class RealtimeService {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.listeners = new Map();
    this.isConnected = false;
    this.isListening = false;
    this.mediaRecorder = null;
    this.audioContext = null;
    this.audioStream = null;
  }

  connect() {
    // Don't create a new connection if one already exists
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('[RealtimeService] Already connected');
      return;
    }
    
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      console.log('[RealtimeService] Connection already in progress');
      return;
    }
    
    const wsUrl = process.env.REACT_APP_REALTIME_WS_URL || 'ws://localhost:8000/ws/realtime';
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('[RealtimeService] Connected to realtime API');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit('message', data);
        } catch (error) {
          console.error('[RealtimeService] Error parsing message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('[RealtimeService] Connection closed:', event.code, event.reason);
        this.isConnected = false;
        this.emit('disconnected');
        
        // Don't auto-reconnect if it was a clean close or server error
        if (event.code === 1000 || event.code === 1011) {
          console.log('[RealtimeService] Clean close or server error, not reconnecting');
          return;
        }
        
        this.handleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[RealtimeService] Error:', error);
        this.emit('error', error);
      };

    } catch (error) {
      console.error('[RealtimeService] Connection failed:', error);
      this.handleReconnect();
    }
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[RealtimeService] Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('[RealtimeService] Max reconnection attempts reached');
      this.emit('maxReconnectAttemptsReached');
    }
  }

  async startListening() {
    if (this.isListening) {
      console.log('[RealtimeService] Already listening');
      return;
    }

    if (!this.isConnected) {
      console.error('[RealtimeService] Cannot start listening - not connected to realtime API');
      this.emit('error', new Error('Not connected to realtime API'));
      return;
    }

    try {
      console.log('[RealtimeService] Requesting microphone access...');
      
      // Request microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });

      console.log('[RealtimeService] Microphone access granted');

      // Create audio context for processing
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000
      });

      // Create media recorder for audio streaming
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && this.isConnected) {
          // Convert audio data to base64 and send
          const reader = new FileReader();
          reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            this.send({
              type: 'audio_data',
              data: base64
            });
          };
          reader.readAsDataURL(event.data);
        }
      };

      this.mediaRecorder.start(100); // Send data every 100ms
      this.isListening = true;
      this.emit('listening_started');

      console.log('[RealtimeService] Started listening and streaming audio');

    } catch (error) {
      console.error('[RealtimeService] Error starting listening:', error);
      this.emit('error', error);
      
      // Provide user-friendly error messages
      if (error.name === 'NotAllowedError') {
        this.emit('error', new Error('Microphone access denied. Please allow microphone access and try again.'));
      } else if (error.name === 'NotFoundError') {
        this.emit('error', new Error('No microphone found. Please connect a microphone and try again.'));
      } else {
        this.emit('error', new Error(`Failed to start listening: ${error.message}`));
      }
    }
  }

  stopListening() {
    if (!this.isListening) {
      return;
    }

    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
    }

    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
    }

    if (this.audioContext) {
      this.audioContext.close();
    }

    this.isListening = false;
    this.emit('listening_stopped');

    console.log('[RealtimeService] Stopped listening');
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[RealtimeService] Cannot send message - not connected');
    }
  }

  disconnect() {
    this.stopListening();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  // Event listener system
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    const callbacks = this.listeners.get(event);
    if (!callbacks.includes(callback)) {
      callbacks.push(callback);
    }
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[RealtimeService] Error in event listener for ${event}:`, error);
        }
      });
    }
  }
}

// Create singleton instance
const realtimeService = new RealtimeService();

export default realtimeService;
