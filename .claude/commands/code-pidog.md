---
description: PiDog API reference for writing robot control code
---

# PiDog Coding Reference

Use this API reference when writing Python code for the PiDog robot.

---

# Part 1: Hardware API (pidog library)

## Initialization

```python
from pidog import Pidog
my_dog = Pidog()

# With custom servo angles:
my_dog = Pidog(
    leg_init_angles=[25, 25, -25, -25, 70, -45, -70, 45],  # 8 leg servos
    head_init_angles=[0, 0, -25],  # yaw, roll, pitch
    tail_init_angle=[0]
)
```

## Movement APIs

### Leg Movement
```python
my_dog.legs_move(target_angles, immediately=True, speed=50)
```
- `target_angles`: 2D array of 8 servo angles, e.g. `[[25, 25, -25, -25, 70, -45, -70, 45]]`
- `immediately`: `True` = execute now (clear buffer), `False` = queue for smooth sequences
- `speed`: 1-100

```python
my_dog.is_legs_done()    # Returns True if queue empty
my_dog.wait_legs_done()  # Block until done
my_dog.legs_stop()       # Clear queue, stop movement
```

### Head Movement
```python
my_dog.head_move(target_yrps, roll_comp=0, pitch_comp=0, immediately=True, speed=50)
```
- `target_yrps`: 2D array of 3 angles [yaw, roll, pitch], e.g. `[[0, 0, 30]]`
- `roll_comp` / `pitch_comp`: Compensation for body tilt
- Nod: alternate `[0, 0, 30]` and `[0, 0, -30]`
- Shake: alternate `[30, 0, 0]` and `[-30, 0, 0]`

```python
my_dog.is_head_done()    # Returns True if queue empty
my_dog.wait_head_done()  # Block until done
my_dog.head_stop()       # Clear queue, stop movement
```

### Tail Movement
```python
my_dog.tail_move(target_angles, immediately=True, speed=50)
```
- `target_angles`: 2D array of 1 angle, e.g. `[[30], [-30]]` for wagging

```python
my_dog.is_tail_done()    # Returns True if queue empty
my_dog.wait_tail_done()  # Block until done
my_dog.tail_stop()       # Clear queue, stop movement
```

## Preset Actions

```python
my_dog.do_action(action_name, step_count=1, speed=50)
```

**Available actions (24):**

| Category | Actions |
|----------|---------|
| Postures | `sit`, `half_sit`, `stand`, `lie`, `lie_with_hands_out` |
| Movement | `forward`, `backward`, `turn_left`, `turn_right`, `trot` |
| Body | `stretch`, `push_up`, `doze_off`, `wag_tail` |
| Head | `nod_lethargy`, `shake_head`, `tilting_head_left`, `tilting_head_right`, `tilting_head`, `head_bark`, `head_up_down` |

## Control Methods

```python
my_dog.wait_all_done()   # Wait for legs, head, and tail buffers
my_dog.body_stop()       # Stop all movement immediately
my_dog.stop_and_lie()    # Stop all and reset to lie pose
my_dog.close()           # Cleanup, close threads (call on exit)
```

## Sound

```python
my_dog.speak(name, volume=100)  # Requires sudo
```

**Available sounds:** `angry`, `confused_1`, `confused_2`, `confused_3`, `growl_1`, `growl_2`, `howling`, `pant`, `single_bark_1`, `single_bark_2`, `snoring`, `woohoo`

## RGB Strip

```python
my_dog.rgb_strip.set_mode(style, color, brightness=1.0, bps=1.0)
my_dog.rgb_strip.close()  # Turn off
```

- **style:** `"breath"`, `"boom"`, `"bark"`
- **color:** `"white"`, `"red"`, `"yellow"`, `"green"`, `"blue"`, `"cyan"`, `"magenta"`, `"pink"` or hex `"#a10a0a"`
- **brightness:** 0.0 - 1.0
- **bps:** Speed (lower = faster animation)

## Sensors

### Ultrasonic Distance
```python
distance = my_dog.ultrasonic.read_distance()  # Returns 2-400 cm
```

### IMU (Accelerometer + Gyroscope)
```python
ax, ay, az = my_dog.accData  # Divide by 16384 for g-force
gx, gy, gz = my_dog.gyroData  # Degrees per second

# Calculate body pitch angle:
import math
body_pitch = math.degrees(math.atan2(ay, ax))
```

### Sound Direction
```python
if my_dog.ears.isdetected():
    direction = my_dog.ears.read()  # 0-359 degrees (0=front, 90=right)
```

