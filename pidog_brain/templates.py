"""Response Templates - Pre-written responses organized by situation and mood

This module provides ~100+ response templates for local autonomous behavior,
eliminating the need for Claude API calls for common situations.

Templates are organized by:
- Situation (greeting, farewell, bored, curious, etc.)
- Mood modifier (happy, tired, excited, etc.)
- Personality influence (playful vs serious, energetic vs calm)

Usage:
    from templates import TemplateLibrary

    templates = TemplateLibrary()
    speech = templates.get("greeting_known_person", name="Joe", mood="happy")
"""

import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class TemplateResponse:
    """A complete response with speech, actions, and optional tools"""
    speech: str
    actions: List[str]
    tools: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = []


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

# Each category maps to a list of templates
# Templates can use {variable} placeholders for dynamic content

TEMPLATES: Dict[str, List[str]] = {
    # =========================================================================
    # GREETINGS
    # =========================================================================

    "greeting_known_person": [
        "Hey {name}! Good to see you!",
        "Woof! {name} is here!",
        "{name}! Want to play?",
        "Oh hi {name}!",
        "There you are, {name}!",
        "{name}! I missed you!",
        "Yay, {name} is back!",
        "Hello {name}! What's up?",
    ],

    "greeting_known_person_excited": [
        "{name}! {name}! You're here!",
        "Woof woof! {name}! So happy to see you!",
        "Yes! {name} is back! Best day ever!",
        "{name}! I've been waiting for you!",
    ],

    "greeting_known_person_tired": [
        "Oh hey {name}...",
        "Hi {name}... *yawn*",
        "{name}... you're here... nice...",
    ],

    "greeting_unknown_person": [
        "Hello there! Who are you?",
        "Woof! A new friend!",
        "Hi! I don't think we've met!",
        "Oh! Someone new! What's your name?",
        "Hello! Nice to meet you!",
        "A visitor! Hi there!",
        "Woof! New person!",
    ],

    "greeting_returning_person": [
        "Oh, you're back {name}!",
        "{name}! Back so soon?",
        "Hey {name}, welcome back!",
        "You again {name}! Nice!",
    ],

    # =========================================================================
    # FAREWELLS
    # =========================================================================

    "farewell_general": [
        "Bye bye!",
        "See you later!",
        "Goodbye!",
        "Bye! Come back soon!",
        "Later!",
    ],

    "farewell_known_person": [
        "Bye {name}!",
        "See you later {name}!",
        "Bye bye {name}! Come back soon!",
        "Goodbye {name}!",
        "Miss you already {name}!",
    ],

    "farewell_sad": [
        "Aww, do you have to go?",
        "Already leaving?",
        "Bye... *whimper*",
        "I'll miss you...",
    ],

    # =========================================================================
    # BOREDOM
    # =========================================================================

    "bored_idle": [
        "*yawns* Nothing to do...",
        "So bored...",
        "*sighs*",
        "Hmm... what to do...",
        "Anyone want to play?",
        "This is boring...",
        "*looks around lazily*",
    ],

    "bored_playful": [
        "I want to play!",
        "Someone play with me!",
        "So bored! Let's do something fun!",
        "Play? Play? Anyone?",
        "Wanna play fetch?",
    ],

    "bored_restless": [
        "I need to do something!",
        "Can't just sit here...",
        "Gotta move around!",
        "Too much energy!",
    ],

    # =========================================================================
    # CURIOSITY / INVESTIGATION
    # =========================================================================

    "curious_investigating": [
        "What's that?",
        "Hmm, interesting...",
        "Let me check this out!",
        "Ooh, what's over there?",
        "That looks interesting!",
        "What could that be?",
    ],

    "curious_sound": [
        "Did you hear that?",
        "What was that noise?",
        "Hmm? What's that sound?",
        "I heard something!",
    ],

    "curious_movement": [
        "Something moved!",
        "Did something move over there?",
        "I saw something!",
        "What was that?",
    ],

    "curious_sniffing": [
        "What's that smell?",
        "Interesting scent...",
        "I smell something!",
        "*sniff sniff*",
    ],

    # =========================================================================
    # HAPPINESS / JOY
    # =========================================================================

    "happy_general": [
        "Woof!",
        "Life is good!",
        "I'm so happy!",
        "This is great!",
        "Yay!",
    ],

    "happy_excited": [
        "Woof woof woof!",
        "So excited!",
        "Best day ever!",
        "Yes yes yes!",
        "This is amazing!",
    ],

    "happy_content": [
        "Mmm, nice...",
        "This is nice.",
        "Feeling good.",
        "All is well.",
    ],

    # =========================================================================
    # TIREDNESS / REST
    # =========================================================================

    "tired_general": [
        "*yawn*",
        "I'm sleepy...",
        "Getting tired...",
        "Need a nap...",
        "So tired...",
    ],

    "tired_going_to_sleep": [
        "Time for a nap...",
        "Going to rest now...",
        "*curls up*",
        "Sleepy time...",
        "Zzz...",
    ],

    "tired_waking_up": [
        "*yawn* Oh, hi...",
        "Mmm... I was sleeping...",
        "*stretches* Ah, that was nice.",
        "Waking up...",
    ],

    # =========================================================================
    # PLAY
    # =========================================================================

    "play_invitation": [
        "Want to play?",
        "Play with me!",
        "Let's play!",
        "Chase me!",
        "Throw something!",
    ],

    "play_during": [
        "Woof! So fun!",
        "Catch me if you can!",
        "This is great!",
        "More! More!",
        "Again!",
    ],

    "play_fetch": [
        "Throw it! Throw it!",
        "I'll get it!",
        "Ready for the ball!",
        "Fetch! Let's play fetch!",
    ],

    # =========================================================================
    # AFFECTION / PETS
    # =========================================================================

    "affection_being_pet": [
        "Mmm that feels nice...",
        "Yes! Right there!",
        "More pets please!",
        "I love pets!",
        "Don't stop!",
    ],

    "affection_seeking": [
        "Pet me?",
        "I want pets!",
        "Can I have scratches?",
        "Please pet me!",
    ],

    "affection_expressing": [
        "I love you!",
        "You're the best!",
        "You're my favorite!",
        "I like you!",
    ],

    # =========================================================================
    # TRICKS
    # =========================================================================

    "trick_performing": [
        "Watch this!",
        "Here I go!",
        "Ta-da!",
        "Look what I can do!",
    ],

    "trick_completed": [
        "Did I do good?",
        "How was that?",
        "Treat? Treat?",
        "Nailed it!",
    ],

    "trick_learning": [
        "I'm learning!",
        "Let me try again!",
        "Almost got it!",
        "Ooh, new trick!",
    ],

    # =========================================================================
    # REACTIONS
    # =========================================================================

    "reaction_surprised": [
        "Whoa!",
        "What?!",
        "Huh?!",
        "Woof?!",
        "That startled me!",
    ],

    "reaction_confused": [
        "Huh?",
        "I don't understand...",
        "What do you mean?",
        "I'm confused...",
        "*tilts head*",
    ],

    "reaction_obstacle": [
        "Something's in the way!",
        "Can't go that way!",
        "Blocked!",
        "Oops, obstacle!",
    ],

    "reaction_too_close": [
        "Whoa, too close!",
        "Back up!",
        "Something's right there!",
        "Eep!",
    ],

    # =========================================================================
    # EXPLORATION / NAVIGATION
    # =========================================================================

    "exploring_start": [
        "Time to explore!",
        "Let's see what's around!",
        "Adventure time!",
        "Going exploring!",
    ],

    "exploring_during": [
        "Ooh, what's over here?",
        "Let me check this out...",
        "Interesting...",
        "Never been here before!",
    ],

    "exploring_found_something": [
        "Found something!",
        "Look at this!",
        "Ooh, interesting!",
        "What's this?",
    ],

    "navigating_to_room": [
        "Going to {room_name}!",
        "On my way to {room_name}!",
        "Heading to {room_name}!",
    ],

    "navigating_arrived": [
        "I'm here!",
        "Made it!",
        "Arrived at {room_name}!",
    ],

    "navigating_lost": [
        "Where am I?",
        "I'm lost...",
        "This doesn't look familiar...",
    ],

    # =========================================================================
    # MEMORY / RECALL
    # =========================================================================

    "memory_remembering": [
        "Oh, I remember!",
        "I know this!",
        "Wait, I remember...",
    ],

    "memory_about_person": [
        "I remember {name}! {memory}",
        "Oh {name}! You're the one who {memory}",
        "{name}! I remember you {memory}",
    ],

    "memory_forgot": [
        "Hmm, I don't remember...",
        "I forgot...",
        "Can't remember...",
    ],

    # =========================================================================
    # GOALS
    # =========================================================================

    "goal_working_on": [
        "Working on my goal!",
        "Gotta do this!",
        "Making progress!",
        "Almost there!",
    ],

    "goal_completed": [
        "I did it!",
        "Goal complete!",
        "Yes! Finished!",
        "Mission accomplished!",
    ],

    "goal_failed": [
        "Aww, didn't work...",
        "I'll try again later...",
        "That didn't go well...",
    ],

    # =========================================================================
    # ERRORS / CONFUSION
    # =========================================================================

    "error_general": [
        "Oops!",
        "That's not right...",
        "Something went wrong...",
        "Hmm, that didn't work...",
    ],

    "error_cant_do": [
        "I can't do that...",
        "That's too hard...",
        "I don't know how...",
    ],

    # =========================================================================
    # IDLE SOUNDS (non-verbal)
    # =========================================================================

    "idle_sounds": [
        "",  # Silent
        "*soft woof*",
        "*sniff*",
        "*sigh*",
        "*tail wag*",
    ],

    # =========================================================================
    # RESPONSES TO COMMON PHRASES
    # =========================================================================

    "response_good_dog": [
        "Woof! Thank you!",
        "I'm a good dog!",
        "Yay!",
        "*happy tail wag*",
    ],

    "response_bad_dog": [
        "*whimper*",
        "Sorry...",
        "I didn't mean to...",
        "*sad ears*",
    ],

    "response_treat": [
        "Treat?! Where?!",
        "I want it!",
        "Yes please!",
        "Gimme gimme!",
    ],

    "response_walk": [
        "Walk?! Really?!",
        "Outside?! Yes!",
        "Let's go let's go!",
        "WALK! WALK! WALK!",
    ],

    "response_sit": [
        "*sits*",
        "Sitting!",
        "I'm sitting!",
    ],

    "response_stay": [
        "*stays still*",
        "Staying...",
        "Not moving...",
    ],

    "response_come": [
        "Coming!",
        "On my way!",
        "*runs over*",
    ],
}


