#!/usr/bin/env python3
"""
Claude Remote Control via Terminal Automation (macOS)
Uses AppleScript to control Terminal.app and screen capture
"""
import asyncio
import sys
import os
import subprocess
import json
from datetime import datetime, timezone
import logging
import random
import string
import time
import base64
import io
from recording_manager import RecordingManager

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try loading from parent directory .env
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(dotenv_path):
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('claude-wrapper')

try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    print("⚠️ Anthropic client not available. Install with: pip install anthropic")
    CLAUDE_AVAILABLE = False

# Import our new modules
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config, Features
from utils.llm_analyzer import LLMAnalyzer
from utils.question_detector import QuestionDetector
from utils.command_registry import CommandRegistry
from utils.static_screen_detector import StaticScreenDetector
from utils.completion_detector import CompletionDetector
from utils.task_classifier import TaskClassifier


class TerminalClaudeWrapper:
    def __init__(self, start_directory=None, screenshots_folder=None):
        self.server_url = os.getenv('SERVER_URL', 'ws://claudeonthebeach.com:8081/ws')
        self.pairing_code = self._generate_pairing_code()
        self.websocket = None
        self.paired = False
        self.terminal_window_id = None
        self.running = False
        self.start_directory = start_directory or os.getcwd()
        self.start_time = time.time()

        self.is_processing = False  # Track if we're currently processing a command
        
        # Priority system for command processing
        self.command_priority = asyncio.Event()  # Signal when command is being processed
        self.monitoring_paused = False  # Pause monitoring during command processing
        
        # Connection monitoring
        self.last_heartbeat = time.time()  # Track last server communication
        self.heartbeat_timeout = 120  # 2 minutes before checking connection (less aggressive)
        
        # Screenshot coordination to prevent conflicts with recording
        self.screenshot_lock = asyncio.Lock()  # Prevent concurrent screencapture calls
        
        # Task management to prevent duplicate monitoring
        self.active_monitoring_tasks = set()  # Track active monitoring tasks
        self.completion_sent = False  # Track if completion message was sent
        
        self.waiting_for_input = False  # Track if Claude is waiting for input
        self.input_response_event = asyncio.Event()  # Event to signal input response received
        self.pending_input = None  # Store the input response
        self.last_screenshot_hash = None  # Track last screenshot to detect changes
        self.last_screenshot_time = 0  # Track when we last sent a screenshot
        self.last_was_waiting_for_input = False  # Track if last state was waiting for input
        self.last_status_update = 0  # Track when we last sent a status update
        self.last_status_text = ""  # Track last status to avoid duplicates
        self.last_question_sent = ""  # Track last question to avoid repeating
        
        # Screenshot saving functionality - only save if folder is specified
        self.screenshots_folder = screenshots_folder
        self.save_screenshots = screenshots_folder is not None
        self.screenshot_counter = 0  # Counter for unique filenames
        
        # Setup screenshots folder only if specified
        if self.save_screenshots:
            self._setup_screenshots_folder()
        
        # Initialize recording manager
        self.recording_manager = RecordingManager(terminal_window_id=None)  # Will be set after terminal starts
        
        # Initialize new modules
        self.llm_analyzer = None  # Will be set after Claude client is initialized
        self.question_detector = QuestionDetector()
        self.command_registry = CommandRegistry()
        self.static_screen_detector = StaticScreenDetector()
        self.completion_detector = CompletionDetector()
        self.task_classifier = TaskClassifier()
        
        # Initialize Claude client if available
        self.claude_client = None
        if CLAUDE_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.claude_client = Anthropic(api_key=api_key)
                self.llm_analyzer = LLMAnalyzer(self.claude_client)
                print("✅ Claude API client and LLM analyzer initialized")
            else:
                print("⚠️ ANTHROPIC_API_KEY not set - LLM analysis disabled")
                self.llm_analyzer = None
        else:
            self.llm_analyzer = None
        
    def _generate_pairing_code(self) -> str:
        chars = string.ascii_lowercase + string.digits
        chars = chars.replace('o', '').replace('0', '').replace('i', '').replace('l', '').replace('1', '')
        code = ''.join(random.choices(chars, k=6))
        print(f"🎲 Generated pairing code: {code}")
        return code
    
    def _setup_screenshots_folder(self):
        """Setup folder structure for saving screenshots"""
        try:
            # Create main screenshots folder
            if not os.path.exists(self.screenshots_folder):
                os.makedirs(self.screenshots_folder)
                print(f"📁 Created screenshots folder: {self.screenshots_folder}")
            
            # Create session-specific subfolder with timestamp
            from datetime import datetime
            session_folder = datetime.now().strftime("session_%Y%m%d_%H%M%S")
            self.session_screenshots_path = os.path.join(self.screenshots_folder, session_folder)
            
            if not os.path.exists(self.session_screenshots_path):
                os.makedirs(self.session_screenshots_path)
                print(f"📁 Created session folder: {self.session_screenshots_path}")
                
        except Exception as e:
            print(f"❌ Failed to setup screenshots folder: {e}")
            self.save_screenshots = False
    
    def _show_pairing_instructions(self):
        print("\n" + "="*80)
        print("🏖️  CLAUDE ON THE BEACH - REMOTE CONTROL SETUP")
        print("="*80)
        print()
        print("📱 STEP 1: OPEN TELEGRAM")
        print("   • Open Telegram on your phone or computer")
        print("   • Search for: @ClaudeOnTheBeach_bot")
        print("   • Or click this link: https://t.me/ClaudeOnTheBeach_bot")
        print()
        print("🤖 STEP 2: START THE BOT")
        print("   • Send /start to the bot")
        print("   • Wait for the bot to respond")
        print()
        print("🔑 STEP 3: PASTE YOUR PAIRING CODE")
        print("   • Copy this code: " + "="*20)
        print("   • " + " " * 15 + f"🔑 {self.pairing_code} 🔑")
        print("   • " + " " * 15 + "="*20)
        print("   • Paste it in Telegram and send it to the bot")
        print()
        print("✅ STEP 4: WAIT FOR CONFIRMATION")
        print("   • The bot will confirm the connection")
        print("   • You'll see '✅ SUCCESSFULLY PAIRED!' below")
        print()
        print("💻 CLAUDE TERMINAL INFO:")
        print(f"   • Working directory: {self.start_directory}")
        print("   • Recording: 20-minute rolling buffer")
        print("   • Screenshots: Automatic after commands")
        print()
        print("📋 AVAILABLE TELEGRAM COMMANDS:")
        print("   • /sc or /screenshot - Take screenshot now")
        print("   • /rec or /rc - Get 20-minute recording")
        print("   • /status - Show current status")
        print("   • /help - Show all commands")
        print("   • Any text - Send as command to Claude")
        print()
        print("="*80)
        print("⏳ Waiting for you to connect via Telegram...")
        print("="*80)
        
        if not WEBSOCKET_AVAILABLE:
            print("\n⚠️  WebSocket not installed - install with: pip install websockets")
            
        if not SCREENSHOT_AVAILABLE:
            print("\n⚠️  PIL not installed - install with: pip install Pillow")
    
    async def wait_for_pairing(self, timeout: int = 60):
        """Wait for Telegram pairing for specified timeout, then continue."""
        if not WEBSOCKET_AVAILABLE:
            print("⚠️  WebSocket not available - continuing without Telegram connection")
            print("💡 To enable Telegram control, install with: pip install websockets")
            return False
        
        print(f"🔑 Pairing code: {self.pairing_code}")    
        print("⏳ Waiting for Telegram connection...")
        print(f"🔗 Server: {self.server_url}")
        print(f"⏱️  Timeout: {timeout} seconds")
        
        try:
            # Connect to WebSocket
            ws_url = f"{self.server_url}?code={self.pairing_code}"
            print(f"🔌 Connecting to: {ws_url}")
            
            try:
                self.websocket = await asyncio.wait_for(
                    websockets.connect(ws_url),
                    timeout=5
                )
            except asyncio.TimeoutError:
                print("❌ Cannot connect to server - is combined-server.js running?")
                print("💻 Continuing without Telegram connection...")
                return False
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                print("💻 Continuing without Telegram connection...")
                return False
            
            print("✅ WebSocket connected! Waiting for Telegram pairing...")
            print("📱 Open Telegram and send the pairing code to the bot")
            
            # Wait for pairing confirmation
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                    data = json.loads(message)
                    
                    if data.get('type') == 'paired':
                        self.paired = True
                        phone = data.get('phone', 'Unknown')
                        print(f"\n✅ SUCCESSFULLY PAIRED!")
                        print(f"📱 Connected to Telegram user: {phone}")
                        print("💬 Ready for terminal control!")
                        print("="*60)
                        return True
                except asyncio.TimeoutError:
                    # Show progress every 15 seconds with helpful reminders
                    elapsed = int(time.time() - start_time)
                    if elapsed % 15 == 0 and elapsed > 0:
                        remaining = timeout - elapsed
                        print(f"\n⏳ Still waiting for Telegram connection... ({remaining}s left)")
                        print(f"📱 Remember: Send '{self.pairing_code}' to @ClaudeOnTheBeach_bot")
                        if elapsed == 15:
                            print("💡 Tip: Make sure you sent /start to the bot first")
                        elif elapsed == 30:
                            print("💡 Tip: Check that you're messaging the correct bot")
                        elif elapsed == 45:
                            print("💡 Tip: Try copying and pasting the code again")
                    else:
                        print(".", end="", flush=True)
                except websockets.exceptions.ConnectionClosed:
                    print("\n❌ WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"\n⚠️ Warning: {e}")
                    break
                    
        except KeyboardInterrupt:
            print("\n⏭️ Skipping pairing")
        except Exception as e:
            print(f"\n❌ Error during pairing: {e}")
        
        # Timeout reached or error occurred
        print("\n⏱️ Pairing timeout - continuing without Telegram connection")
        print("💻 You can still use the terminal directly")
        print("="*60)
        
        # Close websocket if still open
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
        return False
    
    def start_claude_terminal(self):
        """Start Claude in a new Terminal window using AppleScript"""
        # Escape directory path for AppleScript
        escaped_dir = self.start_directory.replace('\\', '\\\\').replace('"', '\\"')
        
        # Start Claude directly in the terminal window
        applescript = f'''
        tell application "Terminal"
            activate
            
            -- Create new window with Claude
            do script "cd \\"{escaped_dir}\\" && claude"
            
            -- Get the front window ID (the one we just created)
            set windowId to id of front window
            
            return windowId
        end tell
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', applescript], 
                                  capture_output=True, text=True, check=True)
            self.terminal_window_id = result.stdout.strip()
            # Update recording manager with terminal window ID
            self.recording_manager.terminal_window_id = int(self.terminal_window_id)
                
            print(f"✅ Started Claude in Terminal window ID: {self.terminal_window_id}")
            print(f"📁 Working directory: {self.start_directory}")
            time.sleep(4)  # Give time for Claude to start and show trust prompt
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start Terminal: {e}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            return False
    
    async def send_to_telegram(self, message_type, content, **kwargs):
        """Send a message to Telegram via WebSocket"""
        print(f"🔍 DEBUG: websocket={bool(self.websocket)}, paired={self.paired}")
        if not self.websocket or not self.paired:
            print(f"📱 Not connected - would have sent: {message_type}")
            print(f"   websocket exists: {bool(self.websocket)}")
            print(f"   paired status: {self.paired}")
            return False
        
        try:
            # Prepare the message
            message = {
                'type': message_type,
                'content': content,
                **kwargs
            }
            
            # Handle screenshot data
            if message_type == 'screenshot' and hasattr(content, 'save'):
                # Convert PIL image to base64 string
                import io
                import base64
                buffer = io.BytesIO()
                content.save(buffer, format='PNG')
                buffer.seek(0)
                image_bytes = buffer.read()
                image_data = base64.b64encode(image_bytes).decode('utf-8')
                message['content'] = image_data
                message['format'] = 'png'
                
                # Generate proper caption if not provided
                if 'caption' not in message:
                    screenshot_type = kwargs.get('screenshot_type', 'screenshot')
                    source = kwargs.get('source', 'manual')
                    message['caption'] = self._get_screenshot_caption(screenshot_type, source)
                
                print(f"📸 Encoded screenshot: {len(image_bytes)} bytes -> {len(image_data)} base64 chars")
                print(f"📝 Caption: {message.get('caption', 'No caption')}")
            
            # Send message
            await self.websocket.send(json.dumps(message))
            return True
            
        except Exception as e:
            print(f"❌ Failed to send message to Telegram: {e}")
            return False
    
    async def capture_initial_screenshot(self):
        """Capture and send initial screenshot after Claude starts"""
        # Wait for Claude to fully initialize and display prompt
        print("⏳ Waiting for Claude to initialize...")
        await asyncio.sleep(4)  # Longer wait for Claude to fully load
        
        print("📸 Capturing initial Claude state...")
        screenshot = self.capture_terminal_screenshot()
        if screenshot:
            # Always initialize tracking
            self.last_screenshot_hash = self.get_screenshot_hash(screenshot)
            self.last_screenshot_time = time.time()
            
            if self.paired:
                await self.send_to_telegram('screenshot', screenshot, screenshot_type="initial", source="auto-initial")
                print("📸 Initial screenshot sent to Telegram")
            else:
                print("📸 Initial screenshot captured (will send when paired)")
            
            # Save locally if screenshots folder is configured
            if self.save_screenshots:
                self._save_screenshot_locally(screenshot, "initial", "auto-startup")
        else:
            print("❌ Failed to capture initial screenshot - trying again in 2 seconds...")
            await asyncio.sleep(2)
            screenshot = self.capture_terminal_screenshot()
            if screenshot:
                self.last_screenshot_hash = self.get_screenshot_hash(screenshot)
                self.last_screenshot_time = time.time()
                if self.paired:
                    await self.send_to_telegram('screenshot', screenshot, screenshot_type="initial", source="auto-initial-retry")
                    print("📸 Initial screenshot sent to Telegram (retry)")
                if self.save_screenshots:
                    self._save_screenshot_locally(screenshot, "initial", "auto-startup-retry")
            else:
                print("❌ Failed to capture initial screenshot after retry")
    
    async def send_keys_to_terminal(self, text: str, max_retries: int = 3):
        """Send keystrokes to the Terminal window with verification"""
        if not self.terminal_window_id:
            print("❌ No terminal window ID")
            return False
        
        # Debug: show exactly what we received
        print(f"🔍 Original text repr: {repr(text)}")
        print(f"📏 Original length: {len(text)}")
        
        # Clean the text by removing trailing whitespace (including single newlines from Telegram formatting)
        clean_text = text.rstrip('\n\r ').replace('\n', ' ').replace('\r', '').strip()
        
        # Debug: show what we cleaned it to
        print(f"🧹 Cleaned text repr: {repr(clean_text)}")
        print(f"📏 Cleaned length: {len(clean_text)}")
        
        # Always execute commands - special commands like /screenshot are handled before we get here
        # Normal Telegram messages should execute the command, just without extra newlines
        should_execute = True
        
        # Log what we're doing
        print(f"📋 Cleaned text: '{clean_text}'")
        
        if should_execute:
            print(f"⌨️ Executing command: '{clean_text}'")
            return await self._execute_single_command(clean_text, max_retries)
        else:
            # Just send the text without executing
            print(f"⌨️ Sending text only: '{clean_text}' (no execution)")
            return await self._send_text_only(clean_text, max_retries)
    
    async def _execute_single_command(self, text: str, max_retries: int = 3):
        """Execute a single command with verification and defensive retries"""
        unexecuted_detected = False
        
        for attempt in range(max_retries):
            print(f"📝 Attempt {attempt + 1}/{max_retries}")
            
            # Take screenshot before typing
            before_screenshot = self.capture_terminal_screenshot()
            
            # Try keystroke method first (explicit Enter key press)
            keystroke_success = await self._try_keystroke_method(text)
            if keystroke_success:
                # Verify command was written and executed
                execution_verified = await self._verify_command_executed(text, before_screenshot)
                if execution_verified:
                    print(f"✅ Command verified executed via keystroke on attempt {attempt + 1}")
                    return True
                else:
                    print(f"⚠️ Keystroke method didn't execute on attempt {attempt + 1}")
                    # Check if this was due to Enter key failure
                    current_screenshot = self.capture_terminal_screenshot()
                    if current_screenshot:
                        unexecuted_detected = await self._detect_unexecuted_command(text, current_screenshot)
                        if unexecuted_detected:
                            print(f"🔧 RETRY: Detected unexecuted command, sending Enter key")
                            await self._send_enter_key()
                            await asyncio.sleep(0.5)
                            # Re-verify after sending Enter
                            if await self._verify_command_executed(text, before_screenshot):
                                print(f"✅ Command executed after defensive Enter key on attempt {attempt + 1}")
                                return True
            
            # If keystroke failed or Enter key fix didn't work, try do script method as fallback
            print("🔄 Trying do script method...")
            if await self._try_do_script_method(text):
                if await self._verify_command_executed(text, before_screenshot):
                    print(f"✅ Command verified executed via do script on attempt {attempt + 1}")
                    return True
                else:
                    print(f"⚠️ Do script method didn't execute on attempt {attempt + 1}")
            
            # DEFENSIVE: Final check for unexecuted command on last attempt
            if attempt == max_retries - 1 and not unexecuted_detected:
                current_screenshot = self.capture_terminal_screenshot()
                if current_screenshot and await self._detect_unexecuted_command(text, current_screenshot):
                    print(f"🚨 FINAL DEFENSE: Command still unexecuted, making one last Enter attempt")
                    await self._send_enter_key()
                    await asyncio.sleep(1)
                    if await self._verify_command_executed(text, before_screenshot):
                        print(f"✅ Command finally executed with defensive Enter key")
                        return True
            
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in a moment...")
                await asyncio.sleep(1)
        
        print("❌ All attempts failed to execute command")
        return False
    
    async def send_multiline_input(self, text: str, max_retries: int = 3):
        """Send multi-line input using Option+Enter combination"""
        for attempt in range(max_retries):
            print(f"📝 Multi-line attempt {attempt + 1}/{max_retries}")
            
            # Try multiline keystroke method
            if await self._try_multiline_keystroke(text):
                # Verify the input was processed
                await asyncio.sleep(0.5)  # Give Claude time to process
                print(f"✅ Multi-line input sent successfully on attempt {attempt + 1}")
                return True
            
            if attempt < max_retries - 1:
                print(f"🔄 Retrying multi-line input...")
                await asyncio.sleep(1)
        
        print("❌ All multi-line input attempts failed")
        return False

    async def _try_multiline_keystroke(self, text: str):
        """Send multi-line input via keystrokes with Option+Enter"""
        try:
            # Text has already been cleaned, just escape for AppleScript
            escaped_text = (text
                          .replace('\\', '\\\\')
                          .replace('"', '\\"')
                          .replace('\t', ' ')
                          .replace('`', '\\`')
                          .replace('$', '\\$'))
            
            print(f"🎹 Multi-line keystroke: '{text}'")
            print(f"🔤 Escaped text: '{escaped_text}'")
            print(f"📋 Will press Option+Return after typing")
            
            # Send the text followed by Option+Enter
            applescript = f'''
            tell application "Terminal"
                set targetWindow to window id {self.terminal_window_id}
                set frontmost of targetWindow to true
                set index of targetWindow to 1
                activate
            end tell
            
            -- Small delay to ensure Terminal is ready
            delay 0.1
            
            tell application "System Events"
                tell process "Terminal"
                    keystroke "{escaped_text}"
                    delay 0.1
                    -- Send Option+Return for multi-line input
                    key code 36 using {{option down}}
                end tell
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Multi-line keystroke method failed: {e}")
            return False

    async def _send_text_only(self, text: str, max_retries: int = 3):
        """Send text without executing (no Enter key press)"""
        for attempt in range(max_retries):
            print(f"📝 Text-only attempt {attempt + 1}/{max_retries}")
            
            # Try keystroke method first for text-only input
            if await self._try_keystroke_text_only(text):
                print(f"✅ Text sent successfully on attempt {attempt + 1}")
                return True
            
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in a moment...")
                await asyncio.sleep(1)
        
        print("❌ All attempts failed to send text")
        return False
    
    async def _try_keystroke_text_only(self, text: str):
        """Send text via keystrokes without pressing Enter"""
        try:
            # Text has already been cleaned in send_keys_to_terminal, just escape for AppleScript
            # More comprehensive escaping for AppleScript
            escaped_text = (text
                          .replace('\\', '\\\\')    # Escape backslashes first
                          .replace('"', '\\"')      # Escape quotes
                          .replace('\t', ' ')       # Replace tabs with spaces  
                          .replace('`', '\\`')      # Escape backticks
                          .replace('$', '\\$'))     # Escape dollar signs
            
            print(f"🎹 Keystroke text-only: '{text}'")
            
            # Send keystrokes WITHOUT pressing return
            applescript = f'''
            tell application "Terminal"
                set targetWindow to window id {self.terminal_window_id}
                set frontmost of targetWindow to true
                set index of targetWindow to 1
                activate
            end tell
            
            tell application "System Events"
                tell process "Terminal"
                    keystroke "{escaped_text}"
                end tell
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Keystroke text-only method failed: {e}")
            return False
    
    async def _try_keystroke_method(self, text: str):
        """Try sending command via keystrokes"""
        try:
            # Text has already been cleaned in send_keys_to_terminal, just escape for AppleScript
            # More comprehensive escaping for AppleScript
            escaped_text = (text
                          .replace('\\', '\\\\')    # Escape backslashes first
                          .replace('"', '\\"')      # Escape quotes
                          .replace('\t', ' ')       # Replace tabs with spaces  
                          .replace('`', '\\`')      # Escape backticks
                          .replace('$', '\\$'))     # Escape dollar signs
            
            print(f"🎹 Keystroke method: '{text}'")
            print(f"🔤 Escaped text: '{escaped_text}'")
            print(f"📋 Will press RETURN after typing")
            
            # Send the keystrokes with explicit return
            applescript = f'''
            tell application "Terminal"
                set targetWindow to window id {self.terminal_window_id}
                set frontmost of targetWindow to true
                set index of targetWindow to 1
                activate
            end tell
            
            -- Small delay to ensure Terminal is ready
            delay 0.1
            
            tell application "System Events"
                tell process "Terminal"
                    keystroke "{escaped_text}"
                    delay 0.1
                    keystroke return
                end tell
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Keystroke method failed: {e}")
            return False
    
    async def _try_do_script_method(self, text: str):
        """Try sending command via do script"""
        try:
            # Text has already been cleaned in send_keys_to_terminal, just escape for AppleScript
            # More comprehensive escaping for AppleScript
            escaped_text = (text
                          .replace('\\', '\\\\')    # Escape backslashes first
                          .replace('"', '\\"')      # Escape quotes
                          .replace('\t', ' ')       # Replace tabs with spaces  
                          .replace('`', '\\`')      # Escape backticks
                          .replace('$', '\\$'))     # Escape dollar signs
            
            print(f"📜 Do script method: '{text}'")
            
            applescript = f'''
            tell application "Terminal"
                set targetWindow to window id {self.terminal_window_id}
                do script "{escaped_text}" in targetWindow
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Do script method failed: {e}")
            return False
    
    async def _send_enter_key(self):
        """Send just the Enter key to execute a typed command"""
        try:
            applescript = f'''
            tell application "Terminal"
                set targetWindow to window id {self.terminal_window_id}
                set frontmost of targetWindow to true
                set index of targetWindow to 1
                activate
            end tell
            
            delay 0.1
            
            tell application "System Events"
                tell process "Terminal"
                    keystroke return
                end tell
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            print("✅ Sent Enter key to execute typed command")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to send Enter key: {e}")
            return False

    async def _validate_terminal_state(self, screenshot):
        """Validate terminal state for errors or issues that need attention"""
        if not self.claude_client or not screenshot:
            return {"has_error": False, "needs_attention": False}
            
        try:
            # Convert PIL image to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Prompt to detect terminal issues
            prompt = """Analyze this terminal screenshot for any issues that need attention.

Look for:
- Error messages (red text, "Error:", "Failed:", etc.)
- Stuck processes that might need interruption
- Permission issues or access denied messages
- Broken connections or timeouts
- Unusual prompts or unexpected states

Return JSON:
{
  "has_error": true/false,
  "needs_attention": true/false,
  "error_message": "brief description if has_error is true",
  "attention_message": "brief description if needs_attention is true"
}

If everything looks normal, return has_error and needs_attention as false."""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=100,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text", 
                                "text": prompt
                            }
                        ]
                    }]
                )
            )
            
            response_text = response.content[0].text.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Try to find JSON in response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return {
                        "has_error": result.get("has_error", False),
                        "needs_attention": result.get("needs_attention", False),
                        "error_message": result.get("error_message", ""),
                        "attention_message": result.get("attention_message", "")
                    }
                except json.JSONDecodeError:
                    pass
            
            return {"has_error": False, "needs_attention": False}
            
        except Exception as e:
            print(f"⚠️ Failed to validate terminal state: {e}")
            return {"has_error": False, "needs_attention": False}

    async def _detect_unexecuted_command(self, command: str, screenshot):
        """Detect if command was typed but not executed (Enter key failure)"""
        if not self.claude_client or not screenshot:
            return False
            
        try:
            # Convert PIL image to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Specific prompt to detect unexecuted commands
            prompt = f"""Look at this terminal screenshot. I just tried to execute the command: "{command}"

Is this command visible on the screen but NOT executed? Look for signs like:
- The command text is visible at a prompt (like "$ {command}" or "> {command}")
- Cursor is at the end of the command line 
- No output or response from the command yet
- Still showing the same prompt without executing

This suggests the Enter key wasn't properly sent.

Reply with just: YES (command typed but not executed) or NO (command was executed or not visible)"""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=10,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text", 
                                "text": prompt
                            }
                        ]
                    }]
                )
            )
            
            response_text = response.content[0].text.strip().upper()
            is_unexecuted = "YES" in response_text
            
            if is_unexecuted:
                print(f"🚨 DETECTED: Command '{command}' was typed but not executed!")
            
            return is_unexecuted
            
        except Exception as e:
            print(f"⚠️ Failed to detect unexecuted command: {e}")
            return False

    async def _verify_command_executed(self, command: str, before_screenshot, max_wait: int = 2):
        """Verify that command was actually executed by checking terminal state"""
        try:
            check_start_time = time.time()
            
            for check in range(max_wait):
                # Only wait on first check to let command register
                if check == 0:
                    await asyncio.sleep(0.2)
                
                # DEFENSIVE: Timeout check to avoid infinite verification loops
                elapsed_verification_time = time.time() - check_start_time
                if elapsed_verification_time > 15:  # Max 15 seconds for verification
                    print(f"⏰ Verification timeout after {elapsed_verification_time:.1f}s - assuming command completed")
                    return True  # Assume success to avoid blocking
                
                current_screenshot = self.capture_terminal_screenshot()
                if not current_screenshot:
                    continue
                
                # DEFENSIVE CODE: Enhanced validation for command execution
                if check == 1:  # Check after first wait for defensive action
                    is_unexecuted = await self._detect_unexecuted_command(command, current_screenshot)
                    if is_unexecuted:
                        print(f"🔧 DEFENSIVE ACTION: Sending Enter key for unexecuted command")
                        # Send just Enter key to execute the typed command
                        await self._send_enter_key()
                        await asyncio.sleep(0.5)  # Wait for execution
                        # Take another screenshot to verify
                        current_screenshot = self.capture_terminal_screenshot()
                        
                        # Double-check that the Enter key worked
                        if current_screenshot:
                            still_unexecuted = await self._detect_unexecuted_command(command, current_screenshot)
                            if still_unexecuted:
                                print(f"⚠️ Command still unexecuted after Enter key - may need different approach")
                            else:
                                print(f"✅ Defensive Enter key successfully executed the command")
                
                # Additional validation: Check if terminal is in an error state
                if check >= 2 and current_screenshot:
                    terminal_state = await self._validate_terminal_state(current_screenshot)
                    if terminal_state.get('has_error', False):
                        print(f"⚠️ Terminal shows error state: {terminal_state.get('error_message', 'Unknown error')}")
                    elif terminal_state.get('needs_attention', False):
                        print(f"ℹ️ Terminal needs attention: {terminal_state.get('attention_message', 'Unknown issue')}")
                
                # Use LLM to analyze if command is executing
                if self.claude_client:
                    analysis = await self.analyze_screenshot_with_llm(current_screenshot)
                    
                    # Check if command is being processed or completed
                    summary = analysis.get('summary', '').lower()
                    
                    # Look for signs that command is executing
                    executing_indicators = [
                        'processing', 'running', 'executing', 'working',
                        'installing', 'building', 'compiling', 'creating',
                        'writing', 'generating', 'loading'
                    ]
                    
                    # Or look for completion
                    completion_indicators = [
                        'completed', 'finished', 'done', 'created', 'saved',
                        'installed', 'built', 'generated'
                    ]
                    
                    if any(indicator in summary for indicator in executing_indicators + completion_indicators):
                        print(f"✅ Command execution verified: {summary}")
                        return True
                    
                    # If it needs input, command probably started
                    if analysis.get('needs_input', False):
                        print(f"✅ Command prompted for input: {analysis.get('question', 'waiting for input')}")
                        return True
                
                # Fallback: compare screenshots to see if anything changed
                if current_screenshot != before_screenshot:
                    print("✅ Terminal state changed - command likely executed")
                    return True
                
                await asyncio.sleep(1)
            
            print("⚠️ No evidence command executed, but assuming success for Claude commands")
            return True  # Be more lenient - assume Claude commands work
            
        except Exception as e:
            print(f"⚠️ Verification error: {e}")
            return False
    
    async def wait_for_claude_prompt(self, timeout: int = 10):
        """Check if Claude is ready for input by analyzing terminal state"""
        try:
            print("🔍 Checking if Claude is ready for input...")
            
            # Take a screenshot to see current state
            screenshot = self.capture_terminal_screenshot()
            if not screenshot:
                print("⚠️ Could not capture screenshot to check Claude state")
                return True  # Assume ready if we can't check
            
            # Use LLM to analyze if Claude is ready for input
            if self.claude_client:
                analysis = await self.analyze_screenshot_with_llm(screenshot)
                
                # If Claude is asking a question or waiting for input, it's ready
                if analysis.get('needs_input', False):
                    print("✅ Claude is waiting for input - ready to send command")
                    return True
                
                # If process is complete (showing prompt), it's ready
                if analysis.get('is_complete', False):
                    print("✅ Claude shows prompt - ready for new command")
                    return True
                
                # If still processing, not ready yet
                print("⏳ Claude is still processing - not ready for input")
                return False
            else:
                # Without LLM analysis, do a simple heuristic check
                # Convert screenshot to text and look for common prompt indicators
                print("🔍 Using heuristic check (no LLM available)")
                # For now, assume ready (could enhance with OCR later)
                return True
            
        except Exception as e:
            print(f"⚠️ Error checking Claude state: {e}")
            return True  # Assume ready if check fails
    
    def _send_via_do_script(self, text: str):
        """Send text via do script to specific window"""
        try:
            # Clean and escape the text
            clean_text = text.strip()
            # Escape for do script
            escaped_text = clean_text.replace('\\', '\\\\').replace('"', '\\"')
            
            print(f"🔄 Using do script method for: '{clean_text}'")
            
            # Send to the specific window's active tab
            applescript = f'''
            tell application "Terminal"
                set targetWindow to window id {self.terminal_window_id}
                do script "{escaped_text}" in targetWindow
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            print(f"✅ Do script method succeeded")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Do script method failed: {e}")
            print(f"   Error: {e.stderr}")
            return False
    
    def _send_keys_simple(self, text: str):
        """Simpler keystroke sending without frontmost"""
        try:
            print("🔄 Using simple keystroke method...")
            
            # Just activate Terminal and send keystrokes
            applescript = f'''
            tell application "Terminal"
                activate
            end tell
            
            delay 1
            
            tell application "System Events"
                keystroke "{text.strip()}"
                keystroke return
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True, check=True)
            print(f"✅ Alternative method succeeded")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Alternative method also failed: {e}")
            print("\n⚠️  IMPORTANT: You need to grant accessibility permissions:")
            print("   1. Open System Preferences → Security & Privacy → Privacy → Accessibility")
            print("   2. Add and enable these apps:")
            print("      - Terminal.app")
            print("      - Python or Python3")
            print("      - Your terminal app (if using iTerm2, etc.)")
            return False
    
    async def send_char_sequence(self, sequence: str):
        """Send a sequence of keyboard commands to the terminal
        
        Args:
            sequence: A string that can be either:
                     - Space-separated: "v v v > e"
                     - Or continuous: "vvv>e" (will be split automatically)
                     
                     Characters:
                     > = right arrow
                     < = left arrow  
                     ^ = up arrow
                     v = down arrow
                     e = Enter key
                     x = Escape key
        
        Example: "v v v > > e" or "vvv>>e" sends 3 down arrows, 2 right arrows, then Enter
        """
        try:
            if not self.terminal_window_id:
                print("❌ No terminal window ID")
                return False
            
            print(f"🎮 Processing character sequence: '{sequence}'")
            
            # Parse the sequence - handle both space-separated and continuous
            if ' ' in sequence:
                # Space-separated format: "v v v > x"
                commands = sequence.split()
            else:
                # Continuous format: "vvv>x" - split into individual characters
                commands = list(sequence)
            
            # Map characters to AppleScript key codes
            key_map = {
                '>': 'key code 124',  # Right arrow
                '<': 'key code 123',  # Left arrow
                '^': 'key code 126',  # Up arrow
                'v': 'key code 125',  # Down arrow
                'e': 'return',        # Enter key
                'x': 'key code 53'    # Escape key
            }
            
            # Build AppleScript commands
            applescript_commands = []
            for cmd in commands:
                cmd_lower = cmd.lower().strip()
                if cmd_lower and cmd_lower in key_map:
                    applescript_commands.append(key_map[cmd_lower])
                elif cmd_lower:  # Only warn if not empty
                    print(f"⚠️ Unknown command: '{cmd}' - skipping")
            
            if not applescript_commands:
                print("❌ No valid commands found in sequence")
                return False
            
            print(f"📋 Parsed {len(applescript_commands)} valid commands")
            
            # Build the AppleScript - use simpler approach without frontmost
            applescript = '''
            tell application "Terminal"
                activate
            end tell
            
            delay 0.2
            
            tell application "System Events"
            '''
            
            # Add each key command with a small delay between them
            for i, key_cmd in enumerate(applescript_commands):
                if key_cmd == 'return':
                    applescript += f'\n                keystroke return'
                else:
                    applescript += f'\n                {key_cmd}'
                
                # Add small delay between commands (except after the last one)
                if i < len(applescript_commands) - 1:
                    applescript += '\n                delay 0.1'
            
            applescript += '''
            end tell
            '''
            
            print(f"📝 Executing AppleScript with {len(applescript_commands)} commands")
            
            # Execute the AppleScript
            result = subprocess.run(['osascript', '-e', applescript],
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Successfully sent {len(applescript_commands)} keyboard commands")
                return True
            else:
                print(f"❌ AppleScript failed: {result.stderr}")
                # Try alternative method without window activation
                return await self._send_char_sequence_fallback(applescript_commands)
                
        except subprocess.TimeoutExpired:
            print("❌ Command timed out")
            return False
        except Exception as e:
            print(f"❌ Error sending char sequence: {e}")
            return False
    
    async def _send_char_sequence_fallback(self, commands):
        """Fallback method for sending keyboard commands"""
        try:
            print("🔄 Trying fallback method...")
            
            # Simple AppleScript without Terminal activation
            applescript = 'tell application "System Events"\n'
            
            for i, key_cmd in enumerate(commands):
                if key_cmd == 'return':
                    applescript += '    keystroke return\n'
                else:
                    applescript += f'    {key_cmd}\n'
                
                if i < len(commands) - 1:
                    applescript += '    delay 0.1\n'
            
            applescript += 'end tell'
            
            result = subprocess.run(['osascript', '-e', applescript],
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Fallback method succeeded")
                return True
            else:
                print(f"❌ Fallback also failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Fallback error: {e}")
            return False
    
    def get_screenshot_hash(self, screenshot):
        """Get a hash of the screenshot for comparison"""
        if not screenshot:
            return None
        try:
            import hashlib
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            return hashlib.md5(buffer.getvalue()).hexdigest()
        except Exception as e:
            print(f"⚠️ Error computing screenshot hash: {e}")
            return None
    
    def _questions_are_similar(self, q1: str, q2: str, threshold: float = 0.8) -> bool:
        """Check if two questions are semantically similar"""
        # Remove common question patterns that vary
        import re
        
        def normalize_question(q):
            # Remove common variable parts
            q = re.sub(r'\b(options?:?|1\.|2\.|3\.|yes|no)\b', '', q, flags=re.IGNORECASE)
            q = re.sub(r'\b(press|for|shortcuts?|enter|return)\b', '', q, flags=re.IGNORECASE)
            q = re.sub(r'\([^)]*\)', '', q)  # Remove parenthetical content
            q = re.sub(r'[^\w\s]', ' ', q)  # Replace punctuation with spaces
            q = ' '.join(q.split())  # Normalize whitespace
            return q.strip()
        
        norm_q1 = normalize_question(q1)
        norm_q2 = normalize_question(q2)
        
        # If either normalized question is too short, use exact match
        if len(norm_q1) < 10 or len(norm_q2) < 10:
            return norm_q1 == norm_q2
        
        # Simple similarity check - count common words
        words1 = set(norm_q1.lower().split())
        words2 = set(norm_q2.lower().split())
        
        # Remove very common words that don't add meaning
        stop_words = {'do', 'you', 'want', 'to', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'by', 'for', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 and not words2:
            return True
        if not words1 or not words2:
            return False
            
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= threshold
    
    async def capture_terminal_screenshot_async(self):
        """Capture screenshot with coordination to prevent recording conflicts"""
        async with self.screenshot_lock:
            # Add a small delay to ensure recording process isn't interrupted
            await asyncio.sleep(0.1)
            screenshot = self._capture_terminal_screenshot_internal()
            # Add another small delay after screenshot to let recording stabilize
            await asyncio.sleep(0.1)
            return screenshot
    
    def capture_terminal_screenshot(self):
        """Capture screenshot of the terminal even if not in front"""
        # Always use the internal method directly for sync calls
        # The async version should be called explicitly when needed
        return self._capture_terminal_screenshot_internal()
    
    def _capture_terminal_screenshot_internal(self):
        """Internal screenshot capture method"""
        if not SCREENSHOT_AVAILABLE:
            print("⚠️ Screenshot not available - PIL not installed")
            return None
            
        if not self.terminal_window_id:
            print("⚠️ No terminal window ID available")
            return None
            
        try:
            import tempfile
            import os
            
            # Create temp file for screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            
            print(f"🔍 Attempting to capture Terminal window ID: {self.terminal_window_id}")
            
            # Method 1: Use AppleScript with screencapture -o flag (PROVEN TO WORK)
            # The -o flag captures onscreen-only windows, which works even when behind other windows
            try:
                print("📸 Using AppleScript with onscreen-only capture...")
                
                content_capture_script = f'''
                tell application "Terminal"
                    set targetWindow to window id {self.terminal_window_id}
                    set tempPath to "{tmp_path}"
                    
                    try
                        do shell script "screencapture -x -o -l " & {self.terminal_window_id} & " " & quoted form of tempPath
                        return "SUCCESS"
                    on error errMsg
                        return "FAILED:" & errMsg
                    end try
                end tell
                '''
                
                result = subprocess.run(['osascript', '-e', content_capture_script], 
                                      capture_output=True, text=True, check=True)
                
                if result.stdout.startswith("SUCCESS") and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    # Load the screenshot
                    from PIL import Image
                    screenshot = Image.open(tmp_path)
                    
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    
                    print(f"📸 Onscreen-only window capture successful: {screenshot.size}")
                    return screenshot
                else:
                    print(f"⚠️ Onscreen-only capture failed: {result.stdout}")
                
            except Exception as e:
                print(f"⚠️ Method 1 (onscreen-only) failed: {e}")
            
            # Method 2: Try direct screencapture -l without AppleScript
            try:
                print("🔍 Trying direct screencapture with window ID...")
                
                capture_cmd = [
                    'screencapture',
                    '-x',  # No sound
                    '-o',  # Onscreen-only flag
                    '-l', str(self.terminal_window_id),  # Window ID
                    tmp_path
                ]
                
                result = subprocess.run(capture_cmd, capture_output=True)
                
                if result.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    # Load the screenshot
                    from PIL import Image
                    screenshot = Image.open(tmp_path)
                    
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    
                    print(f"📸 Direct onscreen capture successful: {screenshot.size}")
                    return screenshot
                else:
                    print(f"⚠️ Direct onscreen capture failed (return code: {result.returncode})")
                
            except Exception as e:
                print(f"⚠️ Method 2 (direct) failed: {e}")
            
            # Method 3: Fallback to region capture (may show overlapping windows)
            try:
                print("🔍 Falling back to region capture...")
                
                bounds_script = f'''
                tell application "Terminal"
                    set targetWindow to window id {self.terminal_window_id}
                    return bounds of targetWindow
                end tell
                '''
                
                result = subprocess.run(['osascript', '-e', bounds_script], 
                                      capture_output=True, text=True, check=True)
                
                bounds_str = result.stdout.strip()
                bounds = [int(x.strip()) for x in bounds_str.split(',')]
                x1, y1, x2, y2 = bounds
                
                # Region capture
                capture_cmd = [
                    'screencapture',
                    '-x',  # No sound
                    '-R', f'{x1},{y1},{x2-x1},{y2-y1}',
                    tmp_path
                ]
                
                subprocess.run(capture_cmd, check=True, capture_output=True)
                
                # Load the screenshot
                from PIL import Image
                screenshot = Image.open(tmp_path)
                
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                print(f"📸 Region capture successful (may show overlapping content): {screenshot.size}")
                return screenshot
                
            except Exception as e:
                print(f"⚠️ Method 3 (region) failed: {e}")
            
            # Method 4: Last resort - quick window focus with better restoration
            print("📸 Using enhanced quick focus method...")
            try:
                quick_focus_script = f'''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                end tell
                
                tell application "Terminal"
                    set targetWindow to window id {self.terminal_window_id}
                    
                    -- Quickly bring to front
                    set index of targetWindow to 1
                    activate
                    delay 0.05  -- Very brief delay
                    
                    set windowBounds to bounds of targetWindow
                end tell
                
                -- Immediately restore focus
                if frontApp is not "Terminal" then
                    tell application frontApp to activate
                end if
                
                return windowBounds
                '''
                
                result = subprocess.run(['osascript', '-e', quick_focus_script], 
                                      capture_output=True, text=True, check=True)
                
                bounds_str = result.stdout.strip()
                bounds = [int(x.strip()) for x in bounds_str.split(',')]
                x1, y1, x2, y2 = bounds
                
                # Quick region capture
                capture_cmd = [
                    'screencapture',
                    '-x',  # No sound
                    '-R', f'{x1},{y1},{x2-x1},{y2-y1}',
                    tmp_path
                ]
                
                subprocess.run(capture_cmd, check=True, capture_output=True)
                
                # Load the screenshot
                from PIL import Image
                screenshot = Image.open(tmp_path)
                
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                print(f"📸 Quick focus capture successful: {screenshot.size}")
                return screenshot
                
            except Exception as e:
                print(f"⚠️ Method 4 failed: {e}")
            
            print("❌ All capture methods failed")
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Screenshot capture error: {e}")
            return None
        except Exception as e:
            print(f"❌ Failed to capture screenshot: {e}")
            return None
    
    def capture_dual_screenshots(self, delay_ms=100):
        """Capture two screenshots with a small delay for comparison"""
        if not self.terminal_window_id:
            print("⚠️ No terminal window ID - cannot capture screenshots")
            return None, None
        
        try:
            # Capture first screenshot
            first_screenshot = self.capture_terminal_screenshot()
            if not first_screenshot:
                return None, None
            
            # Wait for the specified delay
            time.sleep(delay_ms / 1000.0)
            
            # Capture second screenshot
            second_screenshot = self.capture_terminal_screenshot()
            if not second_screenshot:
                return first_screenshot, None
            
            print(f"📸 Dual screenshots captured with {delay_ms}ms delay")
            return first_screenshot, second_screenshot
            
        except Exception as e:
            print(f"❌ Failed to capture dual screenshots: {e}")
            return None, None
    
    def _save_screenshot_locally(self, screenshot, screenshot_type="manual", source="telegram"):
        """Save screenshot locally with metadata"""
        if not self.save_screenshots or not screenshot:
            return None
            
        try:
            self.screenshot_counter += 1
            from datetime import datetime
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{self.screenshot_counter:04d}_{screenshot_type}_{timestamp}.png"
            filepath = os.path.join(self.session_screenshots_path, filename)
            
            # Save the screenshot
            screenshot.save(filepath, format='PNG')
            
            # Create metadata file
            metadata = {
                'filename': filename,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': source,  # 'telegram', 'auto-question', 'auto-completion'
                'type': screenshot_type,
                'pairing_code': self.pairing_code,
                'counter': self.screenshot_counter
            }
            
            metadata_file = os.path.join(self.session_screenshots_path, f"screenshot_{self.screenshot_counter:04d}_{screenshot_type}_{timestamp}.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"📸 Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Failed to save screenshot locally: {e}")
            return None

    def _get_screenshot_caption(self, screenshot_type, source):
        """Generate appropriate caption for screenshot based on type and source"""
        captions = {
            ('manual', 'telegram-command'): '📸 Screenshot (requested by user)',
            ('manual', 'telegram'): '📸 Screenshot (requested by user)', 
            ('status', 'telegram-status'): '📊 Status Screenshot',
            ('initial', 'auto-initial'): '🚀 Initial Claude State',
            ('question', 'auto-question'): '❓ Auto-Screenshot: Claude is asking a question',
            ('completion', 'auto-completion'): '✅ Auto-Screenshot: Task completed',
            ('claude-command', 'telegram-claude-cmd'): '🔧 Claude Command Output'
        }
        
        # Default caption if combination not found
        key = (screenshot_type, source)
        return captions.get(key, f'📸 Screenshot ({screenshot_type})')
    

    
    async def handle_telegram_commands(self):
        """Listen for Telegram commands"""
        print("🔄 Starting Telegram command handler...")
        if not self.websocket:
            print("❌ No websocket connection")
            return
        if not self.paired:
            print("❌ Not paired")
            return
            
        print("✅ Telegram handler ready, waiting for commands...")
        
        try:
            async for message in self.websocket:
                print(f"📨 Raw message received: {message}")
                # Update heartbeat on any message from server
                self.last_heartbeat = time.time()
                data = json.loads(message)
                
                if data.get('type') == 'command':
                    cmd = data.get('text', '')
                    print(f"\n📱 [Telegram Command]: '{cmd}'")

                    
                    
                    print(f"🔍 Raw command repr: {repr(cmd)}")
                    print(f"📏 Command length: {len(cmd)}")
                    
                    # Strip whitespace for command checking
                    cmd_stripped = cmd.strip()
                    
                    # Handle special commands using command registry
                    if await self.command_registry.handle_command(self, cmd_stripped):
                        continue
                    

                    

                    

                    

                    
                    elif cmd_stripped.startswith('//') and len(cmd_stripped) > 2:
                        # Handle double-slash commands - convert //command to /command in Claude
                        claude_command = cmd_stripped[1:]  # Remove one slash: //help -> /help
                        print(f"🔧 Processing double-slash command: {cmd_stripped} -> {claude_command}")
                        print(f"🔍 DEBUG: Will send '{claude_command}' to Claude terminal only, NOT back to server")
                        
                        # Send the command directly to Claude terminal (NOT back to server)
                        success = await self.send_keys_to_terminal(claude_command)
                        
                        if success:
                            print(f"✅ Successfully sent '{claude_command}' to Claude terminal")
                            # Wait a moment for Claude to process the command
                            await asyncio.sleep(1.5)
                            
                            # Take a screenshot to show the command output
                            screenshot = await self.capture_terminal_screenshot_async()
                            if screenshot:
                                await self.send_to_telegram('screenshot', screenshot, 
                                    screenshot_type="claude-command", 
                                    source="telegram-claude-cmd",
                                    caption=f"🔧 Claude: {claude_command}")
                                print(f"📸 Claude command screenshot sent to Telegram: {claude_command}")
                            
                            # Only send a simple status message, not the command text that could trigger server
                            await self.send_to_telegram('status', f'🔧 Command executed in Claude terminal')
                        else:
                            await self.send_to_telegram('status', f'❌ Failed to execute command in Claude terminal')
                        continue
                    
                    # Check current terminal state to determine if Claude needs input
                    needs_input_now = False
                    
                    # Take a quick screenshot and analyze if Claude is waiting for input
                    if self.is_processing:  # Only check if we're actively processing something
                        print(f"🔍 Checking if Claude needs input right now...")
                        screenshot = await self.capture_terminal_screenshot_async()
                        if screenshot:
                            needs_input_now = await self.check_needs_input_quick(screenshot)
                            if needs_input_now:
                                print(f"✅ Claude IS waiting for input")
                            else:
                                print(f"❌ Claude is NOT waiting for input")
                        else:
                            print(f"⚠️ Screenshot failed, checking waiting_for_input flag: {self.waiting_for_input}")
                    
                    # Decide based on real-time check OR existing waiting_for_input flag
                    print(f"🎯 Decision: needs_input_now={needs_input_now}, waiting_for_input={self.waiting_for_input}")
                    if needs_input_now or self.waiting_for_input:
                        # This is an input response, not a new command
                        print(f"📝 Received input response: '{cmd}'")
                        
                        # Set command priority for input responses too
                        self.command_priority.set()
                        self.monitoring_paused = True
                        print(f"🚨 Input response: Setting priority mode")
                        
                        # Recording should already be active - just ensure it's running
                        if not self.recording_manager.is_recording_active:
                            print(f"🎬 Starting recording for input response")
                            self.recording_manager.start_rolling_recording()
                        else:
                            print(f"🎬 Recording continues during input response")
                        
                        # Always send directly to terminal when input is needed
                        print(f"➡️ Sending '{cmd}' directly to terminal")
                        
                        # Wait a moment for Claude to be ready
                        await asyncio.sleep(0.5)
                        
                        # Check if this is a multi-line input scenario
                        is_multiline_prompt = False
                        if self.last_question_sent:
                            is_multiline_prompt = ('option+enter' in self.last_question_sent.lower() or 
                                                 'multi-line' in self.last_question_sent.lower())
                        
                        # For multi-line prompts, we need to handle this specially
                        if is_multiline_prompt:
                            print(f"🔄 Handling multi-line input: '{cmd}'")
                            # For multi-line messages, we need to send Option+Enter instead of just Enter
                            success = await self.send_multiline_input(cmd)
                        else:
                            # Send the command normally
                            success = await self.send_keys_to_terminal(cmd)
                        
                        if success:
                            # Clear waiting state and question tracking
                            self.waiting_for_input = False
                            self.last_was_waiting_for_input = False
                            self.last_question_sent = ""  # Clear so new questions can be sent
                            print(f"✅ Input '{cmd}' successfully sent")
                            
                            # Clear priority before starting monitoring (to avoid infinite loop)
                            self.command_priority.clear()
                            self.monitoring_paused = False
                            print(f"✅ Input response priority cleared before monitoring")
                            
                            # Start monitoring for completion after input response (non-blocking)
                            print(f"🚀 Starting monitoring for completion after input: {cmd}")
                            await self.start_monitoring_task(f"Completion after input: {cmd}", "input")
                            print(f"🏁 Monitoring started for input (non-blocking)")
                        else:
                            print(f"❌ Failed to send input '{cmd}', will retry on next message")
                            
                        await self.send_to_telegram('status', f'📝 Sent response: {cmd}')
                    else:
                        # Start recording only if not already active (continuous rolling buffer)
                        if not self.recording_manager.is_recording_active:
                            print(f"🎬 Starting rolling 20-minute recording buffer for new command")
                            self.recording_manager.start_rolling_recording()
                        else:
                            print(f"🎬 Recording already active - continuing rolling buffer")
                        
                        # Set command priority immediately when command is received
                        self.command_priority.set()
                        self.monitoring_paused = True
                        print(f"🚨 Command received: Setting priority mode")
                        
                        # Execute command immediately instead of queuing
                        print(f"⚡ Executing command immediately: '{cmd}'")
                        
                        # Execute the command immediately
                        success = await self._execute_single_command(cmd)
                        if success:
                            print(f"✅ Command executed successfully: {cmd}")
                            
                            # Clear priority before starting monitoring (to avoid infinite loop)
                            self.command_priority.clear()
                            self.monitoring_paused = False
                            print(f"✅ Command priority cleared before monitoring")
                            
                            # Start smart monitoring for the command (non-blocking)
                            print(f"🚀 Starting smart monitoring for command: {cmd}")
                            await self.start_monitoring_task(cmd, "command")
                            print(f"🏁 Smart monitoring started (non-blocking)")
                        else:
                            await self.send_to_telegram('status', '❌ Failed to execute command after all attempts')
                            # Keep recording running - don't stop on failure
                            if self.recording_manager.is_recording_active:
                                print(f"🎬 Recording continues - command failed")
                            else:
                                print(f"🎬 Starting recording for next attempt")
                                self.recording_manager.start_rolling_recording()
                            
                            # Reset command priority after command failure
                            self.command_priority.clear()
                            self.monitoring_paused = False
                            print(f"✅ Command priority mode: Monitoring activities resumed")
                elif data.get('type') == 'paired':
                    print(f"✅ Pairing confirmed from server")
                else:
                    print(f"📨 Other message type: {data.get('type')}")
                    
        except websockets.exceptions.ConnectionClosed:
            await self.handle_server_shutdown()
        except websockets.exceptions.WebSocketException as e:
            print(f"\n🔌 WebSocket error: {e}")
            await self.handle_server_shutdown()
        except Exception as e:
            print(f"❌ Telegram handler error: {e}")
            import traceback
            traceback.print_exc()
            self.paired = False
            self.websocket = None
    
    async def get_comprehensive_status(self, screenshot):
        """Get comprehensive status including activity, questions, and completion state"""
        if not self.claude_client or not screenshot:
            return {"status": "Status unavailable", "needs_input": False, "is_complete": False, "question": None}
            
        try:
            # Convert PIL image to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Comprehensive analysis prompt
            prompt = """Analyze this terminal screenshot and provide a comprehensive status update in JSON format:

{
  "status": "Brief description of current activity or completion state",
  "needs_input": true/false,
  "is_complete": true/false,
  "question": "Full question text if needs_input is true, null otherwise"
}

IMPORTANT - Look for Claude's activity state:

ACTIVE (is_complete: false): 
- Blinking activity indicators like ✢,✶,·,✳ next to tasks (CRITICAL CHECK)
- "Imagining...", "Razzmatazzing...", "Undulating...", "Grooving...", "Swooping..." type messages
- ANY message ending with "(esc to interrupt)" - this ALWAYS means still processing
- Progress being shown
- ANY line starting with ✶ or · or ✳ means still processing
- Status messages like "Grooving...", "Swooping...", "Caramelizing..." etc.

COMPLETED (is_complete: true): 
- Only ⏺ symbols with completed tasks, no blinking indicators
- Terminal prompt ready for new commands (> prompt visible)
- No active processing messages
- No "(esc to interrupt)" messages anywhere
- Task explicitly shows as finished
- NO lines starting with ✶·✳ anywhere visible
- NO status messages like "Grooving...", "Swooping...", etc.

NEEDS INPUT (needs_input: true) - ONLY set this to true for ACTUAL QUESTIONS that require user decision:
- Numbered options (1., 2., 3.) with clear choices asking user to select
- File edit confirmations ("Do you want to create/edit..." with options)
- "Do you want to proceed?" with explicit yes/no/options
- Multiple choice questions with clear decision points
- Permission requests for specific actions

INFORMATIONAL MESSAGES (needs_input: false) - These are NOT questions requiring input:
- "Press '?' for shortcuts" - just a hint about available shortcuts
- "Next task is to..." - status update about what's happening next
- General status messages about current progress
- Messages ending with "(Press ? for shortcuts)" - informational hints
- Progress updates, completion notifications, or task descriptions
- Status lines showing what Claude is currently working on
- Prompts that are just showing available shortcuts or help

CONTEXT CLUES for determining state:
- If there are visible numbered options (1., 2., 3.) with different actions → needs_input: true
- If message describes what's happening next without asking for choice → needs_input: false
- If showing task progress or what Claude is doing → needs_input: false
- If asking permission for a specific action with choices → needs_input: true

For status field:
- If active: Describe what Claude is currently doing
- If completed: Say "Task completed" or summarize what was accomplished  
- If needs input: Include the actual question being asked

Focus on the recent activity at the bottom of the screen."""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=150,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text", 
                                "text": prompt
                            }
                        ]
                    }]
                )
            )
            
            response_text = response.content[0].text.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Try to find the first complete JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group())
                    return analysis
                except json.JSONDecodeError:
                    pass
            
            # Fallback if JSON parsing fails - assume still working
            return {"status": "Processing...", "needs_input": False, "is_complete": False, "question": None}
            
        except Exception as e:
            print(f"⚠️ Comprehensive status failed: {e}")
            # Fallback: try basic text-based detection without API
            if "overloaded" in str(e).lower():
                print("🔄 API overloaded - using fallback text detection")
                return self._fallback_status_detection(screenshot)
            return {"status": "Status check failed", "needs_input": False, "is_complete": False, "question": None}
    
    def _fallback_status_detection(self, screenshot):
        """Basic status detection without API when Anthropic is overloaded"""
        try:
            # Try basic OCR or image analysis without API
            # For now, assume still processing when API is overloaded
            print("📊 Fallback: Assuming still processing (API unavailable)")
            return {
                "status": "Processing (API unavailable)", 
                "needs_input": False, 
                "is_complete": False, 
                "question": None
            }
        except Exception as e:
            print(f"⚠️ Fallback detection failed: {e}")
            return {"status": "Status unknown", "needs_input": False, "is_complete": False, "question": None}
    
    async def extract_claude_status(self, screenshot):
        """Extract Claude's current status from the bottom status line"""
        if not self.claude_client or not screenshot:
            return "Status unavailable"
            
        try:
            # Convert PIL image to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Focused prompt to extract just the status line
            prompt = """Look at this terminal screenshot and extract Claude's current status.

Focus on the bottom area of the screen where Claude shows its current activity. Look for:
- Lines starting with ✢ (like "✢ Creating Python hello world script...")
- Lines starting with ⏺ (completed actions)
- Lines starting with > (commands being processed)
- Any status indicators showing what Claude is currently doing

Extract the most recent/current activity status. If Claude is idle or ready for input, say "Ready for input".

Reply with just the status text (one line, under 80 characters)."""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text", 
                                "text": prompt
                            }
                        ]
                    }]
                )
            )
            
            status = response.content[0].text.strip()
            # Remove any quotes or extra formatting
            status = status.strip('"\'').strip()
            return status
            
        except Exception as e:
            print(f"⚠️ Status extraction failed: {e}")
            return "Status check failed"
    
    async def check_needs_input_quick(self, screenshot):
        """Quick check if Claude needs input - optimized for speed"""
        if not self.claude_client or not screenshot:
            return False
            
        try:
            # Convert PIL image to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Simplified prompt for faster response
            prompt = """Look at this terminal screenshot. Is Claude currently showing a prompt that needs user input?

Look for signs like:
- Numbered options (1., 2., 3.) 
- "Do you want to proceed?" or "Do you want to make this edit?"
- "Choose an option"
- File edit confirmation prompts
- Permission requests
- Input prompts with cursor waiting
- Yes/No questions
- Selection menus with highlighted options (❯)
- Any question asking the user to choose between options

Reply with just: YES or NO"""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=10,  # Just need YES or NO
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            },
                            {
                                "type": "text", 
                                "text": prompt
                            }
                        ]
                    }]
                )
            )
            
            response_text = response.content[0].text.strip().upper()
            return "YES" in response_text
            
        except Exception as e:
            print(f"⚠️ Quick input check failed: {e}")
            return False
    
    async def analyze_screenshot_with_llm(self, screenshot, second_screenshot=None):
        """Analyze screenshot with Claude API to understand terminal state"""
        if not self.claude_client:
            # Fallback analysis without LLM - be more conservative
            print("⚠️ No Claude API available - using fallback analysis")
            return {
                'status': 'Status unknown (no API)',
                'needs_input': False,
                'is_complete': True,  # Conservative: assume ready for commands
                'question': None
            }
        
        try:
            # Convert PIL image to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Prepare content for Claude API
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_base64
                    }
                }
            ]
            
            # If we have a second screenshot, add it for comparison
            if second_screenshot:
                buffer2 = io.BytesIO()
                second_screenshot.save(buffer2, format='PNG')
                img_base64_2 = base64.b64encode(buffer2.getvalue()).decode()
                
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_base64_2
                    }
                })
                
                # Dual screenshot analysis prompt
                prompt = """Analyze these two terminal screenshots taken 100ms apart and respond with a JSON object containing:

1. "status": Brief description of what's happening (e.g., "Installing npm packages", "File edit confirmation", "Ready for input")
2. "needs_input": true if waiting for user input/response, false otherwise  
3. "is_complete": true if process appears finished (showing prompt/ready for commands), false if actively running/processing
4. "question": if needs_input is true, what question/prompt is being asked
5. "screenshots_match": true if the two screenshots are identical/very similar, false if they show changes

DUAL SCREENSHOT ANALYSIS RULES:
- If screenshots are IDENTICAL (screenshots_match: true):
  * This indicates a STATIC state (either completed or waiting for input)
  * Check if it's a clean prompt (>) - if so, likely COMPLETE
  * Check if it's a question/selection - if so, needs_input: true
- If screenshots are DIFFERENT (screenshots_match: false):
  * This indicates an ACTIVE process (animations, progress, etc.)
  * Process is NOT complete - something is still happening
  * is_complete: false, needs_input: false

CRITICAL COMPLETION DETECTION RULES:
- Process is NOT complete if screenshots are different (screenshots_match: false)
- Process is NOT complete if you see "esc to interrupt" - this means it's still actively running
- Process is NOT complete if you see red text with symbols like ✶·✳ at the end of the screenshot - these indicate active processing
- Process is NOT complete if you see any loading indicators, progress bars, or "processing..." messages
- Process is NOT complete if you see "Imagining...", "Caramelizing...", "Bewitching...", "Fermenting...", "Grooving...", "Swooping..." or similar status messages
- Process is NOT complete if you see any status message ending with "(esc to interrupt)"
- Process is NOT complete if you see reddish/orange colored text - this indicates active processes
- Process is NOT complete if you see "+ Running..." or "+ Running the tests..." - these are active process indicators
- Process is ONLY complete when screenshots are identical AND you see a clean prompt (>) with no active processing indicators
- Process is ONLY complete when screenshots are identical AND there are NO status messages like "Grooving...", "Swooping...", etc.
- Process is ONLY complete when screenshots are identical AND there is NO reddish/orange colored text anywhere

VISUAL COLOR DETECTION:
- Reddish/orange text = IMMEDIATE "NOT COMPLETE" signal
- These colors are used specifically to indicate active processes
- "+ Running the tests..." in reddish text = NOT COMPLETE
- Any status message in reddish/orange = NOT COMPLETE

IMPORTANT: Pay special attention to:
- Numbered options (1., 2., 3.) - these always need input
- File edit confirmation prompts with diff views
- "Do you want to..." questions
- Selection menus with highlighted options (❯)
- Permission/confirmation dialogs
- Any prompt asking user to choose between options

Look for signs of active processing (progress bars, "installing...", loading indicators, "esc to interrupt") vs. waiting for input (selection menus, confirmation dialogs, numbered choices).

Keep status under 50 characters. Set needs_input=true if you see any selection prompt or question.

Examples:
{"status": "Installing dependencies", "needs_input": false, "is_complete": false, "question": null, "screenshots_match": false}
{"status": "File edit confirmation", "needs_input": true, "is_complete": false, "question": "Do you want to make this edit to hello.py?", "screenshots_match": true}
{"status": "Choose framework option", "needs_input": true, "is_complete": false, "question": "React or Vue? (R/V)", "screenshots_match": true}
{"status": "Ready for input", "needs_input": false, "is_complete": true, "question": null, "screenshots_match": true}"""
            else:
                # Single screenshot analysis prompt (fallback)
                prompt = """Analyze this terminal screenshot and respond with a JSON object containing:

1. "status": Brief description of what's happening (e.g., "Installing npm packages", "File edit confirmation", "Ready for input")
2. "needs_input": true if waiting for user input/response, false otherwise  
3. "is_complete": true if process appears finished (showing prompt/ready for commands), false if actively running/processing
4. "question": if needs_input is true, what question/prompt is being asked

CRITICAL COMPLETION DETECTION RULES:
- Process is NOT complete if you see "esc to interrupt" - this means it's still actively running
- Process is NOT complete if you see red text with symbols like ✶·✳ at the end of the screenshot - these indicate active processing
- Process is NOT complete if you see any loading indicators, progress bars, or "processing..." messages
- Process is NOT complete if you see "Imagining...", "Caramelizing...", "Bewitching...", "Fermenting...", "Grooving...", "Swooping..." or similar status messages
- Process is NOT complete if you see any status message ending with "(esc to interrupt)"
- Process is NOT complete if you see reddish/orange colored text - this indicates active processes
- Process is NOT complete if you see "+ Running..." or "+ Running the tests..." - these are active process indicators
- Process is ONLY complete when you see a clean prompt (>) with no active processing indicators
- Process is ONLY complete when there are NO status messages like "Grooving...", "Swooping...", etc.
- Process is ONLY complete when there is NO reddish/orange colored text anywhere

VISUAL COLOR DETECTION:
- Reddish/orange text = IMMEDIATE "NOT COMPLETE" signal
- These colors are used specifically to indicate active processes
- "+ Running the tests..." in reddish text = NOT COMPLETE
- Any status message in reddish/orange = NOT COMPLETE

IMPORTANT: Pay special attention to:
- Numbered options (1., 2., 3.) - these always need input
- File edit confirmation prompts with diff views
- "Do you want to..." questions
- Selection menus with highlighted options (❯)
- Permission/confirmation dialogs
- Any prompt asking user to choose between options

Look for signs of active processing (progress bars, "installing...", loading indicators, "esc to interrupt") vs. waiting for input (selection menus, confirmation dialogs, numbered choices).

Keep status under 50 characters. Set needs_input=true if you see any selection prompt or question.

Examples:
{"status": "Installing dependencies", "needs_input": false, "is_complete": false, "question": null}
{"status": "File edit confirmation", "needs_input": true, "is_complete": false, "question": "Do you want to make this edit to hello.py?"}
{"status": "Choose framework option", "needs_input": true, "is_complete": false, "question": "React or Vue? (R/V)"}
{"status": "Ready for input", "needs_input": false, "is_complete": true, "question": null}"""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=200,
                    messages=[{
                        "role": "user",
                        "content": content + [{"type": "text", "text": prompt}]
                    }]
                )
            )
            
            # Parse Claude's response as JSON
            response_text = response.content[0].text.strip()
            print(f"🧠 Raw Claude response: {response_text}")
            
            # Extract JSON from response (Claude might add explanation)
            import json
            import re
            
            # Try to find the first complete JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text)
            if json_match:
                json_text = json_match.group()
                try:
                    analysis = json.loads(json_text)
                except json.JSONDecodeError:
                    # Try a more greedy match for nested JSON
                    json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                    else:
                        raise ValueError("No valid JSON found in response")
            else:
                raise ValueError("No JSON object found in response")
            
            # Validate required keys
            required_keys = ['status', 'needs_input', 'is_complete', 'question']
            if not all(key in analysis for key in required_keys):
                raise ValueError("Missing required keys in analysis")
            
            # Add screenshots_match if not present (for backward compatibility)
            if 'screenshots_match' not in analysis:
                analysis['screenshots_match'] = True  # Assume static for single screenshot
            
            print(f"🧠 Claude analysis: {analysis['status']}")
            return analysis
            
        except Exception as e:
            print(f"⚠️ Claude API analysis failed: {e}")
            # Fallback analysis - be conservative and assume still working
            # This prevents false completion detection when API fails
            return {
                'status': 'Processing...',  # Generic in-progress message
                'needs_input': False,
                'is_complete': False,  # Conservative: assume still working, never complete on API failure
                'question': None
            }
    
    async def start_monitoring_task(self, command: str, task_type: str = "command"):
        """Start a monitoring task and track it to prevent duplicates"""
        # Cancel any existing monitoring tasks
        await self.cancel_existing_monitoring_tasks()
        
        # Reset completion tracking
        self.completion_sent = False
        
        # Reset detectors for new command
        self.static_screen_detector.reset()
        self.completion_detector.reset()
        
        # Create and track the new monitoring task
        task = asyncio.create_task(self.smart_monitor_process(command))
        self.active_monitoring_tasks.add(task)
        
        # Add callback to remove task when done
        task.add_done_callback(self.active_monitoring_tasks.discard)
        
        print(f"🚀 Started monitoring task for {task_type}: {command[:50]}...")
        return task
    
    async def cancel_existing_monitoring_tasks(self):
        """Cancel any existing monitoring tasks to prevent duplicates"""
        if self.active_monitoring_tasks:
            print(f"🛑 Cancelling {len(self.active_monitoring_tasks)} existing monitoring tasks")
            for task in self.active_monitoring_tasks.copy():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self.active_monitoring_tasks.clear()
    
    async def smart_monitor_process(self, command: str, max_wait: int = 300):
        """Smart monitoring with LLM analysis - minimal noise"""
        print(f"🔥 SMART MONITOR STARTED for command: {command}")
        start_time = asyncio.get_event_loop().time()
        last_check = 0  # Start with 0 to force immediate first check
        
        # Responsive monitoring for quick feedback
        STATUS_UPDATE_INTERVAL = Config.STATUS_UPDATE_INTERVAL
        INITIAL_WAIT = Config.INITIAL_WAIT
        COMPLETION_CHECK_INTERVAL = Config.COMPLETION_CHECK_INTERVAL
        
        print(f"🧠 Smart monitoring: {command[:50]}...")
        print(f"📅 Current time: {start_time}, Last update: {self.last_status_update}")
        
        # Start rolling recording buffer if not already active
        if not self.recording_manager.is_recording_active:
            print(f"🎬 Starting rolling 5-minute recording buffer")
            self.recording_manager.start_rolling_recording()
        
        # Initial wait and first analysis
        await asyncio.sleep(INITIAL_WAIT)
        
        process_complete = False
        
        while not process_complete:
            # Check if command priority is active - if so, pause monitoring
            if self.monitoring_paused:
                print(f"⏸️ Smart monitoring paused due to command priority")
                await asyncio.sleep(0.5)  # Shorter sleep when paused
                continue  # Skip the rest of the monitoring loop when paused
            
            current_time = asyncio.get_event_loop().time()
            elapsed = int(current_time - start_time)
            print(f"🔄 Monitor loop - elapsed: {elapsed}s, process_complete: {process_complete}")
            
            # Simple timeout check (but don't spam user with timeout messages)
            if elapsed > max_wait:
                print(f"⏱️ Process monitoring timeout after {elapsed}s")
                # Keep recording running - don't stop on timeout
                if self.recording_manager.is_recording_active:
                    print(f"🎬 Recording continues - timeout reached")
                break
            
            # Smart status update logic - different intervals for different situations
            time_since_last = current_time - self.last_status_update
            print(f"⏰ Time since last update: {time_since_last:.1f}s (need {STATUS_UPDATE_INTERVAL}s)")
            
            # More frequent checks for completion, less frequent for status updates
            should_check_completion = time_since_last >= COMPLETION_CHECK_INTERVAL
            should_send_status = time_since_last >= STATUS_UPDATE_INTERVAL
            
            if should_check_completion or should_send_status:
                print(f"🔍 Taking dual screenshots for status update (elapsed: {elapsed}s)")
                first_screenshot, second_screenshot = self.capture_dual_screenshots(delay_ms=Config.DUAL_SCREENSHOT_DELAY_MS)
                if first_screenshot:
                    print(f"📸 Dual screenshots captured, analyzing...")
                    status_info = await self.llm_analyzer.analyze_screenshot_with_llm(first_screenshot, second_screenshot)
                    print(f"🧠 Analysis result: {status_info}")
                    
                    # Enhanced completion detection using multiple methods
                    static_result = self.static_screen_detector.update_screenshot(first_screenshot)
                    self.completion_detector.update_static_screen_status(
                        static_result['is_static'], 
                        static_result['static_duration']
                    )
                    
                    # Classify task type for better completion detection
                    task_type = self.task_classifier.classify_task(command)
                    self.completion_detector.set_task_type(task_type)
                    
                    # Use enhanced completion detection
                    completion_analysis = self.completion_detector.analyze_completion(
                        first_screenshot, status_info, command, task_type
                    )
                    
                    # Update status based on enhanced analysis
                    if completion_analysis['is_complete']:
                        status_info['is_complete'] = True
                        status_info['status'] = f"Task completed ({completion_analysis['method']})"
                        print(f"🎯 Enhanced completion detected: {completion_analysis['method']} (confidence: {completion_analysis['confidence']:.2f})")
                        print(f"🎯 Indicators: {completion_analysis['indicators']}")
                        print(f"🎯 Reasoning: {completion_analysis['reasoning']}")
                    
                    # Build status message based on state - PRIORITIZE COMPLETION OVER QUESTIONS
                    status_msg = ""  # Initialize to prevent UnboundLocalError
                    
                    if status_info['is_complete']:
                        # COMPLETION TAKES PRIORITY - if something is complete, ignore question detection
                        status_msg = f"✅ {status_info['status']}"
                        print(f"🔍 COMPLETION DETECTED: {status_info['status']}")
                        print(f"🔍 Completion details: needs_input={status_info['needs_input']}, is_complete={status_info['is_complete']}")
                        
                        # Validate completion status using the analyzer
                        status_info = self.llm_analyzer.validate_completion_status(status_info)
                        
                        # Only send completion once, and only if not in command priority mode
                        if not process_complete and not self.monitoring_paused and not self.completion_sent:  # Only send if we haven't marked complete yet and not in priority mode
                            await self.send_to_telegram('status', status_msg)
                            print(f"📊 Completion: {status_msg}")
                            process_complete = True
                            self.completion_sent = True  # Mark as sent globally
                            # Clear question tracking
                            self.question_detector.clear_last_question()
                            # Clear waiting state when task is complete
                            self.waiting_for_input = False
                            self.last_was_waiting_for_input = False
                            
                            # 🆕 AUTO-SCREENSHOT: Take screenshot after each task completion
                            print("📸 Auto-screenshot: Taking screenshot after task completion")
                            completion_screenshot = await self.capture_terminal_screenshot_async()
                            if completion_screenshot:
                                await self.send_to_telegram('screenshot', completion_screenshot, screenshot_type="completion", source="auto-completion")
                                print("📸 Completion screenshot sent automatically")
                            else:
                                print("❌ Failed to capture completion screenshot")
                            
                            print("✅ Task completion recorded")
                            
                            # Keep recording running - don't stop on completion
                            if self.recording_manager.is_recording_active:
                                print(f"🎬 Recording continues - process complete")
                            else:
                                print(f"🎬 Starting recording for next command")
                                self.recording_manager.start_rolling_recording()
                            
                            # Exit monitoring loop immediately when complete
                            break
                        else:
                            print(f"🔇 Already sent completion, skipping")
                        
                    elif self.question_detector.is_question(status_info)[0]:  # Check if it's a question
                        # ENHANCED QUESTION DETECTION - only if NOT complete
                        question_text = status_info['question']
                        is_question, confidence, question_type = self.question_detector.is_question(status_info)
                        status_msg = f"❓ {status_info['status']}"  # Set status_msg for question
                        
                        # Check if this is essentially the same question with enhanced similarity
                        is_same_question, similarity_score, similarity_reason = self.question_detector.is_same_question(
                            question_text, self.question_detector.get_last_question()
                        )
                        
                        # Enhanced notification logic
                        should_send = (
                            not is_same_question and 
                            not self.monitoring_paused and
                            self.question_detector.should_send_question_notification(question_text, confidence)
                        )
                        
                        if should_send:
                            self.question_detector.update_last_question(question_text, confidence, question_type)
                            self.waiting_for_input = True
                            self.last_was_waiting_for_input = True
                            print(f"📊 New question detected: {question_text[:50]}... (confidence: {confidence:.2f}, type: {question_type})")
                            
                            # Keep recording running - don't pause for questions
                            # This ensures continuous recording throughout the interaction
                            if self.recording_manager.is_recording_active:
                                print(f"🎬 Recording continues - waiting for user input")
                            else:
                                print(f"🎬 Starting recording for question interaction")
                                self.recording_manager.start_rolling_recording()
                            
                            # Send ONLY screenshot - no text message
                            print("📸 Sending screenshot for question (no text)")
                            question_screenshot = await self.capture_terminal_screenshot_async()
                            if question_screenshot:
                                await self.send_to_telegram('screenshot', question_screenshot, screenshot_type="question", source="auto-question")
                                print("📸 Question screenshot sent automatically")
                            else:
                                print("❌ Failed to capture question screenshot")
                        else:
                            if is_same_question:
                                print(f"🔇 Skipping duplicate question: {question_text[:50]}... (similarity: {similarity_score:.2f}, reason: {similarity_reason})")
                            else:
                                print(f"🔇 Skipping question notification: {question_text[:50]}... (confidence: {confidence:.2f}, recent: {self.question_detector.is_recent_question(question_text)})")
                            # Still set waiting state even if not sending duplicate
                            self.waiting_for_input = True
                            self.last_was_waiting_for_input = True
                        
                    else:
                        status_msg = f"⏳ {status_info['status']}"
                        # Send more frequent status updates, but only if not in command priority mode
                        if (status_msg != self.last_status_text and 
                            should_send_status and 
                            not self.monitoring_paused):  # Don't send status updates during command priority
                            await self.send_to_telegram('status', status_msg)
                            print(f"📊 Status: {status_msg}")
                        else:
                            if self.monitoring_paused:
                                print(f"🔇 Skipping status update due to command priority: {status_msg}")
                            else:
                                print(f"🔇 Skipping duplicate/generic status: {status_msg}")
                    
                    # Update tracking only if we checked or sent something
                    self.last_status_text = status_msg
                    if should_send_status:
                        self.last_status_update = current_time
                else:
                    print("❌ Failed to capture screenshot - skipping this update")
                    self.last_status_update = current_time
            
            # Check if command priority is active - if so, pause monitoring
            if self.monitoring_paused:
                print(f"⏸️ Monitoring paused due to command priority")
                await asyncio.sleep(0.5)  # Shorter sleep when paused
                continue  # Skip the rest of the monitoring loop when paused
            else:
                await asyncio.sleep(1)  # Check every second for responsiveness
        
        print(f"🧠 Smart monitoring complete: {command[:50]}...")
    

    
    async def handle_server_shutdown(self):
        """Handle graceful shutdown when server stops"""
        print("\n" + "="*60)
        print("🔌 SERVER CONNECTION LOST")
        print("="*60)
        print("📱 The Telegram server has stopped or connection was lost")
        print("💻 Claude terminal continues to work locally")
        print("🔄 To reconnect to Telegram:")
        print("   1. Restart the server: ./start.sh")
        print("   2. Restart this client")
        print("   3. Re-pair with your Telegram bot")
        print("="*60)
        
        # Stop recording if active
        if self.recording_manager.is_recording_active:
            print("🎬 Stopping recording due to server disconnect")
            self.recording_manager.stop_recording()
        
        # Reset connection state
        self.paired = False
        self.websocket = None
        
        # Continue with local terminal control
        print("💻 Continuing with local terminal control...")
        print("📝 You can still use Claude directly in the terminal")
        print("⏹️ Press Ctrl+C to exit completely")
    
    async def monitoring_loop(self):
        """Monitor system status without prompting for local input"""
        print("\n🤖 Claude Terminal Control Active")
        print("📱 All commands are sent via Telegram")
        print("🔌 WebSocket connection maintained for remote control")
        print("⏹️ Press Ctrl+C to exit")
        print("-" * 50)
        
        try:
            while self.running:
                # Check connection health (silent unless there's an actual problem)
                if self.paired and self.websocket:
                    time_since_heartbeat = time.time() - self.last_heartbeat
                    if time_since_heartbeat > self.heartbeat_timeout:
                        # Only log once per timeout period to avoid spam
                        if not hasattr(self, '_last_heartbeat_warning') or time.time() - self._last_heartbeat_warning > 60:
                            print(f"🔍 Checking server connection...")
                            self._last_heartbeat_warning = time.time()
                        
                        try:
                            # Try to send a ping to check if connection is alive
                            await self.websocket.ping()
                            self.last_heartbeat = time.time()
                            # Don't print success message - connection is working fine
                        except Exception as e:
                            print(f"❌ Server connection lost: {e}")
                            print("🔌 Continuing with local terminal control")
                            self.paired = False
                            self.websocket = None
                
                # Check recording health periodically (much less frequent)
                if self.recording_manager.is_recording_active:
                    # Only check recording health every 2 minutes to avoid interference
                    if not hasattr(self, '_last_recording_check') or time.time() - self._last_recording_check > 120:
                        self.recording_manager.ensure_recording_health()
                        self._last_recording_check = time.time()
                
                # Check for static screen completion periodically
                if not hasattr(self, '_last_static_check') or time.time() - self._last_static_check > Config.STATIC_SCREEN_CHECK_INTERVAL:
                    # Only check if we're not actively monitoring a command
                    if not self.active_monitoring_tasks:
                        screenshot = self.capture_terminal_screenshot()
                        if screenshot:
                            static_result = self.static_screen_detector.update_screenshot(screenshot)
                            if static_result['should_complete']:
                                print(f"🖥️ Static screen completion detected in monitoring loop: {static_result['static_duration']:.1f}s")
                                # Reset detector (no notification sent to avoid clutter)
                                self.static_screen_detector.reset()
                    self._last_static_check = time.time()
                
                # Just keep the system running and responsive to Telegram commands
                await asyncio.sleep(10)  # Check every 10 seconds (less frequent)
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            self.running = False
    
    async def run(self):
        """Main run method"""
        try:
            # Show pairing instructions
            self._show_pairing_instructions()
            
            # Try to pair for 60 seconds
            paired = await self.wait_for_pairing(timeout=60)
            
            if not paired:
                print("\n❌ Telegram pairing failed or timed out")
                print("📱 To use remote control, please:")
                print("   1. Ensure combined-server.js is running")
                print("   2. Open Telegram and send the pairing code to the bot")
                print("   3. Run this wrapper again")
                print("\n💻 Returning to console...")
                return 1
            
            # Only start Claude if successfully paired
            # Start Claude in terminal
            if not self.start_claude_terminal():
                print("❌ Failed to start Claude terminal")
                return 1
            
            self.running = True
            
            # Start recording immediately when paired and ready
            print("🎬 Starting initial 20-minute rolling recording buffer")
            if self.recording_manager.start_rolling_recording():
                print("✅ Initial recording started successfully")
            else:
                print("⚠️ Failed to start initial recording - will start on first command")
            
            # Schedule initial screenshot capture
            asyncio.create_task(self.capture_initial_screenshot())
            
            # Start background tasks
            tasks = []
            
            # Start Telegram handler since we're paired
            tasks.append(asyncio.create_task(self.handle_telegram_commands()))
            

            
            # Add monitoring loop (no local input prompts)
            tasks.append(asyncio.create_task(self.monitoring_loop()))
            
            # Wait for completion
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                print(f"\n❌ Error in main task loop: {e}")
                print("🔌 Server connection may have been lost")
            finally:
                print("\n🔄 Cleaning up resources...")
            
        finally:
            if self.websocket:
                await self.websocket.close()


