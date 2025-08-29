"""
Command Registry Module
Handles command processing using a registry pattern instead of long elif chains
"""

import asyncio
from typing import Dict, Callable, Any, Optional
from abc import ABC, abstractmethod
import os
import time


class CommandHandler(ABC):
    """Abstract base class for command handlers"""
    
    @abstractmethod
    async def handle(self, wrapper, cmd: str) -> bool:
        """
        Handle a command
        
        Args:
            wrapper: The main wrapper instance
            cmd: The command to handle
            
        Returns:
            True if command was handled, False otherwise
        """
        pass


class ScreenshotCommandHandler(CommandHandler):
    """Handles screenshot commands (/s, /sc, /screenshot)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if cmd.lower() not in ['/screenshot', '/sc', '/s']:
            return False
        
        command_name = '/screenshot' if cmd.lower() == '/screenshot' else ('/sc' if cmd.lower() == '/sc' else '/s')
        print(f"📸 Processing {command_name} command...")
        
        try:
            # Take screenshot
            screenshot = wrapper.capture_terminal_screenshot()
            if screenshot:
                # Save locally if configured
                local_path = wrapper._save_screenshot_locally(screenshot, "manual", "telegram-command")
                
                # Send to Telegram
                await wrapper.send_to_telegram('screenshot', screenshot, 
                    screenshot_type="manual", 
                    source="telegram-command",
                    caption=wrapper._get_screenshot_caption("manual", "telegram-command"))
                
                print(f"📸 Screenshot sent to Telegram")
                
                # Send local path if saved
                if local_path:
                    await wrapper.send_to_telegram('status', f'📸 Screenshot also saved locally: {local_path}')
                
                return True
            else:
                await wrapper.send_to_telegram('status', '❌ Failed to capture screenshot')
                return False
                
        except Exception as e:
            print(f"❌ Screenshot error: {e}")
            await wrapper.send_to_telegram('status', f'❌ Screenshot error: {str(e)}')
            return False


class RecordingCommandHandler(CommandHandler):
    """Handles recording commands (/r, /rec, /rc)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if cmd.lower() not in ['/rec', '/rc', '/r']:
            return False
        
        command_name = '/rec' if cmd.lower() == '/rec' else ('/rc' if cmd.lower() == '/rc' else '/r')
        print(f"🎬 Processing {command_name} command...")
        
        # Get current recording file
        recording_file = wrapper.recording_manager.get_current_recording()
        
        # Enhanced recording file validation and retry logic
        if wrapper.recording_manager.is_recording_active and recording_file:
            print(f"🔍 Validating recording file: {recording_file}")
            
            # Don't check health here - just send the current recording
            # Health checks are done separately in the monitoring loop
            await asyncio.sleep(1)  # Brief pause for stability
            
            # Wait for file to be ready with better validation
            max_retries = 20  # Increased retries
            for attempt in range(max_retries):
                if os.path.exists(recording_file):
                    try:
                        file_size = os.path.getsize(recording_file)
                        if file_size > 1024:  # At least 1KB to ensure it's not empty
                            # Additional validation: check if file is actually a valid video
                            try:
                                import subprocess
                                # Use ffprobe to check if the video file is valid
                                result = subprocess.run([
                                    'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                                    '-show_format', recording_file
                                ], capture_output=True, text=True, timeout=5)
                                
                                if result.returncode == 0:
                                    print(f"✅ Recording file ready and valid: {file_size} bytes (attempt {attempt + 1})")
                                    break
                                else:
                                    print(f"⏳ Recording file exists but not valid video: {file_size} bytes (attempt {attempt + 1})")
                            except (subprocess.TimeoutExpired, FileNotFoundError):
                                # ffprobe not available or timeout, just check file size
                                print(f"✅ Recording file ready: {file_size} bytes (attempt {attempt + 1})")
                                break
                        else:
                            print(f"⏳ Recording file too small: {file_size} bytes (attempt {attempt + 1})")
                    except OSError as e:
                        print(f"⚠️ File access error: {e} (attempt {attempt + 1})")
                else:
                    print(f"⏳ Recording file not found yet (attempt {attempt + 1})")
                
                await asyncio.sleep(0.5)
            else:
                print("⚠️ Recording file not ready after all attempts")
        
        if recording_file and os.path.exists(recording_file):
            try:
                file_size = os.path.getsize(recording_file)
                if file_size > 1024:  # At least 1KB to ensure it's a valid video
                    print(f"🎬 Sending rolling recording: {recording_file} ({file_size} bytes)")
                    await wrapper.recording_manager.send_recording_to_telegram(wrapper.websocket, recording_file, "Last 20 minutes")
                    await wrapper.send_to_telegram('status', f'🎬 Rolling recording sent: {file_size} bytes (last 20 minutes)')
                    
                    # Don't restart recording - let it continue rolling
                    print("🎬 Recording continues with rolling 20-minute buffer")
                    
                    return True
                else:
                    print(f"⚠️ Recording file too small: {file_size} bytes")
                    await wrapper.send_to_telegram('status', f'🎬 Recording file too small ({file_size} bytes). Recording may still be initializing.')
                    
                    return False
            except Exception as e:
                print(f"❌ Failed to send recording: {e}")
                await wrapper.send_to_telegram('status', f'❌ Failed to send recording: {str(e)}')
                
                return False
        else:
            print("🎬 No recording available")
            await wrapper.send_to_telegram('status', '🎬 No recording available. Execute a command first to start recording.')
            return False


