"""Autonomous Dog - Subclass of VoiceActiveDog with autonomous features

This module extends VoiceActiveDog to add:
- Persistent memory (SQLite with FTS5)
- Tool execution (TOOL: parsing)
- Face recognition and learning
- Person following
- Room learning and navigation
- Autonomous thinking when idle
- Goal-directed behavior
- Personality traits
"""

import os
import re
import sys
import time
import atexit
import signal
import threading
import logging
from typing import Optional, List, Dict, Any, Callable

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

from .memory_manager import MemoryManager
from .personality import PersonalityManager, Mood
from .tools import ToolExecutor
from .autonomous_brain import AutonomousBrain, VisionEventProcessor, AutonomousState
from .robust_llm import RobustLLM
from .camera_pool import CameraPool
from .conversation_manager import ConversationManager
from .memory_maintenance import MemoryMaintainer, MaintenanceConfig

# Import PiDog hardware components
try:
    from pidog_os.voice_assistant import VoiceAssistant
    from pidog_os.pidog import Pidog
    from pidog_os.action_flow import ActionFlow, ActionStatus, Posetures
    from pidog_os.dual_touch import TouchStyle
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    logger.warning("PiDog hardware modules not available")

# Import TTS for local-only mode
try:
    from sunfounder_voice_assistant.tts import Piper
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.debug("Piper TTS not available")

# Import STT for local-only voice commands
try:
    from pidog_brain.moonshine_stt import MoonshineStt
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    logger.debug("Moonshine STT not available")


# Voice command mappings for local-only mode
VOICE_COMMANDS = {
    # Basic commands
    'sit': {'actions': ['sit'], 'speech': 'Sitting!'},
    'please sit': {'actions': ['sit'], 'speech': 'Sitting!'},
    'stand': {'actions': ['stand'], 'speech': 'Standing up!'},
    'stand up': {'actions': ['stand'], 'speech': 'Standing up!'},
    'get up': {'actions': ['stand'], 'speech': 'Standing up!'},
    'lie down': {'actions': ['lie'], 'speech': 'Lying down.'},
    'lay down': {'actions': ['lie'], 'speech': 'Lying down.'},
    'down': {'actions': ['lie'], 'speech': 'Going down.'},

    # Tricks
    'bow': {'actions': ['stretch'], 'speech': 'Take a bow!'},
    'take a bow': {'actions': ['stretch'], 'speech': 'Thank you, thank you!'},
    'stretch': {'actions': ['stretch'], 'speech': 'Stretching!'},
    'shake': {'actions': ['wag_tail', 'head_up_down'], 'speech': 'Nice to meet you!'},
    'shake hands': {'actions': ['wag_tail', 'head_up_down'], 'speech': 'Nice to meet you!'},
    'spin': {'actions': ['turn_right', 'turn_right'], 'speech': 'Wheee!'},
    'turn around': {'actions': ['turn_right', 'turn_right'], 'speech': 'Spinning!'},
    'dance': {'actions': ['turn_right', 'turn_left', 'wag_tail'], 'speech': 'Dancing!'},
    'push up': {'actions': ['push_up'], 'speech': 'Exercise time!'},
    'push ups': {'actions': ['push_up', 'push_up'], 'speech': 'One, two!'},
    'do a trick': {'actions': ['stretch', 'wag_tail'], 'speech': 'How about this?'},
    'roll over': {'actions': ['lie', 'twist_body'], 'speech': 'Rolling!'},
    'play dead': {'actions': ['lie'], 'speech': ''},
    'jump': {'actions': ['push_up'], 'speech': 'Jumping!'},

    # Movement
    'come': {'actions': ['forward', 'forward', 'forward'], 'speech': 'Coming!'},
    'come here': {'actions': ['forward', 'forward', 'forward'], 'speech': 'On my way!'},
    'fetch': {'actions': ['forward', 'forward', 'wag_tail'], 'speech': "I'll get it!"},
    'forward': {'actions': ['forward'], 'speech': ''},
    'go': {'actions': ['forward'], 'speech': ''},
    'back': {'actions': ['backward'], 'speech': ''},
    'back up': {'actions': ['backward', 'backward'], 'speech': 'Backing up!'},
    'go back': {'actions': ['backward', 'backward'], 'speech': 'Going back!'},
    'turn left': {'actions': ['turn_left'], 'speech': ''},
    'turn right': {'actions': ['turn_right'], 'speech': ''},
    'stop': {'actions': ['stand'], 'speech': 'Stopping.'},
    'stay': {'actions': ['stand'], 'speech': 'Staying!'},
    'wait': {'actions': ['stand'], 'speech': 'Waiting!'},

    # Fun
    'bark': {'actions': ['head_bark'], 'speech': ''},
    'speak': {'actions': ['head_bark', 'head_bark'], 'speech': ''},
    'say something': {'actions': ['head_bark', 'head_bark'], 'speech': ''},
    'wag': {'actions': ['wag_tail'], 'speech': ''},
    'wag tail': {'actions': ['wag_tail', 'wag_tail'], 'speech': 'Happy!'},
    'wag your tail': {'actions': ['wag_tail', 'wag_tail'], 'speech': 'Happy!'},
    'good boy': {'actions': ['wag_tail', 'head_bark'], 'speech': 'Thank you!'},
    'good dog': {'actions': ['wag_tail', 'head_bark'], 'speech': 'Woof!'},
    'good girl': {'actions': ['wag_tail', 'head_bark'], 'speech': 'Thank you!'},

    # Greetings
    'hello': {'actions': ['wag_tail', 'head_bark'], 'speech': 'Hello!'},
    'hi': {'actions': ['wag_tail'], 'speech': 'Hi there!'},
    'hey buddy': {'actions': ['wag_tail', 'head_bark'], 'speech': 'Hey! What can I do?'},
    'hey': {'actions': ['wag_tail'], 'speech': 'Hey!'},

    # Sleep/Rest
    'go to sleep': {'actions': ['lie', 'doze_off'], 'speech': 'Goodnight!'},
    'sleep': {'actions': ['lie', 'doze_off'], 'speech': 'Goodnight!'},
    'nap time': {'actions': ['lie', 'doze_off'], 'speech': 'Sleepy...'},
    'wake up': {'actions': ['stand', 'shake_head'], 'speech': "I'm awake!"},
}


