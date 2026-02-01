"""Exploration Behaviors - Curiosity and investigation behaviors

Handles exploring, investigating sounds/movements, and navigation.
"""

import random
from typing import Dict, List, Optional, Tuple

from ..templates import get_template_library
from ..personality import Personality, Mood


class ExplorationBehaviors:
    """Exploration and investigation behaviors"""

    def __init__(self, template_library=None):
        self.templates = template_library or get_template_library()
        self._explored_areas: List[str] = []
        self._investigating = False

    def start_exploration(self,
                          mood: Mood,
                          personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Start exploring the environment

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._investigating = True
        response = self.templates.get_response("exploring_start")

        # More curious dogs talk more while exploring
        if personality.curiosity < 0.5:
            response.speech = ""

        tools = [{
            'name': 'explore',
            'params': {}
        }]

        return response.speech, response.actions, tools

    def continue_exploration(self,
                             mood: Mood,
                             personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Continue exploring

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        if not self._investigating:
            return self.start_exploration(mood, personality)

        # Various exploration behaviors
        categories = [
            "exploring_during",
            "curious_investigating",
            "curious_sniffing",
        ]
        category = random.choice(categories)
        response = self.templates.get_response(category)

        # Silent exploration sometimes
        if random.random() > personality.talkativeness:
            response.speech = ""

        return response.speech, response.actions, []

    def investigate_sound(self,
                          mood: Mood,
                          personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Investigate a sound

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("curious_sound")
        return response.speech, response.actions, []

    def investigate_movement(self,
                             mood: Mood,
                             personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Investigate detected movement

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("curious_movement")
        return response.speech, response.actions, []

    def found_something(self,
                        what: str,
                        mood: Mood,
                        personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """React to finding something interesting

        Args:
            what: Description of what was found
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("exploring_found_something")

        tools = [{
            'name': 'remember',
            'params': {
                'category': 'experience',
                'subject': 'exploration',
                'content': f"Found {what} while exploring"
            }
        }]

        return response.speech, response.actions, tools

    def navigate_to_room(self,
                         room_name: str,
                         mood: Mood,
                         personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Navigate to a specific room

        Args:
            room_name: Name of the room
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("navigating_to_room", room_name=room_name)

        tools = [{
            'name': 'go_to_room',
            'params': {'name': room_name}
        }]

        return response.speech, response.actions, tools

    def arrived_at_destination(self,
                               room_name: str,
                               mood: Mood) -> Tuple[str, List[str], List[Dict]]:
        """React to arriving at destination

        Args:
            room_name: Name of the room
            mood: Current mood

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._investigating = False
        response = self.templates.get_response("navigating_arrived", room_name=room_name)
        return response.speech, response.actions, []

    def got_lost(self, mood: Mood) -> Tuple[str, List[str], List[Dict]]:
        """React to being lost

        Args:
            mood: Current mood

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._investigating = False
        response = self.templates.get_response("navigating_lost")
        return response.speech, response.actions, []

    def stop_exploration(self):
        """Stop current exploration"""
        self._investigating = False

    def is_exploring(self) -> bool:
        """Check if currently exploring"""
        return self._investigating
