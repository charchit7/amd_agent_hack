import os
import json
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Import your scheduler functions
from find_free_time import find_common_free_slots
# Import configuration
from config import (
    VLLM_BASE_URL, 
    MODEL_PATH, 
    KEYS_DIRECTORY,
    DEFAULT_MEETING_DURATION,
    CALENDAR_LOOKUP_DAYS,
    WORKING_HOURS_START,
    WORKING_HOURS_END,
    IST_OFFSET_HOURS,
    IST_OFFSET_MINUTES
)

class AISchedulingAgent:
    def __init__(self, base_url=None, model_path=None, keys_directory=None):
        """
        Initialize the AI Scheduling Agent
        
        Args:
            base_url: vLLM server URL (defaults to config value)
            model_path: Model path for DeepSeek (defaults to config value)
            keys_directory: Directory containing Google OAuth tokens (defaults to config value)
        """
        self.base_url = base_url or VLLM_BASE_URL
        self.model_path = model_path or MODEL_PATH
        self.keys_directory = keys_directory or KEYS_DIRECTORY
        self.client = OpenAI(api_key="NULL", base_url=self.base_url, timeout=None, max_retries=0)
        
    def parse_datetime(self, datetime_str):
        """Parse ISO datetime string to datetime object"""
        return datetime.fromisoformat(datetime_str)
    
    def retrive_calendar_events(self, user, start, end):
        """Retrieve calendar events for a user"""
        events_list = []
        token_path = f"{self.keys_directory}/{user.split('@')[0]}.token"
        
        try:
            user_creds = Credentials.from_authorized_user_file(token_path)
            calendar_service = build("calendar", "v3", credentials=user_creds)
            events_result = calendar_service.events().list(
                calendarId='primary', 
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            for event in events:
                attendee_list = []
                try:
                    for attendee in event.get("attendees", []):
                        attendee_list.append(attendee['email'])
                except:
                    attendee_list.append("SELF")
                
                if not attendee_list:
                    attendee_list.append("SELF")
                
                start_time = event.get("start", {}).get("dateTime")
                end_time = event.get("end", {}).get("dateTime")
                
                if start_time and end_time:
                    events_list.append({
                        "StartTime": start_time,
                        "EndTime": end_time,
                        "NumAttendees": len(set(attendee_list)),
                        "Attendees": list(set(attendee_list)),
                        "Summary": event.get("summary", "No Title")
                    })
        except Exception as e:
            print(f"Error retrieving calendar for {user}: {e}")
            # Return default off-hours if calendar access fails
            ist = timezone(timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES))
            start_dt = self.parse_datetime(start)
            end_dt = self.parse_datetime(end)
            
            current_date = start_dt.date()
            while current_date <= end_dt.date():
                off_start = datetime.combine(current_date, datetime.min.time().replace(hour=WORKING_HOURS_END)).replace(tzinfo=ist)
                off_end = datetime.combine(current_date + timedelta(days=1), datetime.min.time().replace(hour=WORKING_HOURS_START)).replace(tzinfo=ist)
                
                events_list.append({
                    "StartTime": off_start.isoformat(),
                    "EndTime": off_end.isoformat(),
                    "NumAttendees": 1,
                    "Attendees": ["SELF"],
                    "Summary": "Off Hours"
                })
                current_date += timedelta(days=1)
        
        return events_list
    
    def parse_meeting_request(self, email_content, attendees_list):
        """Use DeepSeek to parse meeting requirements from email content"""
        
        # Create attendees string
        attendees_str = ", ".join([att["email"] for att in attendees_list])
        
        prompt = f"""
        You are an EVENT SCHEDULING EXPERT ASSISTANT. Parse the following meeting request and extract key information.
        
        Email Content: "{email_content}"
        Attendees: {attendees_str}
        
        Extract and return ONLY a JSON object with these fields:
        {{
            "duration_minutes": <meeting duration in minutes, default {DEFAULT_MEETING_DURATION} if not specified>,
            "time_preference": "<day preference like 'Thursday', 'next week', etc.>",
            "meeting_type": "<type of meeting from subject/content>",
            "urgency": "<high/medium/low based on content tone>"
        }}
        
        Rules:
        - If duration not specified, use {DEFAULT_MEETING_DURATION} minutes
        - Extract day preferences (Monday, Tuesday, etc.)
        - Be concise and accurate
        - Return ONLY valid JSON, no other text
        - Avoid SUNDAY and SATURDAY
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_path,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up the response to ensure it's valid JSON
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing meeting request: {e}")
            # Return default values
            return {
                "duration_minutes": DEFAULT_MEETING_DURATION,
                "time_preference": "any weekday",
                "meeting_type": "general meeting",
                "urgency": "medium"
            }
    
    def find_optimal_meeting_time(self, all_users_events, duration_minutes, time_preference):
        """Find the best meeting time using your scheduler logic"""
        
        # Get date range from events
        all_dates = set()
        for events in all_users_events.values():
            for event in events:
                start_date = self.parse_datetime(event['StartTime']).date()
                all_dates.add(start_date)
        
        date_range = sorted(list(all_dates))
        
        # Filter dates based on time preference
        if "thursday" in time_preference.lower():
            date_range = [d for d in date_range if d.strftime('%A').lower() == 'thursday']
        elif "monday" in time_preference.lower():
            date_range = [d for d in date_range if d.strftime('%A').lower() == 'monday']
        # Add more day filters as needed
        
        # Find best available slot
        for date in date_range:
            free_slots = find_common_free_slots(all_users_events, date, duration_minutes)
            if free_slots:
                # Return the first available slot
                best_slot = free_slots[0]
                return {
                    'date': date,
                    'start_time': best_slot['start'],
                    'end_time': best_slot['start'] + timedelta(minutes=duration_minutes)
                }
        
        # If no slots found on preferred days, try any day
        for date in sorted(list(all_dates)):
            free_slots = find_common_free_slots(all_users_events, date, duration_minutes)
            if free_slots:
                best_slot = free_slots[0]
                return {
                    'date': date,
                    'start_time': best_slot['start'],
                    'end_time': best_slot['start'] + timedelta(minutes=duration_minutes)
                }
        
        return None
    
    def generate_output_format(self, request_data, optimal_time, all_users_events, duration_minutes):
        """Generate the exact output format required"""
        
        if not optimal_time:
            raise Exception("No available time slots found")
        
        # Create the base response
        response = {
            "Request_id": request_data["Request_id"],
            "Datetime": request_data["Datetime"],
            "Location": request_data["Location"],
            "From": request_data["From"],
            "Attendees": [],
            "Subject": request_data["Subject"],
            "EmailContent": request_data["EmailContent"],
            "EventStart": optimal_time['start_time'].isoformat(),
            "EventEnd": optimal_time['end_time'].isoformat(),
            "Duration_mins": str(duration_minutes),
            "MetaData": {}
        }
        
        # Get all attendees including the sender
        all_attendees = [request_data["From"]]
        for att in request_data["Attendees"]:
            all_attendees.append(att["email"])
        
        # Create the new meeting event
        new_meeting = {
            "StartTime": optimal_time['start_time'].isoformat(),
            "EndTime": optimal_time['end_time'].isoformat(),
            "NumAttendees": len(all_attendees),
            "Attendees": all_attendees,
            "Summary": request_data["Subject"]
        }
        
        # Generate attendee data with their existing events + new meeting
        for attendee_email in all_attendees:
            attendee_events = all_users_events.get(attendee_email, []).copy()
            
            # Add the new meeting to their calendar
            attendee_events.append(new_meeting)
            
            # Sort events by start time
            attendee_events.sort(key=lambda x: self.parse_datetime(x['StartTime']))
            
            response["Attendees"].append({
                "email": attendee_email,
                "events": attendee_events
            })
        
        return response
    
    def your_meeting_assistant(self, request_json):
        """
        Main function that processes meeting requests
        This is the function that will be called by the hackathon system
        """
        try:
            # Parse the request
            if isinstance(request_json, str):
                request_data = json.loads(request_json)
            else:
                request_data = request_json
            
            print(f"🚀 Processing meeting request: {request_data['Request_id']}")
            
            # Extract attendees
            all_attendees = [request_data["From"]]
            for att in request_data["Attendees"]:
                all_attendees.append(att["email"])
            
            # Parse meeting requirements using AI
            meeting_info = self.parse_meeting_request(
                request_data["EmailContent"], 
                request_data["Attendees"]
            )
            
            print(f"📝 Parsed meeting info: {meeting_info}")
            
            # Set date range for calendar lookup (next CALENDAR_LOOKUP_DAYS days)
            start_date = datetime.now(timezone(timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)))
            end_date = start_date + timedelta(days=CALENDAR_LOOKUP_DAYS)
            
            start_str = start_date.isoformat()
            end_str = end_date.isoformat()
            
            # Retrieve calendar events for all attendees
            all_users_events = {}
            for attendee in all_attendees:
                print(f"📅 Retrieving calendar for {attendee}")
                events = self.retrive_calendar_events(attendee, start_str, end_str)
                all_users_events[attendee] = events
            
            # Find optimal meeting time
            optimal_time = self.find_optimal_meeting_time(
                all_users_events, 
                meeting_info["duration_minutes"],
                meeting_info["time_preference"]
            )
            
            if optimal_time:
                print(f"✅ Found optimal time: {optimal_time['start_time']} - {optimal_time['end_time']}")
            else:
                print("❌ No available time slots found")
            
            # Generate the final output
            result = self.generate_output_format(
                request_data, 
                optimal_time, 
                all_users_events, 
                meeting_info["duration_minutes"]
            )
            
            print(f"🎯 Successfully scheduled meeting!")
            return result
            
        except Exception as e:
            print(f"❌ Error processing meeting request: {e}")
            return {
                "error": str(e),
                "Request_id": request_data.get("Request_id", "unknown")
            }

# Example usage and testing
if __name__ == "__main__":
    # Initialize the agent
    agent = AISchedulingAgent()
    
    # Test with the sample request
    test_request = {
        "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
        "Datetime": "09-07-2025T12:34:55",
        "Location": "IIT Mumbai",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Agentic AI Project Status Update",
        "EmailContent": "Hi team, let's meet on Thursday for 30 minutes to discuss the status of Agentic AI Project."
    }
    
    # Process the request
    result = agent.your_meeting_assistant(test_request)
    
    # Print the result
    print("\n🏆 FINAL RESULT:")
    print(json.dumps(result, indent=2))
