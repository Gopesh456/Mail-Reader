from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import os
import pickle
import base64
import re
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.utils import parsedate_to_datetime


# Gmail API scope for reading and modifying emails
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Patterns to remove from email body to reduce tokens
DISCLAIMER_PATTERNS = [
    # VIT Disclaimer
    r"Disclaimer:\s*This message was sent from Vellore Institute of Technology\..*?without reading them\.",
    r"Disclaimer:.*?Vellore Institute of Technology.*?without reading them\.",
    # Common email footers
    r"Best [Rr]egards,?\s*[\r\n]+.*?$",
    r"With [Rr]egards,?\s*[\r\n]+.*?$",
    r"Kind [Rr]egards,?\s*[\r\n]+.*?$",
    r"Thanks\s*&?\s*[Rr]egards,?\s*[\r\n]+.*?$",
    r"Warm [Rr]egards,?\s*[\r\n]+.*?$",
    # Confidentiality notices
    r"This email and any files transmitted with it are confidential.*?(?=\n\n|\Z)",
    r"CONFIDENTIALITY NOTICE:.*?(?=\n\n|\Z)",
    # Unsubscribe and footer links
    r"To unsubscribe.*?(?=\n\n|\Z)",
    r"Click here to unsubscribe.*?(?=\n\n|\Z)",
    # Common signatures
    r"Sent from my iPhone",
    r"Sent from my Android",
    r"Get Outlook for.*",
]


def _extract_links(body: str) -> List[str]:
    """Extract important links from email body."""
    if not body:
        return []

    # Pattern to match URLs
    url_pattern = r'https?://[^\s<>"\')]+'
    links = re.findall(url_pattern, body)

    # Filter out common non-important links
    exclude_patterns = [
        r"unsubscribe",
        r"privacy",
        r"terms",
        r"facebook\.com",
        r"twitter\.com",
        r"linkedin\.com",
        r"instagram\.com",
        r"mailto:",
    ]

    filtered_links = []
    for link in links:
        is_excluded = any(
            re.search(pattern, link, re.IGNORECASE) for pattern in exclude_patterns
        )
        if not is_excluded and link not in filtered_links:
            filtered_links.append(link)

    return filtered_links[:5]  # Return max 5 important links


def _build_gmail_link(message_id: str) -> str:
    """Build a Gmail web URL from Message-ID header."""
    if not message_id:
        return ""
    # Remove angle brackets if present
    clean_id = message_id.strip("<>")
    # URL encode the message ID
    from urllib.parse import quote

    encoded_id = quote(clean_id, safe="")
    return f"https://mail.google.com/mail/u/2/#search/rfc822msgid:{encoded_id}"


def _clean_email_body(body: str) -> str:
    """Remove disclaimers, signatures, and unnecessary content to reduce tokens."""
    if not body:
        return body

    cleaned = body

    # Remove disclaimer patterns
    for pattern in DISCLAIMER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    # Remove excessive whitespace and newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # Max 2 newlines
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)  # Max 1 space
    cleaned = re.sub(
        r"^\s+", "", cleaned, flags=re.MULTILINE
    )  # Leading whitespace per line

    # Remove empty lines with just dashes or equals
    cleaned = re.sub(r"\n[-=_]{3,}\n", "\n", cleaned)

    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned


class EmailItem(BaseModel):
    """Schema for a single email item."""

    from_address: str = Field(..., description="The sender's email address or name")
    date: str = Field(..., description="The date and time the email was sent")
    subjects: str = Field(..., description="The subject line of the email")


class GmailBodyReaderInput(BaseModel):
    """Input schema for GmailBodyReaderTool."""

    important_emails: List[EmailItem] = Field(
        ...,
        description="List of email objects with from_address, date, and subjects fields",
    )


class GmailBodyReaderTool(BaseTool):
    name: str = "gmail_body_reader"
    description: str = (
        "Fetches the full body content of emails based on their subject, sender, and date. "
        "Input should be a list of email objects with from_address, date, and subjects fields. "
        "Returns the complete email details including body content."
    )
    args_schema: Type[BaseModel] = GmailBodyReaderInput

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

    def _get_email_body(self, payload) -> str:
        """Extract the body from email payload."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    if part["body"].get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )
                        break
                elif mime_type == "text/html" and not body:
                    if part["body"].get("data"):
                        html_body = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                        # Strip HTML tags for plain text
                        body = re.sub(r"<[^>]+>", "", html_body)
                elif mime_type.startswith("multipart/"):
                    # Recursively check nested parts
                    body = self._get_email_body(part)
                    if body:
                        break

        return body.strip()

    def _search_email(self, service, subject: str, from_addr: str) -> str:
        """Search for a specific email and return its body."""
        try:
            # Build search query
            # Escape special characters in subject
            clean_subject = subject.replace('"', '\\"')
            query = f'subject:"{clean_subject}"'

            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=10)
                .execute()
            )

            messages = results.get("messages", [])

            if not messages:
                return f"No email found with subject: {subject}"

            # Find the matching email
            for msg in messages:
                message = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )

                headers = message.get("payload", {}).get("headers", [])
                msg_subject = ""
                msg_from = ""
                msg_date = ""
                msg_id = ""

                for header in headers:
                    if header["name"].lower() == "subject":
                        msg_subject = header["value"]
                    elif header["name"].lower() == "from":
                        msg_from = header["value"]
                    elif header["name"].lower() == "date":
                        msg_date = header["value"]
                    elif header["name"].lower() == "message-id":
                        msg_id = header["value"]

                # Check if this is the right email (subject match)
                if subject.lower() in msg_subject.lower():
                    body = self._get_email_body(message.get("payload", {}))
                    # Extract links before cleaning
                    links = _extract_links(body) if body else []
                    # Clean the body to reduce tokens
                    cleaned_body = (
                        _clean_email_body(body) if body else "No body content found"
                    )
                    # Build Gmail web link
                    gmail_link = _build_gmail_link(msg_id)

                    return {
                        "from_address": msg_from,
                        "date": msg_date,
                        "subject": msg_subject,
                        "body": cleaned_body,
                        "gmail_link": gmail_link,
                        "links": links,
                    }

            return f"No matching email found for subject: {subject}"

        except Exception as e:
            return f"Error searching email: {str(e)}"

    def _run(self, important_emails: List[Dict[str, Any]]) -> str:
        """Fetch email bodies for the given list of emails."""
        try:
            service, error = self._get_gmail_service()
            if error:
                return f"Authentication Error: {error}"

            results = []

            for email_item in important_emails:
                # Handle both dict and EmailItem objects
                if isinstance(email_item, dict):
                    subject = email_item.get("subjects", "")
                    from_addr = email_item.get("from_address", "")
                else:
                    subject = email_item.subjects
                    from_addr = email_item.from_address

                email_data = self._search_email(service, subject, from_addr)

                if isinstance(email_data, dict):
                    # Build links section
                    links_section = ""
                    if email_data.get("links"):
                        links_section = "\n📎 LINKS IN EMAIL:\n" + "\n".join(
                            f"  • {link}" for link in email_data["links"]
                        )

                    gmail_link_section = ""
                    if email_data.get("gmail_link"):
                        gmail_link_section = (
                            f"\n🔗 OPEN IN GMAIL: {email_data['gmail_link']}"
                        )

                    results.append(
                        f"═══════════════════════════════════════\n"
                        f"FROM: {email_data['from_address']}\n"
                        f"DATE: {email_data['date']}\n"
                        f"SUBJECT: {email_data['subject']}\n"
                        f"{gmail_link_section}\n"
                        f"───────────────────────────────────────\n"
                        f"BODY:\n{email_data['body']}"
                        f"{links_section}\n"
                    )
                else:
                    results.append(f"Error for '{subject}': {email_data}\n")

            return "\n".join(results)

        except Exception as e:
            return f"Error fetching emails: {str(e)}"


# Run standalone for testing
if __name__ == "__main__":
    tool = GmailBodyReaderTool()

    # Test with sample data
    test_input = {
        "important_emails": [
            {
                "from_address": "COE Vellore via B.Tech. - Comp  Sci Engg 2025 Group, Vellore Campus",
                "date": "Fri, 28 Nov 2025 15:33:45 +0530",
                "subjects": "FAT Instructions for Basic Engineering (BAEEE101) course",
            }
        ]
    }

    result = tool._run(important_emails=test_input["important_emails"])
    print(result)
