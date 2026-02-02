"""Autonomous Brain - State machine and think loop for autonomous behavior

The brain manages autonomous behavior through:
1. State machine (IDLE, CURIOUS, THINKING, ACTING, INTERACTING)
2. Think triggers (curiosity, boredom, goals)
3. Observation processing for novelty detection
4. Rate-limited Claude API calls

Key principle: Minimize API calls. Only call Claude for complex decisions.
"""

import time
import threading
import queue
import logging
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import json

from .memory_manager import MemoryManager
from .behavior_engine import BehaviorEngine, ObservationContext, Decision

logger = logging.getLogger(__name__)
from .personality import PersonalityManager, Mood
from .tools import ToolExecutor


class AutonomousState(Enum):
    """Brain state machine states"""
    IDLE = auto()        # Waiting, doing idle animations
    CURIOUS = auto()     # Something interesting detected locally
    THINKING = auto()    # Calling Claude (rate-limited)
    ACTING = auto()      # Executing actions
    INTERACTING = auto() # In voice conversation


@dataclass
class Observation:
    """A sensor observation"""
    sensor_type: str  # "ultrasonic", "touch", "imu", "vision", "audio"
    value: Any
    timestamp: float = field(default_factory=time.time)
    novelty: float = 0.0  # 0-1 novelty score


@dataclass
class ThinkResult:
    """Result of a think cycle"""
    speech: str
    actions: List[str]
    tool_results: List[Any]
    duration: float


class RateLimiter:
    """Rate limiter for API calls"""

    def __init__(self, max_calls_per_minute: int = 5, min_interval: float = 30.0):
        self.max_calls = max_calls_per_minute
        self.min_interval = min_interval
        self._call_times: List[float] = []
        self._last_call = 0

    def can_call(self) -> bool:
        """Check if we can make a call"""
        now = time.time()

        # Check minimum interval
        if now - self._last_call < self.min_interval:
            return False

        # Check calls per minute
        minute_ago = now - 60
        self._call_times = [t for t in self._call_times if t > minute_ago]

        return len(self._call_times) < self.max_calls

    def record_call(self):
        """Record that a call was made"""
        now = time.time()
        self._call_times.append(now)
        self._last_call = now

    def time_until_next(self) -> float:
        """Get seconds until next call is allowed"""
        now = time.time()

        # Check minimum interval
        interval_wait = self.min_interval - (now - self._last_call)
        if interval_wait > 0:
            return interval_wait

        # Check rate limit
        if len(self._call_times) >= self.max_calls:
            oldest = min(self._call_times)
            return max(0, 60 - (now - oldest))

        return 0


class NoveltyDetector:
    """Detect novelty in observations"""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._history: Dict[str, List[Any]] = {}

    def add_observation(self, obs: Observation) -> float:
        """Add observation and return novelty score

        Args:
            obs: The observation

        Returns:
            Novelty score 0-1 (higher = more novel)
        """
        sensor = obs.sensor_type
        value = obs.value

        if sensor not in self._history:
            self._history[sensor] = []
            return 1.0  # First observation is maximally novel

        history = self._history[sensor]

        # Calculate novelty based on sensor type
        if sensor == "ultrasonic":
            novelty = self._numeric_novelty(value, history)
        elif sensor == "touch":
            novelty = self._categorical_novelty(value, history)
        elif sensor == "vision":
            novelty = self._vision_novelty(value, history)
        else:
            novelty = self._generic_novelty(value, history)

        # Update history
        history.append(value)
        if len(history) > self.history_size:
            history.pop(0)

        return novelty

    def _numeric_novelty(self, value: float, history: List[float]) -> float:
        """Calculate novelty for numeric values"""
        if not history:
            return 1.0

        import statistics

        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 1.0

        if stdev == 0:
            stdev = 1.0

        # Z-score based novelty
        z = abs(value - mean) / stdev
        return min(1.0, z / 3.0)  # Normalize to 0-1

    def _categorical_novelty(self, value: str, history: List[str]) -> float:
        """Calculate novelty for categorical values"""
        if not history:
            return 1.0

        # How often has this value occurred?
        count = history.count(value)
        frequency = count / len(history)

        # Rare values are more novel
        return 1.0 - frequency

    def _vision_novelty(self, value: Dict, history: List[Dict]) -> float:
        """Calculate novelty for vision events"""
        # Vision events are things like "person_detected", "face_recognized"
        event_type = value.get("event", "unknown")

        if not history:
            return 1.0

        # Count recent occurrences of this event type
        recent = history[-10:] if len(history) >= 10 else history
        same_events = sum(1 for h in recent if h.get("event") == event_type)

        return max(0.2, 1.0 - (same_events / len(recent)))

    def _generic_novelty(self, value: Any, history: List[Any]) -> float:
        """Generic novelty calculation"""
        if not history:
            return 1.0

        # Check if exact value exists in history
        if value in history:
            return 0.2  # Low novelty for repeat

        return 0.6  # Moderate novelty for new value


