const express = require('express');
const WebSocket = require('ws');
const TelegramBot = require('node-telegram-bot-api');
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');
const { exec } = require('child_process');
const { promisify } = require('util');
require('dotenv').config();

const execAsync = promisify(exec);

console.log('🏖️ Starting ClaudOnTheBeach Server...');
console.log('🌊 Surf\'s up! Time to control Claude from paradise!');

const token = process.env.TELEGRAM_BOT_TOKEN;
const port = process.env.PORT || 8080;

if (!token) {
    console.error('❌ TELEGRAM_BOT_TOKEN environment variable required');
    console.log('💡 Get token from @BotFather on Telegram');
    process.exit(1);
}

class CombinedClaudeServer {
    constructor() {
        this.app = express();
        
        // Production HTTPS setup
        const isProduction = process.env.NODE_ENV === 'production';
        const useHttps = process.env.USE_HTTPS === 'true' || isProduction;
        
        if (useHttps) {
            // HTTPS server for production
            const sslOptions = {
                key: fs.readFileSync(process.env.SSL_KEY_PATH || '/etc/letsencrypt/live/your-domain/privkey.pem'),
                cert: fs.readFileSync(process.env.SSL_CERT_PATH || '/etc/letsencrypt/live/your-domain/fullchain.pem')
            };
            this.server = https.createServer(sslOptions, this.app);
            console.log('🔒 HTTPS server configured for production');
        } else {
            // HTTP server for development
            this.server = http.createServer(this.app);
            console.log('🌐 HTTP server configured for development');
        }
        
        this.wss = new WebSocket.Server({ server: this.server, path: '/ws' });
        this.bot = new TelegramBot(token, { polling: true });
        
        // Session storage
        this.sessions = new Map(); // pairing_code -> session_data
        this.userSessions = new Map(); // telegram_chat_id -> session_data
        
        this.setupHTTP();
        this.setupWebSocket();
        this.setupTelegramBot();
        this.setupCleanup();
    }
    
    async cleanupOnStartup() {
        console.log('🧹 Starting cleanup on startup...');
        
        try {
            // Check if port is already in use
            const isPortInUse = await this.checkPortInUse(port);
            
            if (isPortInUse) {
                console.log(`⚠️ Port ${port} is already in use. Attempting to kill existing processes...`);
                await this.killProcessesOnPort(port);
                
                // Wait a moment for processes to be killed
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Check again
                const stillInUse = await this.checkPortInUse(port);
                if (stillInUse) {
                    throw new Error(`Port ${port} is still in use after cleanup attempt`);
                }
            }
            
            console.log('✅ Startup cleanup completed');
            
        } catch (error) {
            console.error('❌ Startup cleanup failed:', error.message);
            console.log('💡 Try manually killing processes on port', port);
            console.log('   On macOS/Linux: lsof -ti:' + port + ' | xargs kill -9');
            process.exit(1);
        }
    }
    
    async checkPortInUse(port) {
        try {
            const { stdout } = await execAsync(`lsof -ti:${port}`);
            return stdout.trim().length > 0;
        } catch (error) {
            // If lsof returns no results, port is not in use
            return false;
        }
    }
    
    async killProcessesOnPort(port) {
        try {
            console.log(`🔪 Killing processes on port ${port}...`);
            const { stdout } = await execAsync(`lsof -ti:${port} | xargs kill -9`);
            console.log('✅ Killed processes:', stdout.trim());
        } catch (error) {
            console.log('⚠️ No processes found to kill or error killing processes:', error.message);
        }
    }
    
    setupHTTP() {
        this.app.use(express.json());
        
        // Security: No public endpoints exposed
        // Health and session endpoints removed for security
        
        console.log('🌐 HTTP endpoints ready');
    }
    
