from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai import LLM
import os
from pydantic import BaseModel, Field
from mailreader.tools.subjectReaderTool import GmailUnreadTool
from mailreader.tools.bodyReaderTool import GmailBodyReaderTool
from mailreader.tools.pushNoti import PushNotificationTool
from mailreader.tools.reminderTool import ReminderTool
from mailreader.tools.mail_tools import MarkEmailsAsReadTool


class importantEmailSubjects(BaseModel):
    """Schema for important email subjects."""

    email_id: str = Field(..., description="Unique email ID from Gmail")
    from_address: str = Field(..., description="Email address of the recipient")
    date: str = Field(..., description="Date of the emails that requires action")
    subjects: str = Field(..., description="subject of the email that requires action")


class importantEmailSubjectsList(BaseModel):
    """Schema for list of important email subjects."""

    important_emails: List[importantEmailSubjects] = Field(
        ..., description="List of important email subjects that require action"
    )
    all_email_ids: List[str] = Field(
        ..., description="Complete list of all analyzed email IDs for marking as read"
    )


@CrewBase
class MailreaderCrew:
    """Mailreader crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    agents: List[BaseAgent]
    tasks: List[Task]

    def __init__(self):
        # Define different LLMs for different agents
        self.subject_analyst_llm = LLM(
            model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
            api_key=os.getenv("GROQ_API_KEY"),
        )
        self.body_analyst_llm = LLM(
            model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY")
        )

    @agent
    def subject_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["subject_analyst"],  # type: ignore[index]
            verbose=True,
            tools=[GmailUnreadTool()],
            llm=self.subject_analyst_llm,
        )

    @agent
    def body_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["body_analyst"],  # type: ignore[index]
            verbose=True,
            tools=[GmailBodyReaderTool(), ReminderTool(), PushNotificationTool()],
            llm=self.body_analyst_llm,
        )

    @agent
    def mail_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["mail_manager"],
            tools=[MarkEmailsAsReadTool()],
            verbose=True,
        )

    @task
    def subject_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["subject_analysis_task"],
            output_pydantic=importantEmailSubjectsList,  # type: ignore[index]
        )

    @task
    def body_analyst_task(self) -> Task:
        return Task(
            config=self.tasks_config["body_analyst_task"],  # type: ignore[index]
            output_file="report.md",
            input_pydantic=importantEmailSubjectsList,  # type: ignore[index]
        )

    @task
    def mark_emails_read_task(self) -> Task:
        return Task(
            config=self.tasks_config["mark_emails_read_task"],
            agent=self.mail_manager(),
            context=[self.subject_analysis_task()],  # Gets email_ids from previous task
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Mailreader crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=[
                self.subject_analysis_task(),
                self.body_analyst_task(),
                self.mark_emails_read_task(),  # Add as final task
            ],  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
