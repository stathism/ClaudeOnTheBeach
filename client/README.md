# 🏖️ ClaudeOnTheBeach Client

The Python client component of ClaudeOnTheBeach that provides terminal automation, screenshot capture, video recording, and intelligent task detection.

## 🏗️ Client Architecture

The client consists of several key components:
- **Terminal Automation** - Controls Claude Code via keyboard input
- **Screenshot Capture** - Takes and analyzes terminal screenshots
- **Video Recording** - Maintains 20-minute rolling recording buffer
- **Smart Detection** - Intelligent task completion and question detection
- **LLM Analysis** - Uses Claude's vision for intelligent screenshot analysis

## 📋 Prerequisites

- **Python 3.8+** with pip
- **Claude Code CLI** installed and in PATH
- **macOS** (for screenshot and recording features)
- **ffmpeg** (for video recording)
- **Pillow** (for image processing)

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
cd client
pip install -r requirements.txt
```

### 2. Verify Claude Code Installation
```bash
# Check if Claude Code is installed
which claude-code

# If not found, install it first
# See: https://docs.anthropic.com/claude/docs/claude-code
```

### 3. Install System Dependencies (macOS)
```bash
# Install ffmpeg for video recording
brew install ffmpeg

# Install Pillow for image processing
pip install Pillow
```

### 4. Run the Client
```bash
# Basic usage
python3 claudeOnTheBeach.py

# With custom directory
python3 claudeOnTheBeach.py --directory ~/myproject

# With custom screenshot folder
python3 claudeOnTheBeach.py --screenshots-folder ./screenshots
```

## 🔧 Client Configuration

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--directory` | Starting directory for Claude | Current directory |
| `--screenshots-folder` | Folder to save screenshots | `/tmp/claude_screenshots` |
| `--api-key` | Claude API key for intelligent analysis | From environment |
| `--verbose` | Enable verbose logging | False |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key for LLM analysis | None |
| `CLAUDE_CODE_PATH` | Path to Claude Code executable | Auto-detected |

## 📸 Screenshot Features

### Automatic Screenshots
- **Task Completion** - Screenshots taken when tasks complete
- **Question Detection** - Screenshots when user input is needed
- **Error Detection** - Screenshots when errors occur
- **Manual Capture** - Screenshots on demand via Telegram

### Screenshot Analysis
When `ANTHROPIC_API_KEY` is set, screenshots are analyzed using Claude's vision:
- **Intelligent Captions** - Context-aware descriptions
- **Task Status Detection** - Automatic completion recognition
- **Question Identification** - Smart input requirement detection
- **Error Recognition** - Automatic error detection and reporting

## 🎬 Video Recording

### Rolling Buffer System
- **20-minute buffer** - Continuous recording with rolling window
- **High quality** - 5fps, CRF 20, 1000kbps
- **Terminal-only** - Captures only the terminal window
- **Stable playback** - Automatic corruption detection and recovery

### Recording Features
- **Automatic start** - Recording begins when client starts
- **Continuous operation** - No interruption during normal operation
- **Corruption detection** - Automatic validation and restart
- **Thread-safe** - Safe concurrent access with locking

## 🧠 Smart Detection

### Task Completion Detection
Multi-method detection system with confidence levels:

1. **Strong Indicators** (95% confidence)
   - `✅`, `✓`, `PASSED`, `SUCCESS`, `COMPLETE`, `DONE`
   - `all tests pass`, `installation complete`

2. **Task-Specific Patterns** (85% confidence)
   - Test tasks: `pytest passed`, `all tests pass`
   - Script tasks: `script completed`, `execution finished`
   - File tasks: `file created`, `saved successfully`

3. **LLM Analysis** (80% confidence)
   - Validates decisions with additional checks
   - Prevents false positives

### Question Detection
Intelligent question detection with similarity filtering:

1. **High Confidence** (95% confidence)
   - `do you want to`, `would you like to`, `select`, `choose`
   - `yes/no`, `y/n`, `1/2/3`, `enter to`, `press`

2. **Medium Confidence** (85% confidence)
   - `what`, `which`, `where`, `when`, `how`, `why`
   - `enter`, `type`, `input`, `provide`, `specify`

3. **Low Confidence** (70% confidence)
   - `please`, `kindly`, `could you`, `would you`

## 🎯 Task Classification

Automatic task type recognition for better completion detection:

- **Test tasks**: `test`, `pytest`, `unittest`, `verify`
- **Script tasks**: `script`, `python`, `node`, `execute`
- **File tasks**: `file`, `create`, `write`, `save`
- **Install tasks**: `install`, `setup`, `configure`, `package`
- **Build tasks**: `build`, `compile`, `make`, `cmake`
- **Run tasks**: `run`, `execute`, `start`, `launch`

## 🔌 WebSocket Communication

### Connection
Connects to server with pairing code:
```python
ws_url = f"ws://localhost:8081/ws?code={pairing_code}"
```

### Message Types
- **Screenshots** - Base64 encoded images with captions
- **Commands** - Text commands sent to Claude
- **Status** - Connection and task status updates
- **Recordings** - Video file uploads

## 🛡️ Error Handling

### Robust Error Recovery
- **Connection failures** - Automatic reconnection attempts
- **Screenshot errors** - Fallback to basic capture
- **Recording corruption** - Automatic detection and restart
- **LLM failures** - Graceful degradation to basic detection

### Health Monitoring
- **Recording health checks** - Every 5 minutes
- **Connection monitoring** - Continuous WebSocket status
- **Memory monitoring** - Session and connection tracking
- **Performance monitoring** - Processing time tracking

## 🐛 Troubleshooting

### Common Issues

#### Claude Code Not Found
```bash
# Check installation
which claude-code

# Set custom path
export CLAUDE_CODE_PATH="/path/to/claude-code"
```

#### Screenshot Issues
```bash
# Install Pillow
pip install Pillow

# Check macOS screencapture
screencapture -h
```

#### Recording Issues
```bash
# Install ffmpeg
brew install ffmpeg

# Check ffmpeg installation
ffmpeg -version
```

#### LLM Analysis Issues
```bash
# Set API key
export ANTHROPIC_API_KEY="your_api_key"

# Test API connection
curl -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "content-type: application/json" \
     https://api.anthropic.com/v1/messages
```

## 📊 Performance

### Performance Metrics
- **Screenshot capture**: < 0.1s average
- **LLM analysis**: 1-3s average (with API key)
- **Recording**: Continuous with < 1% CPU usage
- **WebSocket communication**: < 0.01s average

### Resource Usage
- **Memory**: ~50MB base + recording buffer
- **CPU**: < 5% during normal operation
- **Disk**: Screenshots + recording files
- **Network**: WebSocket + optional API calls

## 🔄 Development

### File Structure
```
client/
├── claudeOnTheBeach.py      # Main client application
├── config.py                # Configuration management
├── recording_manager.py     # Video recording system
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── utils/
    ├── __init__.py         # Package initialization
    ├── llm_analyzer.py     # LLM-based analysis
    ├── question_detector.py # Question detection
    ├── command_registry.py  # Command processing
    ├── static_screen_detector.py # Static screen detection
    ├── completion_detector.py # Completion detection
    └── task_classifier.py   # Task classification
```

### Adding Features
The client is modular and extensible:
- Add new detection methods in utils/
- Extend recording capabilities
- Implement new screenshot analysis
- Add custom task classifiers

## 📝 License

MIT

---

**Part of the ClaudeOnTheBeach project** - Making Claude Code accessible from anywhere! 🏖️📱