### Touch Sensor
```python
touch = my_dog.dual_touch.read()
# Returns: "LS" (swipe front-to-back), "RS" (swipe back-to-front),
#          "L" (left touch), "R" (right touch), "N" (no touch)
```

---

# Part 2: Autonomous Brain API (pidog_brain)

## Memory Manager

```python
from pidog_brain.memory_manager import MemoryManager
mm = MemoryManager()  # Uses pidog_brain/memory.db
```

### Memory Operations
```python
# Store memory (returns ID)
id = mm.remember(category, subject, content, importance=0.5)
# category: "person" | "fact" | "preference" | "experience" | "location"
# importance: 0.0-1.0

# Recall with FTS5 search
memories = mm.recall(query, limit=5, category=None)

# Other queries
mm.get_memories_by_subject(subject)
mm.get_memories_by_category(category, limit=10)
mm.get_important_memories(min_importance=0.7, limit=10)
mm.update_memory_importance(memory_id, importance)
mm.delete_memory(memory_id)
```

### Trick Learning
```python
# Learn a trick (returns success, message)
success, msg = mm.learn_trick(name, trigger_phrase, actions)
# actions: List of valid actions (max 10)

mm.get_trick(name)                    # Get by name
mm.find_trick_by_trigger(phrase)      # Find by trigger
mm.record_trick_performed(name)       # Increment counter
mm.get_all_tricks()                   # All tricks
mm.delete_trick(name)
```

**Valid trick actions:** `forward`, `backward`, `lie`, `stand`, `sit`, `bark`, `bark harder`, `pant`, `howling`, `wag tail`, `stretch`, `push up`, `scratch`, `handshake`, `high five`, `lick hand`, `shake head`, `relax neck`, `nod`, `think`, `recall`, `head down`, `fluster`, `surprise`, `turn left`, `turn right`, `stop`

### Goal Management
```python
goal_id = mm.set_goal(description, priority=3)  # priority 1-5
mm.get_active_goals()                # Active goals by priority
mm.complete_goal(goal_id)            # Mark complete
mm.update_goal_progress(goal_id, progress_dict)
mm.abandon_goal(goal_id)
```

### Face Storage
```python
face_id = mm.store_face(name, encoding_bytes, image_hash=None)
mm.get_all_faces()                   # All faces by times_seen
mm.get_faces_by_name(name)           # All encodings for person
mm.record_face_seen(face_id)         # Update last_seen
mm.delete_face(face_id)
```

### Room Storage
```python
room_id = mm.store_room(name, description, landmarks=None, image_hash=None)
mm.get_room(name)                    # Get by name
mm.get_all_rooms()                   # All rooms by times_visited
mm.record_room_visited(name)
```

### Context for Claude Prompts
```python
mm.get_memory_context(query=None, max_memories=5)  # Formatted memories
mm.get_goals_context()               # Formatted goals
mm.get_faces_context()               # Known faces list
mm.get_rooms_context()               # Known rooms list
```

---

## Personality Manager

```python
from pidog_brain.personality import PersonalityManager, Mood
pm = PersonalityManager()
```

### Personality Traits (0.0-1.0, persistent)
```python
p = pm.get()  # Returns Personality dataclass
# p.playfulness (0.7), p.curiosity (0.8), p.affection (0.6),
# p.energy (0.5), p.talkativeness (0.6)

pm.update(trait, value)      # Set trait (returns success, msg)
pm.adjust(trait, delta)      # Adjust by delta
pm.get_context()             # Formatted description for Claude
pm.reset()                   # Reset to defaults
```

### Behavior Modifiers
```python
modifiers = pm.get_behavior_modifiers()
# modifiers['play_chance'] = playfulness * energy
# modifiers['investigate_chance'] = curiosity
# modifiers['approach_chance'] = affection
# modifiers['idle_animation_frequency'] = energy * 0.5 + 0.25
# modifiers['response_length'] = talkativeness
# modifiers['think_frequency'] = curiosity * 0.5 + 0.25
```

### Mood (0.0-1.0, transient)
```python
mood = Mood()
# mood.happiness, mood.excitement, mood.tiredness,
# mood.boredom, mood.curiosity_level

mood.update(happiness=0.8, excitement=0.5)
mood.decay(dt=1.0)                   # Time decay
mood.on_interaction()                # User interacted
mood.on_novel_stimulus(novelty=0.7)  # Novel observation
mood.should_think(personality)       # Should trigger thinking?
mood.get_context()                   # Formatted description
```

---

## Tool Executor

```python
from pidog_brain.tools import ToolExecutor, ToolResult

executor = ToolExecutor(
    memory_manager=mm,
    personality_manager=pm,
    action_callback=lambda actions: dog.do_actions(actions),
    vision_callbacks={
        'learn_face': learn_face_fn,
        'follow_person': follow_fn,
        'explore': explore_fn,
        'go_to_room': go_to_room_fn,
        'find_person': find_person_fn
    }
)
```