def check_platform_support():
    """Check if running on supported platform (macOS only) and show appropriate error message"""
    import platform
    
    # Check platform
    system = platform.system()
    
    # Only macOS is supported
    if system != "Darwin":
        print(f"""
🏖️ ClaudeOnTheBeach - {system} Detected

❌ {system} Support Coming Soon!

ClaudeOnTheBeach currently only works on macOS systems due to 
AppleScript integration and Terminal.app automation requirements.

💻 Current Support:
• ✅ macOS (Terminal automation with AppleScript)
• ❌ Windows (Terminal automation coming soon)
• ❌ Linux (Terminal automation coming soon)
• ❌ iOS (Mobile app coming soon)

🔧 Why macOS Only?
• AppleScript integration for Terminal control
• Native screenshot capture capabilities
• Seamless Claude Code integration
• Optimized for macOS Terminal.app

🌊 What's Coming:
• Windows support with PowerShell automation
• Linux support with terminal automation
• iOS app with native interface
• Cross-platform compatibility

🏖️ For now, please use ClaudeOnTheBeach on your Mac.
Follow us for updates: @ClaudeOnTheBeach_bot
        """)
        return False
    
    return True

async def main():
    import argparse
    
    # Check for platform support first
    if not check_platform_support():
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Claude Remote Control via Terminal Automation')
    parser.add_argument('--directory', '-d', 
                       help='Starting directory for Claude (default: current directory)',
                       default=None)
    parser.add_argument('--server', '-s',
                       help='WebSocket server URL (default: ws://claudeonthebeach.com:8081/ws)',
                       default='ws://claudeonthebeach.com:8081/ws')
    parser.add_argument('--screenshots-folder', 
                       help='Folder to save screenshots locally (screenshots disabled by default)',
                       default=None)
    
    args = parser.parse_args()
    
    # Set server URL if provided
    if args.server:
        os.environ['SERVER_URL'] = args.server
    
    # Resolve directory path
    start_dir = None
    if args.directory:
        start_dir = os.path.abspath(os.path.expanduser(args.directory))
        if not os.path.exists(start_dir):
            print(f"❌ Directory does not exist: {start_dir}")
            sys.exit(1)
        if not os.path.isdir(start_dir):
            print(f"❌ Not a directory: {start_dir}")
            sys.exit(1)
    
    wrapper = TerminalClaudeWrapper(
        start_directory=start_dir,
        screenshots_folder=args.screenshots_folder
    )
    await wrapper.run()


if __name__ == "__main__":
    asyncio.run(main())