class AutonomousBrain:
    """Main autonomous brain controller

    Usage:
        brain = AutonomousBrain(
            memory_manager=memory,
            personality_manager=personality,
            llm_callback=lambda prompt: claude.prompt(prompt),
            action_callback=lambda actions: dog.do_actions(actions),
            speak_callback=lambda text: dog.say(text)
        )

        # Start the brain
        brain.start()

        # Feed observations
        brain.observe("ultrasonic", 50)
        brain.observe("touch", "FRONT_TO_REAR")

        # Stop
        brain.stop()
    """

    def __init__(self,
                 memory_manager: MemoryManager,
                 personality_manager: PersonalityManager,
                 llm_callback: Optional[Callable[[str], str]] = None,
                 action_callback: Optional[Callable[[List[str]], None]] = None,
                 speak_callback: Optional[Callable[[str], None]] = None,
                 vision_callbacks: Optional[Dict[str, Callable]] = None,
                 max_calls_per_minute: int = 5,
                 min_think_interval: float = 30.0,
                 local_only: bool = False):
        """Initialize autonomous brain

        Args:
            memory_manager: Memory manager instance
            personality_manager: Personality manager instance
            llm_callback: Function to call Claude (prompt -> response)
            action_callback: Function to execute actions
            speak_callback: Function to speak text
            vision_callbacks: Dict of vision callbacks for tools
            max_calls_per_minute: Max Claude API calls per minute
            min_think_interval: Minimum seconds between thinks
            local_only: If True, use local behavior engine instead of Claude API
        """
        self.memory = memory_manager
        self.personality = personality_manager
        self.llm_callback = llm_callback
        self.action_callback = action_callback
        self.speak_callback = speak_callback
        self.local_only = local_only

        # Create tool executor
        self.tools = ToolExecutor(
            memory_manager=memory_manager,
            personality_manager=personality_manager,
            action_callback=action_callback,
            vision_callbacks=vision_callbacks or {}
        )

        # Create behavior engine for local mode
        self.behavior_engine = BehaviorEngine(
            memory_manager=memory_manager,
            personality_manager=personality_manager
        )

        # State
        self.state = AutonomousState.IDLE
        self.mood = Mood()

        # Rate limiting (less restrictive for local mode)
        if local_only:
            # Local mode: think more often since no API costs
            self.rate_limiter = RateLimiter(max_calls_per_minute=30, min_interval=5.0)
        else:
            self.rate_limiter = RateLimiter(max_calls_per_minute, min_think_interval)

        # Novelty detection
        self.novelty_detector = NoveltyDetector()

        # Observation queue (bounded to prevent memory leaks)
        self._observation_queue: queue.Queue = queue.Queue(maxsize=100)

        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Dedicated mood lock for thread-safe updates
        self._mood_lock = threading.Lock()

        # Timing
        self._last_interaction = time.time()
        self._idle_since = time.time()

        # Recent observations for local behavior engine
        self._recent_person: Optional[str] = None  # Name or None for unknown
        self._person_detected = False
        self._person_is_new = False
        self._last_person_time = 0.0
        self._person_left_time = 0.0  # When person last left view (for returning detection)
        self._obstacle_distance = 100.0
        self._touch_detected = False
        self._touch_style: Optional[str] = None

    def start(self):
        """Start the autonomous brain thread"""
        if self._running:
            return

        self._running = True

        # In local_only mode, start with higher boredom to trigger immediate action
        if self.local_only:
            with self._mood_lock:
                self.mood.boredom = 0.7  # Start bored to trigger first action
                self.mood.curiosity_level = 0.5
            logger.info("Local mode: Starting with elevated boredom to trigger actions")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0):
        """Stop the autonomous brain

        Args:
            timeout: Maximum seconds to wait for thread to stop (default 5.0)
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("Brain thread did not stop within timeout")
            self._thread = None

    def observe(self, sensor_type: str, value: Any):
        """Feed an observation to the brain

        Uses bounded queue with drop-oldest policy to prevent memory leaks.

        Args:
            sensor_type: Type of sensor
            value: Observation value
        """
        obs = Observation(sensor_type=sensor_type, value=value)
        obs.novelty = self.novelty_detector.add_observation(obs)

        try:
            self._observation_queue.put_nowait(obs)
        except queue.Full:
            # Queue full - drop oldest and add new
            try:
                self._observation_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._observation_queue.put_nowait(obs)
            except queue.Full:
                # Very rare race condition - just drop this observation
                pass

    def on_interaction_start(self):
        """Called when user interaction starts (e.g., wake word detected)"""
        # Lock ordering: always acquire _mood_lock BEFORE _lock to prevent deadlock
        with self._mood_lock:
            self.mood.on_interaction()
        with self._lock:
            self.state = AutonomousState.INTERACTING
            self._last_interaction = time.time()

    def on_interaction_end(self):
        """Called when user interaction ends"""
        with self._lock:
            self.state = AutonomousState.IDLE
            self._idle_since = time.time()

    def _run_loop(self):
        """Main brain loop"""
        while self._running:
            try:
                self._process_observations()
                self._update_mood()
                self._maybe_think()
                time.sleep(0.1)  # 10 Hz update rate
            except Exception as e:
                logger.error(f"Brain error: {e}")
                time.sleep(1.0)

    def _process_observations(self):
        """Process queued observations"""
        while not self._observation_queue.empty():
            try:
                obs = self._observation_queue.get_nowait()
                self._handle_observation(obs)
            except queue.Empty:
                break

    def _handle_observation(self, obs: Observation):
        """Handle a single observation"""
        # Update mood based on novelty (thread-safe)
        if obs.novelty > 0.5:
            with self._mood_lock:
                self.mood.on_novel_stimulus(obs.novelty)

        # Check for significant events
        if obs.sensor_type == "vision":
            event = obs.value.get("event", "")
            if event == "person_entered_view":
                # Person appeared - might want to greet
                self._person_detected = True
                self._recent_person = None  # Unknown person
                self._person_is_new = True
                self._last_person_time = time.time()
                with self._lock:
                    if self.state == AutonomousState.IDLE:
                        self.state = AutonomousState.CURIOUS

            elif event == "face_recognized":
                # Recognized someone - could greet by name
                name = obs.value.get("name", "")
                self._person_detected = True
                self._recent_person = name
                self._person_is_new = obs.novelty > 0.5
                self._last_person_time = time.time()
                if name and self.state == AutonomousState.IDLE:
                    with self._lock:
                        self.state = AutonomousState.CURIOUS

            elif event == "unknown_face_detected":
                self._person_detected = True
                self._recent_person = None
                self._person_is_new = True
                self._last_person_time = time.time()

            elif event == "person_left_view":
                self._person_detected = False
                self._person_left_time = time.time()  # Track when person left for returning detection

        elif obs.sensor_type == "ultrasonic":
            # Track obstacle distance
            self._obstacle_distance = obs.value if isinstance(obs.value, (int, float)) else 100.0

        elif obs.sensor_type == "touch" and obs.value:
            # Touch detected (thread-safe mood update)
            self._touch_detected = True
            self._touch_style = obs.value if isinstance(obs.value, str) else None
            with self._mood_lock:
                self.mood.happiness = min(1.0, self.mood.happiness + 0.1)

    def _update_mood(self):
        """Update mood over time (thread-safe)"""
        with self._mood_lock:
            self.mood.decay(0.1)  # Called at 10Hz, so 0.1s per update

    def _maybe_think(self):
        """Check if we should think autonomously"""
        # Lock ordering: always acquire _mood_lock BEFORE _lock to prevent deadlock
        # Read mood state under mood lock first
        with self._mood_lock:
            personality = self.personality.get()
            should_think = self.mood.should_think(personality)

        with self._lock:
            # Don't think during interaction
            if self.state == AutonomousState.INTERACTING:
                return

            if not should_think:
                return

            # Check rate limit
            if not self.rate_limiter.can_call():
                return

            # Start thinking
            self.state = AutonomousState.THINKING

        # Actually think (outside lock)
        self._do_think()

    def _do_think(self):
        """Execute a think cycle - delegates to local or API-based thinking"""
        # Check for shutdown before expensive operations
        if not self._running:
            with self._lock:
                self.state = AutonomousState.IDLE
            return

        # Use local behavior engine if in local_only mode
        if self.local_only:
            self._do_think_local()
            return

        # API-based thinking requires callback
        if self.llm_callback is None:
            with self._lock:
                self.state = AutonomousState.IDLE
            return

        start_time = time.time()

        try:
            # Build autonomous prompt
            prompt = self._build_autonomous_prompt()

            # Check again before API call (expensive operation)
            if not self._running:
                return

            # Call Claude
            self.rate_limiter.record_call()
            response = self.llm_callback(prompt)

            # Parse and execute
            speech, actions, tool_results = self.tools.parse_and_execute(response)

            # Execute actions
            if actions and self.action_callback:
                self.action_callback(actions)

            # Speak if there's speech
            if speech and self.speak_callback:
                self.speak_callback(speech)

            duration = time.time() - start_time

            # Reset curiosity after thinking (thread-safe)
            with self._mood_lock:
                self.mood.curiosity_level = 0.3
                self.mood.boredom = 0.0

        except Exception as e:
            logger.error(f"Think error: {e}")

        finally:
            with self._lock:
                self.state = AutonomousState.IDLE

    def _do_think_local(self):
        """Execute a think cycle using local behavior engine (no API calls)"""
        try:
            self.rate_limiter.record_call()
            logger.info("Local think cycle started")

            # Build observation context for behavior engine
            obs_context = self._build_observation_context()
            logger.debug(f"Observations: person={obs_context.person_detected}, boredom={self.mood.boredom:.2f}")

            # Get mood and personality (thread-safe)
            with self._mood_lock:
                mood = Mood(
                    happiness=self.mood.happiness,
                    excitement=self.mood.excitement,
                    tiredness=self.mood.tiredness,
                    boredom=self.mood.boredom,
                    curiosity_level=self.mood.curiosity_level
                )
            personality = self.personality.get()

            # Get memory context for behavior engine
            memory_ctx = self._build_memory_context()

            # Get decision from behavior engine
            decision = self.behavior_engine.decide(
                mood=mood,
                personality=personality,
                observations=obs_context,
                memory_context=memory_ctx
            )
            logger.info(f"Decision: speech='{decision.speech[:50] if decision.speech else ''}...', actions={decision.actions}")

            # Execute the decision
            self._execute_decision(decision)

            # Reset observation flags after processing
            self._touch_detected = False
            self._touch_style = None

            # Reset curiosity after thinking (thread-safe)
            with self._mood_lock:
                self.mood.curiosity_level = max(0.3, self.mood.curiosity_level - 0.2)
                self.mood.boredom = max(0.0, self.mood.boredom - 0.3)

        except Exception as e:
            logger.error(f"Local think error: {e}")

        finally:
            with self._lock:
                self.state = AutonomousState.IDLE

    def _build_observation_context(self) -> ObservationContext:
        """Build observation context for behavior engine"""
        # Check for active goals
        active_goals = self.memory.get_active_goals() if self.memory else []
        has_goal = len(active_goals) > 0
        goal_id = active_goals[0].id if has_goal else None
        goal_desc = active_goals[0].description if has_goal else None

        # Check if person is returning (was seen, left, now back)
        person_is_returning = (
            self._person_detected and
            self._recent_person is not None and
            not self._person_is_new and
            self._person_left_time > 0 and
            (time.time() - self._person_left_time) < 300  # Returned within 5 minutes
        )

        return ObservationContext(
            person_detected=self._person_detected,
            person_name=self._recent_person,
            person_is_new=self._person_is_new,
            person_is_returning=person_is_returning,
            face_detected=self._person_detected and self._recent_person is not None,
            obstacle_detected=self._obstacle_distance < 30,
            obstacle_distance=self._obstacle_distance,
            touch_detected=self._touch_detected,
            touch_style=self._touch_style,
            time_since_last_person=time.time() - self._last_person_time if self._last_person_time > 0 else float('inf'),
            time_since_last_interaction=time.time() - self._last_interaction,
            idle_time=time.time() - self._idle_since,
            has_active_goal=has_goal,
            active_goal_id=goal_id,
            active_goal_description=goal_desc
        )

    def _build_memory_context(self) -> Dict[str, Any]:
        """Build memory context for behavior engine"""
        if not self.memory:
            return {}

        # Get memories about the current person if detected
        person_memories = {}
        if self._recent_person:
            memories = self.memory.recall(self._recent_person, limit=3)
            if memories:
                person_memories[self._recent_person] = [m.content for m in memories]

        return {
            'person_memories': person_memories,
            'recent_interactions': [],  # Could add more context here
        }

    def _execute_decision(self, decision: Decision):
        """Execute a behavior decision

        Args:
            decision: Decision from behavior engine
        """
        # Execute tools first (may update memory/goals)
        for tool in decision.tools:
            tool_name = tool.get('name', '')
            params = tool.get('params', {})
            if tool_name:
                result = self.tools.execute_tool(tool_name, params)
                if not result.success:
                    logger.warning(f"Tool {tool_name} failed: {result.message}")

        # Execute actions
        if decision.actions and self.action_callback:
            self.action_callback(decision.actions)

        # Speak if there's speech
        if decision.speech and self.speak_callback:
            self.speak_callback(decision.speech)

    def _build_autonomous_prompt(self) -> str:
        """Build prompt for autonomous thinking"""
        # Get context from memory and personality
        memory_context = self.memory.get_memory_context()
        goals_context = self.memory.get_goals_context()
        personality_context = self.personality.get_context()
        mood_context = self.mood.get_context()
        faces_context = self.memory.get_faces_context()
        rooms_context = self.memory.get_rooms_context()

        # Get recent observations summary
        obs_summary = self._get_observation_summary()

        prompt = f"""You are in autonomous mode. No one is currently talking to you.