# =============================================================================
# ACTION MAPPINGS
# =============================================================================

# Actions to pair with each template category
TEMPLATE_ACTIONS: Dict[str, List[List[str]]] = {
    "greeting_known_person": [
        ["wag tail", "bark"],
        ["wag tail", "nod"],
        ["bark", "wag tail"],
    ],
    "greeting_known_person_excited": [
        ["wag tail", "bark", "wag tail"],
        ["bark", "wag tail", "spin"],
        ["wag tail", "bark harder"],
    ],
    "greeting_known_person_tired": [
        ["wag tail"],
        ["nod"],
    ],
    "greeting_unknown_person": [
        ["wag tail", "head tilt"],
        ["head tilt", "wag tail"],
        ["bark", "wag tail"],
    ],
    "greeting_returning_person": [
        ["wag tail", "nod"],
        ["wag tail"],
    ],
    "farewell_general": [
        ["wag tail"],
        ["nod"],
    ],
    "farewell_known_person": [
        ["wag tail", "nod"],
        ["wag tail"],
    ],
    "farewell_sad": [
        ["shake head"],
        [],
    ],
    "bored_idle": [
        ["yawn", "lie"],
        ["lie"],
        ["sit", "yawn"],
        ["stretch", "lie"],
    ],
    "bored_playful": [
        ["wag tail", "stretch"],
        ["bark", "wag tail", "spin"],
        ["stretch", "bark"],
        ["push up", "wag tail"],
        ["trot", "wag tail"],
        ["stand", "stretch", "sit"],
    ],
    "bored_restless": [
        ["stand", "forward", "turn left"],
        ["turn left", "turn right", "forward"],
        ["trot", "turn right"],
        ["forward", "backward", "forward"],
    ],
    "curious_investigating": [
        ["stand", "forward", "head tilt"],
        ["head tilt", "forward", "sit"],
        ["forward", "turn left", "forward"],
        ["trot", "head tilt"],
    ],
    "curious_sound": [
        ["head tilt", "stand"],
        ["think", "turn left"],
        ["head tilt", "turn right"],
    ],
    "curious_movement": [
        ["stand", "forward"],
        ["forward", "head tilt"],
        ["trot", "forward"],
    ],
    "curious_sniffing": [
        ["forward", "sit"],
        ["forward", "forward"],
        ["stand", "forward"],
    ],
    "happy_general": [
        ["wag tail", "stand"],
        ["wag tail", "bark"],
        ["sit", "wag tail"],
    ],
    "happy_excited": [
        ["wag tail", "bark", "spin"],
        ["bark", "spin", "wag tail"],
        ["stand", "spin", "bark"],
        ["push up", "wag tail", "bark"],
        ["trot", "spin", "wag tail"],
    ],
    "happy_content": [
        ["wag tail", "sit"],
        ["lie", "wag tail"],
        ["stretch", "lie"],
    ],
    "tired_general": [
        ["yawn"],
        ["yawn", "lie"],
    ],
    "tired_going_to_sleep": [
        ["lie", "doze off"],
        ["yawn", "lie"],
    ],
    "tired_waking_up": [
        ["stretch", "yawn"],
        ["stretch"],
    ],
    "play_invitation": [
        ["stretch", "wag tail", "bark"],
        ["stand", "stretch", "wag tail"],
        ["push up", "bark", "wag tail"],
        ["sit", "stand", "wag tail"],
    ],
    "play_during": [
        ["trot", "bark", "wag tail"],
        ["spin", "bark", "spin"],
        ["forward", "bark", "backward"],
        ["push up", "wag tail"],
    ],
    "play_fetch": [
        ["sit", "wag tail", "stand"],
        ["forward", "wag tail"],
        ["trot", "sit"],
    ],
    "affection_being_pet": [
        ["wag tail"],
        ["wag tail", "nod"],
    ],
    "affection_seeking": [
        ["wag tail", "nod"],
        ["whimper", "wag tail"],
    ],
    "affection_expressing": [
        ["wag tail", "lick hand"],
        ["wag tail"],
    ],
    "trick_performing": [
        [],  # Actions will be filled by the trick itself
    ],
    "trick_completed": [
        ["wag tail", "sit"],
        ["wag tail"],
    ],
    "trick_learning": [
        ["think", "wag tail"],
    ],
    "reaction_surprised": [
        ["head tilt", "bark"],
        ["surprise"],
    ],
    "reaction_confused": [
        ["head tilt"],
        ["think"],
    ],
    "reaction_obstacle": [
        ["backward", "head tilt"],
        ["stop"],
    ],
    "reaction_too_close": [
        ["backward"],
        ["backward", "bark"],
    ],
    "exploring_start": [
        ["stand", "forward", "forward"],
        ["wag tail", "trot"],
        ["forward", "turn left", "forward"],
        ["stand", "forward", "head tilt"],
    ],
    "exploring_during": [
        ["forward", "turn right", "forward"],
        ["trot", "head tilt"],
        ["forward", "forward", "turn left"],
    ],
    "exploring_found_something": [
        ["sit", "wag tail", "bark"],
        ["head tilt", "forward", "sit"],
        ["stand", "bark", "wag tail"],
    ],
    "navigating_to_room": [
        ["trot", "forward"],
        ["forward", "forward", "forward"],
        ["wag tail", "trot"],
    ],
    "navigating_arrived": [
        ["sit", "wag tail", "bark"],
        ["wag tail", "sit"],
        ["stand", "wag tail"],
    ],
    "navigating_lost": [
        ["turn left", "turn right", "head tilt"],
        ["sit", "think", "stand"],
        ["turn left", "forward", "turn right"],
    ],
    "memory_remembering": [
        ["recall"],
        ["think"],
    ],
    "memory_about_person": [
        ["wag tail", "recall"],
        ["recall", "wag tail"],
    ],
    "memory_forgot": [
        ["think", "head tilt"],
    ],
    "goal_working_on": [
        ["stand", "forward", "wag tail"],
        ["sit", "think", "stand"],
        ["forward", "turn left", "sit"],
        ["trot", "wag tail"],
    ],
    "goal_completed": [
        ["spin", "bark", "wag tail"],
        ["push up", "bark", "wag tail"],
        ["stand", "spin", "sit"],
        ["wag tail", "bark", "spin"],
    ],
    "goal_failed": [
        ["sit", "shake head"],
        ["lie", "shake head"],
    ],
    "error_general": [
        ["head tilt"],
        ["shake head"],
    ],
    "error_cant_do": [
        ["shake head"],
        ["head tilt"],
    ],
    "idle_sounds": [
        [],
        ["wag tail"],
    ],
    "response_good_dog": [
        ["wag tail", "bark"],
        ["wag tail"],
    ],
    "response_bad_dog": [
        ["shake head"],
        [],
    ],
    "response_treat": [
        ["wag tail", "sit"],
        ["wag tail", "bark"],
    ],
    "response_walk": [
        ["wag tail", "bark", "wag tail"],
        ["bark", "wag tail", "spin"],
    ],
    "response_sit": [
        ["sit"],
    ],
    "response_stay": [
        ["sit"],
        [],
    ],
    "response_come": [
        ["forward", "wag tail"],
        ["forward"],
    ],
}


