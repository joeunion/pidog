"""Social Behaviors - Person interaction behaviors

Handles greetings, farewells, affection, and social engagement.
"""

import random
import time
from typing import Dict, List, Optional, Any, Tuple

from ..templates import get_template_library, TemplateResponse
from ..personality import Personality, Mood


class SocialBehaviors:
    """Social interaction behaviors"""

    def __init__(self, template_library=None):
        self.templates = template_library or get_template_library()
        self._greeting_cooldowns: Dict[str, float] = {}
        self._interaction_counts: Dict[str, int] = {}

    def greet_known_person(self,
                           name: str,
                           mood: Mood,
                           personality: Personality,
                           memories: Optional[List[str]] = None) -> Tuple[str, List[str], List[Dict]]:
        """Greet a known person

        Args:
            name: Person's name
            mood: Current mood
            personality: Personality traits
            memories: Optional list of memories about this person

        Returns:
            Tuple of (speech, actions, tools)
        """
        # Check cooldown
        last_greeted = self._greeting_cooldowns.get(name, 0)
        if time.time() - last_greeted < 60:
            # Recently greeted, subtle acknowledgment
            response = self.templates.get_response("happy_general")
            return response.speech, response.actions, []

        # Determine mood modifier
        mood_mod = self._get_mood_modifier(mood)

        # Check if returning (greeted before in this session)
        is_returning = name in self._greeting_cooldowns
        if is_returning:
            category = "greeting_returning_person"
        else:
            category = "greeting_known_person"

        response = self.templates.get_response(category, mood=mood_mod, name=name)

        # Maybe mention a memory
        speech = response.speech
        if memories and random.random() < personality.talkativeness * 0.5:
            memory = random.choice(memories)
            speech += f" I remember {memory}!"

        # Update cooldown
        self._greeting_cooldowns[name] = time.time()
        self._interaction_counts[name] = self._interaction_counts.get(name, 0) + 1

        tools = [{
            'name': 'remember',
            'params': {
                'category': 'interaction',
                'subject': name,
                'content': f"Greeted {name}"
            }
        }]

        return speech, response.actions, tools

    def greet_unknown_person(self,
                             mood: Mood,
                             personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Greet an unknown person

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        mood_mod = self._get_mood_modifier(mood)
        response = self.templates.get_response("greeting_unknown_person", mood=mood_mod)

        tools = [{
            'name': 'remember',
            'params': {
                'category': 'interaction',
                'subject': 'unknown person',
                'content': 'Met a new person'
            }
        }]

        return response.speech, response.actions, tools

    def farewell(self,
                 name: Optional[str],
                 mood: Mood,
                 personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Say farewell

        Args:
            name: Person's name (or None for general farewell)
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        if mood.happiness < 0.4:
            category = "farewell_sad"
            response = self.templates.get_response(category)
        elif name:
            category = "farewell_known_person"
            response = self.templates.get_response(category, name=name)
        else:
            category = "farewell_general"
            response = self.templates.get_response(category)

        # Clear greeting cooldown so we greet them next time
        if name and name in self._greeting_cooldowns:
            del self._greeting_cooldowns[name]

        return response.speech, response.actions, []

    def show_affection(self,
                       mood: Mood,
                       personality: Personality,
                       being_pet: bool = False) -> Tuple[str, List[str], List[Dict]]:
        """Express or respond to affection

        Args:
            mood: Current mood
            personality: Personality traits
            being_pet: Whether currently being petted

        Returns:
            Tuple of (speech, actions, tools)
        """
        if being_pet:
            category = "affection_being_pet"
        elif personality.affection > 0.6:
            category = "affection_seeking"
        else:
            category = "affection_expressing"

        response = self.templates.get_response(category)
        return response.speech, response.actions, []

    def react_to_praise(self, mood: Mood) -> Tuple[str, List[str], List[Dict]]:
        """React to being praised"""
        response = self.templates.get_response("response_good_dog")
        return response.speech, response.actions, []

    def react_to_scolding(self, mood: Mood) -> Tuple[str, List[str], List[Dict]]:
        """React to being scolded"""
        response = self.templates.get_response("response_bad_dog")
        return response.speech, response.actions, []

    def _get_mood_modifier(self, mood: Mood) -> Optional[str]:
        """Get mood modifier string based on mood state"""
        if mood.excitement > 0.7 or mood.happiness > 0.7:
            return "excited"
        elif mood.tiredness > 0.6:
            return "tired"
        return None

    def get_interaction_count(self, name: str) -> int:
        """Get number of interactions with a person"""
        return self._interaction_counts.get(name, 0)
