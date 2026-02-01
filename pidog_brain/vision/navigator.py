"""Navigator - Visual navigation and exploration

Provides autonomous navigation capabilities:
- Safe exploration (wandering while avoiding obstacles)
- Goal-directed navigation to learned rooms
- Person finding (search for known faces)

Combines camera vision with ultrasonic sensor for robust obstacle avoidance.
"""

import time
import random
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum, auto


class NavigationState(Enum):
    """Navigation state machine states"""
    IDLE = auto()
    EXPLORING = auto()
    NAVIGATING = auto()  # Going to specific room
    SEARCHING = auto()   # Looking for person
    AVOIDING = auto()    # Avoiding obstacle
    STOPPED = auto()


@dataclass
class NavigationCommand:
    """A navigation command to execute"""
    action: str  # "forward", "backward", "turn left", "turn right", "stop"
    duration: float = 0.5  # Seconds to execute
    speed: float = 1.0  # Speed modifier (0-1)


class Navigator:
    """Visual navigation and exploration system

    Usage:
        from pidog_brain.vision.navigator import Navigator
        from pidog_brain.vision.obstacle_detector import ObstacleDetector
        from pidog_brain.vision.person_tracker import PersonTracker
        from pidog_brain.vision.face_memory import FaceMemory

        nav = Navigator(
            obstacle_detector=ObstacleDetector(),
            person_tracker=PersonTracker(),
            face_memory=FaceMemory(memory_manager),
            action_callback=lambda actions: dog.do_actions(actions),
            get_distance=lambda: dog.read_distance()
        )

        # Start exploring
        nav.start_explore()

        # Navigate to room
        nav.go_to_room("kitchen")

        # Find person
        nav.find_person("Joe")
    """

    # Safety thresholds
    ULTRASONIC_DANGER = 15  # cm - emergency stop
    ULTRASONIC_CAUTION = 30  # cm - slow down
    ULTRASONIC_CLEAR = 50   # cm - safe to proceed

    # Exploration timing
    EXPLORE_STEP_TIME = 2.0  # Seconds between direction changes
    SEARCH_TURN_TIME = 3.0   # Seconds between search turns

    def __init__(self,
                 obstacle_detector=None,
                 person_tracker=None,
                 face_memory=None,
                 room_memory=None,
                 action_callback: Optional[Callable[[List[str]], None]] = None,
                 get_distance: Optional[Callable[[], float]] = None,
                 get_image: Optional[Callable[[], any]] = None):
        """Initialize navigator

        Args:
            obstacle_detector: ObstacleDetector instance
            person_tracker: PersonTracker instance
            face_memory: FaceMemory instance
            room_memory: RoomMemory instance
            action_callback: Function to execute actions
            get_distance: Function to get ultrasonic distance
            get_image: Function to get current camera image
        """
        self.obstacle_detector = obstacle_detector
        self.person_tracker = person_tracker
        self.face_memory = face_memory
        self.room_memory = room_memory
        self.action_callback = action_callback
        self.get_distance = get_distance
        self.get_image = get_image

        self.state = NavigationState.IDLE
        self.target_room: Optional[str] = None
        self.target_person: Optional[str] = None

        self._last_action_time = 0
        self._explore_direction = "forward"
        self._search_turns = 0

    def _execute(self, actions: List[str]):
        """Execute actions via callback"""
        if self.action_callback:
            self.action_callback(actions)

    def _get_ultrasonic_distance(self) -> float:
        """Get ultrasonic distance, with fallback"""
        if self.get_distance:
            try:
                return self.get_distance()
            except Exception:
                pass
        return 100.0  # Assume clear if no sensor

    def _get_current_image(self):
        """Get current camera image"""
        if self.get_image:
            try:
                return self.get_image()
            except Exception:
                pass
        return None

    def _check_safety(self) -> Tuple[bool, str]:
        """Check if it's safe to move

        Returns:
            Tuple of (is_safe, reason)
        """
        distance = self._get_ultrasonic_distance()

        if distance < self.ULTRASONIC_DANGER:
            return False, "ultrasonic_danger"

        # Check camera-based obstacles
        image = self._get_current_image()
        if image is not None and self.obstacle_detector:
            obstacles = self.obstacle_detector.detect(image)
            if self.obstacle_detector.is_path_blocked(obstacles):
                return False, "vision_blocked"

        return True, "clear"

    def _avoid_obstacle(self) -> NavigationCommand:
        """Determine how to avoid an obstacle

        Returns:
            Navigation command to avoid obstacle
        """
        image = self._get_current_image()

        if image is not None and self.obstacle_detector:
            obstacles = self.obstacle_detector.detect(image)
            direction = self.obstacle_detector.get_clear_direction(obstacles)
        else:
            # Fallback: just turn
            direction = random.choice(["left", "right"])

        if direction == "forward":
            return NavigationCommand("forward", 0.5)
        elif direction == "left":
            return NavigationCommand("turn left", 0.5)
        elif direction == "right":
            return NavigationCommand("turn right", 0.5)
        else:
            return NavigationCommand("backward", 0.5)

    # ==================== EXPLORATION ====================

    def start_explore(self):
        """Start autonomous exploration"""
        self.state = NavigationState.EXPLORING
        self._last_action_time = time.time()
        self._explore_direction = "forward"

    def stop_explore(self):
        """Stop exploration"""
        self.state = NavigationState.IDLE
        self._execute(["stop"])

    def explore_step(self) -> Optional[NavigationCommand]:
        """Execute one step of exploration

        Call this regularly (e.g., every 0.5s) during exploration.

        Returns:
            The command executed, or None if idle
        """
        if self.state != NavigationState.EXPLORING:
            return None

        now = time.time()

        # Check safety
        is_safe, reason = self._check_safety()

        if not is_safe:
            # Avoid obstacle
            cmd = self._avoid_obstacle()
            self._execute([cmd.action])
            self._last_action_time = now
            return cmd

        # Time for a new action?
        if now - self._last_action_time > self.EXPLORE_STEP_TIME:
            # Random exploration behavior
            r = random.random()

            if r < 0.6:
                # Continue forward most of the time
                cmd = NavigationCommand("forward", 1.0)
            elif r < 0.8:
                # Occasionally turn left
                cmd = NavigationCommand("turn left", 0.5)
            else:
                # Occasionally turn right
                cmd = NavigationCommand("turn right", 0.5)

            self._execute([cmd.action])
            self._last_action_time = now
            return cmd

        return None

    # ==================== ROOM NAVIGATION ====================

    def go_to_room(self, room_name: str) -> bool:
        """Start navigating to a room

        Args:
            room_name: Name of the room to go to

        Returns:
            True if room is known and navigation started
        """
        if self.room_memory is None:
            return False

        room = self.room_memory.memory.get_room(room_name)
        if room is None:
            return False

        self.state = NavigationState.NAVIGATING
        self.target_room = room_name
        return True

    def navigate_step(self) -> Tuple[Optional[NavigationCommand], bool]:
        """Execute one step of room navigation

        Returns:
            Tuple of (command, reached_destination)
        """
        if self.state != NavigationState.NAVIGATING:
            return None, False

        # Check safety first
        is_safe, reason = self._check_safety()
        if not is_safe:
            cmd = self._avoid_obstacle()
            self._execute([cmd.action])
            return cmd, False

        # Check if we've reached the room
        image = self._get_current_image()
        if image is not None and self.room_memory:
            match = self.room_memory.identify_room(image)
            if match and match.name.lower() == self.target_room.lower():
                # Reached destination!
                self.state = NavigationState.IDLE
                self._execute(["stop"])
                return NavigationCommand("stop", 0), True

        # Continue exploring toward room
        # In a real implementation, this would use more sophisticated
        # navigation (SLAM, path planning, etc.)
        cmd = NavigationCommand("forward", 0.5)
        self._execute([cmd.action])
        return cmd, False

    # ==================== PERSON FINDING ====================

    def find_person(self, name: str) -> bool:
        """Start searching for a person

        Args:
            name: Name of person to find

        Returns:
            True if person is known and search started
        """
        if self.face_memory is None:
            return False

        known_names = self.face_memory.get_known_names()
        if name not in known_names:
            return False

        self.state = NavigationState.SEARCHING
        self.target_person = name
        self._search_turns = 0
        return True

    def search_step(self) -> Tuple[Optional[NavigationCommand], bool]:
        """Execute one step of person search

        Returns:
            Tuple of (command, found_person)
        """
        if self.state != NavigationState.SEARCHING:
            return None, False

        # Check for target person
        image = self._get_current_image()
        if image is not None and self.face_memory:
            faces = self.face_memory.recognize(image)
            for face in faces:
                if face.name == self.target_person:
                    # Found them!
                    self.state = NavigationState.IDLE
                    self._execute(["stop", "wag tail"])
                    return NavigationCommand("stop", 0), True

        # Check safety
        is_safe, reason = self._check_safety()
        if not is_safe:
            cmd = self._avoid_obstacle()
            self._execute([cmd.action])
            return cmd, False

        now = time.time()

        # Search pattern: turn to scan, then move forward
        if now - self._last_action_time > self.SEARCH_TURN_TIME:
            self._search_turns += 1

            if self._search_turns >= 4:
                # Completed a full rotation, move forward
                self._search_turns = 0
                cmd = NavigationCommand("forward", 1.0)
            else:
                # Turn to scan
                cmd = NavigationCommand("turn left", 0.8)

            self._execute([cmd.action])
            self._last_action_time = now
            return cmd, False

        return None, False

    # ==================== MAIN UPDATE LOOP ====================

    def update(self) -> Tuple[NavigationState, Optional[NavigationCommand]]:
        """Main update method - call regularly

        Returns:
            Tuple of (current_state, executed_command)
        """
        cmd = None

        if self.state == NavigationState.EXPLORING:
            cmd = self.explore_step()

        elif self.state == NavigationState.NAVIGATING:
            cmd, reached = self.navigate_step()
            if reached:
                return NavigationState.IDLE, cmd

        elif self.state == NavigationState.SEARCHING:
            cmd, found = self.search_step()
            if found:
                return NavigationState.IDLE, cmd

        return self.state, cmd

    def stop(self):
        """Stop all navigation"""
        self.state = NavigationState.IDLE
        self.target_room = None
        self.target_person = None
        self._execute(["stop"])