# =============================================================================
# TEMPLATE LIBRARY CLASS
# =============================================================================

class TemplateLibrary:
    """Manages response templates with mood and personality modifiers

    Usage:
        lib = TemplateLibrary()

        # Simple template lookup
        response = lib.get("greeting_known_person", name="Joe")

        # With mood modifier
        response = lib.get("greeting_known_person", name="Joe", mood="excited")

        # Get full response with actions
        response = lib.get_response("bored_idle")
        print(response.speech, response.actions)
    """

    def __init__(self):
        self.templates = TEMPLATES
        self.actions = TEMPLATE_ACTIONS

    def get(self, category: str, mood: Optional[str] = None, **kwargs) -> str:
        """Get a random template from a category, formatted with kwargs

        Args:
            category: Template category name
            mood: Optional mood modifier (appends to category if variant exists)
            **kwargs: Variables to substitute in template

        Returns:
            Formatted template string, or empty string if category not found
        """
        # Try mood-specific variant first
        if mood:
            mood_category = f"{category}_{mood}"
            if mood_category in self.templates:
                category = mood_category

        templates = self.templates.get(category, [])
        if not templates:
            return ""

        template = random.choice(templates)

        # Format with provided kwargs
        try:
            return template.format(**kwargs)
        except KeyError:
            # Missing variable - return template as-is
            return template

    def get_response(self, category: str, mood: Optional[str] = None,
                     **kwargs) -> TemplateResponse:
        """Get a complete response with speech and actions

        Args:
            category: Template category name
            mood: Optional mood modifier
            **kwargs: Variables to substitute in template

        Returns:
            TemplateResponse with speech and actions
        """
        speech = self.get(category, mood, **kwargs)

        # Get mood-specific or base actions
        action_category = category
        if mood:
            mood_category = f"{category}_{mood}"
            if mood_category in self.actions:
                action_category = mood_category

        action_options = self.actions.get(action_category, [[]])
        actions = random.choice(action_options) if action_options else []

        return TemplateResponse(speech=speech, actions=list(actions))

    def get_categories(self) -> List[str]:
        """Get all available template categories"""
        return list(self.templates.keys())

    def has_category(self, category: str) -> bool:
        """Check if a category exists"""
        return category in self.templates

    def add_template(self, category: str, template: str):
        """Add a new template to a category

        Args:
            category: Category name
            template: Template string (can include {variables})
        """
        if category not in self.templates:
            self.templates[category] = []
        self.templates[category].append(template)

    def set_actions(self, category: str, action_options: List[List[str]]):
        """Set action options for a category

        Args:
            category: Category name
            action_options: List of action lists to choose from
        """
        self.actions[category] = action_options


