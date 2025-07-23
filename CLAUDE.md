# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Gerrit Claude Reviewer** - an automated code review system that integrates Claude AI with Gerrit code review platform. The project is written in Python and designed to run as a scheduled service that periodically checks for new code changes in Gerrit and provides AI-powered reviews.

## Key Files Structure

**IMPORTANT**: The main codebase is currently consolidated in `all.txt`. This file contains multiple separate files that need to be extracted:
- `gerrit_claude_reviewer.py` - Main application
- `config.yaml` - Configuration template
- `Dockerfile` & `docker-compose.yml` - Docker deployment files
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template
- `start.sh` & `stop.sh` - Service management scripts
- `README.md` - Installation guide (in Korean)

## Development Commands

### Initial Setup
```bash
# Copy environment configuration
cp .env.example .env
# Edit .env with actual credentials (automatically loaded by app)

# Test connections first
python test_connections.py

# For Docker deployment:
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
- **View logs**: `docker-compose logs -f gerrit-claude-reviewer`
- **Restart**: `docker-compose restart gerrit-claude-reviewer`

## Architecture

### Core Components

1. **GerritAPI** (`gerrit_claude_reviewer.py:48-234`)
   - Handles all Gerrit SSH command interactions
   - Methods: `get_open_changes()`, `get_change_files()`, `get_file_diff()`, `post_review()`
   - Uses SSH keys for authentication and subprocess calls

2. **ClaudeReviewer** (`gerrit_claude_reviewer.py:154-202`)
   - Interfaces with Claude API for code analysis
   - Configurable review aspects (bugs, performance, security, style, testing)

3. **ReviewTracker** (`gerrit_claude_reviewer.py:204-227`)
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
- Gerrit API: Uses SSH authentication with SSH keys for command-line interface
- Claude API: Uses Anthropic's messages API with API key
- SSH commands include: `gerrit query`, `gerrit review`, and `scp` for patch files

## Important Notes

1. **No Test Suite**: This project doesn't include tests
2. **Scheduler-based**: Not event-driven, runs on fixed schedule
3. **Stateless Design**: Uses file tracking, not database
4. **Korean Documentation**: README.md is in Korean
5. **Docker Deployment**: Primary deployment method uses Docker Compose