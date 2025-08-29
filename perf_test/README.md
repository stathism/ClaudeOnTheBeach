# 🏖️ Performance Testing

Quick performance tests for ClaudeOnTheBeach server.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (server must be running)
python3 server_stress_test.py      # Server capacity
python3 realistic_test.py          # Real-world usage
python3 error_handling_test.py     # Error resilience
python3 network_test.py            # Network performance
```

## 📊 Test Overview

| Test | Purpose | What it measures |
|------|---------|------------------|
| `server_stress_test.py` | Server capacity | Messages/second, concurrent sessions |
| `realistic_test.py` | Real usage | User behavior simulation |
| `error_handling_test.py` | Error resilience | Malformed message handling |
| `network_test.py` | Network performance | DNS, TCP, WebSocket latency |

## ⚠️ Important: Server Errors Are Good!

When running tests, you'll see errors like:
```
❌ Error processing wrapper message: SyntaxError: Unexpected end of JSON input
```

**This is EXPECTED and GOOD!** The tests intentionally send malformed messages to verify the server handles errors gracefully without crashing.

## 📈 Typical Results

```
🔥 Processing Capacity: 794+ messages/second
👥 Concurrent Sessions: 100% success rate
🧠 Memory Usage: 50+ sessions handled
⚠️ Error Handling: 100% robust
```

## 🎯 Performance Assessment

**Excellent Performance Indicators:**
- Processing Capacity: > 500 messages/second
- Concurrent Sessions: > 90% success rate
- Error Handling: 100% recovery after errors
- Real-world Usage: < 0.01s average processing

Your server is likely performing excellently! 🏖️✨
