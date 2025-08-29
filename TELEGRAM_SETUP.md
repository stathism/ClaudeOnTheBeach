# 📱 Telegram Bot Setup Guide

Complete guide to setting up your ClaudeOnTheBeach Telegram bot.

## 🤖 Step 1: Create Bot with BotFather

1. **Open Telegram** and search for `@BotFather`
2. **Start conversation** with `/start`
3. **Create new bot** with `/newbot`
4. **Choose bot name** (e.g., "Claude Control Bot")
5. **Choose username** (e.g., "claude_control_bot" - must end with 'bot')
6. **Save the token** - you'll get something like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

## 🔧 Step 2: Configure Bot Settings (Optional)

```bash
# Set bot description
/setdescription
# Choose your bot
# Enter: "Control Claude Code from your phone with pairing codes"

# Set bot commands
/setcommands
# Choose your bot  
# Enter:
start - Get started with Claude control
help - Show help and usage instructions
status - Check connection status
disconnect - Disconnect from current session

# Set bot picture (optional)
/setuserpic
# Choose your bot
# Upload an image
```

## ⚙️ Step 3: Configure Environment

Create `.env` file in project root:
```bash
# Required: Your bot token from BotFather
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional: Server port (default: 8081)
PORT=8081

# Optional: Anthropic API key for intelligent screenshot analysis
ANTHROPIC_API_KEY=your_claude_api_key
```

## 🚀 Step 4: Test Your Bot

```bash
# Install dependencies
npm install

# Start server (includes built-in bot)
./start.sh

# You should see:
# 🤖 Telegram bot ready
# 🌐 HTTP server: http://localhost:8081
# 🔌 WebSocket: ws://localhost:8081/ws
```

## 📲 Step 5: Test Bot Interaction

1. **Find your bot** on Telegram (search for username)
2. **Send `/start`** - should get welcome message
3. **Send `/help`** - should show command list
4. **Ready for pairing!**

## 🔗 Step 6: Full System Test

```bash
# Terminal 1: Start combined server
./start.sh

# Terminal 2: Start client
python3 client/claudeOnTheBeach.py

# Copy pairing code from client (like abc123)
# Send code to Telegram bot
# Should get: ✅ Connected to Claude!

# Test commands:
# - Send "create a python hello world script"
# - Send "/sc" (quick screenshot)
# - Send "//help" (Claude's help menu)
# - Send "/status"
```

## 🌐 Production Deployment Options

### **Option A: Railway (Recommended)**
```bash
# 1. Push code to GitHub
# 2. Connect Railway to your repo
# 3. Set environment variables in Railway dashboard
# 4. Deploy automatically
```

### **Option B: Render**
```bash
# 1. Create Render account
# 2. Connect GitHub repo
# 3. Set environment variables
# 4. Deploy with zero config
```

### **Option C: Heroku**
```bash
# Create Heroku app
heroku create your-claude-bot

# Set config vars
heroku config:set TELEGRAM_BOT_TOKEN=your_token

# Deploy
git push heroku main
```

## 🔧 Current Architecture

### **Combined Server with Built-in Bot**
```javascript
// Bot is integrated directly into the main server
const bot = new TelegramBot(token, { polling: true });
// WebSocket server runs alongside bot
const wss = new WebSocket.Server({ server: this.server, path: '/ws' });
```
- ✅ **Simple deployment** - single process
- ✅ **No separate bot service** needed
- ✅ **Direct message forwarding** between wrapper and Telegram
- ✅ **Session management** with pairing codes

### **Alternative: Webhooks** (Production)
```javascript
const bot = new TelegramBot(token, { webHook: true });
bot.setWebHook(`https://yourdomain.com/bot${token}`);
```
- ✅ **Real-time** - instant message delivery
- ✅ **More efficient** - push-based updates
- ❌ **Requires HTTPS** - need SSL certificate
- ❌ **Complex setup** - need public domain

## 🛠️ Advanced Configuration

### **Message Formatting**
```javascript
// Current: Plain text with markdown
bot.sendMessage(chatId, '*Bold text*', { parse_mode: 'Markdown' });

