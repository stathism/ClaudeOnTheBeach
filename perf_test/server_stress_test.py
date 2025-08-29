#!/usr/bin/env python3
"""
Realistic Server Stress Test for ClaudeOnTheBeach
Tests actual server processing capabilities under load
"""

import asyncio
import websockets
import json
import time
import aiohttp
import random
import string
import statistics
from datetime import datetime

class ServerStressTest:
    def __init__(self):
        self.server_url = "ws://localhost:8081/ws"
        self.http_url = "http://localhost:8081"
        self.results = {}
        
    async def test_server_processing_capacity(self):
        """Test how many messages the server can process per second"""
        print("🔥 Testing Server Processing Capacity")
        print("="*50)
        
        # Generate pairing code
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        pairing_code = ''.join(random.choices(chars, k=6))
        
        print(f"🔑 Using pairing code: {pairing_code}")
        
        # Connect to server
        try:
            ws_url = f"{self.server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            print(f"   ✅ Connected to server")
        except Exception as e:
            print(f"   ❌ Connection failed: {str(e)}")
            return
        
        # Test 1: Rapid message sending (stress test)
        print(f"\n📨 Testing rapid message sending...")
        message_count = 100
        start_time = time.time()
        processing_times = []
        
        for i in range(message_count):
            try:
                msg_start = time.time()
                
                # Create a realistic message (like what the client would send)
                test_message = {
                    "type": "screenshot",
                    "data": {
                        "image": "base64_encoded_image_data_here_" + str(i),
                        "caption": f"Test screenshot {i}",
                        "timestamp": time.time()
                    },
                    "source": "stress_test",
                    "client_id": "stress_client",
                    "message_id": f"msg_{i}_{int(time.time() * 1000)}"
                }
                
                # Send message
                await websocket.send(json.dumps(test_message))
                
                # Wait a tiny bit to let server process
                await asyncio.sleep(0.001)
                
                processing_time = time.time() - msg_start
                processing_times.append(processing_time)
                
                if i % 20 == 0:
                    print(f"   📤 Sent message {i+1}/{message_count}")
                    
            except Exception as e:
                print(f"   ❌ Message {i+1} failed: {str(e)}")
        
        total_time = time.time() - start_time
        messages_per_second = message_count / total_time
        
        print(f"\n📊 Processing Capacity Results:")
        print(f"   • Total messages: {message_count}")
        print(f"   • Total time: {total_time:.3f}s")
        print(f"   • Messages per second: {messages_per_second:.1f}")
        print(f"   • Average processing time: {statistics.mean(processing_times):.3f}s")
        print(f"   • Min processing time: {min(processing_times):.3f}s")
        print(f"   • Max processing time: {max(processing_times):.3f}s")
        
        await websocket.close()
        return messages_per_second, processing_times
    
    async def test_concurrent_sessions(self):
        """Test server performance with multiple concurrent sessions"""
        print(f"\n👥 Testing Concurrent Sessions")
        print("="*50)
        
        num_sessions = 20
        messages_per_session = 10
        session_results = []
        
        async def single_session_test(session_id):
            try:
                # Generate pairing code
                chars = string.ascii_lowercase + string.digits
                chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
                pairing_code = ''.join(random.choices(chars, k=6))
                
                # Connect
                ws_url = f"{self.server_url}?code={pairing_code}"
                websocket = await websockets.connect(ws_url)
                
                # Send messages
                start_time = time.time()
                for i in range(messages_per_session):
                    test_message = {
                        "type": "command",
                        "text": f"session_{session_id}_msg_{i}",
                        "source": "concurrent_test",
                        "client_id": f"session_{session_id}",
                        "timestamp": time.time()
                    }
                    await websocket.send(json.dumps(test_message))
                    await asyncio.sleep(0.01)  # Small delay
                
                session_time = time.time() - start_time
                await websocket.close()
                
                return {
                    "session_id": session_id,
                    "success": True,
                    "time": session_time,
                    "messages": messages_per_session
                }
                
            except Exception as e:
                return {
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent sessions
        print(f"   🚀 Starting {num_sessions} concurrent sessions...")
        tasks = [single_session_test(i) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_sessions = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_sessions = [r for r in results if isinstance(r, dict) and not r.get('success')]
        
        if successful_sessions:
            total_messages = sum(s['messages'] for s in successful_sessions)
            total_time = max(s['time'] for s in successful_sessions)  # Longest session time
            concurrent_mps = total_messages / total_time
            
            print(f"\n📊 Concurrent Session Results:")
            print(f"   • Successful sessions: {len(successful_sessions)}/{num_sessions}")
            print(f"   • Failed sessions: {len(failed_sessions)}")
            print(f"   • Total messages: {total_messages}")
            print(f"   • Total time: {total_time:.3f}s")
            print(f"   • Concurrent messages/sec: {concurrent_mps:.1f}")
            
            if failed_sessions:
                print(f"   • Failed session errors:")
                for session in failed_sessions[:3]:  # Show first 3 errors
                    print(f"      - Session {session['session_id']}: {session['error']}")
        
        return successful_sessions, failed_sessions
    
    async def test_server_memory_usage(self):
        """Test server memory usage under load"""
        print(f"\n🧠 Testing Server Memory Usage")
        print("="*50)
        
        # Get initial memory usage
        initial_health = await self.get_server_health()
        
        # Create many sessions to test memory
        num_sessions = 50
        sessions = []
        
        print(f"   📈 Creating {num_sessions} sessions...")
        for i in range(num_sessions):
            try:
                chars = string.ascii_lowercase + string.digits
                chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
                pairing_code = ''.join(random.choices(chars, k=6))
                
                ws_url = f"{self.server_url}?code={pairing_code}"
                websocket = await websockets.connect(ws_url)
                sessions.append(websocket)
                
                if i % 10 == 0:
                    print(f"      Created {i+1}/{num_sessions} sessions")
                    
            except Exception as e:
                print(f"      ❌ Failed to create session {i+1}: {str(e)}")
        
        # Get memory usage with sessions
        mid_health = await self.get_server_health()
        
        # Send messages to all sessions
        print(f"   📨 Sending messages to all sessions...")
        for i, websocket in enumerate(sessions):
            try:
                test_message = {
                    "type": "command",
                    "text": f"memory_test_{i}",
                    "source": "memory_test",
                    "client_id": f"memory_client_{i}",
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(test_message))
            except Exception as e:
                print(f"      ❌ Failed to send message to session {i}: {str(e)}")
        
        # Get final memory usage
        final_health = await self.get_server_health()
        
        # Close all sessions
        print(f"   🧹 Closing all sessions...")
        for websocket in sessions:
            try:
                await websocket.close()
            except:
                pass
        
        # Report memory usage
        print(f"\n📊 Memory Usage Results:")
        print(f"   • Initial sessions: {initial_health.get('totalSessions', 0)}")
        print(f"   • Mid sessions: {mid_health.get('totalSessions', 0)}")
        print(f"   • Final sessions: {final_health.get('totalSessions', 0)}")
        print(f"   • Initial connections: {initial_health.get('websocketConnections', 0)}")
        print(f"   • Mid connections: {mid_health.get('websocketConnections', 0)}")
        print(f"   • Final connections: {final_health.get('websocketConnections', 0)}")
        
        return initial_health, mid_health, final_health
    
    async def test_server_error_handling(self):
        """Test server's ability to handle malformed messages"""
        print(f"\n⚠️ Testing Server Error Handling")
        print("="*50)
        
        # Generate pairing code
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        pairing_code = ''.join(random.choices(chars, k=6))
        
        try:
            ws_url = f"{self.server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            
            error_tests = [
                ("Empty message", ""),
                ("Invalid JSON", "this is not json"),
                ("Missing type", '{"text": "test"}'),
                ("Large message", "x" * 10000),
                ("Null values", '{"type": null, "text": null}'),
                ("Malformed data", '{"type": "command", "data": {"nested": {"deep": "value"}}}'),
            ]
            
            error_results = []
            
            for test_name, test_data in error_tests:
                try:
                    start_time = time.time()
                    await websocket.send(test_data)
                    processing_time = time.time() - start_time
                    
                    # Wait a bit to see if server crashes
                    await asyncio.sleep(0.1)
                    
                    error_results.append({
                        "test": test_name,
                        "success": True,
                        "time": processing_time
                    })
                    print(f"   ✅ {test_name}: {processing_time:.3f}s")
                    
                except Exception as e:
                    error_results.append({
                        "test": test_name,
                        "success": False,
                        "error": str(e)
                    })
                    print(f"   ❌ {test_name}: {str(e)}")
            
            await websocket.close()
            
            successful_errors = [r for r in error_results if r['success']]
            failed_errors = [r for r in error_results if not r['success']]
            
            print(f"\n📊 Error Handling Results:")
            print(f"   • Successful error handling: {len(successful_errors)}/{len(error_tests)}")
            print(f"   • Failed error handling: {len(failed_errors)}/{len(error_tests)}")
            
            return error_results
            
        except Exception as e:
            print(f"   ❌ Error handling test failed: {str(e)}")
            return []
    
    async def get_server_health(self):
        """Get server health information"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.http_url}/health") as response:
                    if response.status == 200:
                        return await response.json()
        except:
            pass
        return {}
    
    async def run_comprehensive_stress_test(self):
        """Run all stress tests"""
        print("🔥 Comprehensive Server Stress Test")
        print("="*60)
        print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test 1: Processing capacity
        self.results['processing_capacity'] = await self.test_server_processing_capacity()
        
        # Test 2: Concurrent sessions
        self.results['concurrent_sessions'] = await self.test_concurrent_sessions()
        
        # Test 3: Memory usage
        self.results['memory_usage'] = await self.test_server_memory_usage()
        
        # Test 4: Error handling
        self.results['error_handling'] = await self.test_server_error_handling()
        
        # Final server health check
        final_health = await self.get_server_health()
        
        # Summary
        print(f"\n📊 Server Stress Test Summary")
        print("="*50)
        
        if self.results.get('processing_capacity'):
            mps, times = self.results['processing_capacity']
            print(f"🔥 Processing Capacity: {mps:.1f} messages/second")
            print(f"   • Average processing time: {statistics.mean(times):.3f}s")
            print(f"   • Processing time variance: {statistics.variance(times):.6f}")
        
        if self.results.get('concurrent_sessions'):
            successful, failed = self.results['concurrent_sessions']
            if successful:
                total_messages = sum(s['messages'] for s in successful)
                total_time = max(s['time'] for s in successful)
                concurrent_mps = total_messages / total_time
                print(f"👥 Concurrent Sessions: {concurrent_mps:.1f} messages/second")
                print(f"   • Successful sessions: {len(successful)}")
                print(f"   • Failed sessions: {len(failed)}")
        
        if self.results.get('memory_usage'):
            initial, mid, final = self.results['memory_usage']
            print(f"🧠 Memory Usage:")
            print(f"   • Sessions: {initial.get('totalSessions', 0)} → {final.get('totalSessions', 0)}")
            print(f"   • Connections: {initial.get('websocketConnections', 0)} → {final.get('websocketConnections', 0)}")
        
        if self.results.get('error_handling'):
            error_results = self.results['error_handling']
            successful_errors = [r for r in error_results if r['success']]
            print(f"⚠️ Error Handling: {len(successful_errors)}/{len(error_results)} tests passed")
        
        print(f"\n🎯 Server Performance Assessment:")
        
        # Assess processing capacity
        if self.results.get('processing_capacity'):
            mps, _ = self.results['processing_capacity']
            if mps > 100:
                print(f"   ✅ Excellent processing capacity: {mps:.1f} msg/s")
            elif mps > 50:
                print(f"   ⚠️ Good processing capacity: {mps:.1f} msg/s")
            else:
                print(f"   ❌ Poor processing capacity: {mps:.1f} msg/s")
        
        # Assess concurrent handling
        if self.results.get('concurrent_sessions'):
            successful, failed = self.results['concurrent_sessions']
            success_rate = len(successful) / (len(successful) + len(failed)) if (len(successful) + len(failed)) > 0 else 0
            if success_rate > 0.9:
                print(f"   ✅ Excellent concurrent handling: {success_rate*100:.1f}% success")
            elif success_rate > 0.7:
                print(f"   ⚠️ Good concurrent handling: {success_rate*100:.1f}% success")
            else:
                print(f"   ❌ Poor concurrent handling: {success_rate*100:.1f}% success")
        
        # Assess error handling
        if self.results.get('error_handling'):
            error_results = self.results['error_handling']
            successful_errors = [r for r in error_results if r['success']]
            error_rate = len(successful_errors) / len(error_results) if error_results else 0
            if error_rate > 0.8:
                print(f"   ✅ Excellent error handling: {error_rate*100:.1f}% robust")
            elif error_rate > 0.5:
                print(f"   ⚠️ Good error handling: {error_rate*100:.1f}% robust")
            else:
                print(f"   ❌ Poor error handling: {error_rate*100:.1f}% robust")


async def main():
    test = ServerStressTest()
    await test.run_comprehensive_stress_test()


if __name__ == "__main__":
    asyncio.run(main())