    setupWebSocket() {
        this.wss.on('connection', (ws, req) => {
            const query = url.parse(req.url, true).query;
            const pairingCode = query.code;
            
            console.log(`📡 WebSocket connection attempt from ${req.socket.remoteAddress}`);
            console.log(`🔍 Query parameters:`, query);
            
            if (!pairingCode) {
                console.log(`❌ Missing pairing code in WebSocket connection`);
                ws.close(1008, 'Missing pairing code');
                return;
            }
            
            console.log(`🔌 Wrapper connected with pairing code: ${pairingCode}`);
            
            // Create or update session
            let session = this.sessions.get(pairingCode);
            console.log(`🔌 WebSocket connection - existing session for ${pairingCode}: ${session ? 'YES' : 'NO'}`);
            
            if (!session) {
                session = this.createSession(pairingCode);
                console.log(`✅ Created new session for ${pairingCode}`);
            }
            
            // Set connection metadata
            session.wrapperWs = ws;
            session.lastActivity = new Date();
            session.connectionStart = new Date();
            session.remoteAddress = req.socket.remoteAddress;
            
            // Add connection to active connections tracking
            if (!this.activeConnections) {
                this.activeConnections = new Set();
            }
            this.activeConnections.add(ws);
            console.log(`📊 Connection tracking: ${this.activeConnections.size} total connections`);
            
            // Handle WebSocket close
            ws.on('close', (code, reason) => {
                console.log(`🔌 WebSocket connection closed for ${pairingCode}: ${code} - ${reason}`);
                this.handleConnectionClose(ws, session, pairingCode);
            });
            
            // Handle WebSocket errors
            ws.on('error', (error) => {
                console.error(`❌ WebSocket error for ${pairingCode}:`, error.message);
                this.handleConnectionClose(ws, session, pairingCode);
            });
            
            // Send pairing confirmation if already paired with Telegram
            if (session.paired) {
                ws.send(JSON.stringify({
                    type: 'paired',
                    phone: session.telegramChatId,
                    timestamp: new Date().toISOString()
                }));
            }
            
            // Handle messages from wrapper (Claude output)
            ws.on('message', (data) => {
                try {
                    const message = JSON.parse(data.toString());
                    session.lastActivity = new Date();
                    
                    console.log(`📨 Wrapper message: ${message.type}`);
                    
                    // Forward to Telegram if paired
                    if (session.paired && session.telegramChatId) {
                        this.forwardToTelegram(session.telegramChatId, message);
                    }
                    
                } catch (error) {
                    console.error('❌ Error processing wrapper message:', error);
                }
            });
        });
        
        console.log('🔌 WebSocket server ready with enhanced connection tracking');
    }
    
    handleConnectionClose(ws, session, pairingCode) {
        // Remove from active connections
        if (this.activeConnections) {
            this.activeConnections.delete(ws);
        }
        
        // Clean up session if connection is dead
        if (session) {
            session.wrapperWs = null;
            session.lastActivity = new Date();
            
            // If session has been inactive for too long, clean it up
            const now = new Date();
            const maxInactiveTime = 5 * 60 * 1000; // 5 minutes
            
            if (now - session.lastActivity > maxInactiveTime) {
                console.log(`🗑️ Cleaning up inactive session: ${pairingCode}`);
                this.cleanupSession(pairingCode);
            }
        }
        
        console.log(`📊 Active connections: ${this.activeConnections ? this.activeConnections.size : 0}`);
    }
    
    cleanupSession(pairingCode) {
        const session = this.sessions.get(pairingCode);
        if (session) {
            // Notify Telegram user if paired
            if (session.paired && session.telegramChatId) {
                try {
                    this.bot.sendMessage(session.telegramChatId, 
                        `❌ Connection lost to Claude session \`${pairingCode}\`\n\n💡 To reconnect:\n1️⃣ Send /d or /disconnect to end this session\n2️⃣ Send a new pairing code from your computer`);
                } catch (error) {
                    console.log(`⚠️ Could not notify Telegram user ${session.telegramChatId}:`, error.message);
                }
                
                // Remove from user sessions
                this.userSessions.delete(session.telegramChatId);
            }
            
            // Remove session
            this.sessions.delete(pairingCode);
            console.log(`✅ Cleaned up session: ${pairingCode}`);
        }
    }
    
    getConnectionHealth() {
        if (!this.activeConnections) {
            return { total: 0, healthy: 0 };
        }
        
        const total = this.activeConnections.size;
        const healthy = Array.from(this.activeConnections).filter(ws => 
            ws.readyState === WebSocket.OPEN
        ).length;
        
        return { total, healthy };
    }
    