// Alternative: HTML formatting
bot.sendMessage(chatId, '<b>Bold text</b>', { parse_mode: 'HTML' });

// Alternative: Rich keyboard
bot.sendMessage(chatId, 'Choose action:', {
    reply_markup: {
        inline_keyboard: [
            [{ text: 'Connect', callback_data: 'connect' }],
            [{ text: 'Status', callback_data: 'status' }]
        ]
    }
});
```

### **File Handling**
```javascript
// Send Claude output as file if too long
if (output.length > 4000) {
    bot.sendDocument(chatId, Buffer.from(output), {}, {
        filename: 'claude_output.txt',
        contentType: 'text/plain'
    });
}
```

### **Rate Limiting**
```javascript
// Telegram limits: 30 messages/second to different users
const rateLimiter = new Map(); // userId -> lastMessageTime

function canSendMessage(userId) {
    const now = Date.now();
    const lastSent = rateLimiter.get(userId) || 0;
    if (now - lastSent < 1000) return false; // 1 message per second per user
    rateLimiter.set(userId, now);
    return true;
}
```

## 🔒 Security Best Practices

### **1. Token Security**
```bash
# Never commit tokens to git
echo ".env" >> .gitignore

# Use environment variables in production
export TELEGRAM_BOT_TOKEN=your_token
```

### **2. User Validation**
```javascript
// Optional: Restrict to specific users
const ALLOWED_USERS = process.env.ALLOWED_TELEGRAM_USERS?.split(',') || [];

bot.on('message', (msg) => {
    if (ALLOWED_USERS.length > 0 && !ALLOWED_USERS.includes(msg.from.id.toString())) {
        bot.sendMessage(msg.chat.id, '❌ Unauthorized user');
        return;
    }
    // Process message...
});
```

### **3. Rate Limiting**
```javascript
// Prevent spam
const userMessageCounts = new Map();

function isRateLimited(userId) {
    const count = userMessageCounts.get(userId) || 0;
    if (count > 10) return true; // 10 messages per minute
    userMessageCounts.set(userId, count + 1);
    setTimeout(() => userMessageCounts.delete(userId), 60000);
    return false;
}
```

## 📊 Monitoring & Analytics

### **Message Logging**
```javascript
bot.on('message', (msg) => {
    console.log(`📨 Message from ${msg.from.username}: ${msg.text}`);
});

bot.on('callback_query', (query) => {
    console.log(`👆 Button pressed: ${query.data}`);
});
```

### **Error Handling**
```javascript
bot.on('polling_error', (error) => {
    console.error('❌ Polling error:', error);
});

bot.on('webhook_error', (error) => {
    console.error('❌ Webhook error:', error);
});
```

## 🚨 Troubleshooting

### **Common Issues:**

1. **Bot not responding**
   - Check token is correct
   - Verify bot is started with `/start`
   - Check network connectivity

2. **"Unauthorized" error**
   - Token is invalid or expired
   - Regenerate token with BotFather

3. **Messages not formatting**
   - Check markdown syntax
   - Use HTML parse mode instead
   - Escape special characters

4. **Webhook issues**
   - Verify HTTPS certificate
   - Check webhook URL is reachable
   - Use polling for development

### **Testing Commands:**
```bash
# Test bot API directly
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# Test webhook (if using)
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Send test message
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "YOUR_CHAT_ID", "text": "Test message"}'
```

## 🎯 Ready to Use!

Your Telegram bot is now configured and ready to control Claude Code from your phone. The implementation we built supports:

- ✅ **Pairing code system**
- ✅ **Real-time output streaming** 
- ✅ **Bidirectional control**
- ✅ **Session management**
- ✅ **Error handling**
- ✅ **Production deployment ready**