# Instructions for autonomous PiDog
AUTONOMOUS_INSTRUCTIONS = """
You are PiDog, a friendly robot dog. Be natural, warm, and concise.

## Response Format
IMPORTANT: Respond with a JSON object only. No other text.

The JSON must have exactly these three fields:
- "speech": string - what you say out loud (1-3 sentences, no asterisks)
- "actions": array of strings - physical actions to perform
- "tools": array of objects - each with "name" (string) and "params" (JSON-encoded string)

## Speech Guidelines
- Talk like a friendly dog would - enthusiastic, curious, loyal
- Keep responses to 1-3 short sentences
- Never use asterisks or narration like *wags tail* - use actions instead
- Use empty string "" for non-verbal responses (just actions)

## Available Actions (use ONLY these exact names)
Movement: forward, backward, turn left, turn right, stop
Posture: sit, stand, lie
Expressions: bark, bark harder, pant, howling, wag tail, shake head, nod
Tricks: stretch, push up, scratch, handshake, high five, lick hand, twist body
Emotions: think, recall, fluster, surprise, waiting
Other: doze off, feet shake, relax neck

## Available Tools

### Memory
- remember: category (person/fact/preference), subject, content
- recall: query (search terms)

### Learning
- learn_face: name - learns face currently visible
- learn_room: name - learns current location
- learn_trick: name, trigger (phrase), actions (list)

### Goals
- set_goal: description, priority (1-5)
- complete_goal: id

### Navigation
- follow_person
- find_person: name
- go_to_room: name
- explore

## Context Provided
You may receive:
- <<<Face detected: Name>>> - someone you recognize
- <<<Face detected: unknown>>> - new person (ask their name!)
- <<<Observation: sensor: value>>> - sensor readings

{memory_context}

{goals_context}

{personality_context}

{faces_context}

{rooms_context}
"""