    forceCleanup() {
        console.log('🧹 Force cleanup initiated...');
        
        let cleanedSessions = 0;
        let cleanedUserSessions = 0;
        let cleanedConnections = 0;
        
        // Clean up dead connections
        if (this.activeConnections) {
            for (const ws of this.activeConnections) {
                if (ws.readyState !== WebSocket.OPEN) {
                    this.activeConnections.delete(ws);
                    cleanedConnections++;
                }
            }
        }
        
        // Clean up sessions with dead connections
        for (const [code, session] of this.sessions.entries()) {
            if (session.wrapperWs && session.wrapperWs.readyState !== WebSocket.OPEN) {
                this.cleanupSession(code);
                cleanedSessions++;
            }
        }
        
        // Clean up orphaned user sessions
        for (const [chatId, session] of this.userSessions.entries()) {
            if (!this.sessions.has(session.pairingCode)) {
                this.userSessions.delete(chatId);
                cleanedUserSessions++;
            }
        }
        
        console.log(`🧹 Force cleanup completed: ${cleanedConnections} connections, ${cleanedSessions} sessions, ${cleanedUserSessions} user sessions`);
        return { connections: cleanedConnections, sessions: cleanedSessions, userSessions: cleanedUserSessions };
    }
    
    setupTelegramBot() {
        // Start command
        this.bot.onText(/^\/start(\s|$)/, (msg) => {
            const chatId = msg.chat.id;
            this.bot.sendMessage(chatId, `
🤖 *Claude Code Remote Control*

Send me a 6-character pairing code to connect to your Claude session.

Commands:
• Send pairing code (e.g., K7X9M2) to connect
• /t or /status - Check connection status  
• /d or /disconnect - Disconnect from session
• /h or /help - Show this message

Once connected, you'll see Claude's output and can send commands directly!
            `, { parse_mode: 'Markdown' });
        });
        
        // Help command (with /h alias) - only match when /help is the exact message or starts the message
        this.bot.onText(/^\/(help|h)(\s|$)/, (msg) => {
            const chatId = msg.chat.id;
            this.bot.sendMessage(chatId, `
🏖️ *Claude On The Beach Commands* 🌊

📸 *Screenshots:*
• /s or /sc or /screenshot - Take a screenshot now

🎬 *Recordings:*
• /r or /rec or /rc - Get rolling 20-minute recording buffer
• /rec-test - Test recording functionality (10s)
• /rs or /rec-status or /rc-status - Show recording status

⌨️ *Keyboard Commands:*
• /c or /char <seq> - Send keyboard commands
  > = right, < = left, ^ = up, v = down
  e = Enter, x = Escape
  Examples: /c vv>e or /char v v > e

📊 *Status:*
• /t or /status - Connection status
• /d or /disconnect - End session

🔧 *Native Claude Commands:*
• All Claude commands can be accessed by using double //
• Examples: //help //init //shortcuts //search //exit

🧹 *Admin Commands:*
• /cleanup or /debug - Force cleanup of dead connections

💡 *Tips:*
• Commands are processed immediately
• Recording starts automatically when paired
• Screenshots are taken automatically on completion
            `, { parse_mode: 'Markdown' });
        });
        
        // Status command (with /t alias)
        this.bot.onText(/^\/(status|t)(\s|$)/, (msg) => {
            const chatId = msg.chat.id;
            const session = this.userSessions.get(chatId);
            
            if (session) {
                const wrapperStatus = session.wrapperWs && session.wrapperWs.readyState === WebSocket.OPEN ? '🟢 Connected' : '🔴 Disconnected';
                const connectionHealth = this.getConnectionHealth();
                
                this.bot.sendMessage(chatId, `
✅ *Connected to Claude*

Pairing Code: \`${session.pairingCode}\`
Wrapper: ${wrapperStatus}
Connected: ${session.createdAt.toLocaleString()}
Last activity: ${session.lastActivity.toLocaleString()}

📊 *Server Status:*
• Active sessions: ${this.sessions.size}
• Active connections: ${connectionHealth.total}
• Healthy connections: ${connectionHealth.healthy}

Send any message to control Claude!
                `, { parse_mode: 'Markdown' });
            } else {
                this.bot.sendMessage(chatId, '❌ Not connected to any Claude session. Send a pairing code to connect.');
            }
        });
        
        // Disconnect command (with /d and /ds aliases)
        this.bot.onText(/^\/(disconnect|ds|d)(\s|$)/, (msg) => {
            const chatId = msg.chat.id;
            const session = this.userSessions.get(chatId);
            
            if (session) {
                this.userSessions.delete(chatId);
                session.paired = false;
                session.telegramChatId = null;
                
                this.bot.sendMessage(chatId, '✅ Disconnected from Claude session.');
                console.log(`📱 Telegram user ${chatId} disconnected from ${session.pairingCode}`);
            } else {
                this.bot.sendMessage(chatId, '❌ No active session to disconnect.');
            }
        });
        
        // Debug cleanup command (admin only)
        this.bot.onText(/^\/(cleanup|debug)(\s|$)/, (msg) => {
            const chatId = msg.chat.id;
            
            // Only allow cleanup from specific admin users (optional security)
            // You can add admin user IDs here if needed
            // const adminUsers = ['123456789', '987654321'];
            // if (!adminUsers.includes(chatId.toString())) {
            //     this.bot.sendMessage(chatId, '❌ Admin access required for this command.');
            //     return;
            // }
            
            const result = this.forceCleanup();
            const health = this.getConnectionHealth();
            
            this.bot.sendMessage(chatId, `
🧹 *Force Cleanup Completed*

📊 *Cleanup Results:*
• Dead connections: ${result.connections}
• Dead sessions: ${result.sessions}
• Orphaned user sessions: ${result.userSessions}

📈 *Current Health:*
• Active sessions: ${this.sessions.size}
• Active connections: ${health.total}
• Healthy connections: ${health.healthy}

✅ Server cleaned up and optimized!
            `, { parse_mode: 'Markdown' });
        });
        
        // Handle all other messages (pairing codes and commands)
        this.bot.on('message', (msg) => {
            const chatId = msg.chat.id;
            const text = msg.text;
            
            // Skip known bot commands, but allow /screenshot and other commands to pass through
            if (!text) {
                return;
            }
            
            // Only skip these specific bot commands
            const skipCommands = ['/start', '/help', '/h', '/status', '/t', '/disconnect', '/ds', '/d', '/cleanup', '/debug'];
            if (text.startsWith('/') && skipCommands.includes(text.split(' ')[0])) {
                return;
            }
            
            const existingSession = this.userSessions.get(chatId);
            
            // Check if this looks like a pairing code (6 characters, alphanumeric, case-insensitive)
            if (!existingSession && /^[a-zA-Z0-9]{6}$/i.test(text)) {
                const pairingCode = text.toLowerCase();  // Changed to lowercase to match wrapper
                console.log(`🔍 Looking for session with code: ${pairingCode}`);
                console.log(`📊 Available sessions: ${Array.from(this.sessions.keys()).join(', ')}`);
                
                const session = this.sessions.get(pairingCode);
                
                if (session) {
                    // Pair the session
                    session.paired = true;
                    session.telegramChatId = chatId;
                    session.lastActivity = new Date();
                    
                    this.userSessions.set(chatId, session);
                    
                    // Notify wrapper of pairing
                    if (session.wrapperWs && session.wrapperWs.readyState === WebSocket.OPEN) {
                        session.wrapperWs.send(JSON.stringify({
                            type: 'paired',
                            phone: chatId,
                            timestamp: new Date().toISOString()
                        }));
                    }
                    
                    this.bot.sendMessage(chatId, `
🏖️ *Connected to Claude On The Beach!* 🌊

Session: \`${session.pairingCode}\`

You can now:
• Type any message → sends to Claude
• See Claude's output in real-time
• /h or /help - Show all available commands
• /t or /status - Check connection
• /d or /disconnect - End session

🌊 *Ready to code from paradise!* 🚀
                    `, { parse_mode: 'Markdown' });
                    
                    console.log(`✅ Paired Telegram user ${chatId} with session ${pairingCode}`);
                } else {
                    this.bot.sendMessage(chatId, '❌ Invalid pairing code or session expired. Please check the code and try again.');
                }
                return;
            }
            
            // If user has a session, send message as command to wrapper
            if (existingSession) {
                existingSession.lastActivity = new Date();
                
                if (existingSession.wrapperWs && existingSession.wrapperWs.readyState === WebSocket.OPEN) {
                    existingSession.wrapperWs.send(JSON.stringify({
                        type: 'command',
                        text: text,
                        source: 'telegram',
                        timestamp: new Date().toISOString()
                    }));
                    
                    // Confirm command sent
                    this.bot.sendMessage(chatId, `📤 *Command sent:* ${text}`, { parse_mode: 'Markdown' });
                    console.log(`📤 Command from ${chatId}: ${text}`);
                } else {
                    this.bot.sendMessage(chatId, `❌ Claude session not available. W
                        rapper may be disconnected.

💡 To reconnect:
1️⃣ FIRST: Send /d or /disconnect to end this session
2️⃣ THEN: Send a new pairing code from your computer

Or try /t or /status to check connection.`);
                }
            } else {
                // User not connected, prompt for pairing code
                this.bot.sendMessage(chatId, `
❌ Not connected to Claude.

Send me a 6-character pairing code to connect.
Example: K7X9M2

Get the code by running the client on your computer:
python3 client/claudeOnTheBeach.py
                `);
            }
        });
        
        // Error handling
        this.bot.on('polling_error', (error) => {
            console.error('❌ Telegram polling error:', error);
        });
        
        console.log('🤖 Telegram bot ready');
    }
    
