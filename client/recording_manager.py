"""
Recording Manager Module
Handles all video recording functionality for Claude On The Beach
"""

import os
import time
import subprocess
import json
import asyncio
import threading
from typing import Optional, Dict, Any


class RecordingManager:
    """Manages video recording functionality using screencapture method"""
    
    def __init__(self, terminal_window_id: Optional[int] = None):
        self.terminal_window_id = terminal_window_id
        self.recording_process = None
        self.recording_file = None
        self.recording_start_time = None
        self.is_recording_active = False
        self.recording_buffer_duration = 1200  # 20 minutes in seconds (fixed)
        self.extended_buffer_duration = 1200  # 20 minutes for questions/user input
        self.recording_script_file = None
        
        # Recording stability improvements
        self.recording_lock = threading.Lock()  # Prevent concurrent operations
        self.last_health_check = 0  # Track last health check time
        self.health_check_interval = 300  # 5 minutes between health checks
        self.consecutive_failures = 0  # Track consecutive health check failures
        self.max_consecutive_failures = 3  # Only restart after 3 consecutive failures
        self.health_check_disabled_until = 0  # Disable health checks during critical operations

    
    def start_rolling_recording(self) -> bool:
        """Start rolling 5-minute recording buffer using the same method as screenshots"""
        try:
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"❌ ffmpeg not found or not working - recording disabled")
                return False
            
            # Check if we have a paused recording to resume
            if self.is_recording_active and not self.recording_process:
                print(f"🔄 Recording paused - resuming existing recording")
                return self.resume_recording()
            
            # If we already have an active recording, just return
            if self.is_recording_active and self.recording_process:
                print(f"⚠️ Recording already active")
                return True
            
            # Generate filename for new recording
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            temp_dir = "/tmp/claude_recordings"
            os.makedirs(temp_dir, exist_ok=True)
            recording_file = f"{temp_dir}/rolling_{timestamp}.mp4"
            
            # Use the same reliable method as screenshots - screencapture with window ID
            # This works even when terminal is behind other windows
            if self.terminal_window_id:
                print(f"📐 Using screencapture method (same as screenshots) for terminal window ID: {self.terminal_window_id}")
                
                # Create capture script
                capture_script = self._create_capture_script(recording_file)
                
                # Write script to temporary file
                script_file = f"{temp_dir}/capture_script_{timestamp}.sh"
                with open(script_file, 'w') as f:
                    f.write(capture_script)
                
                # Make script executable
                os.chmod(script_file, 0o755)
                
                # Store script file path for cleanup
                self.recording_script_file = script_file
                
                # Run the capture script in background
                self.recording_process = subprocess.Popen(
                    ['bash', script_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
                
                self.recording_file = recording_file
                self.recording_start_time = time.time()
                self.is_recording_active = True
                
                print(f"🎬 Started rolling 20-minute recording buffer")
                print(f"📁 Recording to: {recording_file}")
                print(f"⏱️ Buffer duration: 20 minutes (rolling)")
                print(f"📐 Terminal-only recording (same method as screenshots)")
                print(f"🎥 Quality: 5fps, CRF 20, 1000kbps (improved quality)")
                
                # Give the script a moment to start
                time.sleep(1.0)
                
                # Verify recording started successfully
                if self.recording_process.poll() is not None:
                    print(f"❌ Recording process failed to start (exit code: {self.recording_process.returncode})")
                    self.is_recording_active = False
                    return False
                
                print(f"✅ Recording process started successfully (PID: {self.recording_process.pid})")
                
                # Wait a bit more and check if file is being created
                time.sleep(2.0)
                if os.path.exists(recording_file):
                    file_size = os.path.getsize(recording_file)
                    print(f"✅ Recording file created: {recording_file} ({file_size} bytes)")
                else:
                    print(f"⚠️ Recording file not created yet - may take a moment")
                
                return True
                
            else:
                print(f"⚠️ No terminal window ID - recording disabled")
                return False
            
        except Exception as e:
            print(f"❌ Failed to start rolling recording: {e}")
            return False
    
    def _create_capture_script(self, output_file: str) -> str:
        """Create the bash script for continuous terminal window capture"""
        # Get current buffer duration based on state
        buffer_duration = self.get_current_buffer_duration()
        max_frames = int(buffer_duration * 5)  # 5 fps * duration in seconds
        
        return f'''
#!/bin/bash
# Continuous terminal window capture using the same method as screenshots
temp_dir="/tmp/claude_recordings"
window_id="{self.terminal_window_id}"
output_file="{output_file}"

# Create temporary directory for frames
frames_dir="$temp_dir/frames_$RANDOM"
mkdir -p "$frames_dir"

# Function to create final video and cleanup
cleanup_and_finalize() {{
    echo "Creating final video..."
    if [ $frame_count -gt 0 ]; then
        ffmpeg -y -framerate 5 -i "$frames_dir/frame_%d.png" -c:v libx264 -crf 20 -preset fast -maxrate 1000k -bufsize 2000k "$output_file" 2>/dev/null
        echo "Final video created: $output_file"
    fi
    rm -rf "$frames_dir"
    exit 0
}}

# Set up signal handlers for graceful shutdown
trap cleanup_and_finalize SIGTERM SIGINT

# Capture frames continuously with smart buffer duration
frame_count=0
start_time=$(date +%s)
max_duration={buffer_duration}
max_frames={max_frames}

echo "🎬 Starting recording with {buffer_duration//60} minute buffer ({max_frames} frames max)"

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    if [ $elapsed -ge $max_duration ]; then
        break
    fi
    
    # Use the same screencapture command that works for screenshots
    screencapture -x -o -l $window_id "$frames_dir/frame_$frame_count.png"
    
    if [ $? -eq 0 ]; then
        frame_count=$((frame_count + 1))
        
        # Create video file immediately after first frame, then every 5 frames
        if [ $frame_count -eq 1 ] || [ $((frame_count % 5)) -eq 0 ]; then
            # Convert current frames to video
            ffmpeg -y -framerate 5 -i "$frames_dir/frame_%d.png" -c:v libx264 -crf 20 -preset fast -maxrate 1000k -bufsize 2000k "$output_file" 2>/dev/null
            
            # Keep only the last max_frames - smart rolling buffer
            if [ $frame_count -gt {max_frames} ]; then
                # Remove old frames to maintain rolling buffer
                old_frames=$((frame_count - {max_frames}))
                for i in $(seq 0 $old_frames); do
                    rm -f "$frames_dir/frame_$i.png"
                done
                # Rename remaining frames to start from 0
                for i in $(seq $((old_frames + 1)) $frame_count); do
                    mv "$frames_dir/frame_$i.png" "$frames_dir/frame_$((i - old_frames - 1)).png" 2>/dev/null
                done
                frame_count={max_frames}
            fi
        fi
    fi
    
    # Wait 0.2 seconds (5 fps)
    sleep 0.2
done

# Final video creation with all remaining frames
cleanup_and_finalize
'''
    
    def stop_recording(self) -> bool:
        """Stop the current screen recording"""
        if self.recording_process:
            try:
                # Send SIGTERM to gracefully stop the script
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)
                
                duration = time.time() - self.recording_start_time if self.recording_start_time else 0
                print(f"🎬 Recording stopped after {duration:.1f} seconds")
                
                # Wait for file to be fully written
                if self.recording_file:
                    for _ in range(20):  # Wait up to 10 seconds for script to finish
                        if os.path.exists(self.recording_file):
                            file_size = os.path.getsize(self.recording_file)
                            if file_size > 0:
                                print(f"✅ Recording file ready: {self.recording_file} ({file_size} bytes)")
                                break
                        time.sleep(0.5)
                    else:
                        print(f"⚠️ Recording file not found or empty after stopping: {self.recording_file}")
                
                self.recording_process = None
                self.is_recording_active = False
                
                # Clean up script file
                if self.recording_script_file and os.path.exists(self.recording_script_file):
                    try:
                        os.unlink(self.recording_script_file)
                        print(f"🧹 Cleaned up recording script: {self.recording_script_file}")
                    except Exception as e:
                        print(f"⚠️ Could not clean up script file: {e}")
                self.recording_script_file = None
                
                # Recording stopped - ready for next command
                
                return True
                
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                self.recording_process.kill()
                self.recording_process.wait()
                
                # Still wait for file after force kill
                if self.recording_file:
                    for _ in range(10):  # Wait up to 5 seconds
                        if os.path.exists(self.recording_file):
                            file_size = os.path.getsize(self.recording_file)
                            if file_size > 0:
                                print(f"✅ Recording file ready after force stop: {self.recording_file} ({file_size} bytes)")
                                break
                        time.sleep(0.5)
                    else:
                        print(f"⚠️ Recording file not found after force stop: {self.recording_file}")
                
                self.recording_process = None
                print("🎬 Recording force stopped")
                return True
            except Exception as e:
                print(f"❌ Error stopping recording: {e}")
                self.recording_process = None
                return False
        return True
    
    def stop_recording_on_input(self) -> bool:
        """Pause recording when waiting for user input"""
        if self.is_recording_active:
            print(f"⏸️ Pausing recording - waiting for user input")
            # Stop the recording process but preserve the file and state
            if self.recording_process:
                try:
                    self.recording_process.terminate()
                    self.recording_process.wait(timeout=5)
                    print(f"✅ Recording paused successfully")
                except subprocess.TimeoutExpired:
                    self.recording_process.kill()
                    self.recording_process.wait()
                    print(f"✅ Recording force paused")
                except Exception as e:
                    print(f"⚠️ Error pausing recording: {e}")
                
                self.recording_process = None
                # Don't set is_recording_active = False to preserve state
            return True
        return False
    
    def set_waiting_for_input(self, waiting: bool) -> None:
        """Legacy method - no longer used (fixed 20-minute buffer)"""
        # This method is kept for compatibility but does nothing
        pass
    
    def get_current_buffer_duration(self) -> int:
        """Get the current buffer duration (always 20 minutes)"""
        return self.recording_buffer_duration  # Always 20 minutes
    
    def resume_recording(self) -> bool:
        """Resume recording after user input"""
        if not self.is_recording_active:
            print(f"⚠️ No recording to resume")
            return False
            
        if self.recording_process:
            print(f"⚠️ Recording already running")
            return False
            
        if not self.recording_file:
            print(f"⚠️ No recording file to resume")
            return False
            
        print(f"▶️ Resuming existing recording: {self.recording_file}")
        
        try:
            # For resuming, we need to continue the existing recording
            # Instead of creating a new script, we'll just restart the same recording
            # This maintains the rolling buffer concept
            capture_script = self._create_capture_script(self.recording_file)
            
            # Use a resume-specific script name to avoid conflicts
            temp_dir = "/tmp/claude_recordings"
            script_file = f"{temp_dir}/resume_capture_{os.path.basename(self.recording_file)}.sh"
            
            # Clean up any existing resume script
            if os.path.exists(script_file):
                try:
                    os.unlink(script_file)
                except:
                    pass
            
            with open(script_file, 'w') as f:
                f.write(capture_script)
            
            # Make script executable
            os.chmod(script_file, 0o755)
            
            # Store script file path for cleanup
            self.recording_script_file = script_file
            
            # Run the capture script in background
            self.recording_process = subprocess.Popen(
                ['bash', script_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            
            print(f"✅ Recording resumed successfully (PID: {self.recording_process.pid})")
            print(f"📁 Continuing file: {self.recording_file}")
            print(f"🔄 Note: This continues the rolling buffer")
            return True
            
        except Exception as e:
            print(f"❌ Failed to resume recording: {e}")
            return False
    
    def get_current_recording(self) -> Optional[str]:
        """Get the current recording file path"""
        if self.recording_file and os.path.exists(self.recording_file):
            return self.recording_file
        return None
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Get detailed recording status"""
        status = {
            'is_active': self.is_recording_active,
            'file_path': self.recording_file,
            'file_exists': False,
            'file_size': 0,
            'process_running': False,
            'elapsed_time': 0,
            'is_healthy': False
        }
        
        if self.recording_file and os.path.exists(self.recording_file):
            status['file_exists'] = True
            status['file_size'] = os.path.getsize(self.recording_file)
        
        if self.recording_process:
            status['process_running'] = self.recording_process.poll() is None
        
        if self.recording_start_time:
            status['elapsed_time'] = time.time() - self.recording_start_time
        
        # Determine if recording is healthy
        status['is_healthy'] = (
            status['is_active'] and 
            status['process_running'] and 
            status['file_exists'] and 
            status['file_size'] > 1024 and  # At least 1KB
            status['elapsed_time'] < 3600  # Less than 1 hour (should be rolling)
        )
        
        return status
    
    def ensure_recording_health(self) -> bool:
        """Ensure recording is healthy, restart only if completely broken"""
        # Use lock to prevent concurrent health checks
        if not self.recording_lock.acquire(blocking=False):
            print(f"🔒 Recording health check already in progress - skipping")
            return True
        
        try:
            # Check if health check should be skipped
            if self._should_skip_health_check():
                return True
            
            # Update last health check time
            self.last_health_check = time.time()
            
            status = self.get_recording_status()
            
            # Only restart if the process is completely dead
            if status['is_active'] and not status['process_running']:
                print(f"⚠️ Recording process died - restarting...")
                print(f"   Process running: {status['process_running']}")
                print(f"   File size: {status['file_size']} bytes")
                print(f"   Elapsed time: {status['elapsed_time']:.1f}s")
                
                self.stop_recording()
                time.sleep(1)  # Brief pause
                return self.start_rolling_recording()
            
            # Check if recording file is corrupted (exists but not a valid video)
            # Only check corruption for files larger than 50KB to avoid false positives
            if status['file_exists'] and status['file_size'] > 50000:  # 50KB threshold
                try:
                    import subprocess
                    # Use ffprobe to check if the video file is valid
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                        '-show_format', status['file_path']
                    ], capture_output=True, text=True, timeout=10)  # Increased timeout
                    
                    if result.returncode != 0:
                        # Additional validation: check if file is growing (active recording)
                        current_size = os.path.getsize(status['file_path'])
                        time.sleep(2)  # Wait 2 seconds
                        new_size = os.path.getsize(status['file_path'])
                        
                        if new_size > current_size:
                            # File is still growing - not corrupted, just temporarily unreadable
                            print(f"⚠️ Recording file temporarily unreadable (still growing) - not restarting")
                            print(f"   File size: {current_size} -> {new_size} bytes (growing)")
                            print(f"   ffprobe return code: {result.returncode}")
                            self._reset_failure_counter()  # Reset on success
                        else:
                            # File is not growing and ffprobe failed - check consecutive failures
                            if self._increment_failure_counter():
                                print(f"⚠️ Recording file corrupted (3 consecutive failures) - restarting...")
                                print(f"   File size: {current_size} bytes (static)")
                                print(f"   ffprobe return code: {result.returncode}")
                                
                                self.stop_recording()
                                time.sleep(1)  # Brief pause
                                return self.start_rolling_recording()
                            else:
                                print(f"⚠️ Recording file issue detected (failure {self.consecutive_failures}/3) - monitoring...")
                    else:
                        # ffprobe succeeded - reset failure counter
                        self._reset_failure_counter()
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # ffprobe not available, skip validation
                    pass
            
            # For other issues, just log but don't restart
            if not status['is_healthy']:
                print(f"⚠️ Recording health check warning (not restarting):")
                print(f"   Active: {status['is_active']}")
                print(f"   Process running: {status['process_running']}")
                print(f"   File exists: {status['file_exists']}")
                print(f"   File size: {status['file_size']} bytes")
                print(f"   Elapsed time: {status['elapsed_time']:.1f}s")
            
            return True
            
        finally:
            # Always release the lock
            self.recording_lock.release()
    
    def _should_skip_health_check(self) -> bool:
        """Check if health check should be skipped to prevent interference"""
        current_time = time.time()
        
        # Skip if health checks are temporarily disabled
        if current_time < self.health_check_disabled_until:
            return True
        
        # Skip if health check was done recently
        if current_time - self.last_health_check < self.health_check_interval:
            return True
        
        # Skip if recording is very new (less than 30 seconds)
        if self.recording_start_time and (current_time - self.recording_start_time) < 30:
            return True
        
        return False
    
    def _reset_failure_counter(self):
        """Reset consecutive failure counter on success"""
        self.consecutive_failures = 0
    
    def _increment_failure_counter(self) -> bool:
        """Increment failure counter and return True if max reached"""
        self.consecutive_failures += 1
        return self.consecutive_failures >= self.max_consecutive_failures
    
    def disable_health_checks_temporarily(self, duration_seconds: int = 30):
        """Temporarily disable health checks during critical operations"""
        self.health_check_disabled_until = time.time() + duration_seconds
        print(f"🔒 Health checks disabled for {duration_seconds} seconds")
    
    def cleanup_old_recordings(self, max_age_hours: int = 2) -> None:
        """Clean up old recording files to save disk space"""
        try:
            temp_dir = "/tmp/claude_recordings"
            if not os.path.exists(temp_dir):
                return
                
            current_time = time.time()
            cleaned_count = 0
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(temp_dir):
                if filename.endswith('.mp4'):
                    filepath = os.path.join(temp_dir, filename)
                    
                    # Skip the current recording file unless we're doing full cleanup (max_age_hours=0)
                    if max_age_hours > 0 and filepath == self.recording_file:
                        continue
                        
                    # Delete files older than specified hours (or all files if max_age_hours=0)
                    file_age = current_time - os.path.getmtime(filepath)
                    if max_age_hours == 0 or file_age > max_age_seconds:
                        try:
                            os.remove(filepath)
                            cleaned_count += 1
                        except Exception as e:
                            print(f"⚠️ Could not delete old recording {filename}: {e}")
            
            if cleaned_count > 0:
                print(f"🧹 Cleaned up {cleaned_count} old recording files")
                
        except Exception as e:
            print(f"❌ Error during recording cleanup: {e}")
    
    async def send_recording_to_telegram(self, websocket, recording_file: str, description: str) -> None:
        """Send a video recording to Telegram"""
        try:
            # Check file exists and has content
            if not os.path.exists(recording_file):
                raise Exception("Recording file not found")
                
            file_size = os.path.getsize(recording_file)
            if file_size == 0:
                raise Exception("Recording file is empty")
            
            # Read video file
            with open(recording_file, 'rb') as f:
                video_data = f.read()
            
            # Encode video as base64
            import base64
            video_base64 = base64.b64encode(video_data).decode('utf-8')
            
            # Send video message via WebSocket
            message = {
                'type': 'video',
                'content': video_base64,
                'format': 'mp4',
                'caption': f'🎬 Rolling Recording: {description}',
                'filename': os.path.basename(recording_file)
            }
            
            await websocket.send(json.dumps(message))
            print(f"📹 Sent rolling recording to Telegram: {os.path.basename(recording_file)} ({file_size} bytes)")
            
        except Exception as e:
            print(f"❌ Failed to send recording to Telegram: {e}")
            raise