### Parsing Claude Responses
```python
# Full pipeline
speech, actions, results = executor.parse_and_execute(response_text)

# Just parse
speech, actions, tools = executor.parse_response(text)
tools = executor.parse_tools(text)   # [(tool_name, params), ...]

# Execute single tool
result = executor.execute_tool(tool_name, params)  # Returns ToolResult
```

### Response Format (Claude output)
```
Speech text here (what to say)
ACTIONS: wag tail, nod, forward
TOOL: remember {"category": "person", "subject": "Joe", "content": "Friendly"}
TOOL: set_goal {"description": "Play more", "priority": 4}
```

### Available Tools
| Tool | Parameters |
|------|------------|
| `remember` | category, subject, content, importance(0-1) |
| `recall` | query, category?, limit? |
| `learn_trick` | name, trigger, actions(list) |
| `do_trick` | name |
| `list_tricks` | (none) |
| `set_goal` | description, priority(1-5) |
| `complete_goal` | id |
| `list_goals` | (none) |
| `update_personality` | trait, value(0-1) |
| `learn_face` | name |
| `learn_room` | name |
| `follow_person` | (none) |
| `find_person` | name |
| `go_to_room` | name |
| `explore` | (none) |

---

## Autonomous Brain

```python
from pidog_brain.autonomous_brain import AutonomousBrain, AutonomousState

brain = AutonomousBrain(
    memory_manager=mm,
    personality_manager=pm,
    llm_callback=lambda prompt: claude.prompt(prompt),
    action_callback=lambda actions: dog.do_actions(actions),
    speak_callback=lambda text: dog.say(text),
    vision_callbacks={...},
    max_calls_per_minute=5,
    min_think_interval=30.0
)
```

### State Machine
```python
# States: IDLE, CURIOUS, THINKING, ACTING, INTERACTING

brain.start()                        # Start autonomous thread
brain.stop()                         # Stop thread

brain.observe(sensor_type, value)    # Feed observation
# sensor_type: "ultrasonic" | "touch" | "imu" | "vision" | "audio"

brain.on_interaction_start()         # User started talking
brain.on_interaction_end()           # User stopped talking

state = brain.get_state()            # Current state dict
```

### Vision Event Processor
```python
from pidog_brain.autonomous_brain import VisionEventProcessor

processor = VisionEventProcessor(brain, face_memory, person_tracker)
processor.process_frame(image)       # Call each camera frame
# Emits: face_recognized, unknown_face_detected, person_entered_view, person_left_view
```

---

# Part 3: Vision APIs (pidog_brain.vision)

## Face Memory

```python
from pidog_brain.vision.face_memory import FaceMemory, FaceTracker

faces = FaceMemory(memory_manager)
```

### Face Operations
```python
# Learn face from image (returns success, message)
success, msg = faces.learn_face(image, name)

# Recognize faces in image
detected = faces.recognize(image)  # List[DetectedFace]
for face in detected:
    print(face.name, face.confidence, face.center)

# Other methods
faces.get_known_names()              # All known names
faces.forget_face(name)              # Remove person
faces.detect_faces(image)            # Detect without recognition
```

### Face Tracking
```python
tracker = FaceTracker(face_memory)
tracked = tracker.update(image)      # Returns Optional[DetectedFace]
tracker.start_tracking(name)
tracker.stop_tracking()
```

**Performance:** Detection ~50ms, encoding ~150ms, matching <1ms

---

## Person Tracker

```python
from pidog_brain.vision.person_tracker import PersonTracker, PersonFollower

tracker = PersonTracker()  # Auto-downloads TFLite model
```

### Detection & Following
```python
# Detect people
people = tracker.detect_people(image)  # List[BoundingBox]
for person in people:
    print(person.center_x, person.center_y, person.confidence)

# Get follow command
cmd = tracker.get_follow_command(people[0])
# Returns: "turn left" | "turn right" | "forward" | "backward" | "stop"

# Detailed command
detail = tracker.get_detailed_command(people[0])
# {'action': 'turn left', 'magnitude': 0.3, 'distance': 'medium'}
```

### State Machine Follower
```python
follower = PersonFollower(tracker)
follower.start()
cmd, person_bbox = follower.update(image)
follower.stop()
```

**Performance:** ~100ms per frame

---

## Room Memory

```python
from pidog_brain.vision.room_memory import RoomMemory

rooms = RoomMemory(memory_manager, claude_client)
```

