#!/usr/bin/env python3
"""
Realistic Usage Test for ClaudeOnTheBeach Server
Simulates real-world usage patterns and measures performance
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

class RealisticUsageTest:
    def __init__(self):
        self.server_url = "ws://localhost:8081/ws"
        self.http_url = "http://localhost:8081"
        self.results = {}
        
    async def simulate_real_user_session(self, user_id):
        """Simulate a realistic user session with typical usage patterns"""
        try:
            # Generate pairing code
            chars = string.ascii_lowercase + string.digits
            chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
            pairing_code = ''.join(random.choices(chars, k=6))
            
            # Connect
            ws_url = f"{self.server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            
            session_start = time.time()
            message_times = []
            
            # Simulate typical user behavior
            actions = [
                # User connects and takes a screenshot
                {"type": "screenshot", "delay": 2.0},
                # User sends a command to Claude
                {"type": "command", "text": "help me write a python script", "delay": 5.0},
                # User takes another screenshot after Claude responds
                {"type": "screenshot", "delay": 8.0},
                # User sends another command
                {"type": "command", "text": "run the script", "delay": 3.0},
                # User requests recording
                {"type": "command", "text": "/rec", "delay": 2.0},
                # User takes final screenshot
                {"type": "screenshot", "delay": 4.0},
            ]
            
            for i, action in enumerate(actions):
                # Wait as user would
                await asyncio.sleep(action["delay"])
                
                # Send the action
                start_time = time.time()
                
                if action["type"] == "screenshot":
                    message = {
                        "type": "screenshot",
                        "data": {
                            "image": f"base64_screenshot_data_user_{user_id}_action_{i}",
                            "caption": f"Screenshot {i+1} from user {user_id}",
                            "timestamp": time.time()
                        },
                        "source": "realistic_test",
                        "client_id": f"user_{user_id}",
                        "message_id": f"user_{user_id}_screenshot_{i}"
                    }
                else:
                    message = {
                        "type": "command",
                        "text": action["text"],
                        "source": "realistic_test",
                        "client_id": f"user_{user_id}",
                        "message_id": f"user_{user_id}_command_{i}"
                    }
                
                await websocket.send(json.dumps(message))
                processing_time = time.time() - start_time
                message_times.append(processing_time)
            
            session_time = time.time() - session_start
            await websocket.close()
            
            return {
                "user_id": user_id,
                "success": True,
                "session_time": session_time,
                "message_count": len(actions),
                "avg_processing_time": statistics.mean(message_times),
                "message_times": message_times
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "success": False,
                "error": str(e)
            }
    
    async def test_realistic_concurrent_users(self):
        """Test with multiple realistic concurrent users"""
        print("👥 Testing Realistic Concurrent Users")
        print("="*50)
        
        num_users = 10
        print(f"   🚀 Simulating {num_users} concurrent users...")
        
        # Run concurrent user sessions
        tasks = [self.simulate_real_user_session(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_sessions = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_sessions = [r for r in results if isinstance(r, dict) and not r.get('success')]
        
        if successful_sessions:
            total_messages = sum(s['message_count'] for s in successful_sessions)
            total_time = max(s['session_time'] for s in successful_sessions)
            avg_processing_times = [s['avg_processing_time'] for s in successful_sessions]
            
            print(f"\n📊 Realistic User Results:")
            print(f"   • Successful sessions: {len(successful_sessions)}/{num_users}")
            print(f"   • Failed sessions: {len(failed_sessions)}")
            print(f"   • Total messages: {total_messages}")
            print(f"   • Total time: {total_time:.1f}s")
            print(f"   • Messages per second: {total_messages/total_time:.1f}")
            print(f"   • Average processing time: {statistics.mean(avg_processing_times):.3f}s")
            print(f"   • Min processing time: {min(avg_processing_times):.3f}s")
            print(f"   • Max processing time: {max(avg_processing_times):.3f}s")
            
            if failed_sessions:
                print(f"   • Failed session errors:")
                for session in failed_sessions[:3]:
                    print(f"      - User {session['user_id']}: {session['error']}")
        
        return successful_sessions, failed_sessions
    
    async def test_screenshot_performance(self):
        """Test screenshot processing performance specifically"""
        print(f"\n📸 Testing Screenshot Processing Performance")
        print("="*50)
        
        # Generate pairing code
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        pairing_code = ''.join(random.choices(chars, k=6))
        
        try:
            ws_url = f"{self.server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            
            screenshot_times = []
            
            # Send multiple screenshots (like rapid screenshot capture)
            for i in range(20):
                start_time = time.time()
                
                # Create realistic screenshot data
                screenshot_data = {
                    "type": "screenshot",
                    "data": {
                        "image": f"base64_encoded_screenshot_data_{i}_" + "x" * 1000,  # Simulate large image
                        "caption": f"Performance test screenshot {i+1}",
                        "timestamp": time.time(),
                        "size": "1920x1080",
                        "format": "PNG"
                    },
                    "source": "screenshot_test",
                    "client_id": "screenshot_client",
                    "message_id": f"screenshot_{i}_{int(time.time() * 1000)}"
                }
                
                await websocket.send(json.dumps(screenshot_data))
                processing_time = time.time() - start_time
                screenshot_times.append(processing_time)
                
                # Small delay between screenshots
                await asyncio.sleep(0.1)
            
            await websocket.close()
            
            print(f"📊 Screenshot Processing Results:")
            print(f"   • Total screenshots: {len(screenshot_times)}")
            print(f"   • Average processing time: {statistics.mean(screenshot_times):.3f}s")
            print(f"   • Min processing time: {min(screenshot_times):.3f}s")
            print(f"   • Max processing time: {max(screenshot_times):.3f}s")
            print(f"   • Processing time variance: {statistics.variance(screenshot_times):.6f}")
            
            return screenshot_times
            
        except Exception as e:
            print(f"   ❌ Screenshot test failed: {str(e)}")
            return []
    
    async def test_command_processing_performance(self):
        """Test command processing performance"""
        print(f"\n⌨️ Testing Command Processing Performance")
        print("="*50)
        
        # Generate pairing code
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        pairing_code = ''.join(random.choices(chars, k=6))
        
        try:
            ws_url = f"{self.server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            
            command_times = []
            
            # Test different types of commands
            commands = [
                "help me write a python script",
                "/screenshot",
                "/rec",
                "run the script",
                "/status",
                "create a new file",
                "/disconnect",
                "install package requests",
                "run tests",
                "show me the output"
            ]
            
            for i, command in enumerate(commands):
                start_time = time.time()
                
                command_data = {
                    "type": "command",
                    "text": command,
                    "source": "command_test",
                    "client_id": "command_client",
                    "message_id": f"command_{i}_{int(time.time() * 1000)}",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(command_data))
                processing_time = time.time() - start_time
                command_times.append(processing_time)
                
                # Small delay between commands
                await asyncio.sleep(0.05)
            
            await websocket.close()
            
            print(f"📊 Command Processing Results:")
            print(f"   • Total commands: {len(command_times)}")
            print(f"   • Average processing time: {statistics.mean(command_times):.3f}s")
            print(f"   • Min processing time: {min(command_times):.3f}s")
            print(f"   • Max processing time: {max(command_times):.3f}s")
            
            return command_times
            
        except Exception as e:
            print(f"   ❌ Command test failed: {str(e)}")
            return []
    
    async def test_mixed_workload(self):
        """Test mixed workload (screenshots + commands) like real usage"""
        print(f"\n🔄 Testing Mixed Workload")
        print("="*50)
        
        # Generate pairing code
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        pairing_code = ''.join(random.choices(chars, k=6))
        
        try:
            ws_url = f"{self.server_url}?code={pairing_code}"
            websocket = await websockets.connect(ws_url)
            
            mixed_times = []
            
            # Simulate mixed workload (like real user behavior)
            workload = [
                {"type": "screenshot", "data": "base64_screenshot_1"},
                {"type": "command", "text": "help me with this"},
                {"type": "screenshot", "data": "base64_screenshot_2"},
                {"type": "command", "text": "/rec"},
                {"type": "screenshot", "data": "base64_screenshot_3"},
                {"type": "command", "text": "run the command"},
                {"type": "screenshot", "data": "base64_screenshot_4"},
                {"type": "command", "text": "/status"},
                {"type": "screenshot", "data": "base64_screenshot_5"},
                {"type": "command", "text": "show me the results"}
            ]
            
            for i, item in enumerate(workload):
                start_time = time.time()
                
                if item["type"] == "screenshot":
                    message = {
                        "type": "screenshot",
                        "data": {
                            "image": item["data"],
                            "caption": f"Mixed workload screenshot {i+1}",
                            "timestamp": time.time()
                        },
                        "source": "mixed_test",
                        "client_id": "mixed_client",
                        "message_id": f"mixed_screenshot_{i}"
                    }
                else:
                    message = {
                        "type": "command",
                        "text": item["text"],
                        "source": "mixed_test",
                        "client_id": "mixed_client",
                        "message_id": f"mixed_command_{i}"
                    }
                
                await websocket.send(json.dumps(message))
                processing_time = time.time() - start_time
                mixed_times.append(processing_time)
                
                # Random delay like real user
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            await websocket.close()
            
            print(f"📊 Mixed Workload Results:")
            print(f"   • Total actions: {len(mixed_times)}")
            print(f"   • Average processing time: {statistics.mean(mixed_times):.3f}s")
            print(f"   • Min processing time: {min(mixed_times):.3f}s")
            print(f"   • Max processing time: {max(mixed_times):.3f}s")
            
            return mixed_times
            
        except Exception as e:
            print(f"   ❌ Mixed workload test failed: {str(e)}")
            return []
    
    async def run_realistic_test_suite(self):
        """Run all realistic usage tests"""
        print("🎯 Realistic Usage Test Suite")
        print("="*60)
        print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test 1: Realistic concurrent users
        self.results['concurrent_users'] = await self.test_realistic_concurrent_users()
        
        # Test 2: Screenshot performance
        self.results['screenshot_performance'] = await self.test_screenshot_performance()
        
        # Test 3: Command performance
        self.results['command_performance'] = await self.test_command_processing_performance()
        
        # Test 4: Mixed workload
        self.results['mixed_workload'] = await self.test_mixed_workload()
        
        # Summary
        print(f"\n📊 Realistic Usage Summary")
        print("="*50)
        
        if self.results.get('concurrent_users'):
            successful, failed = self.results['concurrent_users']
            if successful:
                total_messages = sum(s['message_count'] for s in successful)
                total_time = max(s['session_time'] for s in successful)
                print(f"👥 Concurrent Users: {total_messages/total_time:.1f} actions/second")
                print(f"   • Success rate: {len(successful)/(len(successful)+len(failed))*100:.1f}%")
        
        if self.results.get('screenshot_performance'):
            screenshot_times = self.results['screenshot_performance']
            if screenshot_times:
                print(f"📸 Screenshot Processing: {statistics.mean(screenshot_times):.3f}s average")
        
        if self.results.get('command_performance'):
            command_times = self.results['command_performance']
            if command_times:
                print(f"⌨️ Command Processing: {statistics.mean(command_times):.3f}s average")
        
        if self.results.get('mixed_workload'):
            mixed_times = self.results['mixed_workload']
            if mixed_times:
                print(f"🔄 Mixed Workload: {statistics.mean(mixed_times):.3f}s average")
        
        print(f"\n🎯 Real-World Performance Assessment:")
        
        # Assess realistic performance
        if self.results.get('concurrent_users'):
            successful, failed = self.results['concurrent_users']
            if successful:
                avg_processing = statistics.mean([s['avg_processing_time'] for s in successful])
                if avg_processing < 0.01:
                    print(f"   ✅ Excellent real-world performance: {avg_processing:.3f}s")
                elif avg_processing < 0.05:
                    print(f"   ⚠️ Good real-world performance: {avg_processing:.3f}s")
                else:
                    print(f"   ❌ Poor real-world performance: {avg_processing:.3f}s")


async def main():
    test = RealisticUsageTest()
    await test.run_realistic_test_suite()


if __name__ == "__main__":
    asyncio.run(main())