    async forwardToTelegram(chatId, message) {
        try {
            if (message.type === 'screenshot') {
                // Handle screenshot - base64 image data with custom caption
                const caption = message.caption || '📸 Terminal screenshot';
                console.log(`📸 Forwarding screenshot to Telegram: ${caption}`);
                
                // The Python wrapper sends image data in 'content' field
                const imageData = message.content || message.data;
                if (!imageData) {
                    console.log('❌ No image data found in message');
                    return;
                }
                
                try {
                    const imageBuffer = Buffer.from(imageData, 'base64');
                    console.log(`📸 Sending screenshot: ${imageBuffer.length} bytes`);
                    await this.bot.sendPhoto(chatId, imageBuffer, {
                        caption: caption,
                        filename: 'screenshot.png'
                    });
                    console.log(`✅ Screenshot sent successfully`);
                } catch (photoError) {
                    console.error('❌ Error sending screenshot:', photoError);
                    this.bot.sendMessage(chatId, `❌ Failed to send screenshot: ${photoError.message}`);
                }
            } else if (message.type === 'video') {
                // Handle video file - base64 video data
                const caption = message.caption || '🎬 Task Recording';
                const filename = message.filename || 'recording.mov';
                console.log(`🎬 Forwarding video to Telegram: ${filename} (${message.file_size} bytes)`);
                
                try {
                    // The Python wrapper might send video data in 'content' field
                    const videoData = message.content || message.data;
                    if (!videoData) {
                        console.log('❌ No video data found in message');
                        return;
                    }
                    
                    const videoBuffer = Buffer.from(videoData, 'base64');
                    this.bot.sendVideo(chatId, videoBuffer, {
                        caption: caption,
                        filename: filename
                    });
                } catch (videoError) {
                    console.error('❌ Error sending video:', videoError);
                    this.bot.sendMessage(chatId, `❌ Failed to send video: ${videoError.message}`);
                }
            } else if (message.type === 'output') {
                const outputText = message.content || message.data || '';
                let text = this.formatMessage(outputText, message.type);
                this.bot.sendMessage(chatId, text);
            } else if (message.type === 'status') {
                const statusText = message.content || message.data || 'Status update';
                this.bot.sendMessage(chatId, `ℹ️ ${statusText}`);
            } else if (message.type === 'input') {
                const inputText = message.content || message.data || '';
                this.bot.sendMessage(chatId, `💻 Terminal: ${inputText}`);
            }
            
        } catch (error) {
            console.error('❌ Error forwarding to Telegram:', error);
        }
    }
    