class StatusCommandHandler(CommandHandler):
    """Handles status command (/status)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if cmd.lower() != '/status':
            return False
        
        print("📊 Processing /status command...")
        
        try:
            # Take current screenshot and analyze
            screenshot = wrapper.capture_terminal_screenshot()
            if screenshot:
                status_info = await wrapper.get_comprehensive_status(screenshot)
                
                status_msg = f"📊 Current Status:\n"
                status_msg += f"• Activity: {status_info['status']}\n"
                status_msg += f"• Needs Input: {status_info['needs_input']}\n"
                status_msg += f"• Is Complete: {status_info['is_complete']}\n"
                if status_info['question']:
                    status_msg += f"• Question: {status_info['question']}"
                
                await wrapper.send_to_telegram('status', status_msg)
                print("✅ Status sent to Telegram")
                return True
            else:
                await wrapper.send_to_telegram('status', '❌ Failed to capture status screenshot')
                return False
                
        except Exception as e:
            print(f"❌ Status error: {e}")
            await wrapper.send_to_telegram('status', f'❌ Status error: {str(e)}')
            return False


class HelpCommandHandler(CommandHandler):
    """Handles help command (/help)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if cmd.lower() != '/help':
            return False
        
        print("📖 Processing /help command...")
        
        help_text = """🏖️ Claude On The Beach Commands 🌊

📸 Screenshots:
• /s or /sc or /screenshot - Take a screenshot now

🎬 Recordings:
• /r or /rec or /rc - Get rolling 20-minute recording buffer
• /rec-test - Test recording functionality (10s)
• /rs or /rec-status or /rc-status - Show recording status

⌨️ Keyboard Commands:
• /c or /char <seq> - Send keyboard commands
  > = right, < = left, ^ = up, v = down
  e = Enter, x = Escape
  Examples: /c vv>e or /char v v > e

📊 Status:
• /t or /status - Connection status

🔧 Native Claude Commands:
• All Claude commands can be accessed by using double //
• Examples: //help //init //shortcuts //search //exit

💡 Tips:
• Commands are processed immediately
• Recording starts automatically when paired
• Screenshots are taken automatically on completion
• Questions are detected and screenshots sent automatically

Need help? Just ask! 🤝"""
        
        await wrapper.send_to_telegram('status', help_text)
        print("✅ Help sent to Telegram")
        return True