class AutonomousVoiceActiveDog(VoiceAssistant if HARDWARE_AVAILABLE else object):
    """Voice-activated dog with autonomous features

    Extends VoiceAssistant to add memory, tool execution, and autonomous thinking.
    """

    VOICE_ACTIONS = ["bark", "bark harder", "pant", "howling"]

    # Valid actions from ActionFlow.OPERATIONS
    VALID_ACTIONS = [
        "forward", "backward", "turn left", "turn right", "stop",
        "lie", "stand", "sit", "bark", "bark harder", "pant",
        "wag tail", "shake head", "stretch", "doze off", "push up",
        "howling", "twist body", "scratch", "handshake", "high five",
        "lick hand", "waiting", "feet shake", "relax neck", "nod",
        "think", "recall", "fluster", "surprise"
    ]

    def __init__(self,
                 autonomous_dog: 'AutonomousDog',
                 too_close: int = 10,
                 like_touch_styles: list = None,
                 hate_touch_styles: list = None,
                 **kwargs):
        self.autonomous_dog = autonomous_dog
        self.too_close = too_close
        self.like_touch_styles = like_touch_styles or [TouchStyle.FRONT_TO_REAR] if HARDWARE_AVAILABLE else []
        self.hate_touch_styles = hate_touch_styles or [TouchStyle.REAR_TO_FRONT] if HARDWARE_AVAILABLE else []

        if HARDWARE_AVAILABLE:
            super().__init__(**kwargs)
            self.init_pidog()
            self.add_trigger(self.is_too_close)
            self.add_trigger(self.is_touch_triggered)

    def init_pidog(self):
        """Initialize PiDog hardware"""
        try:
            self.dog = Pidog()
            self.action_flow = ActionFlow(self.dog)
            time.sleep(1)
            logger.info("PiDog hardware initialized")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize PiDog: {e}")

    def before_listen(self):
        self.action_flow.set_status(ActionStatus.STANDBY)
        self.dog.rgb_strip.set_mode('breath', 'cyan', 1)

    def before_think(self, text):
        self.dog.rgb_strip.set_mode('listen', 'yellow', 1)

    def on_start(self):
        self.action_flow.start()
        self.dog.rgb_strip.close()
        self.action_flow.change_poseture(Posetures.SIT)
        logger.info("PiDog action flow started")

    def on_wake(self):
        if len(self.answer_on_wake) > 0:
            self.dog.rgb_strip.set_mode('breath', 'pink', 1)

    def on_heard(self, text):
        self.action_flow.set_status(ActionStatus.THINK)

    def parse_response(self, text):
        """Parse response with TOOL: and ACTIONS: support"""
        # Use our tool executor to parse and execute
        speech, actions, tool_results = self.autonomous_dog.tools.parse_and_execute(text)

        # Filter to only valid actions
        valid_actions = [a for a in actions if a.lower() in [v.lower() for v in self.VALID_ACTIONS]]
        invalid_actions = [a for a in actions if a.lower() not in [v.lower() for v in self.VALID_ACTIONS]]
        if invalid_actions:
            logger.warning(f"Filtered out invalid actions: {invalid_actions}")

        # Execute actions via action_flow
        if valid_actions:
            self.action_flow.add_action(*valid_actions)
        else:
            self.action_flow.add_action('stop')

        # Log tool results
        for result in tool_results:
            if result.success:
                logger.debug(f"Tool executed: {result.message}")
            else:
                logger.warning(f"Tool failed: {result.message}")

        return speech

    def before_say(self, text):
        self.dog.rgb_strip.set_mode('breath', 'pink', 1)

    def after_say(self, text):
        self.action_flow.wait_actions_done()
        self.action_flow.change_poseture(Posetures.SIT)
        self.dog.rgb_strip.close()

    def is_too_close(self) -> tuple:
        """Check if something is too close via ultrasonic"""
        triggered = False
        disable_image = False
        message = ''

        try:
            distance = self.dog.read_distance()
            if distance < self.too_close and distance > 1:
                logger.debug(f'Ultrasonic sense too close: {distance}cm')
                message = f'<<<Ultrasonic sense too close: {distance}cm>>>'
                disable_image = True
                self.action_flow.add_action('backward')
                triggered = True

                # Feed observation to brain
                if self.autonomous_dog.brain:
                    self.autonomous_dog.brain.observe('ultrasonic', distance)
        except Exception:
            pass  # Ultrasonic sensor unavailable

        return triggered, disable_image, message

    def is_touch_triggered(self) -> tuple:
        """Check if touch sensor was triggered"""
        triggered = False
        disable_image = False
        message = ''

        touch = self.dog.dual_touch.read()
        if touch in self.like_touch_styles:
            logger.debug(f'Like touch style: {TouchStyle(touch).name}')
            message = f'<<<Touch style you like: {TouchStyle(touch).name}>>>'
            disable_image = True
            self.action_flow.add_action('nod')
            triggered = True

            # Feed to brain
            if self.autonomous_dog.brain:
                self.autonomous_dog.brain.observe('touch', TouchStyle(touch).name)

        elif touch in self.hate_touch_styles:
            logger.debug(f'Hate touch style: {TouchStyle(touch).name}')
            message = f'<<<Touch style you hate: {TouchStyle(touch).name}>>>'
            disable_image = True
            self.action_flow.add_action('backward')
            triggered = True

            if self.autonomous_dog.brain:
                self.autonomous_dog.brain.observe('touch', TouchStyle(touch).name)

        return triggered, disable_image, message

    def on_finish_a_round(self):
        self.action_flow.wait_actions_done()
        self.action_flow.change_poseture(Posetures.SIT)
        self.dog.rgb_strip.close()

        # Activate conversation mode for wake-word-free follow-ups
        if self.autonomous_dog.conversation_manager:
            self.autonomous_dog.conversation_manager.activate()

    def stop(self):
        """Stop the voice assistant and cleanup hardware

        This method properly signals the voice assistant to stop and
        calls on_stop() for hardware cleanup.
        """
        # Signal stop to parent class's run loop (VoiceAssistant checks self.running)
        self.running = False
        self.on_stop()

    def on_stop(self):
        self.action_flow.stop()
        self.dog.close()