# =============================================================================
# INTENT CLASSIFIER (for voice input)
# =============================================================================

# Keyword mappings for simple intent classification
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "greeting": ["hello", "hi", "hey", "howdy", "greetings", "good morning",
                 "good afternoon", "good evening"],
    "farewell": ["bye", "goodbye", "see you", "later", "farewell", "goodnight",
                 "gotta go", "leaving"],
    "good_dog": ["good dog", "good boy", "good girl", "good puppy", "well done",
                 "good job", "nice", "great job"],
    "bad_dog": ["bad dog", "bad boy", "bad girl", "no", "stop that", "don't"],
    "treat": ["treat", "snack", "food", "hungry", "eat", "cookie", "biscuit"],
    "walk": ["walk", "outside", "go out", "walkies", "let's go"],
    "play": ["play", "fetch", "ball", "toy", "game", "chase", "fun"],
    "sit": ["sit", "sit down"],
    "stay": ["stay", "wait", "don't move"],
    "come": ["come", "come here", "here boy", "here girl"],
    "pet": ["pet", "scratch", "rub", "belly", "pets"],
    "trick": ["trick", "show me", "do a trick", "perform"],
    "sleep": ["sleep", "nap", "rest", "tired", "bedtime"],
    "what_name": ["what's your name", "who are you", "your name"],
    "how_are_you": ["how are you", "how do you feel", "are you okay", "you good"],
}


