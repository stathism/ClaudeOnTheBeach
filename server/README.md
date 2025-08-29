# 🏖️ ClaudeOnTheBeach Server

**Control Claude Code from anywhere - even the beach!** 🌊

This is the server component of ClaudeOnTheBeach, a WebSocket server that bridges Telegram bot commands to your local Claude Code terminal sessions.

## 🚀 Quick Start

### Prerequisites
- **Node.js** (v16 or higher) - Works on Windows, macOS, Linux
- **npm** or **yarn**
- **Telegram account** (for bot setup)
- **Any operating system** - Server runs on Windows, macOS, Linux, etc.

### 1. Install Dependencies
```bash
cd server
npm install
```

### 2. Create Telegram Bot
1. **Open Telegram** and search for `@BotFather`
2. **Send** `/newbot` command
3. **Choose a name** for your bot (e.g., "My Claude Controller")
4. **Choose a username** (must end with 'bot', e.g., "myclaude_bot")
5. **Copy the token** - you'll need this for configuration

### 3. Configure Environment
```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your settings
nano .env
```

**Required Configuration:**
```bash
# Your Telegram bot token (from BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Server settings (optional - defaults shown)
PORT=443
HOST=localhost
```

### 4. Start the Server
```bash
# Production mode
npm start

# Development mode (with auto-restart)
npm run dev
```

### 5. Test Connection
- **Open Telegram** and find your bot
- **Send** `/start` to begin
- **Follow the pairing instructions**

## ⚙️ Configuration Options

### Server Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8081` | Server port number |
| `HOST` | `localhost` | Server host address |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warn, error) |

### WebSocket Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `WS_PATH` | `/ws` | WebSocket endpoint path |
| `SESSION_TIMEOUT` | `3600000` | Session timeout (1 hour in ms) |
| `HEARTBEAT_INTERVAL` | `30000` | Heartbeat interval (30s in ms) |

### Security & Performance
| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONNECTIONS` | `100` | Maximum concurrent connections |
| `RATE_LIMIT_WINDOW` | `60000` | Rate limit window (1 min in ms) |
| `RATE_LIMIT_MAX_REQUESTS` | `100` | Max requests per window |

## 🔧 Server Features

### WebSocket Endpoints
- **`/ws`** - Main WebSocket connection for clients
- **No public HTTP endpoints** - Server is locked down for security

### Telegram Bot Commands
| Command | Alias | Description |
|---------|-------|-------------|
| `/start` | - | Initialize bot and show welcome message |
| `/help` | `/h` | Show available commands |
| `/status` | `/t` | Check connection status |
| `/disconnect` | `/d`, `/ds` | End current session |

### Session Management
- **Automatic pairing** with 6-character codes
- **Session timeout** after 1 hour of inactivity
- **Heartbeat monitoring** for connection health
- **Graceful cleanup** of disconnected sessions

### Security Features
- **Rate limiting** to prevent abuse
- **Connection limits** to manage resources
- **Input validation** for all commands
- **Error handling** for malformed messages

## 🏗️ Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Telegram Bot  │ ◄─────────────► │  Claude Client  │
│                 │                 │                 │
│  - /start       │                 │  - Screenshots  │
│  - /help        │                 │  - Commands     │
│  - /status      │                 │  - Recording    │
│  - /disconnect  │                 │  - Monitoring   │
└─────────────────┘                 └─────────────────┘
         │                                   │
         │ HTTP/WebSocket                    │
         ▼                                   ▼
┌─────────────────────────────────────────────────────────┐
│              ClaudeOnTheBeach Server                    │
│                                                         │
│  - WebSocket Server (ws://localhost:443/ws)             │
│  - Session Management                                   │
│  - Message Routing                                      │
│  - Security & Rate Limiting                             │
│  - Cross-Platform (Windows, macOS, Linux)              │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Deployment

### Local Development
```bash
npm run dev  # Auto-restart on file changes
```

### Production
```bash
npm start    # Standard Node.js process
```

**📖 For production deployment with HTTPS, see [PRODUCTION.md](./PRODUCTION.md)**

### Using PM2 (Recommended)
```bash
# Install PM2 globally
npm install -g pm2

# Start with PM2
pm2 start index.js --name "claude-server"

# Monitor
pm2 monit

# View logs
pm2 logs claude-server
```

### Docker Deployment (Cross-Platform)
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 443
CMD ["npm", "start"]
```

**Works on any platform that supports Docker!**

## 🔍 Monitoring & Debugging

### Security Status
```bash
# Server is locked down - no public HTTP endpoints
# Only WebSocket connections on /ws are allowed
```

### Log Levels
- **`debug`** - Detailed debugging information
- **`info`** - General operational messages
- **`warn`** - Warning messages
- **`error`** - Error messages only

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
lsof -i :443

# Kill processes on port
lsof -ti:443 | xargs kill -9
```

#### Telegram Bot Not Responding
1. **Check token** in `.env` file
2. **Verify bot** is not blocked
3. **Restart server** after token changes
4. **Check logs** for polling errors

#### WebSocket Connection Issues
1. **Verify port** is accessible
2. **Check firewall** settings
3. **Test with** `wscat` or browser dev tools
4. **Review** client connection logs

## 🔒 Security Considerations

### Environment Variables
- **Never commit** `.env` files to version control
- **Use strong tokens** for Telegram bots
- **Rotate tokens** periodically

### Network Security
- **Use HTTPS** in production
- **Configure firewall** to limit access
- **Monitor connections** for suspicious activity

### Rate Limiting
- **Adjust limits** based on expected usage
- **Monitor** for abuse patterns
- **Implement** additional security if needed

## 📊 Performance Tuning

### Connection Limits
- **Increase** `MAX_CONNECTIONS` for high traffic
- **Monitor** memory usage with more connections
- **Test** with performance tools

### Rate Limiting
- **Adjust** `RATE_LIMIT_MAX_REQUESTS` based on usage
- **Monitor** rate limit hits in logs
- **Balance** between security and usability

### Session Management
- **Reduce** `SESSION_TIMEOUT` for security
- **Increase** `HEARTBEAT_INTERVAL` for performance
- **Monitor** session cleanup efficiency

## 🤝 Contributing

### Development Setup
```bash
# Install dependencies
npm install

# Install dev dependencies
npm install --include=dev

# Run in development mode
npm run dev
```

### Code Style
- **Follow** existing code patterns
- **Add comments** for complex logic
- **Test** changes thoroughly
- **Update** documentation as needed

## 📝 License

MIT License - see main project README for details.

---

**🏖️ Ready to control Claude from paradise? Start the server and connect your client!** 🌊
