"""
Configuration module for Claude On The Beach
Centralizes all constants, settings, and configuration values
"""

import os
from typing import Optional


class Config:
    """Centralized configuration for the application"""
    
    # Monitoring intervals (seconds)
    STATUS_UPDATE_INTERVAL = 2
    COMPLETION_CHECK_INTERVAL = 1
    INITIAL_WAIT = 1
    MAX_WAIT_TIMEOUT = 300
    
    # Screenshot settings
    DUAL_SCREENSHOT_DELAY_MS = 100
    
    # Recording settings
    RECORDING_BUFFER_DURATION = 1200  # 20 minutes in seconds
    RECORDING_FPS = 5
    RECORDING_QUALITY_CRF = 20
    RECORDING_MAXRATE = "1000k"
    RECORDING_BUFSIZE = "2000k"
    
    # LLM settings
    LLM_MODEL = "claude-3-5-sonnet-20241022"
    LLM_MAX_TOKENS = 200
    
    # File paths
    TEMP_DIR = "/tmp/claude_recordings"
    SCREENSHOT_SUFFIX = ".png"
    
    # WebSocket settings
    DEFAULT_SERVER_URL = "wss://claudeonthebeach-production.up.railway.app/ws"
    PAIRING_TIMEOUT = 60
    
    # Status message patterns
    STATUS_WORDS = ['grooving', 'swooping', 'caramelizing', 'bewitching', 'fermenting', 'imagining']
    RUNNING_INDICATORS = ['running', 'running the tests', '+ running']
    ESC_INTERRUPT_PATTERN = "(esc to interrupt)"
    
    # Completion indicators (including model switching)
    COMPLETION_INDICATORS = [
        'claude opus limit reached',
        'now using sonnet',
        'model limit reached',
        'switching to',
        'falling back to',
        'using sonnet',
        'using opus',
        'model change',
        'limit reached'
    ]
    
    # Question similarity patterns
    QUESTION_PATTERNS = [
        'option+enter', 'multi-line', 'press ?', 'for shortcuts',
        'do you want to create', 'do you want to proceed', 'do you want to make',
        'edit confirmation', 'file edit', 'make this edit'
    ]
    
    # Enhanced question detection patterns
    QUESTION_DETECTION_PATTERNS = {
        # High confidence patterns (95%+)
        'high_confidence': [
            'do you want to', 'would you like to', 'should i', 'can i',
            'select', 'choose', 'pick', 'option', 'choice',
            'confirm', 'proceed', 'continue', 'yes/no',
            'y/n', 'r/v', 'a/b', '1/2/3', 'enter to', 'press'
        ],
        
        # Medium confidence patterns (80-95%)
        'medium_confidence': [
            'what', 'which', 'where', 'when', 'how', 'why',
            'enter', 'type', 'input', 'provide', 'specify',
            'name', 'path', 'directory', 'file', 'folder',
            'framework', 'library', 'package', 'version'
        ],
        
        # Low confidence patterns (60-80%)
        'low_confidence': [
            'please', 'kindly', 'could you', 'would you',
            'if you', 'when you', 'after you', 'before you',
            'ready', 'waiting', 'prompt', 'input needed'
        ],
        
        # File operation patterns
        'file_operations': [
            'create file', 'edit file', 'modify file', 'save file',
            'overwrite', 'replace', 'backup', 'rename',
            'delete', 'remove', 'move', 'copy'
        ],
        
        # Permission patterns
        'permissions': [
            'permission', 'authorize', 'allow', 'grant',
            'sudo', 'admin', 'root', 'privileges',
            'access', 'install', 'system', 'global'
        ],
        
        # Configuration patterns
        'configuration': [
            'configure', 'setup', 'install', 'initialize',
            'settings', 'preferences', 'options', 'parameters',
            'environment', 'variables', 'config', 'profile'
        ]
    }
    
    # Question similarity thresholds
    QUESTION_SIMILARITY_THRESHOLD = 0.75  # Default similarity threshold
    QUESTION_SIMILARITY_HIGH = 0.85       # High similarity threshold
    QUESTION_SIMILARITY_MEDIUM = 0.75     # Medium similarity threshold
    QUESTION_SIMILARITY_LOW = 0.60        # Low similarity threshold
    
    # Question context tracking
    QUESTION_CONTEXT_WINDOW = 5           # Number of previous questions to remember
    QUESTION_TIMEOUT_SECONDS = 300        # Timeout for question context (5 minutes)
    
    # Static screen detection (for completion detection)
    STATIC_SCREEN_TIMEOUT = 30  # seconds - reduced from 90s for faster detection
    STATIC_SCREEN_CHECK_INTERVAL = 5  # seconds - more frequent checks
    
    # Enhanced completion detection
    COMPLETION_DETECTION_TIMEOUT = 60  # seconds - max time to wait for completion
    COMPLETION_CONFIRMATION_DELAY = 3  # seconds - wait before confirming completion
    
    # Task-specific completion patterns
    TASK_COMPLETION_PATTERNS = {
        'test': ['all tests pass', 'test passed', 'pytest passed', '✓', 'PASSED'],
        'script': ['done', 'finished', 'complete', 'script completed', 'execution finished'],
        'file': ['file created', 'file saved', 'write complete', 'saved successfully'],
        'install': ['installation complete', 'installed successfully', 'setup complete'],
        'build': ['build complete', 'compilation finished', 'build successful'],
        'run': ['execution complete', 'program finished', 'process completed']
    }
    
    # Strong completion indicators (override other detection)
    STRONG_COMPLETION_INDICATORS = [
        '✅', '✓', 'PASSED', 'SUCCESS', 'COMPLETE', 'DONE', 'FINISHED',
        'all tests pass', 'installation complete', 'build successful',
        'script completed', 'execution finished', 'process completed'
    ]
    
    # Weak completion indicators (require additional confirmation)
    WEAK_COMPLETION_INDICATORS = [
        'ready', 'available', 'prepared', 'configured', 'set up',
        'waiting for input', 'prompt', '>', 'command line'
    ]
    
    @classmethod
    def get_server_url(cls) -> str:
        """Get WebSocket server URL from environment or default"""
        return os.getenv('SERVER_URL', cls.DEFAULT_SERVER_URL)
    
    @classmethod
    def get_screenshots_folder(cls) -> Optional[str]:
        """Get screenshots folder from environment"""
        return os.getenv('SCREENSHOTS_FOLDER')
    
    @classmethod
    def get_start_directory(cls) -> Optional[str]:
        """Get start directory from environment"""
        return os.getenv('START_DIRECTORY')


class Features:
    """Feature flags for optional functionality"""
    
    DUAL_SCREENSHOTS = os.getenv('DUAL_SCREENSHOTS', 'true').lower() == 'true'
    AUTO_SCREENSHOTS = os.getenv('AUTO_SCREENSHOTS', 'true').lower() == 'true'
    SMART_MONITORING = os.getenv('SMART_MONITORING', 'true').lower() == 'true'
    COMMAND_PRIORITY = os.getenv('COMMAND_PRIORITY', 'true').lower() == 'true'
