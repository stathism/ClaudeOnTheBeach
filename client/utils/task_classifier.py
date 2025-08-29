"""
Task Classifier Module
Automatically determines the type of task being executed for better completion detection
"""

import re
from typing import Dict, Any, Optional


class TaskClassifier:
    """Classifies tasks based on command content and context"""
    
    def __init__(self):
        # Task type patterns
        self.task_patterns = {
            'test': [
                r'\btest\b', r'\bpytest\b', r'\bunittest\b', r'\bcheck\b', r'\bverify\b',
                r'\brun tests\b', r'\bexecute tests\b', r'\btest suite\b', r'\btesting\b'
            ],
            'script': [
                r'\bscript\b', r'\bpython\b', r'\bnode\b', r'\bruby\b', r'\bperl\b',
                r'\bexecute\b', r'\brun\b', r'\bstart\b', r'\blaunch\b', r'\bcreate.*script\b'
            ],
            'file': [
                r'\bfile\b', r'\bcreate\b', r'\bwrite\b', r'\bsave\b', r'\bedit\b',
                r'\bmodify\b', r'\bupdate\b', r'\bgenerate\b', r'\boutput.*file\b'
            ],
            'install': [
                r'\binstall\b', r'\bsetup\b', r'\bconfigure\b', r'\binit\b', r'\binitialize\b',
                r'\bpackage\b', r'\bdependency\b', r'\brequirements\b', r'\bnpm install\b',
                r'\bpip install\b', r'\bbrew install\b', r'\bapt install\b'
            ],
            'build': [
                r'\bbuild\b', r'\bcompile\b', r'\bmake\b', r'\bcmake\b', r'\bgradle\b',
                r'\bmaven\b', r'\bwebpack\b', r'\bbundler\b', r'\bconstruction\b'
            ],
            'run': [
                r'\brun\b', r'\bexecute\b', r'\bstart\b', r'\blaunch\b', r'\bprocess\b',
                r'\bprogram\b', r'\bapplication\b', r'\bserver\b', r'\bservice\b'
            ],
            'search': [
                r'\bsearch\b', r'\bfind\b', r'\blookup\b', r'\bquery\b', r'\bdiscover\b',
                r'\bexplore\b', r'\bscan\b', r'\bseek\b'
            ],
            'analyze': [
                r'\banalyze\b', r'\bexamine\b', r'\binvestigate\b', r'\bstudy\b', r'\bdebug\b',
                r'\bprofile\b', r'\boptimize\b', r'\bperformance\b'
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for task_type, patterns in self.task_patterns.items():
            self.compiled_patterns[task_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def classify_task(self, command: str, context: Dict[str, Any] = None) -> str:
        """
        Classify the type of task based on command and context
        
        Args:
            command: The command being executed
            context: Additional context (e.g., previous commands, file types)
            
        Returns:
            Task type string or 'unknown'
        """
        if not command:
            return 'unknown'
        
        command_lower = command.lower()
        
        # Score each task type
        scores = {}
        for task_type, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(command_lower):
                    score += 1
            
            # Bonus for exact matches
            for pattern in self.task_patterns[task_type]:
                if pattern.lower() in command_lower:
                    score += 0.5
            
            scores[task_type] = score
        
        # Find the highest scoring task type
        if scores:
            best_task = max(scores.items(), key=lambda x: x[1])
            if best_task[1] > 0:
                return best_task[0]
        
        # Fallback classification based on context
        if context:
            return self._classify_from_context(context)
        
        return 'unknown'
    
    def _classify_from_context(self, context: Dict[str, Any]) -> str:
        """Classify task based on context when command classification fails"""
        
        # Check for file extensions in context
        if 'files' in context:
            files = context['files']
            if any(f.endswith('.py') for f in files):
                return 'script'
            if any(f.endswith('.test') or f.endswith('_test.py') for f in files):
                return 'test'
            if any(f.endswith('.json') or f.endswith('.yaml') for f in files):
                return 'file'
        
        # Check for previous commands
        if 'previous_commands' in context:
            prev_commands = context['previous_commands']
            for cmd in prev_commands[-3:]:  # Check last 3 commands
                task_type = self.classify_task(cmd)
                if task_type != 'unknown':
                    return task_type
        
        return 'unknown'
    
    def get_completion_patterns(self, task_type: str) -> list:
        """Get completion patterns for a specific task type"""
        from config import Config
        
        if task_type in Config.TASK_COMPLETION_PATTERNS:
            return Config.TASK_COMPLETION_PATTERNS[task_type]
        
        return []
    
    def is_task_complete(self, task_type: str, status_text: str) -> bool:
        """Check if a specific task type is complete based on status text"""
        patterns = self.get_completion_patterns(task_type)
        
        status_lower = status_text.lower()
        for pattern in patterns:
            if pattern.lower() in status_lower:
                return True
        
        return False
