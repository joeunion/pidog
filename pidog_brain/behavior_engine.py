"""Behavior Engine - Decision tree for local autonomous behavior

Replaces Claude API calls with a local behavior tree that evaluates:
- Current mood (happiness, excitement, tiredness, boredom, curiosity)
- Personality traits (playfulness, curiosity, affection, energy, talkativeness)
- Observations (vision events, sensor readings)
- Memory context (known people, recent interactions)

Returns Decision objects that match the Claude response format:
- speech: What to say (from templates)
- actions: Physical actions to perform
- tools: Memory/goal updates to execute

Usage:
    from behavior_engine import BehaviorEngine

    engine = BehaviorEngine(template_library, memory_manager, personality_manager)
    decision = engine.decide(mood, observations)
"""

import random
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .templates import TemplateLibrary, TemplateResponse, get_template_library
from .personality import Personality, Mood

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Result of a behavior decision - matches Claude response format"""
    speech: str
    actions: List[str]
    tools: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (matches JSON response format)"""
        return {
            'speech': self.speech,
            'actions': self.actions,
            'tools': [{'name': t['name'], 'params': t.get('params', {})} for t in self.tools]
        }


@dataclass
class ObservationContext:
    """Context from recent observations"""
    person_detected: bool = False
    person_name: Optional[str] = None  # None = unknown person
    person_is_new: bool = False  # First time seeing this person
    person_is_returning: bool = False  # Seen recently, left, now back
    face_detected: bool = False
    obstacle_detected: bool = False
    obstacle_distance: float = 100.0
    touch_detected: bool = False
    touch_style: Optional[str] = None
    time_since_last_person: float = float('inf')
    time_since_last_interaction: float = 0.0
    idle_time: float = 0.0
    has_active_goal: bool = False
    active_goal_id: Optional[int] = None  # Goal ID for completion tracking
    active_goal_description: Optional[str] = None


