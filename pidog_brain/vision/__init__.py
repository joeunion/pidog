"""PiDog Vision System - Local ML-based computer vision

All vision processing runs locally on Pi 5 - no API calls needed.

Components:
- FaceMemory: Learn and recognize faces using dlib/face_recognition
- PersonTracker: Detect and follow people using TFLite MobileNet-SSD
- RoomMemory: Learn and identify rooms via Claude descriptions
- Navigator: Visual navigation and exploration
- ObstacleDetector: Camera-based obstacle detection
"""

# Lazy imports to avoid loading heavy ML libraries until needed
def get_face_memory():
    from .face_memory import FaceMemory
    return FaceMemory

def get_person_tracker():
    from .person_tracker import PersonTracker
    return PersonTracker

def get_room_memory():
    from .room_memory import RoomMemory
    return RoomMemory

def get_navigator():
    from .navigator import Navigator
    return Navigator

def get_obstacle_detector():
    from .obstacle_detector import ObstacleDetector
    return ObstacleDetector

__all__ = [
    'get_face_memory',
    'get_person_tracker',
    'get_room_memory',
    'get_navigator',
    'get_obstacle_detector',
]
