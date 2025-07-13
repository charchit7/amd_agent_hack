# Configuration for AI Scheduling Agent
# Updated with your actual vLLM server details

# vLLM Server Configuration
VLLM_BASE_URL = "http://localhost:3000/v1"  # Your actual server URL
MODEL_PATH = "/home/user/Models/deepseek-ai/deepseek-llm-7b-chat"  # DeepSeek model path

# Google Calendar Configuration
KEYS_DIRECTORY = "Keys"  # Directory containing OAuth token files

# Scheduling Configuration
DEFAULT_MEETING_DURATION = 30  # minutes
CALENDAR_LOOKUP_DAYS = 30  # days to look ahead for scheduling
WORKING_HOURS_START = 9  # 9 AM
WORKING_HOURS_END = 17  # 5 PM (17:30 for 5:30 PM)

# Timezone Configuration
IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30

# Example server URLs for different models:
# DeepSeek-7B-Chat: "http://localhost:3000/v1"
# Llama-3.1-8B: "http://localhost:4000/v1"
