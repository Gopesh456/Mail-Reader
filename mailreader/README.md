# 📧 Mail Reader

An intelligent AI-powered email assistant that automatically analyzes your Gmail inbox, identifies important emails, extracts action items, sets reminders, and sends push notifications for urgent matters. Built with [CrewAI](https://crewai.com) multi-agent framework.

## ✨ Features

- **Smart Email Analysis** - Automatically identifies important emails from your unread inbox
- **Priority Filtering** - Focuses on academic matters (quizzes, tests, assignments, deadlines) while filtering out promotional content
- **Body Content Extraction** - Reads and summarizes email content with key action items
- **Automated Reminders** - Sets calendar reminders for time-sensitive items like tests and deadlines
- **Push Notifications** - Sends instant notifications via Pushover for urgent matters
- **Auto Mark as Read** - Marks processed emails as read to prevent re-processing

## 🤖 AI Agents

The system uses three specialized AI agents:

| Agent               | Role                                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| **Subject Analyst** | Analyzes email subjects to identify important/urgent emails                |
| **Body Analyst**    | Reads email content, extracts action items, sets reminders & notifications |
| **Mail Manager**    | Marks analyzed emails as read after successful processing                  |

## 🛠️ Installation

### Prerequisites

- Python >=3.10 <3.14
- [UV](https://docs.astral.sh/uv/) package manager
- Gmail API credentials
- Pushover account (for push notifications)

### Setup

1. **Install UV** (if not already installed):

   ```bash
   pip install uv
   ```

2. **Navigate to project directory and install dependencies**:

   ```bash
   cd mailreader
   crewai install
   ```

3. **Configure Gmail API**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project and enable Gmail API
   - Create OAuth 2.0 credentials (Desktop App)
   - Download `credentials.json` and place it in the project root

4. **Configure environment variables**:
   Create a `.env` file with:
   ```env
   GROQ_API_KEY=your_groq_api_key
   PUSHOVER_USER_KEY=your_pushover_user_key
   PUSHOVER_API_TOKEN=your_pushover_api_token
   ```

## 🚀 Usage

Run the email analysis crew:

```bash
crewai run
```

On first run, a browser window will open for Gmail authentication. After authorization, the system will:

1. Fetch up to 10 unread emails
2. Analyze subjects and filter important ones
3. Read email bodies and extract key information
4. Set reminders for deadlines/tests
5. Send push notifications for urgent items
6. Mark all processed emails as read
7. Generate a `report.md` with analysis results

## 📁 Project Structure

```
mailreader/
├── credentials.json          # Gmail API credentials
├── token.pickle             # Gmail auth token (auto-generated)
├── report.md                # Generated analysis report
├── pyproject.toml           # Project dependencies
├── knowledge/
│   └── user_preference.txt  # User preferences for analysis
└── src/mailreader/
    ├── crew.py              # CrewAI agents & tasks setup
    ├── main.py              # Entry point
    ├── config/
    │   ├── agents.yaml      # Agent configurations
    │   └── tasks.yaml       # Task definitions
    └── tools/
        ├── subjectReaderTool.py   # Gmail subject reader
        ├── bodyReaderTool.py      # Gmail body reader
        ├── mail_tools.py          # Mark emails as read
        ├── reminderTool.py        # Calendar reminder tool
        └── pushNoti.py            # Pushover notifications
```

## ⚙️ Configuration

### Customize Email Filtering

Edit `src/mailreader/config/agents.yaml` to modify:

- Priority keywords and topics
- Emails to ignore (promotions, workshops, etc.)
- Student year filtering

### Customize Tasks

Edit `src/mailreader/config/tasks.yaml` to modify:

- Number of emails to fetch
- Reminder behavior
- Notification triggers

## 📱 Push Notifications

Push notifications are sent via [Pushover](https://pushover.net/). To set up:

1. Create a Pushover account
2. Create an application to get API token
3. Add credentials to `.env` file

## 🔒 Permissions

The app requires the following Gmail scope:

- `gmail.modify` - Read emails and mark as read

## 📄 License

MIT License

## 🙏 Acknowledgments

- [CrewAI](https://crewai.com) - Multi-agent AI framework
- [Groq](https://groq.com) - LLM inference
- [Google Gmail API](https://developers.google.com/gmail/api)
- [Pushover](https://pushover.net/) - Push notifications
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
