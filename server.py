from flask import Flask, request, jsonify
from threading import Thread
import json
import time
import signal
import sys

# Import your final AI scheduling agent
from agent_vinod import AISchedulingAgent

app = Flask(__name__)
received_data = []

# Initialize your AI Scheduling Agent
agent = AISchedulingAgent()


def your_meeting_assistant(data): 
    """
    Main function that processes meeting requests using your AI agent
    This is called by the hackathon system
    """
    try:
        # Use your AI agent to process the meeting request
        result = agent.your_meeting_assistant(data)
        return result
    except Exception as e:
        print(f"❌ Error in your_meeting_assistant: {e}")
        # Return error response in expected format
        return {
            "error": str(e),
            "Request_id": data.get("Request_id", "unknown"),
            "EventStart": "",
            "EventEnd": "", 
            "Duration_mins": ""
        }


@app.route('/receive', methods=['POST'])
def receive():
    data = request.get_json()
    print(f"\n Received: {json.dumps(data, indent=2)}")
    new_data = your_meeting_assistant(data)  # Your AI Meeting Assistant Function Call
    received_data.append(data)
    print(f"\n\n\n Sending:\n {json.dumps(new_data, indent=2)}")
    return jsonify(new_data)

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def signal_handler(sig, frame):
    print('\n🛑 Shutting down server...')
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start Flask in a background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print("🚀 Meeting Assistant Server started on http://0.0.0.0:5000")
    print("📡 Ready to accept requests...")
    print("Press Ctrl+C to stop the server")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n🛑 Shutting down server...')
        sys.exit(0)