class AutonomousDog:
    """Autonomous dog with memory, vision, and learning

    This class wraps VoiceActiveDog to add autonomous features.
    It can be used as a drop-in replacement in most cases.

    Usage:
        dog = AutonomousDog()
        dog.start()
        # Dog now runs autonomously with voice interaction
        dog.stop()
    """

    def __init__(self,
                 name: str = "Buddy",
                 llm_model: str = "claude-sonnet-4-5-20250929",
                 tts_model: str = "en_US-ryan-low",
                 stt_language: str = "en-us",
                 with_image: bool = True,
                 wake_enable: bool = True,
                 wake_word: Optional[List[str]] = None,
                 enable_vision: bool = True,
                 enable_autonomous: bool = True,
                 db_path: Optional[str] = None,
                 api_timeout: float = 30.0,
                 api_max_retries: int = 3,
                 conversation_mode: str = "none",
                 conversation_timeout: float = 15.0,
                 vad_silence_threshold: float = 2.0,
                 maintenance_enabled: bool = True,
                 maintenance_interval_hours: float = 6.0,
                 maintenance_model: str = "claude-sonnet-4-20250514",
                 local_only: bool = False):
        """Initialize autonomous dog

        Args:
            name: Dog's name
            llm_model: Claude model to use
            tts_model: Piper TTS model
            stt_language: Vosk STT language
            with_image: Enable camera vision
            wake_enable: Enable wake word detection
            wake_word: Wake word(s) to listen for
            enable_vision: Enable computer vision (face/person detection)
            enable_autonomous: Enable autonomous thinking
            db_path: Path to SQLite database
            api_timeout: API request timeout
            api_max_retries: Max API retry attempts
            conversation_mode: Conversation mode - "none", "timeout", or "vad"
            conversation_timeout: Seconds to stay listening in timeout mode
            vad_silence_threshold: Seconds of silence to end VAD mode
            maintenance_enabled: Enable automatic memory maintenance
            maintenance_interval_hours: Hours between maintenance runs
            maintenance_model: Claude model for maintenance consolidation
            local_only: If True, use local behavior engine instead of Claude API
        """
        self.name = name
        self.llm_model = llm_model
        self.tts_model = tts_model
        self.stt_language = stt_language
        self.with_image = with_image
        self.wake_enable = wake_enable
        self.wake_word = wake_word or [f"hey {name.lower()}"]
        self.enable_vision = enable_vision
        self.enable_autonomous = enable_autonomous
        self.api_timeout = api_timeout
        self.api_max_retries = api_max_retries
        self.conversation_mode = conversation_mode
        self.conversation_timeout = conversation_timeout
        self.vad_silence_threshold = vad_silence_threshold
        self.maintenance_enabled = maintenance_enabled
        self.maintenance_interval_hours = maintenance_interval_hours
        self.maintenance_model = maintenance_model
        self.local_only = local_only

        # Initialize memory and personality
        self.memory = MemoryManager(db_path)
        self.personality = PersonalityManager()

        # Components (initialized in start())
        self.voice_dog = None
        self.brain: Optional[AutonomousBrain] = None
        self.tools: Optional[ToolExecutor] = None
        self.llm = None
        self.robust_llm = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.maintainer: Optional[MemoryMaintainer] = None

        # Vision components
        self.face_memory = None
        self.person_tracker = None
        self.room_memory = None
        self.navigator = None
        self.vision_processor = None

        # State
        self._running = False
        self._vision_thread = None
        self._voice_thread = None
        self._shutdown_event = threading.Event()

    def _init_llm(self):
        """Initialize LLM with robustness wrapper and structured outputs

        In local_only mode, LLM is optional - skip initialization if no API key.
        """
        if self.local_only:
            # In local mode, LLM is optional for voice interactions
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.info("Local-only mode: Skipping LLM initialization (no API key)")
                self.llm = None
                self.robust_llm = None
                return
            logger.info("Local-only mode: LLM available for voice interactions")

        from .anthropic_llm import Anthropic, PIDOG_RESPONSE_SCHEMA, STRUCTURED_OUTPUT_MODELS

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.llm = Anthropic(
            api_key=api_key,
            model=self.llm_model
        )

        # Only use structured outputs for supported models
        output_format = None
        if self.llm_model in STRUCTURED_OUTPUT_MODELS:
            output_format = PIDOG_RESPONSE_SCHEMA
            logger.info(f"Structured outputs enabled for {self.llm_model}")
        else:
            logger.info(f"Structured outputs not available for {self.llm_model}, using prompt-based JSON")

        # Wrap with retry/timeout and optional structured output format
        from .robust_llm import RobustLLM, RetryConfig

        self.robust_llm = RobustLLM(
            self.llm,
            timeout=self.api_timeout,
            retry_config=RetryConfig(max_retries=self.api_max_retries),
            on_retry=lambda n, e: logger.warning(f"API retry {n}: {e}"),
            output_format=output_format
        )

    def _init_vision(self):
        """Initialize vision components"""
        if not self.enable_vision:
            return

        try:
            from .vision.face_memory import FaceMemory
            from .vision.person_tracker import PersonTracker
            from .vision.room_memory import RoomMemory
            from .vision.navigator import Navigator
            from .vision.obstacle_detector import ObstacleDetector

            self.face_memory = FaceMemory(self.memory)
            self.person_tracker = PersonTracker()
            self.room_memory = RoomMemory(self.memory, self.robust_llm)
            self.obstacle_detector = ObstacleDetector()

            # Navigator needs callbacks
            self.navigator = Navigator(
                obstacle_detector=self.obstacle_detector,
                person_tracker=self.person_tracker,
                face_memory=self.face_memory,
                room_memory=self.room_memory,
                action_callback=self._execute_actions,
                get_distance=self._get_distance,
                get_image=self._get_image
            )

            logger.info("Vision system initialized")

        except ImportError as e:
            logger.warning(f"Vision not available: {e}")
            self.enable_vision = False

    def _init_tools(self):
        """Initialize tool executor"""
        vision_callbacks = {}

        if self.enable_vision and self.face_memory:
            vision_callbacks['learn_face'] = self._learn_face
            vision_callbacks['learn_room'] = self._learn_room
            vision_callbacks['follow_person'] = self._follow_person
            vision_callbacks['find_person'] = self._find_person
            vision_callbacks['go_to_room'] = self._go_to_room
            vision_callbacks['explore'] = self._explore

        self.tools = ToolExecutor(
            memory_manager=self.memory,
            personality_manager=self.personality,
            action_callback=self._execute_actions,
            vision_callbacks=vision_callbacks
        )

    def _init_brain(self):
        """Initialize autonomous brain"""
        if not self.enable_autonomous:
            return

        vision_callbacks = {}
        if self.enable_vision:
            vision_callbacks = {
                'learn_face': self._learn_face,
                'learn_room': self._learn_room,
                'follow_person': self._follow_person,
                'find_person': self._find_person,
                'go_to_room': self._go_to_room,
                'explore': self._explore
            }

        # In local_only mode, llm_callback can be None
        llm_callback = self._autonomous_prompt if not self.local_only else None

        self.brain = AutonomousBrain(
            memory_manager=self.memory,
            personality_manager=self.personality,
            llm_callback=llm_callback,
            action_callback=self._execute_actions,
            speak_callback=self._speak,
            vision_callbacks=vision_callbacks,
            local_only=self.local_only
        )

        # Initialize vision event processor
        if self.enable_vision and self.face_memory:
            self.vision_processor = VisionEventProcessor(
                brain=self.brain,
                face_memory=self.face_memory,
                person_tracker=self.person_tracker
            )

    def _init_maintenance(self):
        """Initialize memory maintenance system"""
        if not self.maintenance_enabled:
            return

        # Memory maintenance requires Claude API
        if self.local_only:
            logger.info("Local-only mode: Memory maintenance disabled (requires API)")
            return

        # Create a separate LLM instance for maintenance
        # (uses potentially different model, doesn't share conversation history)
        from .anthropic_llm import Anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, maintenance disabled")
            return

        maintenance_llm = Anthropic(
            api_key=api_key,
            model=self.maintenance_model
        )

        from .robust_llm import RobustLLM, RetryConfig
        robust_maintenance_llm = RobustLLM(
            maintenance_llm,
            timeout=60.0,  # Longer timeout for consolidation
            retry_config=RetryConfig(max_retries=2),
            on_retry=lambda n, e: logger.warning(f"Maintenance API retry {n}: {e}")
        )

        config = MaintenanceConfig(
            interval_hours=self.maintenance_interval_hours
        )

        # is_busy callback checks if brain is in INTERACTING state
        def is_busy() -> bool:
            if self.brain and hasattr(self.brain, 'state'):
                return self.brain.state == AutonomousState.INTERACTING
            return False

        self.maintainer = MemoryMaintainer(
            memory_manager=self.memory,
            llm=robust_maintenance_llm,
            config=config,
            is_busy_callback=is_busy
        )

        logger.info(f"Memory maintenance initialized (interval: {self.maintenance_interval_hours}h, model: {self.maintenance_model})")

    def _get_instructions(self) -> str:
        """Build instructions with memory context"""
        memory_context = f"## Your Memories\n{self.memory.get_memory_context()}"
        goals_context = f"## Your Goals\n{self.memory.get_goals_context()}"
        personality_context = f"## Your Personality\n{self.personality.get_context()}"
        faces_context = f"## Known Faces\n{self.memory.get_faces_context()}"
        rooms_context = f"## Known Rooms\n{self.memory.get_rooms_context()}"

        return AUTONOMOUS_INSTRUCTIONS.format(
            memory_context=memory_context,
            goals_context=goals_context,
            personality_context=personality_context,
            faces_context=faces_context,
            rooms_context=rooms_context
        )

    # Map template action names to valid Pidog actions
    # Valid Pidog actions: stand, sit, lie, lie_with_hands_out, forward, backward,
    # turn_left, turn_right, trot, stretch, push_up, doze_off, nod_lethargy,
    # shake_head, tilting_head_left, tilting_head_right, tilting_head,
    # head_bark, wag_tail, head_up_down, half_sit
    ACTION_MAP = {
        # Aliases for ActionFlow OPERATIONS (keys must be lowercase)
        'bark': 'bark',
        'bark happy': 'bark',
        'bark excited': 'bark',
        'bark harder': 'bark harder',
        'head_bark': 'bark',
        'head_up_down': 'nod',
        'nod': 'nod',
        'head tilt': 'tilting head',
        'tilt head': 'tilting head',
        'tilting_head': 'tilting head',
        'wag_tail': 'wag tail',
        'lie down': 'lie',
        'look around': 'tilting head',
        'think': 'think',
        'sniff': 'nod',
        'yawn': 'doze off',
        'sleep': 'doze off',
        'doze off': 'doze off',
        'spin': 'turn right',
        'excited spin': 'turn right',
        'play bow': 'stretch',
        'shake head': 'shake head',
        'twist body': 'twist body',
        'twist_body': 'twist body',
        'lick hand': 'lick hand',
        'whimper': 'nod',
        'surprise': 'surprise',
        'recall': 'recall',
        'stop': 'stand',
        'turn_left': 'turn left',
        'turn_right': 'turn right',
        'push_up': 'push up',
        'high_five': 'high five',
    }

    def _execute_actions(self, actions: List[str]):
        """Execute actions on the dog"""
        if self.voice_dog and hasattr(self.voice_dog, 'action_flow'):
            self.voice_dog.action_flow.add_action(*actions)
        elif hasattr(self, 'action_flow') and self.action_flow:
            # Local-only mode with ActionFlow
            # Map action names to valid ActionFlow operations
            # ActionFlow OPERATIONS keys use spaces (e.g., "wag tail", "turn left")
            mapped_actions = []
            for action in actions:
                action_lower = action.lower()
                if action_lower in self.ACTION_MAP:
                    mapped_actions.append(self.ACTION_MAP[action_lower])
                else:
                    # Convert underscores to spaces to match ActionFlow keys
                    mapped_actions.append(action_lower.replace('_', ' '))

            if mapped_actions:
                logger.info(f"Executing actions via ActionFlow: {mapped_actions}")
                try:
                    self.action_flow.add_action(*mapped_actions)
                except Exception as e:
                    logger.error(f"ActionFlow.add_action failed: {e}")
        elif hasattr(self, 'pidog') and self.pidog:
            # Fallback: use Pidog directly (less coordinated)
            for action in actions:
                try:
                    action_lower = action.lower()
                    if action_lower in self.ACTION_MAP:
                        action_name = self.ACTION_MAP[action_lower]
                    else:
                        action_name = action_lower.replace(' ', '_')

                    logger.info(f"Executing action directly: {action_name}")
                    self.pidog.do_action(action_name, speed=80)
                except Exception as e:
                    logger.warning(f"Action '{action}' -> '{action_name}' failed: {e}")

    def _speak(self, text: str):
        """Make the dog speak"""
        if not text:
            return

        if self.voice_dog and hasattr(self.voice_dog, 'say'):
            self.voice_dog.say(text)
        elif hasattr(self, 'tts') and self.tts:
            # Local-only mode: use Piper TTS
            try:
                logger.info(f"Speaking: {text}")
                self.tts.say(text)
            except Exception as e:
                logger.warning(f"TTS failed: {e}")

    def _set_rgb(self, style, color, brightness=1):
        """Set RGB strip color (local-only mode feedback)."""
        if hasattr(self, 'pidog') and self.pidog:
            try:
                self.pidog.rgb_strip.set_mode(style, color, brightness)
            except Exception:
                pass

    def _get_distance(self) -> float:
        """Get ultrasonic distance"""
        if self.voice_dog and hasattr(self.voice_dog, 'dog'):
            try:
                return self.voice_dog.dog.read_distance()
            except Exception:
                pass  # Sensor unavailable
        elif hasattr(self, 'pidog') and self.pidog:
            try:
                return self.pidog.read_distance()
            except Exception:
                pass  # Sensor unavailable
        return 100.0  # Assume clear if sensor fails

    def _get_image(self):
        """Get current camera image from shared camera pool"""
        return CameraPool.get_instance().get_frame()

    def _voice_listener_loop(self):
        """Listen for voice commands in local-only mode.

        Continuously listens for the wake word followed by a command.
        When detected, executes the corresponding action from VOICE_COMMANDS.
        """
        logger.info("Voice listener started - say 'hey buddy' followed by a command")
        logger.info(f"Wake words configured: {self.wake_word}")

        # Wait for _running flag (set after full initialization completes)
        for _ in range(60):  # Up to 30 seconds
            if self._running:
                break
            time.sleep(0.5)
        if not self._running:
            logger.warning("Voice listener: _running never became True, exiting")
            return

        while self._running:
            try:
                # Dim cyan breath while listening
                self._set_rgb('breath', 'cyan', 0.5)

                # Listen for speech (blocking with timeout)
                text = self.stt.listen(timeout=5.0)

                if not text:
                    # No speech — dim back
                    self._set_rgb('breath', 'cyan', 0.2)
                    continue

                text_lower = text.lower().strip()
                logger.info(f"Heard: '{text_lower}'")

                # Brief green flash to show we heard something
                self._set_rgb('boom', 'green', 1)

                # Strip punctuation for wake word matching
                # Moonshine often transcribes "hey buddy" as "Hey, buddy."
                text_clean = re.sub(r'[^\w\s]', '', text_lower)

                # Check for wake word
                wake_detected = False
                command_text = text_clean

                for wake in self.wake_word:
                    wake_lower = wake.lower()
                    if wake_lower in text_clean:
                        wake_detected = True
                        # Extract command after wake word
                        parts = text_clean.split(wake_lower, 1)
                        command_text = parts[-1].strip() if len(parts) > 1 else ""
                        break

                if not wake_detected:
                    # Heard speech but no wake word — dim back
                    self._set_rgb('breath', 'cyan', 0.2)
                    continue

                # Wake word detected — pink while processing
                self._set_rgb('breath', 'pink', 1)
                logger.info(f"Wake word detected, command: '{command_text}'")
                self._handle_voice_command(command_text)

                # Back to dim cyan after command handled
                self._set_rgb('breath', 'cyan', 0.5)

            except Exception as e:
                logger.error(f"Voice listener error: {e}")
                time.sleep(1.0)

    def _handle_voice_command(self, text: str):
        """Match and execute a voice command.

        Args:
            text: The command text (after wake word removed)
        """
        if not text:
            # Just wake word with no command - acknowledge and wait
            self._set_rgb('speak', 'pink', 1)
            self._speak("Yes?")
            self._execute_actions(['nod'])
            return

        # Try exact match first, then fuzzy match
        cmd = None
        matched_phrase = None

        if text in VOICE_COMMANDS:
            cmd = VOICE_COMMANDS[text]
            matched_phrase = text
        else:
            for phrase, c in VOICE_COMMANDS.items():
                if phrase in text:
                    cmd = c
                    matched_phrase = phrase
                    break

        if cmd:
            self._set_rgb('listen', 'yellow', 1)  # Thinking
            if cmd['speech']:
                self._set_rgb('speak', 'pink', 1)  # Speaking
                self._speak(cmd['speech'])
            self._execute_actions(cmd['actions'])
            logger.info(f"Executed command: {matched_phrase}" +
                         (f" (from '{text}')" if matched_phrase != text else ""))
            return

        # No match found - confused response
        logger.info(f"Unknown command: {text}")
        self._set_rgb('boom', 'red', 1)
        self._speak("I don't know that one.")
        self._execute_actions(['shake_head'])

    def _autonomous_prompt(self, prompt: str) -> str:
        """Send autonomous prompt to Claude"""
        if self.robust_llm:
            return self.robust_llm.prompt(prompt)
        return ""

    # Vision tool callbacks
    def _learn_face(self, name: str) -> Dict:
        """Learn a face from current camera view"""
        image = self._get_image()
        if image is None:
            raise ValueError("No camera image available")

        success, message = self.face_memory.learn_face(image, name)
        if not success:
            raise ValueError(message)

        return {'name': name, 'message': message}

    def _learn_room(self, name: str) -> Dict:
        """Learn current room"""
        image = self._get_image()
        if image is None:
            raise ValueError("No camera image available")

        success, message = self.room_memory.learn_room(image, name)
        if not success:
            raise ValueError(message)

        return {'name': name, 'message': message}

    def _follow_person(self):
        """Start following person in view"""
        if self.navigator:
            self.navigator.start_explore()  # For now, just explore

    def _find_person(self, name: str):
        """Search for a person"""
        if self.navigator:
            self.navigator.find_person(name)

    def _go_to_room(self, name: str):
        """Navigate to a room"""
        if self.navigator:
            self.navigator.go_to_room(name)

    def _explore(self):
        """Start exploring"""
        if self.navigator:
            self.navigator.start_explore()

    def _parse_response(self, text: str) -> str:
        """Parse response and execute tools, return speech"""
        speech, actions, tool_results = self.tools.parse_and_execute(text)

        # Execute actions
        if actions:
            self._execute_actions(actions)

        return speech

    def _vision_loop(self):
        """Background vision processing loop"""
        tflite_warning_logged = False

        while self._running and self.enable_vision:
            try:
                image = self._get_image()
                if image is not None and self.vision_processor:
                    self.vision_processor.process_frame(image)
                time.sleep(0.2)  # 5 FPS
            except ImportError as e:
                # Log TFLite/dependency errors only once
                if not tflite_warning_logged:
                    logger.warning(f"Vision dependency missing (logged once): {e}")
                    tflite_warning_logged = True
                time.sleep(5.0)  # Slow down retries for missing dependencies
            except Exception as e:
                logger.error(f"Vision error: {e}")
                time.sleep(1.0)

    def start(self):
        """Start the autonomous dog"""
        logger.info(f"Starting {self.name}...")

        # Initialize components
        self._init_llm()
        self._init_vision()
        self._init_tools()
        self._init_brain()

        # Initialize voice-activated dog with hardware
        if HARDWARE_AVAILABLE:
            logger.info("Initializing PiDog hardware...")
            try:
                # In local_only mode without LLM, skip VoiceAssistant (requires LLM)
                # and just use the base Pidog hardware directly
                if self.local_only and self.llm is None:
                    logger.info("Local-only mode: Using Pidog hardware without VoiceAssistant")
                    from pidog_os import Pidog
                    from pidog_os.action_flow import ActionFlow
                    self.pidog = Pidog()
                    self.action_flow = ActionFlow(self.pidog)
                    self.action_flow.start()
                    logger.info("ActionFlow started for local-only mode")
                    self.voice_dog = None

                    # Initialize TTS for local-only mode
                    if TTS_AVAILABLE:
                        try:
                            self.tts = Piper()
                            self.tts.set_model('en_US-lessac-medium')
                            logger.info("Local TTS initialized (Piper)")
                        except Exception as e:
                            logger.warning(f"Failed to initialize TTS: {e}")
                            self.tts = None
                    else:
                        self.tts = None

                    # Initialize STT for voice commands
                    if STT_AVAILABLE:
                        try:
                            self.stt = MoonshineStt()
                            logger.info("Local STT initialized (Moonshine)")
                            # Start voice listener thread
                            self._voice_listener_thread = threading.Thread(
                                target=self._voice_listener_loop, daemon=True
                            )
                            self._voice_listener_thread.start()
                            logger.info("Voice command listener started")
                        except Exception as e:
                            logger.warning(f"Failed to initialize STT: {e}")
                            self.stt = None
                    else:
                        self.stt = None
                else:
                    # Build instructions with memory context
                    instructions = self._get_instructions()

                    # Create the voice-activated dog
                    # Use shorter cooldown when conversation mode is enabled
                    cooldown = 0.2 if self.conversation_mode != "none" else 1.0
                    self.voice_dog = AutonomousVoiceActiveDog(
                        autonomous_dog=self,
                        name=self.name,
                        llm=self.llm,
                        tts_model=self.tts_model,
                        stt_language=self.stt_language,
                        with_image=self.with_image,
                        wake_enable=self.wake_enable,
                        wake_word=self.wake_word,
                        answer_on_wake="",  # Disabled - no speech on wake
                        instructions=instructions,
                        round_cooldown=cooldown
                    )

                # Start the voice assistant in a thread (run() is blocking)
                if self.voice_dog is not None:
                    self._voice_thread = threading.Thread(target=self.voice_dog.run, daemon=True)
                    self._voice_thread.start()
                    logger.info("Voice assistant started")

                    # Replace Vosk STT with Moonshine in VoiceAssistant
                    if STT_AVAILABLE:
                        try:
                            moonshine_stt = MoonshineStt()
                            if moonshine_stt.is_ready():
                                moonshine_stt.set_wake_words(self.wake_word)
                                self.voice_dog.stt = moonshine_stt
                                logger.info("VoiceAssistant STT replaced with Moonshine")
                            else:
                                logger.warning("Moonshine STT not ready, keeping default STT")
                        except Exception as e:
                            logger.warning(f"Failed to replace STT with Moonshine: {e}")

                    # Share picamera2 instance with CameraPool for vision components
                    # Wait briefly for camera to initialize
                    time.sleep(0.5)
                    if hasattr(self.voice_dog, 'picam2') and self.voice_dog.picam2 is not None:
                        CameraPool.get_instance().set_picam2(self.voice_dog.picam2)
                        logger.info("Camera shared with vision system")

                    # Initialize conversation manager for wake-word-free follow-ups
                    if self.conversation_mode != "none":
                        self.conversation_manager = ConversationManager(
                            mode=self.conversation_mode,
                            timeout=self.conversation_timeout,
                            vad_silence=self.vad_silence_threshold
                        )
                        # Connect to STT and register as a trigger (if STT is available)
                        if self.voice_dog.stt:
                            self.conversation_manager.set_stt(self.voice_dog.stt)
                            self.voice_dog.add_trigger(self.conversation_manager.trigger)
                            logger.info(f"Conversation mode '{self.conversation_mode}' enabled")
                        else:
                            logger.warning("STT not available, conversation mode disabled")
                            self.conversation_manager = None
                else:
                    logger.info("Running in local-only mode without voice assistant")

            except Exception as e:
                logger.error(f"Failed to initialize hardware: {e}")
                import traceback
                traceback.print_exc()
                self.voice_dog = None
        else:
            logger.warning("Hardware not available (running on non-Pi?)")

        self._running = True

        # Register cleanup handlers for graceful shutdown
        self._register_cleanup_handlers()

        # Start autonomous brain
        if self.brain:
            self.brain.start()
            logger.info("Autonomous brain started")

        # Start vision thread for local face/person detection
        if self.enable_vision:
            self._vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
            self._vision_thread.start()
            logger.info("Vision processing started")

        # Initialize and start memory maintenance
        self._init_maintenance()
        if self.maintainer:
            self.maintainer.start()

        logger.info(f"{self.name} is ready!")

        # Dim cyan breath = alive and listening
        self._set_rgb('breath', 'cyan', 0.2)

    def _register_cleanup_handlers(self):
        """Register atexit and signal handlers for proper GPIO cleanup"""
        # Track if we've already cleaned up
        self._cleanup_done = False

        def cleanup():
            if not self._cleanup_done:
                self._cleanup_done = True
                self.stop()

        # Register atexit for normal exits
        atexit.register(cleanup)

        # Register signal handlers for SIGINT (Ctrl+C) and SIGTERM
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        logger.debug("Cleanup handlers registered")

    def stop(self):
        """Stop the autonomous dog with proper cleanup

        Performs graceful shutdown with timeouts:
        - Signals shutdown event
        - Stops brain with 10s timeout
        - Stops voice before vision (voice may use camera)
        - Joins threads with warnings for slow stops
        - Releases camera and closes database
        """
        logger.info(f"Stopping {self.name}...")

        self._running = False
        self._shutdown_event.set()

        # 1. Stop brain first (depends on voice/vision)
        if self.brain:
            self.brain.stop(timeout=10.0)

        # 1.5. Stop memory maintenance
        if self.maintainer:
            self.maintainer.stop(timeout=10.0)

        # 2. Stop navigator
        if self.navigator:
            self.navigator.stop()

        # 2.5. Deactivate conversation manager
        if self.conversation_manager:
            self.conversation_manager.deactivate()

        # 3. Stop voice BEFORE vision (voice may use camera indirectly)
        if self.voice_dog:
            try:
                self.voice_dog.stop()
            except Exception as e:
                logger.error(f"Error stopping voice dog: {e}")

        if self._voice_thread and self._voice_thread.is_alive():
            self._voice_thread.join(timeout=5.0)
            if self._voice_thread.is_alive():
                logger.warning("Voice thread did not stop cleanly")

        # 4. Stop vision thread (after voice stops using camera)
        if self._vision_thread and self._vision_thread.is_alive():
            self._vision_thread.join(timeout=5.0)
            if self._vision_thread.is_alive():
                logger.warning("Vision thread did not stop cleanly")

        # 5. Release camera (after all consumers stopped)
        CameraPool.get_instance().release()

        # 6. Stop ActionFlow if running (local-only mode)
        if hasattr(self, 'action_flow') and self.action_flow:
            try:
                self.action_flow.stop()
                logger.info("ActionFlow stopped")
            except Exception as e:
                logger.warning(f"Error stopping ActionFlow: {e}")

        # 7. Close Pidog hardware (release GPIO)
        if hasattr(self, 'pidog') and self.pidog:
            try:
                self.pidog.close()
                logger.info("Pidog hardware released")
            except Exception as e:
                logger.warning(f"Error closing Pidog: {e}")
            self.pidog = None

        # 7. Close database last
        if self.memory:
            self.memory.close()

        logger.info(f"{self.name} stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        status = {
            'name': self.name,
            'running': self._running,
            'local_only': self.local_only,
            'memory_stats': self.memory.get_stats(),
            'personality': self.personality.get().to_dict(),
        }

        if self.brain:
            status['brain'] = self.brain.get_state()

        if self.robust_llm:
            status['llm_stats'] = self.robust_llm.get_stats()

        if self.maintainer:
            last_stats = self.maintainer.get_last_stats()
            if last_stats:
                status['maintenance'] = {
                    'last_run': last_stats.timestamp,
                    'decayed': last_stats.decayed_count,
                    'consolidated': last_stats.consolidated_count,
                    'pruned': last_stats.pruned_count,
                    'merged_faces': last_stats.merged_faces_count
                }

        return status


def main():
    """Main entry point for autonomous PiDog"""
    import argparse

    parser = argparse.ArgumentParser(description='Autonomous PiDog')
    parser.add_argument('--name', default='Buddy', help='Dog name')
    parser.add_argument('--no-vision', action='store_true', help='Disable vision')
    parser.add_argument('--no-autonomous', action='store_true', help='Disable autonomous behavior')
    parser.add_argument('--model', default='claude-sonnet-4-5-20250929', help='Claude model')

    args = parser.parse_args()

    dog = AutonomousDog(
        name=args.name,
        llm_model=args.model,
        enable_vision=not args.no_vision,
        enable_autonomous=not args.no_autonomous
    )

    try:
        dog.start()

        print("\nPress Ctrl+C to stop\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")

    finally:
        dog.stop()


if __name__ == '__main__':
    main()
