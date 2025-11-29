from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
from datetime import datetime
from py_pushover_simple import pushover


class PushNotificationInput(BaseModel):
    """Input schema for PushNotificationTool."""

    subject: str = Field(
        ...,
        description="The email subject line - this will be used as the notification title",
    )
    description: str = Field(
        ..., description="The description/message content of the notification"
    )
    date: str = Field(
        default="",
        description="The date related to the notification (optional, format: YYYY-MM-DD)",
    )
    time: str = Field(
        default="",
        description="The time related to the notification (optional, format: HH:MM)",
    )
    gmail_link: str = Field(
        default="",
        description="The Gmail link to open the email in browser (optional)",
    )


class PushNotificationTool(BaseTool):
    name: str = "push_notification_tool"
    description: str = (
        "Sends a push notification to the user's phone using Pushover API. "
        "Use this tool to alert the user about important or urgent information from emails. "
        "Input requires: subject (used as title), description, and optionally date, time, and gmail_link."
    )
    args_schema: Type[BaseModel] = PushNotificationInput

    def _run(
        self,
        subject: str,
        description: str,
        date: str = "",
        time: str = "",
        gmail_link: str = "",
    ) -> str:
        """Send a push notification via Pushover."""
        try:
            # Get API credentials from environment
            api_token = os.getenv("PUSHOVER_API_TOKEN")
            user_key = os.getenv("PUSHOVER_USER_KEY")

            if not api_token or not user_key:
                return "Error: PUSHOVER_API_TOKEN or PUSHOVER_USER_KEY not found in environment variables."

            # Build the message with date and time if provided
            message_parts = [description]

            if date or time:
                datetime_str = ""
                if date:
                    datetime_str += f"📅 Date: {date}"
                if time:
                    if datetime_str:
                        datetime_str += f" | ⏰ Time: {time}"
                    else:
                        datetime_str += f"⏰ Time: {time}"
                message_parts.append(datetime_str)

            # Add Gmail link if provided
            if gmail_link:
                message_parts.append(f"\n🔗 Open in Gmail: {gmail_link}")

            # Add current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message_parts.append(f"\n📨 Sent: {current_time}")

            full_message = "\n".join(message_parts)

            # Send the push notification - use subject as title
            p = pushover.Pushover()
            p.user = os.getenv("PUSHOVER_USER_KEY")
            p.token = os.getenv("PUSHOVER_API_TOKEN")
            p.title = subject
            p.send_message(full_message)

            return (
                f"✅ Push notification sent successfully!\n"
                f"Subject/Title: {subject}\n"
                f"Message: {description}\n"
                f"Date: {date if date else 'N/A'}\n"
                f"Time: {time if time else 'N/A'}\n"
                f"Gmail Link: {gmail_link if gmail_link else 'N/A'}"
            )

        except Exception as e:
            return f"Error sending push notification: {str(e)}"


# Run standalone for testing
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    tool = PushNotificationTool()

    # Test with sample data
    result = tool._run(
        subject="FAT Instructions for Basic Engineering (BAEEE101) course",
        description="Basic Engineering FAT exam is scheduled for tomorrow. Make sure to prepare for Module 1 & 2 (Electrical) and Module 3 & 4 (Mechanical).",
        date="2025-11-29",
        time="09:30",
        gmail_link="https://mail.google.com/mail/u/0/#search/rfc822msgid:example123",
    )
    print(result)
