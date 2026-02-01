"""Goal Behaviors - Goal-directed behaviors

Handles goal-directed actions, progress tracking, and goal completion.
"""

import random
from typing import Dict, List, Optional, Tuple, Any

from ..templates import get_template_library
from ..personality import Personality, Mood


class GoalBehaviors:
    """Goal-directed behaviors"""

    def __init__(self, template_library=None):
        self.templates = template_library or get_template_library()
        self._working_on_goal: Optional[Dict[str, Any]] = None
        self._goal_progress: Dict[int, float] = {}  # goal_id -> progress (0-1)

    def work_on_goal(self,
                     goal_id: int,
                     goal_description: str,
                     mood: Mood,
                     personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Work on an active goal

        Args:
            goal_id: Goal ID
            goal_description: Description of the goal
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._working_on_goal = {
            'id': goal_id,
            'description': goal_description
        }

        # Initialize or increment progress
        current_progress = self._goal_progress.get(goal_id, 0.0)
        progress_increment = random.uniform(0.1, 0.3) * personality.energy
        new_progress = min(1.0, current_progress + progress_increment)
        self._goal_progress[goal_id] = new_progress

        response = self.templates.get_response("goal_working_on")

        # Add goal-specific actions based on description
        actions = list(response.actions)
        actions.extend(self._get_goal_actions(goal_description))

        # Less talkative when concentrating
        if random.random() > personality.talkativeness * 0.5:
            response.speech = ""

        return response.speech, actions, []

    def complete_goal(self,
                      goal_id: int,
                      mood: Mood,
                      personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Complete a goal

        Args:
            goal_id: Goal ID
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._working_on_goal = None
        if goal_id in self._goal_progress:
            del self._goal_progress[goal_id]

        response = self.templates.get_response("goal_completed")

        tools = [{
            'name': 'complete_goal',
            'params': {'id': goal_id}
        }]

        return response.speech, response.actions, tools

    def goal_failed(self,
                    goal_id: int,
                    reason: str,
                    mood: Mood,
                    personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Handle goal failure

        Args:
            goal_id: Goal ID
            reason: Reason for failure
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        self._working_on_goal = None

        response = self.templates.get_response("goal_failed")

        tools = [{
            'name': 'remember',
            'params': {
                'category': 'experience',
                'subject': 'goal failure',
                'content': f"Failed goal: {reason}"
            }
        }]

        return response.speech, response.actions, tools

    def set_new_goal(self,
                     description: str,
                     priority: int,
                     mood: Mood,
                     personality: Personality) -> Tuple[str, List[str], List[Dict]]:
        """Set a new goal

        Args:
            description: Goal description
            priority: Priority 1-5
            mood: Current mood
            personality: Personality traits

        Returns:
            Tuple of (speech, actions, tools)
        """
        # Excited about new goal
        response = self.templates.get_response("happy_excited")

        tools = [{
            'name': 'set_goal',
            'params': {
                'description': description,
                'priority': priority
            }
        }]

        return response.speech, response.actions, tools

    def check_goal_progress(self, goal_id: int) -> float:
        """Check progress on a goal

        Args:
            goal_id: Goal ID

        Returns:
            Progress 0-1
        """
        return self._goal_progress.get(goal_id, 0.0)

    def is_goal_complete(self, goal_id: int) -> bool:
        """Check if a goal should be considered complete

        Args:
            goal_id: Goal ID

        Returns:
            True if progress >= 1.0
        """
        return self._goal_progress.get(goal_id, 0.0) >= 1.0

    def get_active_goal(self) -> Optional[Dict[str, Any]]:
        """Get currently active goal"""
        return self._working_on_goal

    def _get_goal_actions(self, description: str) -> List[str]:
        """Get actions appropriate for a goal description

        Args:
            description: Goal description

        Returns:
            List of actions
        """
        description_lower = description.lower()

        # Map goal types to actions
        if any(word in description_lower for word in ['trick', 'learn', 'practice']):
            return random.choice([
                ["think", "wag tail"],
                ["stretch", "think"],
                ["sit", "think"],
            ])
        elif any(word in description_lower for word in ['explore', 'find', 'search']):
            return random.choice([
                ["forward", "think"],
                ["turn left", "forward"],
                ["turn right", "forward"],
            ])
        elif any(word in description_lower for word in ['play', 'fun', 'game']):
            return random.choice([
                ["wag tail", "stretch"],
                ["bark", "wag tail"],
            ])
        else:
            return ["think", "wag tail"]

    def suggest_goal(self,
                     personality: Personality,
                     boredom: float) -> Optional[str]:
        """Suggest a new goal based on personality and state

        Args:
            personality: Personality traits
            boredom: Current boredom level

        Returns:
            Goal description or None
        """
        suggestions = []

        if personality.playfulness > 0.6:
            suggestions.append("Learn a new trick")
            suggestions.append("Have a play session")

        if personality.curiosity > 0.6:
            suggestions.append("Explore the area")
            suggestions.append("Find something interesting")

        if personality.affection > 0.6:
            suggestions.append("Find a friend to greet")

        if boredom > 0.7:
            suggestions.append("Do something fun")
            suggestions.append("Find something to play with")

        if suggestions:
            return random.choice(suggestions)
        return None
