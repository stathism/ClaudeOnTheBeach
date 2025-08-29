"""
Enhanced Completion Detector Module
Combines multiple detection methods for accurate task completion detection
"""

import time
import re
from typing import Dict, Any, List, Optional
from PIL import Image
import io


class CompletionDetector:
    """Enhanced completion detection using multiple methods"""
    
    def __init__(self):
        self.completion_start_time = None
        self.last_completion_check = None
        self.completion_confidence = 0.0
        self.completion_indicators = []
        self.task_type = None
        self.static_screen_start = None
        
    def analyze_completion(self, screenshot_data, status_info: Dict[str, Any], 
                          command: str = None, task_type: str = None) -> Dict[str, Any]:
        """
        Comprehensive completion analysis using multiple detection methods
        
        Args:
            screenshot_data: Screenshot bytes or PIL Image
            status_info: LLM analysis result
            command: Original command that was executed
            task_type: Type of task (test, script, file, install, build, run)
            
        Returns:
            Dict with completion analysis results
        """
        from config import Config
        
        # Convert screenshot to text for pattern matching
        screenshot_text = self._extract_text_from_screenshot(screenshot_data)
        
        # Initialize result
        result = {
            'is_complete': False,
            'confidence': 0.0,
            'method': 'none',
            'indicators': [],
            'reasoning': []
        }
        
        # Method 1: Strong completion indicators (highest priority)
        strong_indicators = self._check_strong_completion_indicators(screenshot_text)
        if strong_indicators:
            result['is_complete'] = True
            result['confidence'] = 0.95
            result['method'] = 'strong_indicators'
            result['indicators'] = strong_indicators
            result['reasoning'].append(f"Found strong completion indicators: {strong_indicators}")
            return result
        
        # Method 2: Task-specific completion patterns
        if task_type and task_type in Config.TASK_COMPLETION_PATTERNS:
            task_indicators = self._check_task_specific_completion(screenshot_text, task_type)
            if task_indicators:
                result['is_complete'] = True
                result['confidence'] = 0.85
                result['method'] = 'task_specific'
                result['indicators'] = task_indicators
                result['reasoning'].append(f"Found task-specific completion for {task_type}: {task_indicators}")
                return result
        
        # Method 3: LLM analysis validation
        if status_info.get('is_complete', False):
            # Validate LLM completion with additional checks
            llm_validation = self._validate_llm_completion(screenshot_text, status_info)
            if llm_validation['valid']:
                result['is_complete'] = True
                result['confidence'] = 0.80
                result['method'] = 'llm_validated'
                result['indicators'] = llm_validation['indicators']
                result['reasoning'].append(f"LLM completion validated: {llm_validation['indicators']}")
                return result
        
        # Method 4: Weak completion indicators with confirmation
        weak_indicators = self._check_weak_completion_indicators(screenshot_text)
        if weak_indicators and self._confirm_weak_completion():
            result['is_complete'] = True
            result['confidence'] = 0.70
            result['method'] = 'weak_indicators'
            result['indicators'] = weak_indicators
            result['reasoning'].append(f"Confirmed weak completion indicators: {weak_indicators}")
            return result
        
        # Method 5: Static screen detection (fallback)
        static_result = self._check_static_screen_completion()
        if static_result['is_complete']:
            result['is_complete'] = True
            result['confidence'] = 0.60
            result['method'] = 'static_screen'
            result['indicators'] = ['static_screen']
            result['reasoning'].append(f"Static screen for {static_result['duration']:.1f}s")
            return result
        
        return result
    
    def _extract_text_from_screenshot(self, screenshot_data) -> str:
        """Extract text from screenshot for pattern matching"""
        # For now, return a placeholder - in a real implementation,
        # you'd use OCR or get text from the LLM analysis
        return ""
    
    def _check_strong_completion_indicators(self, text: str) -> List[str]:
        """Check for strong completion indicators that override other detection"""
        from config import Config
        
        found_indicators = []
        text_lower = text.lower()
        
        for indicator in Config.STRONG_COMPLETION_INDICATORS:
            if indicator.lower() in text_lower:
                found_indicators.append(indicator)
        
        return found_indicators
    
    def _check_task_specific_completion(self, text: str, task_type: str) -> List[str]:
        """Check for task-specific completion patterns"""
        from config import Config
        
        if task_type not in Config.TASK_COMPLETION_PATTERNS:
            return []
        
        found_indicators = []
        text_lower = text.lower()
        
        for pattern in Config.TASK_COMPLETION_PATTERNS[task_type]:
            if pattern.lower() in text_lower:
                found_indicators.append(pattern)
        
        return found_indicators
    
    def _validate_llm_completion(self, text: str, status_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate LLM completion decision with additional checks"""
        from config import Config
        
        # Check if LLM marked as complete but we see active indicators
        if status_info.get('is_complete', False):
            # Look for contradicting active indicators
            active_indicators = []
            
            # Check for status words
            for status_word in Config.STATUS_WORDS:
                if status_word.lower() in text.lower():
                    active_indicators.append(status_word)
            
            # Check for running indicators
            for running_indicator in Config.RUNNING_INDICATORS:
                if running_indicator.lower() in text.lower():
                    active_indicators.append(running_indicator)
            
            # Check for ESC interrupt pattern
            if Config.ESC_INTERRUPT_PATTERN.lower() in text.lower():
                active_indicators.append(Config.ESC_INTERRUPT_PATTERN)
            
            if active_indicators:
                return {
                    'valid': False,
                    'indicators': active_indicators,
                    'reason': f"LLM marked complete but found active indicators: {active_indicators}"
                }
            
            # Check for weak completion indicators to boost confidence
            weak_indicators = self._check_weak_completion_indicators(text)
            return {
                'valid': True,
                'indicators': weak_indicators,
                'reason': "LLM completion validated with weak indicators"
            }
        
        return {'valid': False, 'indicators': [], 'reason': "LLM did not mark as complete"}
    
    def _check_weak_completion_indicators(self, text: str) -> List[str]:
        """Check for weak completion indicators"""
        from config import Config
        
        found_indicators = []
        text_lower = text.lower()
        
        for indicator in Config.WEAK_COMPLETION_INDICATORS:
            if indicator.lower() in text_lower:
                found_indicators.append(indicator)
        
        return found_indicators
    
    def _confirm_weak_completion(self) -> bool:
        """Confirm weak completion with timing and consistency checks"""
        current_time = time.time()
        
        # Start tracking weak completion
        if self.completion_start_time is None:
            self.completion_start_time = current_time
            return False
        
        # Check if we've been seeing weak completion for enough time
        duration = current_time - self.completion_start_time
        from config import Config
        
        if duration >= Config.COMPLETION_CONFIRMATION_DELAY:
            return True
        
        return False
    
    def _check_static_screen_completion(self) -> Dict[str, Any]:
        """Check for static screen completion"""
        from config import Config
        
        current_time = time.time()
        
        # This would be called from the static screen detector
        # For now, return a placeholder
        return {
            'is_complete': False,
            'duration': 0
        }
    
    def update_static_screen_status(self, is_static: bool, duration: float):
        """Update static screen status from the static screen detector"""
        if is_static:
            if self.static_screen_start is None:
                self.static_screen_start = time.time()
        else:
            self.static_screen_start = None
    
    def reset(self):
        """Reset detector state for new task"""
        self.completion_start_time = None
        self.last_completion_check = None
        self.completion_confidence = 0.0
        self.completion_indicators = []
        self.task_type = None
        self.static_screen_start = None
    
    def set_task_type(self, task_type: str):
        """Set the type of task being monitored"""
        self.task_type = task_type
