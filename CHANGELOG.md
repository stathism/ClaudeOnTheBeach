# Changelog

All notable changes to ClaudeOnTheBeach will be documented in this file.

## [2.0.0] - 2025-08-30

### 🎬 Added - Rolling Video Recording System
- **20-minute rolling video buffer** with continuous recording
- **Terminal-only capture** using the same reliable method as screenshots
- **High quality output** (5fps, CRF 20, 1000kbps)
- **Automatic health monitoring** with smart corruption detection
- **Thread-safe operations** with recording locks
- **Smart restart logic** only when necessary
- **Commands**: `/rec`, `/rc`, `/rec-status`, `/rc-status`

### 🎯 Enhanced - Task Completion Detection
- **Multi-method detection system** with confidence scoring
- **Strong completion indicators** (95% confidence) - `✅`, `✓`, `PASSED`, `SUCCESS`
- **Task-specific patterns** (85% confidence) for different task types
- **LLM analysis validation** (80% confidence) with additional checks
- **Weak completion indicators** (70% confidence) with confirmation delay
- **Static screen detection** (60% confidence) - reduced timeout to 30s
- **Automatic task classification** for better context awareness

### 🤖 Added - Automatic Task Classification
- **Pattern-based classification** for 8 task types
- **Context-aware detection** using command content and file types
- **Task-specific completion patterns** for improved accuracy
- **Fallback classification** using previous commands and context

### 🛡️ Enhanced - Recording Stability
- **50KB threshold** for corruption checks (prevents false positives)
- **Growth detection** to distinguish temporary issues from corruption
- **Consecutive failure tracking** (3 failures before restart)
- **5-minute health check intervals** (reduced frequency)
- **Temporary health check disabling** during critical operations
- **Thread-safe operations** with proper locking mechanisms

### 🏗️ Refactored - Modular Architecture
- **Centralized configuration** in `config.py`
- **Modular utils system** with specialized components:
  - `llm_analyzer.py` - LLM-based screenshot analysis
  - `question_detector.py` - Question detection and similarity
  - `command_registry.py` - Command processing system
  - `static_screen_detector.py` - Static screen completion detection
  - `completion_detector.py` - Enhanced completion detection
  - `task_classifier.py` - Automatic task classification
- **Improved code organization** and maintainability

### 🔧 Enhanced - Server Stability
- **Automatic port cleanup** on startup to prevent conflicts
- **Graceful shutdown handling** for all signal types
- **Enhanced error handling** for WebSocket connections
- **Improved session management** with better cleanup

### 📱 Enhanced - Telegram Integration
- **Comprehensive help command** with all available commands
- **Better command aliases** (`/rc` for `/rec`, `/sc` for `/screenshot`)
- **Improved pairing instructions** with clear step-by-step guidance
- **Enhanced status reporting** with detailed information

### 🧠 Enhanced - LLM Analysis
- **Model switching detection** for completion indicators
- **Enhanced prompts** with better completion detection rules
- **Dual screenshot analysis** for improved accuracy
- **Better validation** of LLM completion decisions

### 🔄 Enhanced - Client-Server Communication
- **Heartbeat mechanism** for connection monitoring
- **Graceful disconnection handling** with clear user feedback
- **Command priority system** to ensure user commands take precedence
- **Reduced verbosity** in monitoring logs

### 🎮 Enhanced - Command Processing
- **Command registry system** with specialized handlers
- **Better error handling** for all command types
- **Improved screenshot coordination** to prevent recording interference
- **Enhanced keyboard navigation** with better sequence handling

### 📊 Enhanced - Monitoring and Logging
- **Reduced log verbosity** for better user experience
- **Better status reporting** with confidence scores
- **Improved error messages** with actionable information
- **Enhanced debugging** with detailed analysis information

### 🐛 Fixed - Various Issues
- **Recording reset issues** - now stable with corruption detection
- **False completion detection** - improved with multi-method validation
- **Screenshot interference** - coordinated with recording system
- **Import errors** - fixed for direct script execution
- **Duplicate completion messages** - eliminated with task management
- **Command priority issues** - resolved with proper async handling

### 📚 Documentation
- **Comprehensive README updates** with all new features
- **Enhanced client documentation** with modular architecture details
- **Troubleshooting guides** for new features
- **Configuration documentation** for all new options

## [1.0.0] - 2024-08-27

### 🎉 Initial Release
- **Basic terminal control** via Telegram
- **Screenshot functionality** with macOS screencapture
- **WebSocket communication** between client and server
- **Session-based pairing** with 6-character codes
- **LLM analysis** for intelligent screenshot processing
- **Question detection** and automatic notifications
- **Keyboard navigation** with arrow key sequences
- **Basic command processing** and status reporting

---

## Version History

- **v2.0.0** - Major feature release with recording, enhanced detection, and modular architecture
- **v1.0.0** - Initial release with basic terminal control and screenshot functionality

## Migration Guide

### From v1.0.0 to v2.0.0

1. **Update dependencies** - New Python packages may be required
2. **Check configuration** - New environment variables available
3. **Review commands** - New recording commands available (`/rec`, `/rc`)
4. **Test completion detection** - Enhanced system may behave differently
5. **Verify recording** - New 20-minute rolling buffer system

### Breaking Changes
- None - All changes are backward compatible
- Enhanced features are additive and don't break existing functionality

### New Requirements
- **ffmpeg** - Required for video recording functionality
- **Additional Python packages** - See `requirements.txt` for updates
