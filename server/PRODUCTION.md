# 🚀 Production Deployment Guide

**Deploy ClaudeOnTheBeach Server with HTTPS for production use**

## 🔒 HTTPS Setup

### Option 1: Let's Encrypt (Recommended - Free)

#### 1. Install Certbot
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot

# CentOS/RHEL
sudo yum install certbot

# macOS
brew install certbot
```

#### 2. Get SSL Certificate
```bash
# Replace 'your-domain.com' with your actual domain
sudo certbot certonly --standalone -d your-domain.com

# Certificates will be saved to:
# /etc/letsencrypt/live/your-domain.com/privkey.pem
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
```

#### 3. Configure Environment
```bash
# Copy and edit environment file
cp env.example .env

# Update with your domain
nano .env
```

**Production Environment:**
```bash
# Server Configuration
PORT=443
HOST=0.0.0.0

# Production HTTPS Configuration
NODE_ENV=production
USE_HTTPS=true
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Security & Performance
LOG_LEVEL=info
MAX_CONNECTIONS=100
RATE_LIMIT_WINDOW=60000
RATE_LIMIT_MAX_REQUESTS=100
```

### Option 2: Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Update environment
SSL_KEY_PATH=./key.pem
SSL_CERT_PATH=./cert.pem
```

## 🚀 Deployment Methods

### Method 1: PM2 (Recommended)

#### 1. Install PM2
```bash
npm install -g pm2
```

#### 2. Create PM2 Configuration
```bash
# Create ecosystem.config.js
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'claude-server',
    script: 'index.js',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 443
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true
  }]
}
EOF
```

#### 3. Start with PM2
```bash
# Create logs directory
mkdir logs

# Start the application
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
```

#### 4. Monitor
```bash
# View status
pm2 status

# Monitor resources
pm2 monit

# View logs
pm2 logs claude-server
```

### Method 2: Docker

#### 1. Create Dockerfile
```dockerfile
FROM node:18-alpine

# Install dependencies
RUN apk add --no-cache openssl

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

# Create SSL directory
RUN mkdir -p /etc/ssl/certs

# Expose HTTPS port
EXPOSE 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('https').get('https://localhost:443/ws', (res) => { process.exit(res.statusCode === 400 ? 0 : 1) })"

CMD ["npm", "start"]
```

#### 2. Build and Run
```bash
# Build image
docker build -t claude-server .

# Run container
docker run -d \
  --name claude-server \
  -p 443:443 \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  --env-file .env \
  claude-server
```

### Method 3: Systemd Service

#### 1. Create Service File
```bash
sudo nano /etc/systemd/system/claude-server.service
```

**Service Configuration:**
```ini
[Unit]
Description=ClaudeOnTheBeach Server
After=network.target

[Service]
Type=simple
User=claude
WorkingDirectory=/opt/claude-server
Environment=NODE_ENV=production
ExecStart=/usr/bin/node index.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and Start
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable claude-server

# Start service
sudo systemctl start claude-server

# Check status
sudo systemctl status claude-server
```

## 🔧 Production Configuration

### Security Settings
```bash
# Firewall (UFW)
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp  # For Let's Encrypt renewal
sudo ufw enable

# SELinux (if applicable)
sudo setsebool -P httpd_can_network_connect 1
```

### SSL Certificate Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab for automatic renewal
sudo crontab -e

# Add this line:
0 12 * * * /usr/bin/certbot renew --quiet
```

### Monitoring
```bash
# Install monitoring tools
npm install -g pm2-logrotate

# Configure log rotation
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

## 📊 Performance Tuning

### Node.js Optimization
```bash
# Increase memory limit
export NODE_OPTIONS="--max-old-space-size=2048"

# Enable garbage collection logging
export NODE_OPTIONS="--trace-gc"
```

### System Optimization
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize TCP settings
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
sysctl -p
```

## 🔍 Troubleshooting

### Common Issues

#### SSL Certificate Errors
```bash
# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -text -noout

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -noout -dates
```

#### Port Already in Use
```bash
# Check what's using port 443
sudo lsof -i :443

# Kill processes if needed
sudo lsof -ti:443 | xargs sudo kill -9
```

#### Permission Issues
```bash
# Fix SSL certificate permissions
sudo chown -R $USER:$USER /etc/letsencrypt/live/
sudo chmod 755 /etc/letsencrypt/live/
sudo chmod 644 /etc/letsencrypt/live/*/privkey.pem
sudo chmod 644 /etc/letsencrypt/live/*/fullchain.pem
```

### Log Analysis
```bash
# View application logs
pm2 logs claude-server --lines 100

# View system logs
sudo journalctl -u claude-server -f

# Monitor real-time connections
watch -n 1 "netstat -an | grep :443 | wc -l"
```

## 🚀 Go Live Checklist

- [ ] **SSL Certificate** installed and valid
- [ ] **Environment variables** configured
- [ ] **Firewall** configured (port 443 open)
- [ ] **Service** running and auto-start enabled
- [ ] **Monitoring** set up (PM2, logs, alerts)
- [ ] **Backup** strategy in place
- [ ] **Domain DNS** pointing to server
- [ ] **Client configuration** updated to use `wss://`
- [ ] **Telegram bot** tested and working
- [ ] **Load testing** completed

---

**🏖️ Your ClaudeOnTheBeach server is now production-ready with HTTPS!** 🌊
