# AI-Scheduling-Assistant (AMD MI300 GPU)

## 🚀 Introduction 

### Overview:
Welcome to the Agentic AI Scheduling Assistant Hackathon! This challenge invites developers, AI enthusiasts, and innovators to build an intelligent scheduling system that leverages Agentic AI - a next-generation approach where AI acts autonomously to achieve complex goals. 

Your mission: Create an AI assistant that eliminates the back-and-forth of meeting coordination by autonomously scheduling, rescheduling, and optimizing calendars.

## 🏗️ Architecture

This AI Scheduling Assistant consists of:

- **Flask Server** (`server.py`) - HTTP API endpoint for receiving meeting requests
- **AI Scheduling Agent** (`agent_vinod.py`) - Core AI logic for parsing and scheduling
- **Calendar Integration** - Google Calendar API integration for real-time availability
- **Free Time Finder** (`find_free_time.py`) - Algorithm for finding optimal meeting slots
- **Configuration** (`config.py`) - Centralized configuration management

## 📋 Prerequisites

### 1. Python Dependencies
```bash
pip install flask openai google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 2. vLLM Server Setup
- **DeepSeek Model**: Ensure vLLM server is running on `http://localhost:3000/v1`
- **Model Path**: `/home/user/Models/deepseek-ai/deepseek-llm-7b-chat`

### 3. Google Calendar API Setup
1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create OAuth 2.0 credentials
4. Download credentials and set up OAuth tokens
5. Place token files in `Keys/` directory with format: `{username}.token`

## ⚙️ Configuration

Edit `config.py` to match your setup:

```python
# vLLM Server Configuration
VLLM_BASE_URL = "http://localhost:3000/v1"
MODEL_PATH = "/home/user/Models/deepseek-ai/deepseek-llm-7b-chat"

# Google Calendar Configuration
KEYS_DIRECTORY = "Keys"  # Directory containing OAuth token files

# Scheduling Configuration
DEFAULT_MEETING_DURATION = 30  # minutes
CALENDAR_LOOKUP_DAYS = 30  # days to look ahead
WORKING_HOURS_START = 9  # 9 AM
WORKING_HOURS_END = 17  # 5 PM

# Timezone (IST)
IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30
```

## 🚀 Running the Server

### Start the AI Scheduling Assistant:
```bash
python server.py
```

The server will start on `http://0.0.0.0:5000` and display:
```
🚀 Meeting Assistant Server started on http://0.0.0.0:5000
📡 Ready to accept requests...
Press Ctrl+C to stop the server
```

## 📡 API Documentation

### Endpoint: `POST /receive`

**Request Format:**
```json
{
    "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
    "Datetime": "09-07-2025T12:34:55",
    "Location": "IIT Mumbai",
    "From": "userone.amd@gmail.com",
    "Attendees": [
        {
            "email": "usertwo.amd@gmail.com"
        },
        {
            "email": "userthree.amd@gmail.com"
        }
    ],
    "Subject": "Agentic AI Project Status Update",
    "EmailContent": "Hi team, let's meet on Thursday for 30 minutes to discuss the status of Agentic AI Project."
}
```

**Response Format:**
```json
{
    "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
    "EventStart": "2025-07-17T14:00:00+05:30",
    "EventEnd": "2025-07-17T14:30:00+05:30",
    "Duration_mins": "30",
    "Attendees": [
        {
            "email": "userone.amd@gmail.com",
            "events": [
                {
                    "StartTime": "2025-07-17T14:00:00+05:30",
                    "EndTime": "2025-07-17T14:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"],
                    "Summary": "Agentic AI Project Status Update"
                }
            ]
        }
    ]
}
```

## 🧪 Testing

### Using curl:
```bash
curl -X POST http://localhost:5000/receive \
  -H "Content-Type: application/json" \
  -d '{
    "Request_id": "test-123",
    "Datetime": "09-07-2025T12:34:55",
    "Location": "IIT Mumbai",
    "From": "userone.amd@gmail.com",
    "Attendees": [
        {"email": "usertwo.amd@gmail.com"}
    ],
    "Subject": "Test Meeting",
    "EmailContent": "Let'\''s meet tomorrow for 30 minutes to discuss the project."
  }'
```

### Using Python:
```python
import requests
import json

payload = {
    "Request_id": "test-123",
    "Datetime": "09-07-2025T12:34:55",
    "Location": "IIT Mumbai",
    "From": "userone.amd@gmail.com",
    "Attendees": [{"email": "usertwo.amd@gmail.com"}],
    "Subject": "Test Meeting",
    "EmailContent": "Let's meet tomorrow for 30 minutes."
}

response = requests.post(
    "http://localhost:5000/receive",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload)
)

print(response.json())
```

## 🔧 Features

### ✅ Implemented Features:
- **Natural Language Processing**: Parses meeting requirements from email content
- **Multi-User Calendar Integration**: Retrieves calendar events for all attendees
- **Intelligent Scheduling**: Finds optimal meeting times based on availability
- **Conflict Resolution**: Avoids scheduling conflicts automatically
- **Working Hours Respect**: Schedules within configured working hours
- **Duration Flexibility**: Supports custom meeting durations
- **Error Handling**: Graceful error handling with meaningful responses

### 🔄 AI Processing Pipeline:
1. **Request Parsing**: Extract attendees, subject, and content
2. **NLP Analysis**: Use DeepSeek AI to understand meeting requirements
3. **Calendar Retrieval**: Fetch calendar events for all participants
4. **Slot Finding**: Identify common free time slots
5. **Optimization**: Select the best meeting time based on preferences
6. **Response Generation**: Format the scheduled meeting details

## 📁 Project Structure

```
amd_agent_hack/
├── server.py              # Flask HTTP server
├── agent_vinod.py         # AI Scheduling Agent core logic
├── find_free_time.py      # Free time slot finding algorithms
├── config.py              # Configuration settings
├── Keys/                  # Google OAuth token files
│   ├── userone.token
│   ├── usertwo.token
│   └── userthree.token
└── README.md              # This file
```

## 🛠️ Troubleshooting

### Common Issues:

1. **vLLM Server Not Running**
   ```
   Error: Connection refused to http://localhost:3000/v1
   ```
   **Solution**: Start your vLLM server with DeepSeek model

2. **Google Calendar Access Denied**
   ```
   Error retrieving calendar for user@example.com
   ```
   **Solution**: Ensure OAuth tokens are properly configured in `Keys/` directory

3. **No Available Time Slots**
   ```
   ❌ No available time slots found
   ```
   **Solution**: Check if attendees have conflicting schedules or extend `CALENDAR_LOOKUP_DAYS`

### Debug Mode:
The server provides detailed console output for debugging:
- 📥 **Received requests**
- 📝 **Parsed meeting info**
- 📅 **Calendar retrieval status**
- ✅ **Optimal time found**
- 📤 **Response sent**

## 🏆 Hackathon Submission

This AI Scheduling Assistant demonstrates:
- **Autonomous AI Decision Making**: No human intervention required
- **Multi-Modal Integration**: Calendar APIs + NLP + Optimization algorithms
- **Real-World Applicability**: Production-ready meeting scheduling
- **Scalable Architecture**: Supports multiple users and complex scheduling scenarios

## 📞 Support

For issues or questions:
1. Check the console output for detailed error messages
2. Verify all prerequisites are installed and configured
3. Ensure vLLM server and Google Calendar API are accessible
4. Test with the provided example payloads

---

**Built for AMD MI300 GPU Hackathon** 🚀
