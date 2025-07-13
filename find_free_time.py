from datetime import datetime, timedelta, timezone

def parse_datetime(datetime_str):
    """
    Parse ISO datetime string to datetime object.
    
    Converts an ISO 8601 formatted datetime string (with timezone information)
    into a Python datetime object for further processing.
    
    Args:
        datetime_str (str): ISO 8601 formatted datetime string with timezone
                           Example: '2025-07-13T18:00:00+05:30'
    
    Returns:
        datetime: Timezone-aware datetime object
        
    Example:
        >>> dt_str = '2025-07-13T18:00:00+05:30'
        >>> dt_obj = parse_datetime(dt_str)
        >>> print(dt_obj)
        2025-07-13 18:00:00+05:30
    
    Raises:
        ValueError: If the datetime string is not in valid ISO format
    """
    return datetime.fromisoformat(datetime_str)

def format_datetime_for_calendar(dt):
    """Format datetime object back to calendar API format"""
    return dt.isoformat()

def get_user_working_hours(user_email, events_list):
    """Determine working hours for a user based on their Off Hours pattern"""
    off_hours_events = [e for e in events_list if e['Summary'] == 'Off Hours']
    
    if not off_hours_events:
        # Default working hours if no Off Hours found
        return (7, 30), (18, 0)  # 7:30 AM to 6 PM
    
    # Analyze Off Hours pattern to determine working hours
    sample_event = off_hours_events[0]
    off_start = parse_datetime(sample_event['StartTime'])
    off_end = parse_datetime(sample_event['EndTime'])
    
    # Working hours are the gap between Off Hours
    work_start_hour = off_end.hour
    work_start_min = off_end.minute
    work_end_hour = off_start.hour
    work_end_min = off_start.minute
    
    return (work_start_hour, work_start_min), (work_end_hour, work_end_min)

def find_common_free_slots(all_users_events, target_date, duration_minutes=30):
    """Find time slots when ALL attendees are free"""
    
    # Get working hours for each user
    user_working_hours = {}
    for user_email, events in all_users_events.items():
        user_working_hours[user_email] = get_user_working_hours(user_email, events)
    
    # Find the most restrictive working hours (intersection)
    earliest_start = max([wh[0] for wh in user_working_hours.values()])
    latest_end = min([wh[1] for wh in user_working_hours.values()])
    
    # Create timezone object
    ist = timezone(timedelta(hours=5, minutes=30))
    
    # Define the common working window
    common_start = datetime.combine(target_date, datetime.min.time().replace(
        hour=earliest_start[0], minute=earliest_start[1])).replace(tzinfo=ist)
    common_end = datetime.combine(target_date, datetime.min.time().replace(
        hour=latest_end[0], minute=latest_end[1])).replace(tzinfo=ist)
    
    # Collect all busy periods for the target date
    all_busy_periods = []
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    for user_email, events in all_users_events.items():
        for event in events:
            event_start = parse_datetime(event['StartTime'])
            event_end = parse_datetime(event['EndTime'])
            event_date = event_start.date().strftime('%Y-%m-%d')
            
            if event_date == target_date_str and event['Summary'] != 'Off Hours':
                all_busy_periods.append({
                    'start': event_start,
                    'end': event_end,
                    'user': user_email,
                    'summary': event['Summary']
                })
    
    # Sort busy periods by start time
    all_busy_periods.sort(key=lambda x: x['start'])
    
    # Find free slots in the common working window
    free_slots = []
    current_time = common_start
    
    for busy_period in all_busy_periods:
        # If there's a gap before this busy period
        if current_time < busy_period['start']:
            gap_duration = (busy_period['start'] - current_time).total_seconds() / 60
            if gap_duration >= duration_minutes:
                free_slots.append({
                    'start': current_time,
                    'end': busy_period['start'],
                    'duration_minutes': int(gap_duration)
                })
        
        # Move current time to end of this busy period
        current_time = max(current_time, busy_period['end'])
    
    # Check if there's time after the last busy period
    if current_time < common_end:
        gap_duration = (common_end - current_time).total_seconds() / 60
        if gap_duration >= duration_minutes:
            free_slots.append({
                'start': current_time,
                'end': common_end,
                'duration_minutes': int(gap_duration)
            })
    
    return free_slots