{personality_context}

{mood_context}

## Your Memories
{memory_context}

## Your Goals
{goals_context}

## Known Faces
{faces_context}

## Known Rooms
{rooms_context}

## Recent Observations
{obs_summary}

## What to do
Based on your personality, mood, goals, and observations:
- Think about something interesting
- Work on a goal
- Explore or do an idle behavior
- Or just rest

Respond with what you want to do (or nothing if resting).
Keep responses brief - you're just thinking to yourself.
"""
        return prompt

    def _get_observation_summary(self) -> str:
        """Get summary of recent observations"""
        lines = []

        idle_time = time.time() - self._idle_since
        if idle_time > 60:
            lines.append(f"Been idle for {int(idle_time / 60)} minutes")

        # Thread-safe mood reads
        with self._mood_lock:
            boredom = self.mood.boredom
            curiosity = self.mood.curiosity_level

        if boredom > 0.5:
            lines.append("Feeling a bit bored")

        if curiosity > 0.6:
            lines.append("Curious about something")

        return "\n".join(lines) if lines else "Nothing notable recently"

    def get_state(self) -> Dict[str, Any]:
        """Get current brain state for debugging"""
        # Lock ordering: always acquire _mood_lock BEFORE _lock to prevent deadlock
        with self._mood_lock:
            mood_snapshot = {
                'happiness': self.mood.happiness,
                'excitement': self.mood.excitement,
                'tiredness': self.mood.tiredness,
                'boredom': self.mood.boredom,
                'curiosity_level': self.mood.curiosity_level
            }
        with self._lock:
            return {
                'state': self.state.name,
                'mood': mood_snapshot,
                'can_think': self.rate_limiter.can_call(),
                'time_until_think': self.rate_limiter.time_until_next(),
                'idle_time': time.time() - self._idle_since,
                'local_only': self.local_only,
                'person_detected': self._person_detected,
                'recent_person': self._recent_person
            }


class VisionEventProcessor:
    """Process vision events and feed them to the brain"""

    def __init__(self, brain: AutonomousBrain, face_memory=None, person_tracker=None):
        self.brain = brain
        self.face_memory = face_memory
        self.person_tracker = person_tracker
        self._last_faces: List[str] = []
        self._last_person_count = 0

    def process_frame(self, image):
        """Process a camera frame for events

        Args:
            image: BGR camera frame
        """
        # Face recognition
        if self.face_memory:
            faces = self.face_memory.recognize(image)

            current_names = [f.name for f in faces if f.name]

            # Check for new faces
            for name in current_names:
                if name not in self._last_faces:
                    self.brain.observe("vision", {
                        "event": "face_recognized",
                        "name": name
                    })

            # Check for unknown faces
            unknown_count = sum(1 for f in faces if f.name is None)
            if unknown_count > 0 and "unknown" not in self._last_faces:
                self.brain.observe("vision", {
                    "event": "unknown_face_detected"
                })

            self._last_faces = current_names + (["unknown"] if unknown_count > 0 else [])

        # Person detection
        if self.person_tracker:
            people = self.person_tracker.detect_people(image)

            if len(people) > self._last_person_count:
                self.brain.observe("vision", {
                    "event": "person_entered_view",
                    "count": len(people)
                })
            elif len(people) < self._last_person_count and len(people) == 0:
                self.brain.observe("vision", {
                    "event": "person_left_view"
                })

            self._last_person_count = len(people)
