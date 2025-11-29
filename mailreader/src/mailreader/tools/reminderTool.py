from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Google Calendar API scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class ReminderToolInput(BaseModel):
    """Input schema for ReminderTool."""

    title: str = Field(..., description="The title of the event/reminder")
    date: str = Field(
        ..., description="The date of the event in format YYYY-MM-DD (e.g., 2025-11-30)"
    )
    time: str = Field(
        ..., description="The time of the event in 24-hour format HH:MM (e.g., 14:30)"
    )
    subject: str = Field(
        default="",
        description="The email subject line to include in the event description",
    )
    description: str = Field(
        default="", description="Additional description or details for the event"
    )
    gmail_link: str = Field(
        default="", description="Gmail link to open the related email in browser"
    )
    email_links: str = Field(
        default="",
        description="Important links from the email (e.g., exam links, registration links)",
    )


class ReminderTool(BaseTool):
    name: str = "reminder_tool"
    description: str = (
        "Creates a calendar event with reminder alarms using Google Calendar API. "
        "The event will have pop-up notification reminders at 30 minutes and 10 minutes before the event. "
        "Input requires: title, date (YYYY-MM-DD), time (HH:MM in 24-hour format), and optional description, gmail_link, and email_links."
    )
    args_schema: Type[BaseModel] = ReminderToolInput

    def _get_calendar_service(self):
        """Authenticate and return Google Calendar API service."""
        creds = None
        token_path = "calendar_token.pickle"
        credentials_path = "credentials.json"

        # Load existing credentials if available
        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        # Refresh or get new credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    return (
                        None,
                        "credentials.json not found. Please download it from Google Cloud Console.",
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        service = build("calendar", "v3", credentials=creds)
        return service, None

    def _run(
        self,
        title: str,
        date: str,
        time: str,
        subject: str = "",
        description: str = "",
        gmail_link: str = "",
        email_links: str = "",
    ) -> str:
        """Create a calendar event with reminders."""
        try:
            service, error = self._get_calendar_service()
            if error:
                return f"Authentication Error: {error}"

            # Parse date and time
            try:
                event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            except ValueError:
                return f"Invalid date/time format. Use date: YYYY-MM-DD and time: HH:MM (24-hour format)"

            # Set event end time (1 hour after start by default)
            end_datetime = event_datetime + timedelta(hours=1)

            # Get timezone (default to IST for India)
            timezone = "Asia/Kolkata"

            # Build enhanced description with subject and links
            full_description = ""
            if subject:
                full_description += f"📩 Email Subject: {subject}\n\n"
            if description:
                full_description += f"{description}"
            if gmail_link:
                full_description += f"\n\n📧 Open Email: {gmail_link}"
            if email_links:
                full_description += f"\n\n🔗 Important Links:\n{email_links}"

            # Create the event
            event = {
                "summary": title,
                "description": full_description,
                "start": {
                    "dateTime": event_datetime.isoformat(),
                    "timeZone": timezone,
                },
                "end": {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": timezone,
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 30},  # 30 minutes before
                        {"method": "popup", "minutes": 10},  # 10 minutes before
                    ],
                },
            }

            # Insert the event into the calendar
            created_event = (
                service.events().insert(calendarId="primary", body=event).execute()
            )

            return (
                f"✅ Reminder created successfully!\n"
                f"Title: {title}\n"
                f"Date: {date}\n"
                f"Time: {time}\n"
                f"Description: {description if description else 'N/A'}\n"
                f"Gmail Link: {gmail_link if gmail_link else 'N/A'}\n"
                f"Email Links: {email_links if email_links else 'N/A'}\n"
                f"Reminders: 30 min and 10 min before\n"
                f"Event Link: {created_event.get('htmlLink', 'N/A')}"
            )

        except Exception as e:
            return f"Error creating reminder: {str(e)}"


# Run standalone for testing
if __name__ == "__main__":
    tool = ReminderTool()

    # Test with sample data
    result = tool._run(
        title="Test Quiz Reminder",
        date="2025-11-30",
        time="10:00",
        description="Basic Engineering FAT exam - Module 1 & 2",
    )
    print(result)
