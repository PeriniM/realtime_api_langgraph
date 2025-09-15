#!/usr/bin/env python3
"""
Startup script for the Agent in the Loop API server.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add parent directory to path to import our modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

if __name__ == "__main__":
    # Check if .env file exists
    env_file = parent_dir / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found. Make sure to set your OpenAI API key.")
        print("   Create a .env file with: OPENAI_API_KEY=your_key_here")
    
    print("🚀 Starting Agent in the Loop API server...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws")
    print("🌐 API documentation: http://localhost:8000/docs")
    print("🔗 Frontend should connect to: http://localhost:3000")
    print("")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
