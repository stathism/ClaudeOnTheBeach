#!/usr/bin/env python3
"""
Claude Remote Control System Launcher
Starts both the server and wrapper for easy development and testing.
"""
import subprocess
import sys
import os
import time
import threading
import signal

def start_server():
    """Start the Node.js server"""
    try:
        print("🚀 Starting server...")
        server_process = subprocess.Popen(
            ['node', 'index.js'],
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server')
        )
        return server_process
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def start_wrapper(directory=None, screenshots_folder=None):
    """Start the Python client"""
    try:
        print("🔧 Starting client...")
        cmd = ['python3', 'client/claudeOnTheBeach.py']
        
        if directory:
            cmd.extend(['--directory', directory])
        if screenshots_folder:
            cmd.extend(['--screenshots-folder', screenshots_folder])
            
        wrapper_process = subprocess.Popen(cmd)
        return wrapper_process
    except Exception as e:
        print(f"❌ Failed to start wrapper: {e}")
        return None

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

def main():
    import argparse
    
    # Check for platform support first
    if not check_platform_support():
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Launch Claude Remote Control System')
    parser.add_argument('--directory', '-d', 
                       help='Starting directory for Claude (default: current directory)',
                       default=None)
    parser.add_argument('--screenshots-folder', 
                       help='Folder to save screenshots locally',
                       default=None)
    parser.add_argument('--server-only', action='store_true',
                       help='Only start the server (no client)')
    parser.add_argument('--client-only', action='store_true',
                       help='Only start the client (no server)')
    
    args = parser.parse_args()
    
    processes = []
    
    try:
        if not args.client_only:
            # Start server
            server_process = start_server()
            if server_process:
                processes.append(('Server', server_process))
                time.sleep(3)  # Give server time to start
        
        # Client disabled by default - user can manually run it when needed
        # if not args.server_only:
        #     # Start client
        #     client_process = start_wrapper(args.directory, args.screenshots_folder)
        #     if client_process:
        #         processes.append(('Client', client_process))
        
        if not processes:
            print("❌ No processes started")
            sys.exit(1)
        
        print(f"\n✅ Started {len(processes)} process(es)")
        print("Press Ctrl+C to stop all processes")
        
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if any process died (only report once)
            processes_to_remove = []
            for i, (name, process) in enumerate(processes):
                if process.poll() is not None:
                    print(f"⚠️ {name} process exited (exit code: {process.returncode})")
                    processes_to_remove.append(i)
            
            # Remove exited processes from list to avoid repeat messages
            for i in reversed(processes_to_remove):
                processes.pop(i)
            
            # If all processes have exited, break
            if not processes:
                print("ℹ️ All processes have exited")
                break
                    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        
        # Kill all processes
        for name, process in processes:
            try:
                print(f"🛑 Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"🔨 Force killing {name}...")
                process.kill()
                process.wait()
            except Exception as e:
                print(f"⚠️ Error stopping {name}: {e}")
        
        print("👋 All processes stopped")

if __name__ == "__main__":
    main()