def suggest_optimal_meeting_time(all_users_events, duration_minutes=30, preferred_days=None):
    """
    Suggest the best meeting time across multiple days.
    
    Analyzes availability across multiple dates to suggest optimal meeting times.
    Can filter by preferred days of the week and considers meeting duration
    requirements.
    
    Args:
        all_users_events (dict): Dictionary mapping user emails to their event lists
                                Format: {'user@example.com': [event1, event2, ...]}
                                Each event should contain:
                                - 'StartTime': ISO datetime string with timezone
                                - 'EndTime': ISO datetime string with timezone
                                - 'Summary': Event title/description
                                - 'NumAttendees': Number of attendees
                                - 'Attendees': List of attendee emails
        duration_minutes (int, optional): Required meeting duration in minutes.
                                        Defaults to 30.
        preferred_days (list, optional): List of preferred day names (e.g., ['Monday', 'Tuesday']).
                                       If None, considers all days. Defaults to None.
    
    Returns:
        list: List of meeting suggestion dictionaries, each containing:
              - 'date': date object for the suggested date
              - 'start_time': datetime object for suggested start time
              - 'end_time': datetime object for suggested end time
              - 'available_duration': Total available duration in minutes
              - 'day_of_week': Day name (e.g., 'Monday')
    
    Example:
        >>> all_users = {
        ...     'user1@example.com': [event1, event2],
        ...     'user2@example.com': [event3, event4]
        ... }
        >>> suggestions = suggest_optimal_meeting_time(
        ...     all_users, 
        ...     duration_minutes=60, 
        ...     preferred_days=['Monday', 'Tuesday']
        ... )
        >>> for suggestion in suggestions[:3]:
        ...     print(f"{suggestion['date']} at {suggestion['start_time'].strftime('%H:%M')}")
    
    Algorithm:
        1. Extracts all unique dates from user events
        2. Filters by preferred days if specified
        3. Finds free slots for each date using find_common_free_slots()
        4. Creates meeting suggestions for each available slot
        5. Sorts suggestions chronologically
    
    Note:
        - Results are sorted by date and time (earliest first)
        - Each suggestion represents a potential meeting slot
        - Duration filtering ensures only slots of adequate length are suggested
    """
    
    # Get date range from all events
    all_dates = set()
    for events in all_users_events.values():
        for event in events:
            start_date = parse_datetime(event['StartTime']).date()
            all_dates.add(start_date)
    
    all_dates = sorted(list(all_dates))
    
    # If preferred days specified, filter to those
    if preferred_days:
        all_dates = [d for d in all_dates if d.strftime('%A').lower() in [day.lower() for day in preferred_days]]
    
    suggestions = []
    
    for date in all_dates:
        free_slots = find_common_free_slots(all_users_events, date, duration_minutes)
        for slot in free_slots:
            suggestions.append({
                'date': date,
                'start_time': slot['start'],
                'end_time': slot['start'] + timedelta(minutes=duration_minutes),
                'available_duration': slot['duration_minutes'],
                'day_of_week': date.strftime('%A')
            })
    
    # Sort by date and time
    suggestions.sort(key=lambda x: x['start_time'])
    
    return suggestions

def analyze_multi_user_availability(all_users_events):
    """
    Comprehensive analysis of multi-user availability.
    
    Performs a complete analysis of calendar availability across multiple users,
    providing detailed output including working hours, daily availability,
    and meeting suggestions. This is the main entry point for multi-user
    scheduling analysis.
    
    Args:
        all_users_events (dict): Dictionary mapping user emails to their event lists
                                Format: {'user@example.com': [event1, event2, ...]}
                                Each event should contain:
                                - 'StartTime': ISO datetime string with timezone
                                - 'EndTime': ISO datetime string with timezone
                                - 'Summary': Event title/description
                                - 'NumAttendees': Number of attendees
                                - 'Attendees': List of attendee emails
    
    Returns:
        dict: Analysis results containing:
              - 'total_available_slots': Total number of free slots across all dates
              - 'suggestions': List of top 3 meeting suggestions (30-minute slots)
              - 'analysis_complete': Boolean indicating successful completion
    
    Output:
        Prints detailed analysis to console including:
        - Each user's working hours
        - Date range being analyzed
        - Daily breakdown of free slots with times and durations
        - Summary statistics
        - Top 3 meeting time recommendations
    
    Example:
        >>> all_users = {
        ...     'user1@example.com': [
        ...         {'StartTime': '2025-07-13T18:00:00+05:30', 
        ...          'EndTime': '2025-07-14T09:00:00+05:30',
        ...          'Summary': 'Off Hours', 'NumAttendees': 1, 'Attendees': ['SELF']}
        ...     ],
        ...     'user2@example.com': [...]
        ... }
        >>> result = analyze_multi_user_availability(all_users)
        >>> print(f"Found {result['total_available_slots']} available slots")
    
    Features:
        - Automatically detects working hours from "Off Hours" events
        - Finds intersection of all users' working hours
        - Identifies common free time slots
        - Provides formatted console output for easy reading
        - Returns structured data for programmatic use
    
    Note:
        - Assumes IST (Indian Standard Time) timezone
        - Uses 30-minute minimum slot duration for analysis
        - Excludes "Off Hours" events from busy time calculation
        - Provides both human-readable output and machine-readable results
    """
    print("🎯 MULTI-USER AVAILABILITY ANALYSIS")
    print("=" * 60)
    
    # Analyze each user's working hours
    print("\n👥 USER WORKING HOURS:")
    for user_email, events in all_users_events.items():
        working_hours = get_user_working_hours(user_email, events)
        print(f"   {user_email}: {working_hours[0][0]:02d}:{working_hours[0][1]:02d} - {working_hours[1][0]:02d}:{working_hours[1][1]:02d}")
    
    # Get date range
    all_dates = set()
    for events in all_users_events.values():
        for event in events:
            start_date = parse_datetime(event['StartTime']).date()
            all_dates.add(start_date)
    all_dates = sorted(list(all_dates))
    
    print(f"\n📅 ANALYZING DATES: {all_dates[0]} to {all_dates[-1]}")
    
    # Analyze each date
    total_slots = 0
    for date in all_dates:
        print(f"\n🗓️  {date} ({date.strftime('%A')}):")
        free_slots = find_common_free_slots(all_users_events, date, 30)
        print('testing free slots')
        print(free_slots)
        
        if free_slots:
            print(f"   ✅ {len(free_slots)} common free slots:")
            for i, slot in enumerate(free_slots, 1):
                print(f"      {i}. {slot['start'].strftime('%H:%M')} - {slot['end'].strftime('%H:%M')} ({slot['duration_minutes']} mins)")
            total_slots += len(free_slots)
        else:
            print("   ❌ No common free time")
    
    print(f"\n📊 SUMMARY: {total_slots} total available slots across all dates")
    
    # Get top 3 suggestions for 30-minute meetings
    suggestions = suggest_optimal_meeting_time(all_users_events, 30)
    if suggestions:
        print(f"\n🏆 TOP 3 MEETING SUGGESTIONS (30 mins):")
        for i, suggestion in enumerate(suggestions[:3], 1):
            print(f"{i}. {suggestion['date']} ({suggestion['day_of_week']}) at {suggestion['start_time'].strftime('%H:%M')}")
    
    return {
        'total_available_slots': total_slots,
        'suggestions': suggestions[:3],
        'analysis_complete': True
    }