    formatMessage(text, type = 'output') {
        // Telegram message size limit
        const maxLength = 4000;
        if (text.length > maxLength) {
            return text.substring(0, maxLength) + '\n\n[Message truncated...]';
        }
        return text;
    }
    
    createSession(pairingCode) {
        const session = {
            pairingCode,
            wrapperWs: null,
            telegramChatId: null,
            paired: false,
            createdAt: new Date(),
            lastActivity: new Date()
        };
        
        this.sessions.set(pairingCode, session);
        console.log(`📝 Created session with code: ${pairingCode}`);
        console.log(`📊 Total sessions now: ${this.sessions.size}`);
        
        // Auto-cleanup after 30 minutes if not paired
        setTimeout(() => {
            if (!session.paired) {
                this.sessions.delete(pairingCode);
                console.log(`🗑️ Cleaned up unpaired session: ${pairingCode}`);
            }
        }, 30 * 60 * 1000);
        
        return session;
    }
    
    setupCleanup() {
        // Cleanup inactive sessions every 5 minutes (more frequent)
        setInterval(() => {
            const now = new Date();
            const maxAge = 2 * 60 * 60 * 1000; // 2 hours for old sessions
            const maxInactiveTime = 3 * 60 * 1000; // 3 minutes for inactive connections
            
            let cleanedSessions = 0;
            let cleanedUserSessions = 0;
            
            for (const [code, session] of this.sessions.entries()) {
                let shouldCleanup = false;
                
                // Clean up very old sessions
                if (now - session.createdAt > maxAge) {
                    shouldCleanup = true;
                    console.log(`🗑️ Cleaning up old session: ${code} (age: ${Math.round((now - session.createdAt) / 60000)}m)`);
                }
                
                // Clean up sessions with dead connections
                if (session.wrapperWs && session.wrapperWs.readyState !== WebSocket.OPEN) {
                    shouldCleanup = true;
                    console.log(`🗑️ Cleaning up session with dead connection: ${code}`);
                }
                
                // Clean up inactive sessions
                if (now - session.lastActivity > maxInactiveTime) {
                    shouldCleanup = true;
                    console.log(`🗑️ Cleaning up inactive session: ${code} (inactive: ${Math.round((now - session.lastActivity) / 60000)}m)`);
                }
                
                if (shouldCleanup) {
                    this.cleanupSession(code);
                    cleanedSessions++;
                }
            }
            
            // Clean up orphaned user sessions
            for (const [chatId, session] of this.userSessions.entries()) {
                if (!this.sessions.has(session.pairingCode)) {
                    this.userSessions.delete(chatId);
                    cleanedUserSessions++;
                    console.log(`🗑️ Cleaned up orphaned user session: ${chatId}`);
                }
            }
            
            if (cleanedSessions > 0 || cleanedUserSessions > 0) {
                console.log(`🧹 Cleanup completed: ${cleanedSessions} sessions, ${cleanedUserSessions} user sessions`);
                console.log(`📊 Active sessions: ${this.sessions.size}, Active user sessions: ${this.userSessions.size}`);
            }
            
            // Log connection health
            if (this.activeConnections) {
                const healthyConnections = Array.from(this.activeConnections).filter(ws => 
                    ws.readyState === WebSocket.OPEN
                ).length;
                console.log(`📊 Connection health: ${healthyConnections}/${this.activeConnections.size} healthy`);
            }
            
        }, 5 * 60 * 1000); // Every 5 minutes
        
        // More aggressive cleanup for dead connections every 2 minutes
        setInterval(() => {
            if (this.activeConnections) {
                let deadConnections = 0;
                
                for (const ws of this.activeConnections) {
                    if (ws.readyState !== WebSocket.OPEN) {
                        this.activeConnections.delete(ws);
                        deadConnections++;
                    }
                }
                
                if (deadConnections > 0) {
                    console.log(`🧹 Cleaned up ${deadConnections} dead connections`);
                }
            }
        }, 2 * 60 * 1000); // Every 2 minutes
        
        console.log('🧹 Enhanced cleanup scheduler ready');
    }
    
