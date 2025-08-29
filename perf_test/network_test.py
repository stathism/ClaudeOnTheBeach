#!/usr/bin/env python3
"""
Network Latency Component Test for ClaudeOnTheBeach
Tests different parts of the network stack separately
"""

import asyncio
import websockets
import json
import time
import aiohttp
import random
import string
import socket
import subprocess
import platform

async def test_network_components():
    """Test different network latency components"""
    print("🌐 Network Latency Component Test")
    print("="*50)
    
    server_url = "ws://localhost:8081/ws"
    http_url = "http://localhost:8081"
    
    results = {}
    
    # Test 1: DNS Resolution
    print("🔍 Testing DNS Resolution...")
    dns_times = []
    for i in range(5):
        start_time = time.time()
        try:
            socket.gethostbyname("api.telegram.org")
            dns_time = time.time() - start_time
            dns_times.append(dns_time)
            print(f"   ✅ DNS lookup {i+1}: {dns_time:.3f}s")
        except Exception as e:
            print(f"   ❌ DNS lookup {i+1} failed: {str(e)}")
    
    if dns_times:
        results['dns'] = sum(dns_times) / len(dns_times)
        print(f"   📊 Average DNS time: {results['dns']:.3f}s")
    
    # Test 2: TCP Connection to Telegram
    print(f"\n🔌 Testing TCP Connection to Telegram...")
    tcp_times = []
    for i in range(3):
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("api.telegram.org", 443))
            sock.close()
            tcp_time = time.time() - start_time
            tcp_times.append(tcp_time)
            print(f"   ✅ TCP connection {i+1}: {tcp_time:.3f}s")
        except Exception as e:
            print(f"   ❌ TCP connection {i+1} failed: {str(e)}")
    
    if tcp_times:
        results['tcp'] = sum(tcp_times) / len(tcp_times)
        print(f"   📊 Average TCP time: {results['tcp']:.3f}s")
    
    # Test 3: Local WebSocket Connection
    print(f"\n🔌 Testing Local WebSocket Connection...")
    ws_times = []
    for i in range(5):
        start_time = time.time()
        try:
            chars = string.ascii_lowercase + string.digits
            chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
            pairing_code = ''.join(random.choices(chars, k=6))
            ws_url = f"{server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            ws_time = time.time() - start_time
            ws_times.append(ws_time)
            await websocket.close()
            print(f"   ✅ WebSocket connection {i+1}: {ws_time:.3f}s")
        except Exception as e:
            print(f"   ❌ WebSocket connection {i+1} failed: {str(e)}")
    
    if ws_times:
        results['websocket'] = sum(ws_times) / len(ws_times)
        print(f"   📊 Average WebSocket time: {results['websocket']:.3f}s")
    
    # Test 4: HTTP Request to Local Server
    print(f"\n🌐 Testing HTTP Request to Local Server...")
    http_times = []
    for i in range(5):
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{http_url}/health") as response:
                    if response.status == 200:
                        await response.json()
                        http_time = time.time() - start_time
                        http_times.append(http_time)
                        print(f"   ✅ HTTP request {i+1}: {http_time:.3f}s")
        except Exception as e:
            print(f"   ❌ HTTP request {i+1} failed: {str(e)}")
    
    if http_times:
        results['http'] = sum(http_times) / len(http_times)
        print(f"   📊 Average HTTP time: {results['http']:.3f}s")
    
    # Test 5: Message Send Time (WebSocket)
    print(f"\n📨 Testing WebSocket Message Send...")
    msg_times = []
    try:
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        pairing_code = ''.join(random.choices(chars, k=6))
        ws_url = f"{server_url}?code={pairing_code}"
        websocket = await websockets.connect(ws_url)
        
        for i in range(10):
            start_time = time.time()
            test_message = {
                "type": "command",
                "text": f"network_test_{i}",
                "source": "network_test",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(test_message))
            msg_time = time.time() - start_time
            msg_times.append(msg_time)
            print(f"   ✅ Message send {i+1}: {msg_time:.3f}s")
        
        await websocket.close()
        
        if msg_times:
            results['message_send'] = sum(msg_times) / len(msg_times)
            print(f"   📊 Average message send time: {results['message_send']:.3f}s")
    
    except Exception as e:
        print(f"   ❌ Message send test failed: {str(e)}")
    
    # Test 6: Network Ping (if available)
    print(f"\n🏓 Testing Network Ping...")
    ping_times = []
    try:
        # Test ping to Telegram servers
        host = "api.telegram.org"
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", host]
        else:
            cmd = ["ping", "-c", "1", host]
        
        for i in range(3):
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            ping_time = time.time() - start_time
            if result.returncode == 0:
                ping_times.append(ping_time)
                print(f"   ✅ Ping {i+1}: {ping_time:.3f}s")
            else:
                print(f"   ❌ Ping {i+1} failed")
    
    except Exception as e:
        print(f"   ❌ Ping test failed: {str(e)}")
    
    if ping_times:
        results['ping'] = sum(ping_times) / len(ping_times)
        print(f"   📊 Average ping time: {results['ping']:.3f}s")
    
    # Summary
    print(f"\n📊 Network Component Summary")
    print("="*50)
    
    if 'dns' in results:
        print(f"🔍 DNS Resolution: {results['dns']:.3f}s")
    if 'tcp' in results:
        print(f"🔌 TCP Connection: {results['tcp']:.3f}s")
    if 'websocket' in results:
        print(f"🔌 WebSocket Connection: {results['websocket']:.3f}s")
    if 'http' in results:
        print(f"🌐 HTTP Request: {results['http']:.3f}s")
    if 'message_send' in results:
        print(f"📨 Message Send: {results['message_send']:.3f}s")
    if 'ping' in results:
        print(f"🏓 Network Ping: {results['ping']:.3f}s")
    
    # Calculate estimated Telegram API latency
    print(f"\n💡 Estimated Telegram API Latency:")
    estimated_telegram = 0
    if 'dns' in results:
        estimated_telegram += results['dns']
    if 'tcp' in results:
        estimated_telegram += results['tcp']
    # Add estimated HTTPS overhead
    estimated_telegram += 0.05  # ~50ms for HTTPS handshake
    # Add estimated API processing time
    estimated_telegram += 0.1   # ~100ms for API processing
    
    print(f"   • Estimated Telegram API: {estimated_telegram:.3f}s")
    print(f"   • Local WebSocket: {results.get('websocket', 0):.3f}s")
    print(f"   • Total estimated E2E: {estimated_telegram + results.get('websocket', 0):.3f}s")
    
    print(f"\n🎯 Performance Insights:")
    print(f"   • Local network: {results.get('websocket', 0):.3f}s (should be < 0.1s)")
    print(f"   • Internet latency: {estimated_telegram:.3f}s (varies by location)")
    print(f"   • Bottleneck: {'Local' if results.get('websocket', 0) > estimated_telegram else 'Internet'}")


if __name__ == "__main__":
    asyncio.run(test_network_components())