### Room Operations
```python
# Learn room (uses Claude for description if not provided)
success, msg = rooms.learn_room(image, name, description=None)

# Identify current room (uses Claude vision)
match = rooms.identify_room(image)  # Optional[RoomMatch]
if match and match.confidence > 0.7:
    print(match.name, match.description)

rooms.get_all_rooms()  # List of room names
```

---

## Navigator

```python
from pidog_brain.vision.navigator import Navigator, NavigationState

nav = Navigator(
    obstacle_detector=detector,
    person_tracker=tracker,
    face_memory=faces,
    room_memory=rooms,
    action_callback=lambda actions: dog.do_actions(actions),
    get_distance=lambda: dog.ultrasonic.read_distance(),
    get_image=lambda: camera.read()
)
```

### Navigation Methods
```python
# Explore
nav.start_explore()
cmd = nav.explore_step()             # Returns Optional[NavigationCommand]
nav.stop_explore()

# Navigate to room
nav.go_to_room("kitchen")
cmd, reached = nav.navigate_step()   # Returns (cmd, bool)

# Search for person
nav.find_person("Joe")
cmd, found = nav.search_step()       # Returns (cmd, bool)

# Main update loop
state, cmd = nav.update()            # Returns (NavigationState, cmd)
nav.stop()
```

**Safety thresholds:** DANGER=15cm, CAUTION=30cm, CLEAR=50cm

---

## Obstacle Detector

```python
from pidog_brain.vision.obstacle_detector import ObstacleDetector

detector = ObstacleDetector()
```

### Detection
```python
obstacles = detector.detect(image)   # List[Obstacle]
# obstacle.position: "left" | "center" | "right"
# obstacle.distance_estimate: "close" | "medium" | "far"

if detector.is_path_blocked(obstacles):
    direction = detector.get_clear_direction(obstacles)
    dog.do_action(f"turn {direction}")
```

**Performance:** <50ms per frame

---

# Part 4: Integration Patterns

## Full Autonomous Setup
```python
from pidog import Pidog
from pidog_brain.memory_manager import MemoryManager
from pidog_brain.personality import PersonalityManager
from pidog_brain.autonomous_brain import AutonomousBrain, VisionEventProcessor
from pidog_brain.vision.face_memory import FaceMemory
from pidog_brain.vision.person_tracker import PersonTracker
from pidog_brain.vision.navigator import Navigator

# Initialize
dog = Pidog()
memory = MemoryManager()
personality = PersonalityManager()
faces = FaceMemory(memory)
tracker = PersonTracker()
nav = Navigator(...)

brain = AutonomousBrain(
    memory_manager=memory,
    personality_manager=personality,
    llm_callback=claude_prompt,
    action_callback=lambda a: dog.do_action(a[0]) if a else None,
    speak_callback=lambda t: dog.speak("single_bark_1"),
    vision_callbacks={
        'learn_face': lambda n: faces.learn_face(get_image(), n),
        'follow_person': tracker.start_following,
        'explore': nav.start_explore,
        'go_to_room': nav.go_to_room,
        'find_person': nav.find_person
    }
)

vision_processor = VisionEventProcessor(brain, faces, tracker)

try:
    brain.start()
    while True:
        frame = camera.read()
        vision_processor.process_frame(frame)
        nav.update()
        time.sleep(0.1)
finally:
    brain.stop()
    dog.close()
```

## Tool Response Handling
```python
from pidog_brain.tools import ToolExecutor

executor = ToolExecutor(memory, personality)

# Parse Claude response
response = """I learned something about you!
ACTIONS: wag tail, nod
TOOL: remember {"category": "person", "subject": "Joe", "content": "Likes fetch"}
"""

speech, actions, results = executor.parse_and_execute(response)
# speech = "I learned something about you!"
# actions = ["wag tail", "nod"]
# results = [ToolResult(success=True, message="Remembered: Joe", data={"id": 1})]

for action in actions:
    dog.do_action(action)
```

## Mood-Driven Behavior
```python
import random

modifiers = personality.get_behavior_modifiers()

# Probabilistic play
if random.random() < modifiers['play_chance']:
    dog.do_action('wag_tail')

# Check if should think autonomously
if brain.mood.should_think(personality.get()):
    brain._do_think()
```

---

# Notes

- Run with `sudo` for sound and GPIO access
- Use `immediately=False` for smooth queued movement sequences
- Always call `dog.close()` and `brain.stop()` on exit
- Rate limiting: max 5 Claude calls/minute, 30s minimum between calls
- Vision runs at 5-10 FPS to save CPU for other tasks
- Memory database: `pidog_brain/memory.db` (SQLite with FTS5)