class RecordingStatusCommandHandler(CommandHandler):
    """Handles recording status commands (/rs, /rec-status, /rc-status)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if cmd.lower() not in ['/rec-status', '/rc-status', '/rs']:
            return False
        
        command_name = '/rec-status' if cmd.lower() == '/rec-status' else ('/rc-status' if cmd.lower() == '/rc-status' else '/rs')
        print(f"📊 Processing {command_name} command...")
        
        try:
            status = wrapper.recording_manager.get_recording_status()
            status_msg = f"📊 Recording Status:\n"
            status_msg += f"• Active: {status['is_active']}\n"
            status_msg += f"• Process running: {status['process_running']}\n"
            status_msg += f"• File exists: {status['file_exists']}\n"
            status_msg += f"• File size: {status['file_size']} bytes\n"
            status_msg += f"• Elapsed time: {status['elapsed_time']:.1f}s\n"
            status_msg += f"• File path: {status['file_path'] or 'None'}"
            await wrapper.send_to_telegram('status', status_msg)
            print("✅ Recording status sent to Telegram")
            return True
        except Exception as e:
            print(f"❌ Error in {command_name}: {e}")
            await wrapper.send_to_telegram('status', f'❌ Status error: {str(e)}')
            return False


class RecordingTestCommandHandler(CommandHandler):
    """Handles recording test command (/rec-test)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if cmd.lower() != '/rec-test':
            return False
        
        print("🧪 Processing /rec-test command...")
        
        try:
            # Test recording start
            if wrapper.recording_manager.start_rolling_recording():
                await wrapper.send_to_telegram('status', '✅ Recording test started successfully')
                
                # Wait 10 seconds
                await asyncio.sleep(10)
                
                # Stop recording
                if wrapper.recording_manager.stop_recording():
                    recording_file = wrapper.recording_manager.get_current_recording()
                    if recording_file and os.path.exists(recording_file):
                        file_size = os.path.getsize(recording_file)
                        await wrapper.send_to_telegram('status', f'✅ Recording test completed: {file_size} bytes')
                    else:
                        await wrapper.send_to_telegram('status', '❌ Recording test failed - no file created')
                else:
                    await wrapper.send_to_telegram('status', '❌ Recording test failed - could not stop recording')
            else:
                await wrapper.send_to_telegram('status', '❌ Recording test failed - could not start recording')
            return True
        except Exception as e:
            await wrapper.send_to_telegram('status', f'❌ Recording test error: {str(e)}')
            return False





class CharCommandHandler(CommandHandler):
    """Handles character sequence command (/c, /char)"""
    
    async def handle(self, wrapper, cmd: str) -> bool:
        if not (cmd.lower().startswith('/char ') or cmd.lower().startswith('/c ')):
            return False
        
        print("⌨️ Processing /char command...")
        
        # Parse the character sequence
        if cmd.lower().startswith('/char '):
            char_sequence = cmd[6:].strip()  # Remove '/char ' prefix
        else:
            char_sequence = cmd[3:].strip()  # Remove '/c ' prefix
        
        if not char_sequence:
            await wrapper.send_to_telegram('status', '❌ /c or /char command requires arguments. Example: /c vvv>e or /char v v > e')
            return True
        
        # Send keyboard commands
        success = await wrapper.send_char_sequence(char_sequence)
        
        if success:
            # Wait a moment for the actions to complete
            await asyncio.sleep(0.5)
            
            # Take a screenshot after the actions
            screenshot = wrapper.capture_terminal_screenshot()
            if screenshot:
                await wrapper.send_to_telegram('screenshot', screenshot, 
                    screenshot_type="char-command", 
                    source="telegram-char",
                    caption=f"⌨️ After /char: {char_sequence}")
            
            await wrapper.send_to_telegram('status', f'✅ Executed: /c {char_sequence}')
        else:
            await wrapper.send_to_telegram('status', f'❌ Failed to execute: /c {char_sequence}')
        
        return True


class CommandRegistry:
    """Registry for command handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, CommandHandler] = {
            'screenshot': ScreenshotCommandHandler(),
            'recording': RecordingCommandHandler(),
            'status': StatusCommandHandler(),
            'help': HelpCommandHandler(),
            'recording_status': RecordingStatusCommandHandler(),
            'recording_test': RecordingTestCommandHandler(),
            'char': CharCommandHandler(),
        }
    
    async def handle_command(self, wrapper, cmd: str) -> bool:
        """
        Handle a command using registered handlers
        
        Args:
            wrapper: The main wrapper instance
            cmd: The command to handle
            
        Returns:
            True if command was handled, False if no handler found
        """
        for handler in self.handlers.values():
            if await handler.handle(wrapper, cmd):
                return True
        return False
    
    def register_handler(self, name: str, handler: CommandHandler) -> None:
        """
        Register a new command handler
        
        Args:
            name: Handler name
            handler: Command handler instance
        """
        self.handlers[name] = handler