class BehaviorEngine:
    """Local behavior decision engine

    Evaluates mood, personality, and observations to select appropriate
    behaviors without requiring API calls.

    The decision tree prioritizes:
    1. Person interactions (greetings, social behaviors)
    2. Active goals (goal-directed behavior)
    3. Mood-based behaviors (bored, curious, tired, happy)
    4. Default idle behaviors
    """

    def __init__(self,
                 template_library: Optional[TemplateLibrary] = None,
                 memory_manager=None,
                 personality_manager=None):
        """Initialize behavior engine

        Args:
            template_library: Template library instance (uses default if None)
            memory_manager: Memory manager for context
            personality_manager: Personality manager for traits
        """
        self.templates = template_library or get_template_library()
        self.memory = memory_manager
        self.personality = personality_manager

        # Track state for avoiding repetition
        self._last_template_category = None
        self._last_decision_time = 0
        self._recent_categories: List[str] = []  # Last 5 categories used
        self._greeting_cooldown: Dict[str, float] = {}  # name -> last greeted time

    def decide(self,
               mood: Mood,
               personality: Personality,
               observations: ObservationContext,
               memory_context: Optional[Dict[str, Any]] = None) -> Decision:
        """Make a behavior decision based on current state

        Args:
            mood: Current mood state
            personality: Personality traits
            observations: Recent observations context
            memory_context: Optional memory context (recent memories, goals, etc.)

        Returns:
            Decision with speech, actions, and tools
        """
        memory_context = memory_context or {}

        # Evaluate decision tree
        decision = self._evaluate_tree(mood, personality, observations, memory_context)

        # Track for anti-repetition
        self._last_decision_time = time.time()

        return decision

    def _evaluate_tree(self,
                       mood: Mood,
                       personality: Personality,
                       obs: ObservationContext,
                       memory_ctx: Dict[str, Any]) -> Decision:
        """Evaluate the behavior decision tree

        Tree structure:
        1. [Priority] Person detected?
           - Known person -> greet_known_person
           - Unknown person -> greet_unknown_person
        2. [Priority] Obstacle too close?
           - Back up and react
        3. [Priority] Touch detected?
           - React to touch (positive or negative)
        4. [Priority] Active goal?
           - Work on goal
        5. [Selector] Mood-based behavior
           - boredom > 0.7 -> play/restless behaviors
           - curiosity > 0.6 -> investigate behaviors
           - tiredness > 0.7 -> rest behaviors
           - happiness > 0.6 -> joy behaviors
        6. [Fallback] Idle behavior
        """

        # 1. Person detection (highest priority for social dog)
        if obs.person_detected:
            return self._handle_person(mood, personality, obs, memory_ctx)

        # 2. Obstacle too close
        if obs.obstacle_detected and obs.obstacle_distance < 15:
            return self._handle_obstacle(mood, personality, obs)

        # 3. Touch detected
        if obs.touch_detected:
            return self._handle_touch(mood, personality, obs)

        # 4. Active goal
        if obs.has_active_goal and obs.active_goal_description:
            return self._handle_goal(mood, personality, obs, memory_ctx)

        # 5. Mood-based behaviors
        mood_decision = self._handle_mood(mood, personality, obs)
        if mood_decision:
            return mood_decision

        # 6. Fallback: idle behavior
        return self._handle_idle(mood, personality, obs)

    def _handle_person(self,
                       mood: Mood,
                       personality: Personality,
                       obs: ObservationContext,
                       memory_ctx: Dict[str, Any]) -> Decision:
        """Handle person detection"""

        # Check greeting cooldown (don't greet same person repeatedly)
        name = obs.person_name or "unknown"
        last_greeted = self._greeting_cooldown.get(name, 0)
        cooldown_seconds = 60  # Don't re-greet for 60 seconds

        if time.time() - last_greeted < cooldown_seconds:
            # Already greeted recently, do a subtle acknowledgment instead
            if mood.excitement > 0.6:
                response = self.templates.get_response("happy_general")
            else:
                # Just idle, don't keep greeting
                return self._handle_idle(mood, personality, obs)
            return Decision(
                speech=response.speech,
                actions=response.actions
            )

        # Determine mood modifier for greeting
        mood_mod = None
        if mood.excitement > 0.7 or mood.happiness > 0.7:
            mood_mod = "excited"
        elif mood.tiredness > 0.6:
            mood_mod = "tired"

        if obs.person_name:
            # Known person
            if obs.person_is_returning:
                category = "greeting_returning_person"
            else:
                category = "greeting_known_person"

            response = self.templates.get_response(category, mood=mood_mod, name=obs.person_name)

            # Remember the interaction
            tools = [{
                'name': 'remember',
                'params': {
                    'category': 'interaction',
                    'subject': obs.person_name,
                    'content': f"Greeted {obs.person_name}"
                }
            }]

            # Add memory recall if we have memories about this person
            person_memories = memory_ctx.get('person_memories', {}).get(obs.person_name, [])
            if person_memories and random.random() < 0.3:  # 30% chance to mention memory
                memory = random.choice(person_memories)
                # Format memory recall to sound natural
                # Filter for memories that work grammatically with "I remember you..."
                action_starters = ('like', 'love', 'enjoy', 'prefer', 'hate', 'want', 'need',
                                   'play', 'gave', 'taught', 'showed', 'told', 'said')
                memory_lower = memory.lower().strip()
                if any(memory_lower.startswith(s) for s in action_starters):
                    response.speech += f" I remember you {memory}!"
                else:
                    # Use alternative phrasing for other memories
                    response.speech += f" I remember: {memory}"

        else:
            # Unknown person
            category = "greeting_unknown_person"
            response = self.templates.get_response(category, mood=mood_mod)
            tools = [{
                'name': 'remember',
                'params': {
                    'category': 'interaction',
                    'subject': 'unknown person',
                    'content': 'Met an unknown person'
                }
            }]

        # Update greeting cooldown
        self._greeting_cooldown[name] = time.time()
        self._track_category(category)

        return Decision(
            speech=response.speech,
            actions=response.actions,
            tools=tools
        )

    def _handle_obstacle(self,
                         mood: Mood,
                         personality: Personality,
                         obs: ObservationContext) -> Decision:
        """Handle obstacle detection"""
        if obs.obstacle_distance < 10:
            category = "reaction_too_close"
        else:
            category = "reaction_obstacle"

        response = self.templates.get_response(category)
        self._track_category(category)

        # Always include backward action for safety
        actions = list(response.actions)
        if "backward" not in actions:
            actions.insert(0, "backward")

        return Decision(
            speech=response.speech,
            actions=actions
        )

    def _handle_touch(self,
                      mood: Mood,
                      personality: Personality,
                      obs: ObservationContext) -> Decision:
        """Handle touch detection"""
        # Determine if this is a liked or disliked touch
        liked_touches = ["FRONT_TO_REAR", "PRESS"]
        disliked_touches = ["REAR_TO_FRONT"]

        if obs.touch_style in liked_touches:
            category = "affection_being_pet"
            response = self.templates.get_response(category)
        elif obs.touch_style in disliked_touches:
            category = "response_bad_dog"  # Negative reaction
            response = self.templates.get_response(category)
            response.actions = ["backward", "shake head"]
        else:
            category = "reaction_surprised"
            response = self.templates.get_response(category)

        self._track_category(category)

        return Decision(
            speech=response.speech,
            actions=response.actions
        )

    def _handle_goal(self,
                     mood: Mood,
                     personality: Personality,
                     obs: ObservationContext,
                     memory_ctx: Dict[str, Any]) -> Decision:
        """Handle active goal"""
        # Simple goal handling - just express working on it
        # More sophisticated goal handling would be in behavior_trees/goals.py

        category = "goal_working_on"
        response = self.templates.get_response(category)
        self._track_category(category)

        tools = []

        # Track goal progress and potentially complete
        # Goals complete after sustained work (simulated by random chance per cycle)
        if obs.active_goal_id is not None and random.random() < 0.1:  # 10% chance to complete
            category = "goal_completed"
            response = self.templates.get_response(category)
            tools.append({'name': 'complete_goal', 'params': {'id': obs.active_goal_id}})
            logger.info(f"Goal {obs.active_goal_id} completed: {obs.active_goal_description}")

        return Decision(
            speech=response.speech,
            actions=response.actions,
            tools=tools
        )

    def _handle_mood(self,
                     mood: Mood,
                     personality: Personality,
                     obs: ObservationContext) -> Optional[Decision]:
        """Handle mood-based behaviors

        Returns None if no mood-triggered behavior
        """

        # Boredom behaviors (high boredom = do something)
        if mood.boredom > 0.7:
            if personality.playfulness > 0.6:
                category = "bored_playful"
            elif personality.energy > 0.5:
                category = "bored_restless"
            else:
                category = "bored_idle"

            response = self.templates.get_response(category)
            self._track_category(category)

            return Decision(
                speech=response.speech,
                actions=response.actions
            )

        # Curiosity behaviors
        if mood.curiosity_level > 0.6:
            # Pick a curiosity category
            categories = ["curious_investigating", "curious_sniffing", "exploring_start"]
            category = random.choice(categories)

            response = self.templates.get_response(category)
            self._track_category(category)

            return Decision(
                speech=response.speech,
                actions=response.actions
            )

        # Tiredness behaviors
        if mood.tiredness > 0.7:
            if mood.tiredness > 0.9:
                category = "tired_going_to_sleep"
            else:
                category = "tired_general"

            response = self.templates.get_response(category)
            self._track_category(category)

            return Decision(
                speech=response.speech,
                actions=response.actions
            )

        # Happiness behaviors (when happy and not bored/tired)
        if mood.happiness > 0.6 and mood.excitement > 0.5:
            if mood.excitement > 0.7:
                category = "happy_excited"
            else:
                category = "happy_general"

            response = self.templates.get_response(category)
            self._track_category(category)

            return Decision(
                speech=response.speech,
                actions=response.actions
            )

        return None

    def _handle_idle(self,
                     mood: Mood,
                     personality: Personality,
                     obs: ObservationContext) -> Decision:
        """Handle idle state - default fallback behavior"""

        # Use a single random roll to determine idle behavior
        # Higher energy dogs get more animated idles
        roll = random.random()
        animation_threshold = 0.3 + (personality.energy * 0.4)  # 0.3 to 0.7 based on energy

        if roll < animation_threshold:
            # Animated idle behavior
            categories = ["happy_content", "curious_sniffing"]
            category = random.choice(categories)
        else:
            # Standard idle sounds
            category = "idle_sounds"

        response = self.templates.get_response(category)
        self._track_category(category)

        # Mostly silent for idle - 70% chance to suppress speech
        if category == "idle_sounds" and random.random() < 0.7:
            response.speech = ""

        return Decision(
            speech=response.speech,
            actions=response.actions
        )

    def _track_category(self, category: str):
        """Track recently used categories to avoid repetition"""
        self._last_template_category = category
        self._recent_categories.append(category)
        if len(self._recent_categories) > 5:
            self._recent_categories.pop(0)

    def handle_voice_input(self,
                           text: str,
                           mood: Mood,
                           personality: Personality,
                           known_person: Optional[str] = None) -> Decision:
        """Handle voice input using intent classification

        Args:
            text: User's spoken text
            mood: Current mood
            personality: Personality traits
            known_person: Name of person speaking (if recognized)

        Returns:
            Decision for responding to voice input
        """
        from .templates import get_intent_classifier

        classifier = get_intent_classifier()
        intent = classifier.classify(text)

        if not intent:
            # No recognized intent - confused response
            response = self.templates.get_response("reaction_confused")
            return Decision(
                speech=response.speech,
                actions=response.actions
            )

        # Get response category for intent
        category = classifier.get_response_category(intent)

        # Special handling for some intents
        if intent == "greeting":
            if known_person:
                category = "greeting_known_person"
                response = self.templates.get_response(category, name=known_person)
            else:
                category = "greeting_unknown_person"
                response = self.templates.get_response(category)
        elif intent == "farewell":
            if known_person:
                category = "farewell_known_person"
                response = self.templates.get_response(category, name=known_person)
            else:
                response = self.templates.get_response(category)
        elif category:
            response = self.templates.get_response(category)
        else:
            response = self.templates.get_response("reaction_confused")

        return Decision(
            speech=response.speech,
            actions=response.actions
        )


# Singleton instance
_behavior_engine: Optional[BehaviorEngine] = None


def get_behavior_engine() -> BehaviorEngine:
    """Get the singleton behavior engine instance"""
    global _behavior_engine
    if _behavior_engine is None:
        _behavior_engine = BehaviorEngine()
    return _behavior_engine
