# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Gerrit Claude Reviewer** - an automated code review system that integrates Claude AI with Gerrit code review platform. The project is written in Python and designed to run as a scheduled service that periodically checks for new code changes in Gerrit and provides AI-powered reviews.

## Key Files Structure

- `gerrit_claude_reviewer.py` - Main application with all core logic
- `config.yaml` - Configuration template with scheduler and filtering settings
- `docker-compose.yml` & `Dockerfile` - Docker deployment files
- `requirements.txt` - Python dependencies (includes selenium for web automation)
- `start.sh` & `stop.sh` - Service management scripts
- `test_connections.py` - Connection testing utility for both Gerrit SSH and Claude web interface
- `README.md` - Detailed installation guide (in Korean)
- Additional test files: `test_env.py`, `test_claude_login.py`, `test_simple_login.py`

## Development Commands

### Initial Setup
```bash
# Create .env file for environment variables
# Set GERRIT_HOST, GERRIT_PORT, GERRIT_USERNAME, SSH_KEY_PATH
# Set CLAUDE_EMAIL, CLAUDE_PASSWORD for web authentication
# Set CHROME_DRIVER_PATH for selenium automation

# Test all connections (Gerrit SSH + Claude web authentication)
python test_connections.py

# For Docker deployment (recommended):
chmod +x start.sh stop.sh
./start.sh

# For direct Python execution:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python gerrit_claude_reviewer.py
```

### Service Management
- **Start service**: `./start.sh` or `docker-compose up -d`
- **Stop service**: `./stop.sh` or `docker-compose down`
- **View logs**: `docker-compose logs -f gerrit-nicolas.choi`
- **Restart**: `docker-compose restart gerrit-nicolas.choi`

## Architecture

### Core Components

1. **GerritAPI** (`gerrit_claude_reviewer.py:48-234`)
   - Handles all Gerrit SSH command interactions
   - Methods: `get_open_changes()`, `get_change_files()`, `get_file_diff()`, `post_review()`
   - Uses SSH keys for authentication and subprocess calls

2. **ClaudeReviewer** (`gerrit_claude_reviewer.py:248-393`)
   - Web-based Claude interface using Selenium automation
   - Requires CLAUDE_EMAIL/CLAUDE_PASSWORD for authentication
   - Automated browser session management with headless Chrome

3. **ReviewTracker** (`gerrit_claude_reviewer.py:394-418`)
   - File-based tracking system to prevent duplicate reviews
   - Stores reviewed change IDs in `reviewed_changes.txt`

4. **Scheduler System**
   - Uses Python `schedule` library for periodic execution
   - Default: runs every 30 minutes + daily at 9:00 and 14:00

### Processing Workflow

1. Query Gerrit for open changes (last 24 hours)
2. Filter files by extension and patterns
3. Skip already-reviewed changes
4. Send code to Claude for review
5. Post review comments back to Gerrit
6. Mark changes as reviewed

### Configuration Structure

The `config.yaml` supports:
- Gerrit SSH connection settings (host, port, username, ssh_key_path)
- Claude API configuration
- Schedule customization
- File filtering rules (extensions, patterns, size limits)
- Project-specific review rules
- Optional notifications (Slack, email)

## Working with the Code

### Adding New Features
- All business logic is in `gerrit_claude_reviewer.py`
- Configuration options go in `config.yaml`
- Environment secrets use `.env` file (automatically loaded with python-dotenv)

### File Filtering Logic
- Review target extensions: `.py`, `.java`, `.js`, `.ts`, `.go`, `.rs`, `.cpp`, `.c`, `.h`
- Excluded patterns: test directories, node_modules, build outputs
- Size limits: 500 lines changed, 100KB file size

### API Integration Points
- **Gerrit SSH API**: Uses SSH authentication with SSH keys for command-line interface
  - SSH commands: `gerrit query`, `gerrit review`, and `scp` for patch files
  - Requires proper SSH key setup and Gerrit account permissions
- **Claude Web Interface**: Uses Selenium WebDriver for browser automation
  - Automated login with email/password credentials
  - Text area interaction for prompt submission and response extraction
  - Requires Chrome/Chromium and ChromeDriver installation

## Important Notes

1. **Web-based Claude Integration**: Uses Selenium automation instead of direct API calls
2. **Scheduler-based**: Not event-driven, runs on fixed schedule (configurable intervals)
3. **Stateless Design**: Uses file tracking (`reviewed_changes.txt`), not database
4. **Korean Documentation**: README.md is in Korean with detailed setup instructions
5. **Docker Deployment**: Primary deployment method uses Docker Compose with Chrome/ChromeDriver
6. **Connection Testing**: Use `python test_connections.py` to verify both Gerrit SSH and Claude web access
