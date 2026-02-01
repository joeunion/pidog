"""Play Behaviors - Play and entertainment behaviors

Handles play invitations, active play, tricks, and fun expressions.
"""

import random
from typing import Dict, List, Optional, Tuple

from ..templates import get_template_library
from ..personality import Personality, Mood


class PlayBehaviors:
    """Play and entertainment behaviors"""

    def __init__(self, template_library=None):
        self.templates = template_library or get_template_library()
        self._playing = False
        self._tricks_performed: List[str] = []

    def invite_to_play(self,
                       mood: Mood,
                       personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Invite someone to play

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        # More playful dogs have more enthusiastic invitations
        if personality.playfulness > 0.7:
            response = self.templates.get_response("play_invitation")
            # Add extra actions for very playful dogs
            response.actions = response.actions + ["stretch", "wag tail"]
        else:
            response = self.templates.get_response("play_invitation")

        return response.speech, response.actions, []

    def play_fetch(self,
                   mood: Mood,
                   personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Play fetch

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._playing = True
        response = self.templates.get_response("play_fetch")
        return response.speech, response.actions, []

    def during_play(self,
                    mood: Mood,
                    personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Express during active play

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._playing = True
        response = self.templates.get_response("play_during")

        # High energy dogs vocalize more during play
        if personality.energy < 0.5 and random.random() > 0.5:
            response.speech = ""

        return response.speech, response.actions, []

    def perform_trick(self,
                      trick_name: str,
                      trick_actions: List[str],
                      mood: Mood,
                      personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Perform a learned trick

        Args:
            trick_name: Name of the trick
            trick_actions: Actions that make up the trick
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        # Announcement
        response = self.templates.get_response("trick_performing")

        # The trick actions
        actions = list(trick_actions)

        self._tricks_performed.append(trick_name)

        tools = [{
            'name': 'do_trick',
            'params': {'name': trick_name}
        }]

        return response.speech, actions, tools

    def trick_completed(self,
                        mood: Mood,
                        personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """React after completing a trick

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("trick_completed")
        return response.speech, response.actions, []

    def learning_trick(self,
                       trick_name: str,
                       mood: Mood,
                       personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Express while learning a new trick

        Args:
            trick_name: Name of the trick being learned
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        response = self.templates.get_response("trick_learning")

        tools = [{
            'name': 'remember',
            'params': {
                'category': 'experience',
                'subject': 'tricks',
                'content': f"Learning {trick_name}"
            }
        }]

        return response.speech, response.actions, tools

    def express_joy(self,
                    mood: Mood,
                    personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Express happiness/joy

        Args:
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        if mood.excitement > 0.7:
            response = self.templates.get_response("happy_excited")
        else:
            response = self.templates.get_response("happy_general")

        return response.speech, response.actions, []

    def stop_playing(self):
        """Stop current play session"""
        self._playing = False

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self._playing

    def get_random_play_action(self,
                               personality: Personality) -> Tuple[str, List[str]]:
        """Get a random play action based on personality

        Args:
            personality: Personality traits

        Returns:
            Tuple of (speech, actions)
        """
        play_actions = [
            (["wag tail", "spin"], "Wheee!"),
            (["twist body", "wag tail"], "So fun!"),
            (["stretch", "wag tail"], "Play time!"),
            (["bark", "wag tail"], "Woof!"),
        ]

        if personality.energy > 0.7:
            # High energy - more active play
            play_actions.append((["bark harder", "twist body", "wag tail"], "WOOF WOOF!"))

        actions, speech = random.choice(play_actions)

        # Less talkative dogs don't speak as much during play
        if random.random() > personality.talkativeness:
            speech = ""

        return speech, actions
