from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Gmail API scope for reading and modifying emails
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailUnreadToolInput(BaseModel):
    """Input schema for GmailUnreadTool."""

    max_results: int = Field(
        default=10, description="Maximum number of unread emails to fetch (default: 10)"
    )


class GmailUnreadTool(BaseTool):
    name: str = "gmail_unread_reader"
    description: str = (
        "Reads the subject lines of unread emails from Gmail. "
        "Returns a list of subjects from unread emails in the inbox."
    )
    args_schema: Type[BaseModel] = GmailUnreadToolInput

    def _get_gmail_service(self):
        """Authenticate and return Gmail API service."""
        creds = None
        token_path = "token.pickle"
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

        service = build("gmail", "v1", credentials=creds)
        return service, None

    def _run(self, max_results: int = 10) -> str:
        """Fetch unread email subjects from Gmail."""
        try:
            service, error = self._get_gmail_service()
            if error:
                return f"Authentication Error: {error}"

            # Query for unread emails in inbox
            results = (
                service.users()
                .messages()
                .list(userId="me", q="is:unread in:inbox", maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])

            if not messages:
                return "No unread emails found."

            subjects = []
            for msg in messages:
                # Get the full message details
                message = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date"],
                    )
                    .execute()
                )

                headers = message.get("payload", {}).get("headers", [])
                subject = "No Subject"
                sender = "Unknown"
                date = "Unknown"

                for header in headers:
                    if header["name"] == "Subject":
                        subject = header["value"]
                    elif header["name"] == "From":
                        sender = header["value"]
                    elif header["name"] == "Date":
                        date = header["value"]

                email_id = msg["id"]
                subjects.append(
                    f"Email ID: {email_id}\nFrom: {sender}\nDate: {date}\nSubject: {subject}\n"
                )

            result = f"Found {len(subjects)} unread email(s):\n\n"
            result += "\n---\n".join(subjects)
            return result

        except Exception as e:
            return f"Error fetching emails: {str(e)}"


# Run standalone for testing
if __name__ == "__main__":
    tool = GmailUnreadTool()
    result = tool._run(max_results=5)
    print(result)