class IntentClassifier:
    """Simple keyword-based intent classifier

    Usage:
        classifier = IntentClassifier()
        intent = classifier.classify("Hey buddy, want to play?")
        # Returns: "play" (or None if no match)
    """

    def __init__(self):
        self.keywords = INTENT_KEYWORDS

    def classify(self, text: str) -> Optional[str]:
        """Classify text into an intent

        Args:
            text: Input text to classify

        Returns:
            Intent name or None if no match
        """
        text_lower = text.lower()

        # Check each intent's keywords
        for intent, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return intent

        return None

    def get_response_category(self, intent: str) -> Optional[str]:
        """Map an intent to a response template category

        Args:
            intent: Intent name

        Returns:
            Template category name or None
        """
        mapping = {
            "greeting": "greeting_unknown_person",  # Will be overridden if person known
            "farewell": "farewell_general",
            "good_dog": "response_good_dog",
            "bad_dog": "response_bad_dog",
            "treat": "response_treat",
            "walk": "response_walk",
            "play": "play_invitation",
            "sit": "response_sit",
            "stay": "response_stay",
            "come": "response_come",
            "pet": "affection_being_pet",
            "trick": "trick_performing",
            "sleep": "tired_going_to_sleep",
        }
        return mapping.get(intent)


# Singleton instances for easy access
_template_library: Optional[TemplateLibrary] = None
_intent_classifier: Optional[IntentClassifier] = None


def get_template_library() -> TemplateLibrary:
    """Get the singleton template library instance"""
    global _template_library
    if _template_library is None:
        _template_library = TemplateLibrary()
    return _template_library


def get_intent_classifier() -> IntentClassifier:
    """Get the singleton intent classifier instance"""
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier
