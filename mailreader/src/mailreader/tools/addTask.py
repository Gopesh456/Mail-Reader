from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import pickle
from datetime import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Google Tasks API scope
SCOPES = ["https://www.googleapis.com/auth/tasks"]


class AddTaskInput(BaseModel):
    """Input schema for AddTaskTool."""

    title: str = Field(..., description="The title of the task")
    date: str = Field(
        ...,
        description="The due date of the task in format YYYY-MM-DD (e.g., 2025-11-30)",
    )
    description: str = Field(
        default="", description="Additional notes or details for the task"
    )


class AddTaskTool(BaseTool):
    name: str = "add_task_tool"
    description: str = (
        "Creates a task in Google Tasks with a due date. "
        "The task will appear in the Google Tasks app with reminders. "
        "Input requires: title, date (YYYY-MM-DD format), and optional description."
    )
    args_schema: Type[BaseModel] = AddTaskInput

    def _get_tasks_service(self):
        """Authenticate and return Google Tasks API service."""
        creds = None
        token_path = "tasks_token.pickle"
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

        service = build("tasks", "v1", credentials=creds)
        return service, None

    def _get_or_create_tasklist(self, service, list_name: str = "Mail Reader Tasks"):
        """Get or create a task list for the app."""
        try:
            # List all task lists
            results = service.tasklists().list().execute()
            task_lists = results.get("items", [])

            # Check if our list already exists
            for task_list in task_lists:
                if task_list.get("title") == list_name:
                    return task_list.get("id")

            # Create a new task list if it doesn't exist
            new_list = service.tasklists().insert(body={"title": list_name}).execute()
            return new_list.get("id")

        except Exception as e:
            # Fall back to the default task list
            return "@default"

    def _run(self, title: str, date: str, description: str = "") -> str:
        """Create a task in Google Tasks."""
        try:
            service, error = self._get_tasks_service()
            if error:
                return f"Authentication Error: {error}"

            # Parse and validate date
            try:
                due_date = datetime.strptime(date, "%Y-%m-%d")
                # Google Tasks API requires RFC 3339 format for due date
                due_date_rfc3339 = due_date.strftime("%Y-%m-%dT00:00:00.000Z")
            except ValueError:
                return f"Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-30)"

            # Get or create the task list
            tasklist_id = self._get_or_create_tasklist(service)

            # Create the task
            task = {
                "title": title,
                "notes": description,
                "due": due_date_rfc3339,
            }

            # Insert the task
            created_task = (
                service.tasks().insert(tasklist=tasklist_id, body=task).execute()
            )

            return (
                f"✅ Task created successfully!\n"
                f"Title: {title}\n"
                f"Due Date: {date}\n"
                f"Description: {description if description else 'N/A'}\n"
                f"Task ID: {created_task.get('id', 'N/A')}"
            )

        except Exception as e:
            return f"Error creating task: {str(e)}"


# Run standalone for testing
if __name__ == "__main__":
    tool = AddTaskTool()

    # Test with sample data
    result = tool._run(
        title="Submit Assignment",
        date="2025-12-01",
        description="Complete and submit the Basic Engineering assignment before deadline.",
    )
    print(result)