# Test with your data
if __name__ == "__main__":
    # Your sample data
    user_one_events = [
        {'StartTime': '2025-07-13T18:00:00+05:30', 'EndTime': '2025-07-14T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-14T18:00:00+05:30', 'EndTime': '2025-07-15T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-15T18:00:00+05:30', 'EndTime': '2025-07-16T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-16T18:00:00+05:30', 'EndTime': '2025-07-17T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-17T18:00:00+05:30', 'EndTime': '2025-07-18T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'}
    ]
    
    user_two_events = [
        {'StartTime': '2025-07-13T18:00:00+05:30', 'EndTime': '2025-07-14T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-14T18:00:00+05:30', 'EndTime': '2025-07-15T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-15T09:00:00+05:30', 'EndTime': '2025-07-15T16:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'AMD AI Workshop'},
        {'StartTime': '2025-07-15T18:00:00+05:30', 'EndTime': '2025-07-16T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-16T18:00:00+05:30', 'EndTime': '2025-07-17T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-17T18:00:00+05:30', 'EndTime': '2025-07-18T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-18T18:00:00+05:30', 'EndTime': '2025-07-19T09:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'}
    ]
    
    user_three_events = [
        {'StartTime': '2025-07-13T16:00:00+05:30', 'EndTime': '2025-07-14T07:30:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-14T09:00:00+05:30', 'EndTime': '2025-07-14T10:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': '1V1 Team Member'},
        {'StartTime': '2025-07-14T16:00:00+05:30', 'EndTime': '2025-07-15T07:30:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-15T09:00:00+05:30', 'EndTime': '2025-07-15T16:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'AMD AI Workshop'},
        {'StartTime': '2025-07-15T16:00:00+05:30', 'EndTime': '2025-07-16T07:30:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-16T10:00:00+05:30', 'EndTime': '2025-07-16T11:00:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Customer Call - Quarterly update'},
        {'StartTime': '2025-07-16T16:00:00+05:30', 'EndTime': '2025-07-17T07:30:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-17T16:00:00+05:30', 'EndTime': '2025-07-18T07:30:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'},
        {'StartTime': '2025-07-18T16:00:00+05:30', 'EndTime': '2025-07-19T07:30:00+05:30', 'NumAttendees': 1, 'Attendees': ['SELF'], 'Summary': 'Off Hours'}
    ]
    
    # Combine all user data
    all_users = {
        'userone.amd@gmail.com': user_one_events,
        'usertwo.amd@gmail.com': user_two_events,
        'userthree.amd@gmail.com': user_three_events
    }
    
    # Run analysis
    analysis = analyze_multi_user_availability(all_users)
