# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ClaudOnTheBeach** 🏖️ - A system that enables monitoring and controlling Claude Code (and other dev tools) from anywhere, even the beach! Control your development workflow via Telegram messaging from your phone.

## Architecture

```
Claude Code (local) → Wrapper Script → Combined Server → Telegram Bot → Your Phone
```

### Core Components

1. **Client** - Controls Claude Code via Terminal automation
   - File: `client/claudeOnTheBeach.py`
   - Uses AppleScript to control Terminal.app on macOS
   - Takes screenshots of Claude's output using screencapture
   - Connects to server via WebSocket
   - Generates 6-character pairing codes for secure connection

2. **Server** - All-in-one communication hub
   - File: `server/index.js` (Node.js)
   - WebSocket server for client connections
   - Telegram Bot API integration (built-in)
   - Session management with pairing codes
   - Message forwarding between client and Telegram
   - No separate bot process needed

## Development Commands

### Initial Setup
```bash
# Install server dependencies (Node.js)
cd server && npm install

# Install client dependencies (Python)
cd client && pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN
```

### Running the System
```bash
# Option 1: Start server only (recommended)
./start.sh

# Then manually run client when needed:
python3 client/claudeOnTheBeach.py

# Option 2: Check server status
curl http://localhost:8081/health
```

### Testing
```bash
# Test keyboard commands
python3 test_char_command.py

# Test client functionality
python3 client/claudeOnTheBeach.py --help

# Check server endpoints
curl http://localhost:8081/sessions
```

### Development
```bash
# View server logs in real-time
./start.sh

# Monitor client activity
python3 client/claudeOnTheBeach.py --screenshots-folder ./screenshots

# Debug connection issues
# Check the debug output in terminal
```

## Key Implementation Areas

### Client (`client/claudeOnTheBeach.py`)
- Terminal automation using AppleScript on macOS
- Screenshot capture using screencapture command
- WebSocket client for server communication
- Claude API integration for intelligent screenshot analysis
- Automatic pairing code generation and connection management
- Command queue processing with smart monitoring

### Server (`server/index.js`)
- Express.js HTTP server with WebSocket support
- Telegram Bot API integration (no separate process)
- Session management with pairing codes
- Real-time message forwarding between client and Telegram
- Health check endpoints and session monitoring
- Automatic cleanup of inactive sessions

## Implemented Features ✅

1. **Real-time Progress Monitoring** - Screenshots sent automatically to Telegram
2. **Command Queue** - Sequential command processing from Telegram
3. **Smart Notifications** - Task completion alerts with screenshots
4. **Telegram Commands**:
   - `/screenshot` or `/sc` - Take screenshot immediately
   - `/status` - Current session status and uptime
   - `/char <sequence>` - Send keyboard commands (arrows, enter, escape)
   - `//command` - Run `/command` inside Claude (e.g. `//help`, `//init`)
   - `/help` - Show available commands
   - Any text - Send as command to Claude Code
5. **Pairing System** - Secure 6-character codes for device connection
6. **Intelligent Analysis** - Claude API analyzes screenshots for status and questions
7. **Auto-screenshots** - Captures initial state, questions, and completion

## Technology Stack

- **Wrapper Script**: Python 3 with asyncio and AppleScript
- **Server**: Node.js with Express and WebSocket (ws library)
- **Bot Integration**: Telegram Bot API (node-telegram-bot-api)
- **Screenshot Analysis**: Anthropic Claude API for vision analysis
- **Message Queue**: In-memory queue with asyncio
- **Platform**: macOS only (uses Terminal.app and AppleScript)

## Important Considerations

### Security
- Implement authentication for wrapper-to-server connection
- Use environment variables for API keys and tokens
- Sanitize all user inputs from WhatsApp
- Implement rate limiting on bot commands

### Error Handling
- Gracefully handle claude-code crashes
- Implement reconnection logic for WebSocket
- Queue messages during connection loss
- Provide clear error messages to WhatsApp

### Performance
- Stream output in chunks to avoid memory issues
- Implement message batching for high-frequency updates
- Use connection pooling for database/Redis
- Consider output throttling for mobile readability

## Environment Variables

```bash
# Required: Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Optional: Custom server URL (default: ws://localhost:8081/ws)
SERVER_URL=ws://claudeonthebeach.com:8081/ws

# Optional: Anthropic API for screenshot analysis
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: Server port (default: 8081)
PORT=8081
```

## Future Expansion Plans

- Integration with CI/CD pipelines
- Git operations monitoring
- Server health monitoring
- Multiple tool support beyond Claude Code
- Web dashboard for detailed views
- Voice command support via WhatsApp audio