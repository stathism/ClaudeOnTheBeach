"""
Static Screen Detector Module
Detects when the terminal screen has been unchanged for a long period,
indicating task completion
"""

import time
import hashlib
from typing import Optional, Dict, Any
from PIL import Image
import io


class StaticScreenDetector:
    """Detects when terminal screen has been static for a long period"""
    
    def __init__(self):
        self.last_screenshot_hash = None
        self.last_change_time = None
        self.static_start_time = None
        self.is_static = False
        
    def update_screenshot(self, screenshot_data) -> Dict[str, Any]:
        """
        Update with new screenshot and check if screen has been static
        
        Args:
            screenshot_data: PIL Image object or bytes
            
        Returns:
            Dict with static detection results
        """
        # Convert PIL Image to bytes if needed
        if hasattr(screenshot_data, 'save'):
            # It's a PIL Image object
            import io
            img_bytes = io.BytesIO()
            screenshot_data.save(img_bytes, format='PNG')
            screenshot_bytes = img_bytes.getvalue()
        else:
            # It's already bytes
            screenshot_bytes = screenshot_data
        
        # Calculate hash of current screenshot
        current_hash = self._calculate_screenshot_hash(screenshot_bytes)
        current_time = time.time()
        
        # Check if screenshot has changed
        if current_hash != self.last_screenshot_hash:
            # Screen has changed
            self.last_screenshot_hash = current_hash
            self.last_change_time = current_time
            self.static_start_time = None
            self.is_static = False
            
            return {
                'is_static': False,
                'static_duration': 0,
                'should_complete': False,
                'last_change_time': self.last_change_time
            }
        else:
            # Screen is the same
            if self.static_start_time is None:
                # First time seeing this static screen
                self.static_start_time = current_time
                self.is_static = True
            
            static_duration = current_time - self.static_start_time
            
            # Check if static for long enough to consider complete
            from config import Config
            should_complete = static_duration >= Config.STATIC_SCREEN_TIMEOUT
            
            return {
                'is_static': True,
                'static_duration': static_duration,
                'should_complete': should_complete,
                'last_change_time': self.last_change_time
            }
    
    def _calculate_screenshot_hash(self, screenshot_data: bytes) -> str:
        """Calculate a hash of the screenshot for comparison"""
        # Use a simple hash for quick comparison
        return hashlib.md5(screenshot_data).hexdigest()
    
    def reset(self) -> None:
        """Reset the detector state (e.g., after completion detected)"""
        self.last_screenshot_hash = None
        self.last_change_time = None
        self.static_start_time = None
        self.is_static = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current detector status"""
        current_time = time.time()
        static_duration = 0
        
        if self.static_start_time:
            static_duration = current_time - self.static_start_time
        
        return {
            'is_static': self.is_static,
            'static_duration': static_duration,
            'last_change_time': self.last_change_time,
            'static_start_time': self.static_start_time
        }
