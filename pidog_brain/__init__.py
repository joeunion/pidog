"""PiDog Brain - Autonomous memory, learning, and decision-making system

This package provides the cognitive systems for an autonomous robot dog:
- Memory: Persistent SQLite storage with FTS5 full-text search
- Tools: Action system for learning tricks, storing memories, setting goals
- Vision: Face recognition, person tracking, room memory, navigation
- Personality: Self-modifiable traits (bounded 0-1)
- Autonomous Brain: State machine and think loop for autonomous behavior
- Camera Pool: Thread-safe shared camera access
- Logging: Structured logging configuration
- Health Monitor: Component health tracking
"""

from .memory_manager import MemoryManager
from .personality import PersonalityManager
from .tools import ToolExecutor
from .camera_pool import CameraPool
from .logging_config import setup_logging, get_logger
from .health_monitor import HealthMonitor, HealthStatus

__all__ = [
    'MemoryManager',
    'PersonalityManager',
    'ToolExecutor',
    'CameraPool',
    'setup_logging',
    'get_logger',
    'HealthMonitor',
    'HealthStatus',
]

__version__ = '0.2.0'
