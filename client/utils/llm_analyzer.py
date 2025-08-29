"""
LLM Analyzer Module
Handles all LLM-based screenshot analysis and status detection
"""

import asyncio
import base64
import io
import json
import re
from typing import Dict, Any, Optional, Tuple
from PIL import Image

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class LLMAnalyzer:
    """Handles LLM-based analysis of terminal screenshots"""
    
    def __init__(self, claude_client):
        self.claude_client = claude_client
    
    async def analyze_screenshot_with_llm(
        self, 
        screenshot: Image.Image, 
        second_screenshot: Optional[Image.Image] = None
    ) -> Dict[str, Any]:
        """
        Analyze screenshot with Claude API to understand terminal state
        
        Args:
            screenshot: Primary screenshot to analyze
            second_screenshot: Optional second screenshot for dual analysis
            
        Returns:
            Dictionary with analysis results
        """
        if not self.claude_client:
            return self._fallback_analysis()
        
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
                
                prompt = self._get_dual_screenshot_prompt()
            else:
                prompt = self._get_single_screenshot_prompt()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.claude_client.messages.create(
                    model=Config.LLM_MODEL,
                    max_tokens=Config.LLM_MAX_TOKENS,
                    messages=[{
                        "role": "user",
                        "content": content + [{"type": "text", "text": prompt}]
                    }]
                )
            )
            
            return self._parse_llm_response(response)
            
        except Exception as e:
            print(f"⚠️ Claude API analysis failed: {e}")
            return self._fallback_analysis()
    
    def _get_dual_screenshot_prompt(self) -> str:
        """Get prompt for dual screenshot analysis"""
        return f"""Analyze these two terminal screenshots taken 100ms apart and respond with a JSON object containing:

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
- Process is NOT complete if you see "{Config.ESC_INTERRUPT_PATTERN}" - this means it's still actively running
- Process is NOT complete if you see red text with symbols like ✶·✳ at the end of the screenshot - these indicate active processing
- Process is NOT complete if you see any loading indicators, progress bars, or "processing..." messages
- Process is NOT complete if you see any of these status messages: {', '.join(Config.STATUS_WORDS)}
- Process is NOT complete if you see any status message ending with "{Config.ESC_INTERRUPT_PATTERN}"
- Process is NOT complete if you see reddish/orange colored text - this indicates active processes
- Process is NOT complete if you see any of these running indicators: {', '.join(Config.RUNNING_INDICATORS)}
- Process is ONLY complete when screenshots are identical AND you see a clean prompt (>) with no active processing indicators
- Process is ONLY complete when screenshots are identical AND there are NO status messages like {', '.join(Config.STATUS_WORDS)}
- Process is ONLY complete when screenshots are identical AND there is NO reddish/orange colored text anywhere

VISUAL COLOR DETECTION:
- Reddish/orange text = IMMEDIATE "NOT COMPLETE" signal
- These colors are used specifically to indicate active processes
- Any status message in reddish/orange = NOT COMPLETE

IMPORTANT: Pay special attention to:
- Numbered options (1., 2., 3.) - these always need input
- File edit confirmation prompts with diff views
- "Do you want to..." questions
- Selection menus with highlighted options (❯)
- Permission/confirmation dialogs
- Any prompt asking user to choose between options

Look for signs of active processing (progress bars, "installing...", loading indicators, "{Config.ESC_INTERRUPT_PATTERN}") vs. waiting for input (selection menus, confirmation dialogs, numbered choices).

Keep status under 50 characters. Set needs_input=true if you see any selection prompt or question.

Examples:
{{"status": "Installing dependencies", "needs_input": false, "is_complete": false, "question": null, "screenshots_match": false}}
{{"status": "File edit confirmation", "needs_input": true, "is_complete": false, "question": "Do you want to make this edit to hello.py?", "screenshots_match": true}}
{{"status": "Choose framework option", "needs_input": true, "is_complete": false, "question": "React or Vue? (R/V)", "screenshots_match": true}}
{{"status": "Ready for input", "needs_input": false, "is_complete": true, "question": null, "screenshots_match": true}}"""
    
    def _get_single_screenshot_prompt(self) -> str:
        """Get prompt for single screenshot analysis"""
        return f"""Analyze this terminal screenshot and respond with a JSON object containing:

1. "status": Brief description of what's happening (e.g., "Installing npm packages", "File edit confirmation", "Ready for input")
2. "needs_input": true if waiting for user input/response, false otherwise  
3. "is_complete": true if process appears finished (showing prompt/ready for commands), false if actively running/processing
4. "question": if needs_input is true, what question/prompt is being asked

CRITICAL COMPLETION DETECTION RULES:
- Process is NOT complete if you see "{Config.ESC_INTERRUPT_PATTERN}" - this means it's still actively running
- Process is NOT complete if you see red text with symbols like ✶·✳ at the end of the screenshot - these indicate active processing
- Process is NOT complete if you see any loading indicators, progress bars, or "processing..." messages
- Process is NOT complete if you see any of these status messages: {', '.join(Config.STATUS_WORDS)}
- Process is NOT complete if you see any status message ending with "{Config.ESC_INTERRUPT_PATTERN}"
- Process is NOT complete if you see reddish/orange colored text - this indicates active processes
- Process is NOT complete if you see any of these running indicators: {', '.join(Config.RUNNING_INDICATORS)}
- Process is ONLY complete when you see a clean prompt (>) with no active processing indicators
- Process is ONLY complete when there are NO status messages like {', '.join(Config.STATUS_WORDS)}
- Process is ONLY complete when there is NO reddish/orange colored text anywhere
- Process IS complete when you see model switching messages like: {', '.join(Config.COMPLETION_INDICATORS)}

VISUAL COLOR DETECTION:
- Reddish/orange text = IMMEDIATE "NOT COMPLETE" signal
- These colors are used specifically to indicate active processes
- Any status message in reddish/orange = NOT COMPLETE

IMPORTANT: Pay special attention to:
- Numbered options (1., 2., 3.) - these always need input
- File edit confirmation prompts with diff views
- "Do you want to..." questions
- Selection menus with highlighted options (❯)
- Permission/confirmation dialogs
- Any prompt asking user to choose between options

Look for signs of active processing (progress bars, "installing...", loading indicators, "{Config.ESC_INTERRUPT_PATTERN}") vs. waiting for input (selection menus, confirmation dialogs, numbered choices).

Keep status under 50 characters. Set needs_input=true if you see any selection prompt or question.

Examples:
{{"status": "Installing dependencies", "needs_input": false, "is_complete": false, "question": null}}
{{"status": "File edit confirmation", "needs_input": true, "is_complete": false, "question": "Do you want to make this edit to hello.py?"}}
{{"status": "Choose framework option", "needs_input": true, "is_complete": false, "question": "React or Vue? (R/V)"}}
{{"status": "Model switch detected", "needs_input": false, "is_complete": true, "question": null}}
{{"status": "Ready for input", "needs_input": false, "is_complete": true, "question": null}}"""
    
    def _parse_llm_response(self, response) -> Dict[str, Any]:
        """Parse Claude's response and extract JSON"""
        response_text = response.content[0].text.strip()
        print(f"🧠 Raw Claude response: {response_text}")
        
        # Extract JSON from response (Claude might add explanation)
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
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when LLM is not available"""
        print("⚠️ No Claude API available - using fallback analysis")
        return {
            'status': 'Status unknown (no API)',
            'needs_input': False,
            'is_complete': True,  # Conservative: assume ready for commands
            'question': None,
            'screenshots_match': True
        }
    
    def validate_completion_status(self, status_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and potentially override completion status based on known patterns
        
        Args:
            status_info: LLM analysis result
            
        Returns:
            Validated status info with potential overrides
        """
        status_lower = status_info.get('status', '').lower()
        
        # Check for completion indicators (model switching, etc.)
        if any(completion_indicator in status_lower for completion_indicator in Config.COMPLETION_INDICATORS):
            print(f"✅ Override: Found completion indicator - IS complete")
            status_info['is_complete'] = True
            status_info['status'] = "Task completed (model switch detected)"
            return status_info
        
        if status_info.get('is_complete', False):
            # Double-check: If we see known patterns, it's NOT complete
            if Config.ESC_INTERRUPT_PATTERN in status_lower:
                print(f"⚠️ Override: Found '{Config.ESC_INTERRUPT_PATTERN}' - NOT complete")
                status_info['is_complete'] = False
                status_info['status'] = "Still processing"
            elif any(status_word in status_lower for status_word in Config.STATUS_WORDS):
                print(f"⚠️ Override: Found status message - NOT complete")
                status_info['is_complete'] = False
                status_info['status'] = "Still processing"
            elif any(running_indicator in status_lower for running_indicator in Config.RUNNING_INDICATORS):
                print(f"⚠️ Override: Found running indicator - NOT complete")
                status_info['is_complete'] = False
                status_info['status'] = "Still processing"
        
        return status_info