    async shutdown() {
        console.log('🔄 Starting graceful shutdown...');
        
        // Set a timeout for the entire shutdown process
        const shutdownTimeout = setTimeout(() => {
            console.log('⏰ Shutdown timeout reached, forcing exit...');
            process.exit(1);
        }, 10000); // 10 second timeout
        
        try {
            // Step 1: Stop Telegram bot polling
            console.log('🤖 Stopping Telegram bot polling...');
            await this.bot.stopPolling();
            console.log('✅ Telegram bot stopped');
            
            // Step 2: Close all WebSocket connections
            console.log('🔌 Closing WebSocket connections...');
            const wsConnections = Array.from(this.wss.clients);
            console.log(`📊 Found ${wsConnections.length} active WebSocket connections`);
            
            for (const ws of wsConnections) {
                try {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.close(1000, 'Server shutdown');
                        console.log('🔌 Closed WebSocket connection');
                    }
                } catch (error) {
                    console.log('⚠️ Error closing WebSocket:', error.message);
                }
            }
            
            // Step 3: Close WebSocket server
            console.log('🔌 Closing WebSocket server...');
            await new Promise((resolve) => {
                this.wss.close(() => {
                    console.log('✅ WebSocket server closed');
                    resolve();
                });
            });
            
            // Step 4: Close HTTP server
            console.log('🌐 Closing HTTP server...');
            await new Promise((resolve) => {
                this.server.close(() => {
                    console.log('✅ HTTP server closed');
                    resolve();
                });
            });
            
            // Step 5: Clean up sessions
            console.log('🧹 Cleaning up sessions...');
            const sessionCount = this.sessions.size;
            const userSessionCount = this.userSessions.size;
            this.sessions.clear();
            this.userSessions.clear();
            console.log(`✅ Cleaned up ${sessionCount} sessions and ${userSessionCount} user sessions`);
            
            // Step 6: Wait a moment for cleanup
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            console.log('✅ Graceful shutdown complete');
            
        } catch (error) {
            console.error('❌ Error during shutdown:', error);
        } finally {
            // Clear the timeout
            clearTimeout(shutdownTimeout);
            // Force exit after cleanup
            process.exit(0);
        }
    }
    
    async start() {
        // Clean up on startup first
        await this.cleanupOnStartup();
        
        return new Promise((resolve, reject) => {
            this.server.listen(port, () => {
                console.log('✅ Combined Claude Remote Server ready!');
                console.log(`🌐 HTTP server: http://localhost:${port}`);
                console.log(`🔌 WebSocket: ws://localhost:${port}/ws`);
                console.log(`🤖 Telegram bot: @${this.bot.me?.username || 'Unknown'}`);
                console.log(`🔒 Server locked down - no public endpoints exposed`);
                console.log('');
                console.log('💡 Usage:');
                console.log('1. Run client: python3 client/claudeOnTheBeach.py');
                console.log('2. Send pairing code to Telegram bot');
                console.log('3. Control Claude from your phone! 📱');
                resolve();
            });
            
            this.server.on('error', (error) => {
                if (error.code === 'EADDRINUSE') {
                    console.error(`❌ Port ${port} is already in use`);
                    console.log('💡 Try manually killing processes:');
                    console.log(`   lsof -ti:${port} | xargs kill -9`);
                    reject(error);
                } else {
                    console.error('❌ Server error:', error);
                    reject(error);
                }
            });
        });
    }
}

// Start the combined server
const server = new CombinedClaudeServer();

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Received SIGINT, starting graceful shutdown...');
    await server.shutdown();
});

process.on('SIGTERM', async () => {
    console.log('\n🛑 Received SIGTERM, starting graceful shutdown...');
    await server.shutdown();
});

process.on('SIGUSR2', async () => {
    console.log('\n🛑 Received SIGUSR2, starting graceful shutdown...');
    await server.shutdown();
});

// Handle uncaught exceptions
process.on('uncaughtException', async (error) => {
    console.error('❌ Uncaught Exception:', error);
    console.log('🛑 Starting emergency shutdown...');
    await server.shutdown();
});

process.on('unhandledRejection', async (reason, promise) => {
    console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
    console.log('🛑 Starting emergency shutdown...');
    await server.shutdown();
});

// Start the server
server.start().catch(error => {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
});