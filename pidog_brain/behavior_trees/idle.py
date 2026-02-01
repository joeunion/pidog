"""Idle Behaviors - Boredom and rest behaviors

Handles idle states, boredom expressions, tiredness, and resting.
"""

import random
from typing import Dict, List, Optional, Tuple

from ..templates import get_template_library
from ..personality import Personality, Mood


class IdleBehaviors:
    """Idle, boredom, and rest behaviors"""

    def __init__(self, template_library=None):
        self.templates = template_library or get_template_library()
        self._resting = False
        self._sleeping = False
        self._idle_count = 0  # Track idle cycles to vary behavior

    def express_boredom(self,
                        mood: Mood,
                        personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Express boredom

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        # Different boredom styles based on personality
        if personality.playfulness > 0.6:
            category = "bored_playful"
        elif personality.energy > 0.5:
            category = "bored_restless"
        else:
            category = "bored_idle"

        response = self.templates.get_response(category)

        # Less talkative dogs might just do the action
        if random.random() > personality.talkativeness:
            response.speech = ""

        return response.speech, response.actions, []

    def express_tiredness(self,
                          mood: Mood,
                          personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Express tiredness

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("tired_general")
        return response.speech, response.actions, []

    def go_to_sleep(self,
                    mood: Mood,
                    personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Go to sleep

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._sleeping = True
        self._resting = True
        response = self.templates.get_response("tired_going_to_sleep")
        return response.speech, response.actions, []

    def wake_up(self,
                mood: Mood,
                personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Wake up from sleep

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._sleeping = False
        self._resting = False
        response = self.templates.get_response("tired_waking_up")
        return response.speech, response.actions, []

    def idle_animation(self,
                       mood: Mood,
                       personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Do an idle animation

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._idle_count += 1

        # Vary idle behaviors to avoid repetition
        if self._idle_count % 5 == 0:
            # Occasional content sound
            response = self.templates.get_response("happy_content")
        elif self._idle_count % 3 == 0:
            # Occasional sniff
            response = self.templates.get_response("curious_sniffing")
            response.speech = ""  # Silent sniffing
        else:
            # Standard idle
            response = self.templates.get_response("idle_sounds")

        # Mostly silent for idle
        if random.random() < 0.7:
            response.speech = ""

        # Lower energy dogs do fewer actions
        if personality.energy < 0.4 and random.random() > personality.energy:
            response.actions = []

        return response.speech, response.actions, []

    def start_resting(self,
                      mood: Mood,
                      personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Start resting (not sleeping, just relaxing)

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._resting = True

        # Pick a rest action
        rest_actions = [
            ["lie"],
            ["sit"],
            ["lie", "relax neck"],
        ]
        actions = random.choice(rest_actions)

        # Usually silent when resting
        speech = ""
        if random.random() < 0.2:
            response = self.templates.get_response("happy_content")
            speech = response.speech

        return speech, actions, []

    def stop_resting(self):
        """Stop resting"""
        self._resting = False
        self._sleeping = False
        self._idle_count = 0

    def is_resting(self) -> bool:
        """Check if currently resting"""
        return self._resting

    def is_sleeping(self) -> bool:
        """Check if currently sleeping"""
        return self._sleeping

    def get_idle_behavior(self,
                          mood: Mood,
                          personality: Personality,
                          idle_time: float) -> Tuple[str, List[str], List[Dict]]:
        """Get appropriate idle behavior based on state

        Args:
            mood: Current mood
            personality: Personality traits
            idle_time: Time in seconds since last activity

        Returns:
            Tuple of (speech, actions, tools)
        """
        # Very tired - go to sleep
        if mood.tiredness > 0.8 and idle_time > 60:
            return self.go_to_sleep(mood, personality)

        # Getting tired - start resting
        if mood.tiredness > 0.6 and idle_time > 30:
            return self.start_resting(mood, personality)

        # Very bored - express it
        if mood.boredom > 0.7:
            return self.express_boredom(mood, personality)

        # Moderate boredom with energy - might want to play
        if mood.boredom > 0.5 and personality.playfulness > 0.5:
            response = self.templates.get_response("bored_playful")
            return response.speech, response.actions, []

        # Default idle animation
        return self.idle_animation(mood, personality)
