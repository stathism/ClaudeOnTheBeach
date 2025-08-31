# 🏖️ ClaudeOnTheBeach 🌊

<p align="center">
  <img src="ClaudeOnTheBeach.png" alt="ClaudeOnTheBeach Logo" width="600">
</p>

Control Claude Code from anywhere - even the beach! Watch output in real-time and send commands remotely via Telegram.

**Why code from the office when you can code from the sand?** 🏝️
🇬🇷✨

## 🌊 Features

- 🏄 **Remote Control** - Control Claude from anywhere with Telegram
- 📸 **Screenshots** - Take terminal screenshots remotely
- 🎬 **Video Recording** - 20-minute rolling recording buffer
- 🧠 **Smart Detection** - Intelligent task completion and question detection
- 🎯 **Task Classification** - Automatic task type recognition
- 🛡️ **Stable System** - Robust recording and error handling

## 📋 Prerequisites

- **Python 3** with pip
- **Telegram** account
- **[Claude Code CLI](https://docs.anthropic.com/claude/docs/claude-code)** installed
- **macOS** (client only - server runs on any OS)

## 🛠️ Quick Setup

### 1. Install Dependencies
```bash
# Install client dependencies
cd client && pip install -r requirements.txt && cd ..
```

### 2. Configure Environment (Optional)
```bash
# Create .env file for custom server (optional - uses Railway deployment by default)
echo "SERVER_URL=wss://claudeonthebeach-production.up.railway.app/ws" > .env

# Optional: Add Claude API key for intelligent analysis
echo "ANTHROPIC_API_KEY=your_claude_api_key" >> .env
```

## 🚀 Quick Start

### Run the Client
```bash
python3 client/claudeOnTheBeach.py

# Optional: Specify directory
python3 client/claudeOnTheBeach.py --directory ~/myproject

# Optional: Use custom server
python3 client/claudeOnTheBeach.py --server ws://localhost:8081/ws
```

### Connect via Telegram
1. Find @ClaudeOnTheBeach_bot on Telegram
2. Send `/start`
3. Send the pairing code from terminal
4. Start controlling Claude remotely!

## 📱 Available Commands

### Basic Commands
- `/s` or `/sc` - Take screenshot
- `/r` or `/rec` - Get 20-minute recording
- `/t` or `/status` - Check connection
- `/h` or `/help` - Show all commands
- `/d` or `/disconnect` - End session

### Navigation Commands
- `/c vv>e` - Send keyboard commands (down, down, right, enter)
- `//help` - Run Claude's help command
- Any text - Send to Claude as input







## 🐛 Troubleshooting

### Bot Not Responding
- Ensure you're using @ClaudeOnTheBeach_bot on Telegram
- Try `/start` command in Telegram
- Check your internet connection

## 🔒 Security

- Pairing codes expire after 30 minutes
- Sessions auto-cleanup after 2 hours
- No sensitive data stored
- All communication is session-based
- **Check out the server code**: [server/index.js](server/index.js) - Full transparency on how your data is handled

## 🛠️ For Developers

Want to run your own server? See [`server/README.md`](server/README.md) for detailed setup instructions.

**💡 Server Platform Support:**
- ✅ **Windows** - Full Node.js support
- ✅ **macOS** - Full Node.js support  
- ✅ **Linux** - Full Node.js support
- ✅ **Docker** - Cross-platform deployment
- ✅ **Cloud platforms** - Railway, Heroku, AWS, etc.

## 🎉 Why This is Awesome

Imagine this: You're lounging on a beautiful Greek beach 🏖️, sipping your frappé ☕, and suddenly you remember you need to check on that Python script you left running. Instead of rushing back to your laptop, you just pull out your phone and:

- 📱 **Check the output** - See what Claude is doing in real-time
- 🎬 **Watch the recording** - See the last 20 minutes of activity
- 📸 **Take a screenshot** - Capture the current state
- ⌨️ **Send commands** - Tell Claude what to do next

**That's the Greek way - take something simple and make it even more convenient!** 🇬🇷

From the beaches of Mykonos to the cafes of Athens, now you can code from anywhere. Because why should your coding be limited by location when you can have the power of Claude in your pocket? 📱✨

## 📝 License

MIT

---

**Created for controlling Claude Code remotely.** Enjoy coding from anywhere! 📱✨

*Made with 🇬🇷 Greek ingenuity - because we take the simple and make it even more convenient!* 🏖️