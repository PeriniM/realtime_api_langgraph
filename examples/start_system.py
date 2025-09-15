#!/usr/bin/env python3
"""
Startup script for the entire Agent in the Loop system.
Starts both the FastAPI server and provides instructions for the React frontend.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def check_requirements():
    """Check if required files and directories exist"""
    print("🔍 Checking system requirements...")
    
    # Check for .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("   Create a .env file with: OPENAI_API_KEY=your_key_here")
        return False
    
    # Check for API directory
    api_dir = Path("api")
    if not api_dir.exists():
        print("❌ API directory not found!")
        return False
    
    # Check for frontend directory
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return False
    
    print("✅ All requirements met!")
    return True

def start_api_server():
    """Start the FastAPI server"""
    print("\n🚀 Starting FastAPI server...")
    try:
        # Change to API directory and start server
        os.chdir("api")
        subprocess.Popen([
            sys.executable, "start_server.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ FastAPI server started on http://localhost:8000")
        return True
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return False

def main():
    """Main startup function"""
    print("🤖 Agent in the Loop System Startup")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ System requirements not met. Please fix the issues above.")
        return
    
    # Start API server
    if not start_api_server():
        print("\n❌ Failed to start the system.")
        return
    
    # Wait a moment for server to start
    time.sleep(2)
    
    print("\n" + "=" * 50)
    print("🎉 System started successfully!")
    print("\n📋 Next steps:")
    print("1. Open a new terminal")
    print("2. Navigate to the frontend directory: cd frontend")
    print("3. Install dependencies: npm install")
    print("4. Start the React app: npm start")
    print("\n🌐 URLs:")
    print("   • Frontend: http://localhost:3000")
    print("   • API Server: http://localhost:8000")
    print("   • API Docs: http://localhost:8000/docs")
    print("   • WebSocket: ws://localhost:8000/ws")
    print("\n💡 The frontend will automatically connect to the API server")
    print("   and you'll see 'Connected to API' in the status indicator.")
    print("\n🛑 To stop the system, press Ctrl+C in this terminal")

if __name__ == "__main__":
    try:
        main()
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down system...")
        print("✅ System stopped.")
