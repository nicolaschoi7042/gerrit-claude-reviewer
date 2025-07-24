# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Gerrit Claude Reviewer** - an automated code review system that integrates Claude AI with Gerrit code review platform. The project is written in Python and designed to run as a scheduled service that periodically checks for new code changes in Gerrit and provides AI-powered reviews using Claude CLI API.

## Key Files Structure

- `gerrit_claude_reviewer.py` - Main application with all core logic
- `config.yaml` - Configuration template with scheduler and filtering settings
- `docker-compose.yml` & `Dockerfile` - Docker deployment files
- `requirements.txt` - Python dependencies
- `startup.sh` & `install.sh` - Service management and installation scripts
- `tests/` - Test directory containing:
  - `test_connections.py` - Connection testing utility for Gerrit SSH and Claude CLI
  - `test_claude_api.py` - Claude CLI API testing
  - `test_integrated_review.py` - Full integration testing
- `README.md` - Detailed installation guide (in Korean)

## Development Commands

### Initial Setup
```bash
# Create .env file for environment variables
# Set GERRIT_HOST, GERRIT_PORT, GERRIT_USERNAME, SSH_KEY_PATH
# Claude CLI API authentication will be handled automatically

# Test all connections (Gerrit SSH + Claude CLI API)
python tests/test_connections.py

# For Docker deployment (recommended):
chmod +x startup.sh install.sh
./startup.sh

# For direct Python execution:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Install Claude CLI globally: npm install -g @anthropic-ai/claude-code
python gerrit_claude_reviewer.py
```

### Service Management
- **Start service**: `./startup.sh` or `docker compose up -d gerrit-nicolas.choi`
- **Stop service**: `docker compose down`
- **View logs**: `docker compose logs -f gerrit-nicolas.choi`
- **Restart**: `docker compose restart gerrit-nicolas.choi`
- **Test connections**: `docker compose exec gerrit-nicolas.choi python tests/test_integrated_review.py`

## Architecture

### Core Components

1. **GerritAPI** (`gerrit_claude_reviewer.py:52-410`)
   - Handles all Gerrit SSH command interactions
   - Methods: `get_open_changes()`, `get_change_files()`, `get_file_diff()`, `post_review()`
   - Uses SSH keys for authentication and subprocess calls
   - Enhanced file summary with `_get_enhanced_file_summary()` providing detailed context

2. **ClaudeReviewer** (`gerrit_claude_reviewer.py:412-523`)
   - Claude CLI API integration using subprocess calls
   - Automated authentication through Claude CLI
   - Handles JSON response parsing and timeout management

3. **ReviewTracker** (`gerrit_claude_reviewer.py:525-549`)
   - File-based tracking system to prevent duplicate reviews
   - Stores reviewed change IDs in `reviewed_changes.txt`

4. **Scheduler System**
   - Uses Python `schedule` library for periodic execution
   - Default: runs every 30 minutes + daily at 9:00 and 14:00

### Processing Workflow

1. Query Gerrit for open changes using `status:open NOT is:wip` filter
2. Filter files by extension and patterns (expanded to 20+ file types)
3. Skip already-reviewed changes using ReviewTracker
4. Generate enhanced file summaries with project context and change analysis
5. Send structured prompts to Claude CLI API for code review
6. Post review comments back to Gerrit with AI attribution
7. Mark changes as reviewed in tracking file

### Configuration Structure

The `.env` file supports:
- Gerrit SSH connection settings (GERRIT_HOST, GERRIT_PORT, GERRIT_USERNAME, SSH_KEY_PATH)
- Schedule customization (SCHEDULE_MINUTES, SCHEDULE_MORNING, SCHEDULE_AFTERNOON)
- File filtering rules (MAX_LINES_CHANGED=5000, MAX_FILE_SIZE_KB=1000)
- Query settings (GERRIT_QUERY_AGE - leave empty for all open changes)
- Logging configuration (LOG_FILE, LOG_LEVEL)
- API timing (API_DELAY_SECONDS, CLAUDE_CLI_TIMEOUT)

## Working with the Code

### Adding New Features
- All business logic is in `gerrit_claude_reviewer.py`
- Configuration options go in `config.yaml`
- Environment secrets use `.env` file (automatically loaded with python-dotenv)

### File Filtering Logic
- Review target extensions: `.py`, `.java`, `.js`, `.ts`, `.go`, `.rs`, `.cpp`, `.c`, `.h`, `.sh`, `.yaml`, `.json`, `.xml`, `.sql`, `.md`, `.kt`, `.scala`, `.rb`, `.php`, `.swift`, `.dart` and more
- Excluded patterns: test directories, node_modules, build outputs, generated files
- Size limits: 5000 lines changed, 1000KB file size (configurable via MAX_LINES_CHANGED, MAX_FILE_SIZE_KB)

### API Integration Points
- **Gerrit SSH API**: Uses SSH authentication with SSH keys for command-line interface
  - SSH commands: `gerrit query`, `gerrit review` for change management
  - Enhanced file analysis using `query --files --current-patch-set` commands
  - Requires proper SSH key setup and Gerrit account permissions
- **Claude CLI API**: Uses official Claude CLI for AI integration
  - Command: `claude --print` for non-interactive API calls
  - JSON response parsing with fallback to raw text
  - Automated authentication through Claude CLI session management
  - Requires Node.js and `npm install -g @anthropic-ai/claude-code`

## Important Notes

1. **Claude CLI Integration**: Uses official Claude CLI API instead of web automation
2. **Scheduler-based**: Not event-driven, runs on fixed schedule (configurable intervals)
3. **Stateless Design**: Uses file tracking (`reviewed_changes.txt`), not database
4. **Enhanced Diff Analysis**: Provides detailed file context including project info, change patterns, and recommendations
5. **Expanded File Support**: Reviews 20+ file types including scripts, configs, and documentation
6. **Korean Documentation**: README.md is in Korean with detailed setup instructions
7. **Docker Deployment**: Primary deployment method uses Docker Compose with Node.js and Claude CLI
8. **Connection Testing**: Use `python tests/test_integrated_review.py` to verify all components

## Recent Improvements

### Enhanced File Summary System
- **Problem Fixed**: Claude was receiving only basic file statistics, leading to generic reviews
- **Solution**: Implemented `_get_enhanced_file_summary()` function providing:
  - Project name and commit message context
  - File type analysis and change pattern detection
  - Scale analysis (small/medium/large changes)
  - Contextual recommendations based on file type and change patterns
- **Result**: Claude now receives meaningful context for generating specific, actionable code reviews

### Query Optimization
- Updated Gerrit query from `status:open` to `status:open NOT is:wip` to match web interface exactly
- Handles non-WIP (Work In Progress) changes for production-ready reviews
