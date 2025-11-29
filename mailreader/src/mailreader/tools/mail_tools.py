from crewai.tools import BaseTool
from typing import Type, List, Union, Any
from pydantic import BaseModel, Field, field_validator
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import pickle


# Gmail API scope for modifying emails
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class MarkEmailsAsReadInput(BaseModel):
    """Input schema for MarkEmailsAsReadTool."""

    email_ids: Any = Field(..., description="List of email IDs to mark as read")

    @field_validator("email_ids", mode="before")
    @classmethod
    def extract_email_ids(cls, v):
        """Handle case where LLM passes dict instead of list."""
        if isinstance(v, dict) and "email_ids" in v:
            return v["email_ids"]
        return v


class MarkEmailsAsReadTool(BaseTool):
    name: str = "mark_emails_as_read"
    description: str = (
        "Marks the specified emails as read in Gmail. "
        "Accepts a list of email IDs that have been analyzed."
    )
    args_schema: Type[BaseModel] = MarkEmailsAsReadInput

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
                    raise FileNotFoundError(
                        "credentials.json not found. Please download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        return build("gmail", "v1", credentials=creds)

    def _run(self, email_ids: List[str]) -> str:
        """Mark emails as read."""
        if not email_ids:
            return "No email IDs provided to mark as read."

        try:
            service = self._get_gmail_service()

            # Batch modify to remove UNREAD label
            service.users().messages().batchModify(
                userId="me", body={"ids": email_ids, "removeLabelIds": ["UNREAD"]}
            ).execute()

            return f"Successfully marked {len(email_ids)} email(s) as read."

        except Exception as e:
            return f"Error marking emails as read: {str(e)}"
