# pidog: Actions System

<!-- Status: COMPLETE | Iteration: 1 -->

> Covers: `actions_dictionary.py` (257 lines), `action_flow.py` (284 lines), `preset_actions.py` (656 lines)

## Purpose

The actions system provides named animations and behaviors for PiDog. `ActionDict` defines static poses and gaits, `ActionFlow` manages action sequencing with posture tracking, and `preset_actions.py` implements complex multi-step behaviors like scratching, handshakes, and howling.

## API Reference

### ActionDict Class (actions_dictionary.py:8)

A dictionary-like class that returns action data tuples via property accessors.

#### `__init__()`

Initialize action dictionary with default height and barycenter.

**Attributes**:
- `self.barycenter` (int): Body center offset (mm). Default: -15
- `self.height` (int): Body height (mm). Default: 95

#### `__getitem__(item)` (actions_dictionary.py:16)

Access actions via string key. Spaces converted to underscores.

**Parameters**:
- `item` (str): Action name (e.g., "stand", "turn left")

**Returns**: Tuple `(action_data, part)` where:
- `action_data` (list): List of angle arrays
- `part` (str): One of 'legs', 'head', 'tail'

**Example**:
```python
actions_dict = ActionDict()
action_data, part = actions_dict['stand']
# action_data = [[angles1], [angles2], ...], part = 'legs'
```

#### `set_height(height)` (actions_dictionary.py:19)

Set body height for standing actions.

**Parameters**:
- `height` (int): Height in mm. Valid range: 20-95.

**Side effects**: Updates `self.height`, affects `stand` action IK

#### `set_barycenter(offset)` (actions_dictionary.py:23)

Set body center of gravity offset.

**Parameters**:
- `offset` (int): Offset in mm. Valid range: -60 to 60.

**Side effects**: Updates `self.barycenter`, affects `stand` action IK

---

### ActionFlow Class (action_flow.py:18)

Manages action execution with posture tracking, before/after callbacks, and automatic posture transitions.

#### Enums

**Posetures** (action_flow.py:7):
- `STAND = 0`
- `SIT = 1`
- `LIE = 2`

**ActionStatus** (action_flow.py:12):
- `STANDBY = 'standby'`
- `THINK = 'think'`
- `ACTIONS = 'actions'`
- `ACTIONS_DONE = 'actions_done'`

#### `__init__(dog_obj)` (action_flow.py:158)

Initialize action flow manager.

**Parameters**:
- `dog_obj` (Pidog): Pidog instance to control

**Attributes**:
- `self.dog_obj`: Reference to Pidog instance
- `self.head_yrp` (list): Current head YRP (updated by actions)
- `self.head_pitch_init` (int): Head pitch compensation offset
- `self.posture` (Posetures): Current body posture (STAND/SIT/LIE)
- `self.last_actions` (str): Last executed action name
- `self.thread` (Thread): Action handler thread
- `self.thread_running` (bool): Thread run flag
- `self.thread_action_state` (ActionStatus): Current action state
- `self.action_queue` (Queue): FIFO action queue

#### `run(action)` (action_flow.py:194)

Execute a single action from `OPERATIONS` dict.

**Parameters**:
- `action` (str): Action key from `OPERATIONS`

**Side effects**:
- Changes posture if action requires different posture
- Executes "before" callback (if defined)
- Executes action function
- Executes "after" callback (if defined)
- Blocks until action complete

**Thread-safe**: No (should be called from action handler thread)

**Exception handling**: Catches all exceptions, prints error, continues

#### `add_action(*actions)` (action_flow.py:261)

Queue one or more actions for execution.

**Parameters**:
- `*actions` (str): Action names

**Side effects**:
- Adds actions to `action_queue`
- Sets `thread_action_state` to `ACTIONS`

**Thread-safe**: Yes

#### `set_status(status)` (action_flow.py:266)

Set action handler state.

**Parameters**:
- `status` (ActionStatus): New state

**Thread-safe**: Yes (simple attribute write)

#### `wait_actions_done()` (action_flow.py:269)

Block until action queue empty and state is STANDBY.

**Thread-safe**: Yes

**Blocks**: Until `thread_action_state == STANDBY`

#### `start()` (action_flow.py:273)

Start action handler thread.

**Side effects**:
- Sets `thread_running = True`
- Sets `thread_action_state = STANDBY`
- Clears `action_queue`
- Starts daemon thread running `action_handler()`

**Thread-safe**: Yes

#### `stop()` (action_flow.py:280)

Stop action handler thread and wait for exit.

**Side effects**:
- Sets `thread_running = False`
- Joins thread (blocks until thread exits)

**Thread-safe**: Yes

#### `change_poseture(poseture)` (action_flow.py:176)

Transition to target posture (STAND/SIT/LIE).

**Parameters**:
- `poseture` (Posetures): Target posture

**Side effects**:
- Adjusts `head_pitch_init` based on posture
- Executes transition action (sit_2_stand if STAND, otherwise direct do_action)
- Updates `self.posture`
- Blocks until transition complete

**Thread-safe**: No (calls Pidog methods)

**Notes**: Standing from sitting uses special `sit_2_stand()` function for smooth transition.

#### `set_head_pitch_init(pitch)` (action_flow.py:171)

Set head pitch compensation and move head immediately.

**Parameters**:
- `pitch` (float): Pitch offset (degrees)

**Side effects**:
- Updates `head_pitch_init`
- Moves head to `[head_yrp[0], head_yrp[1], head_yrp[2] + pitch]`

**Thread-safe**: No

---

### OPERATIONS Dictionary (action_flow.py:31)

Defines all available actions with metadata.

**Structure**:
```python
"action_name": {
    "function": lambda self: function_call(),  # Required: action function
    "poseture": Posetures.STAND,               # Optional: required posture
    "before": "other_action" or lambda,         # Optional: pre-action
    "after": "other_action" or lambda,          # Optional: post-action
}
```

**Available Actions**:

| Action Name | Function | Posture | Speed | Notes |
|-------------|----------|---------|-------|-------|
| `forward` | `dog.do_action('forward')` | STAND | 98 | Walk forward |
| `backward` | `dog.do_action('backward')` | STAND | 98 | Walk backward |
| `turn left` | `dog.do_action('turn_left')` | STAND | 98 | Turn left |
| `turn right` | `dog.do_action('turn_right')` | STAND | 98 | Turn right |
| `stop` | None | - | - | No-op |
| `lie` | `dog.do_action('lie')` | LIE | 70 | Lie down |
| `stand` | `dog.do_action('stand')` | STAND | 65 | Stand up |
| `sit` | `dog.do_action('sit')` | SIT | 70 | Sit down |
| `bark` | `bark()` | - | - | Single bark with head tilt |
| `bark harder` | `bark_action()` + attack_posture | STAND | - | Aggressive bark |
| `pant` | `pant()` | - | - | Panting animation |
| `wag tail` | `dog.do_action('wag_tail')` | - | 100 | Wag tail, after: wag again |
| `shake head` | `shake_head()` | - | - | Shake head left-right |
| `stretch` | `stretch()` | SIT | - | Stretch, after: sit |
| `doze off` | `dog.do_action('doze_off')` | LIE | 95 | Dozing animation |
| `push up` | `push_up()` | STAND | - | Push-up motion |
| `howling` | `howling()` | SIT | - | Howl, after: sit |
| `twist body` | `body_twisting()` | STAND | - | Body twist, after: sit |
| `scratch` | `scratch()` | SIT | - | Scratch with hind leg |
| `handshake` | `hand_shake()` | SIT | - | Raise paw for handshake |
| `high five` | `high_five()` | SIT | - | Raise paw for high five |
| `lick hand` | `lick_hand()` | SIT | - | Lick extended paw |
| `waiting` | `waiting()` | - | - | Idle head movement |
| `feet shake` | `feet_shake()` | SIT | - | Shake feet |
| `relax neck` | `relax_neck()` | SIT | - | Neck relaxation |
| `nod` | `nod()` | SIT | - | Nod head up-down |
| `think` | `think()` | SIT | - | Thinking pose (head tilted) |
| `recall` | `recall()` | SIT | - | Recall pose (head opposite tilt) |
| `fluster` | `fluster()` | SIT | - | Flustered head shake |
| `surprise` | `surprise()` | SIT | - | Surprise reaction |

---

### Preset Actions Functions (preset_actions.py)

All functions in `preset_actions.py` follow this pattern:
```python
def action_name(my_dog, *args):
    # Set up action sequences
    # Call my_dog.legs_move(), my_dog.head_move(), etc.
    # my_dog.wait_all_done()
```

**Common Parameters**:
- `my_dog` (Pidog): Pidog instance
- `pitch_comp` (float): Head pitch compensation (degrees). Default varies.
- `speed` (int): Movement speed 0-100. Default varies.
- `volume` (int): Sound effect volume 0-100. Default 100.
- `yrp` (list): Head yaw/roll/pitch starting position. Default `[0,0,0]`.

**Functions**:

#### `scratch(my_dog)` (preset_actions.py:7)

Scratch with right hind leg 10 times.

**Side effects**:
- Sits first
- Raises right front paw
- Tilts head right
- Rapid leg movements (speed 94)
- Returns to sit

**Duration**: ~3 seconds

---

#### `hand_shake(my_dog)` (preset_actions.py:31)

Raise left front paw and shake 8 times.

**Side effects**:
- Raises paw to handshake position
- 8 shake cycles (speed 90)
- Slow paw withdrawal
- Returns to sit with head down

**Duration**: ~2 seconds

---

#### `high_five(my_dog)` (preset_actions.py:65)

Raise left front paw up, slam down once.

**Side effects**:
- Raises paw high
- Quick downward motion (speed 94)
- 0.5s pause
- Returns to sit

**Duration**: ~1.5 seconds

---

#### `pant(my_dog, yrp=None, pitch_comp=0, speed=80, volume=100)` (preset_actions.py:96)

Panting animation with sound.

**Parameters**:
- `yrp` (list): Head starting position. Default: `[0,0,0]`
- `pitch_comp` (float): Pitch offset. Default: 0
- `speed` (int): Head movement speed. Default: 80
- `volume` (int): Pant sound volume. Default: 100

**Side effects**:
- Plays 'pant' sound
- 6 cycles of head down-up motion

**Duration**: ~1 second

---

#### `body_twisting(my_dog)` (preset_actions.py:109)

Body twist motion.

**Side effects**:
- Complex leg movements (speed 50)
- Returns to sit via 2-stage transition

**Duration**: ~2 seconds

---

#### `bark_action(my_dog, yrp=None, speak=None, volume=100)` (preset_actions.py:127)

Single bark with body lunge.

**Parameters**:
- `yrp` (list): Head starting position. Default: `[0,0,0]`
- `speak` (str): Sound to play. Default: None (silent)
- `volume` (int): Volume. Default: 100

**Side effects**:
- Body lunge forward
- Head tilts up
- Plays sound (if specified)
- Returns to neutral

**Duration**: ~0.3 seconds

---

#### `shake_head(my_dog, yrp=None)` (preset_actions.py:150)

Shake head left-right-center.

**Parameters**:
- `yrp` (list): Head starting position. Default: `[0,0,-20]`

**Side effects**: 3-position head movement (speed 92)

**Duration**: ~0.5 seconds

---

#### `shake_head_smooth(my_dog, pitch_comp=0, amplitude=40, speed=90)` (preset_actions.py:162)

Smooth sinusoidal head shake.

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: 0
- `amplitude` (float): Shake amplitude (degrees). Default: 40
- `speed` (int): Movement speed. Default: 90

**Side effects**: 15-frame sine wave head motion

**Duration**: ~1 second

---

#### `bark(my_dog, yrp=None, pitch_comp=0, roll_comp=0, volume=100)` (preset_actions.py:178)

Single bark with head tilt up.

**Parameters**:
- `yrp` (list): Head starting position. Default: `[0,0,0]`
- `pitch_comp` (float): Pitch offset. Default: 0
- `roll_comp` (float): Roll offset. Default: 0
- `volume` (int): Volume. Default: 100

**Side effects**:
- Head tilts up 25°
- Plays 'single_bark_1' sound
- Returns to neutral
- 0.5s pause

**Duration**: ~1 second

---

#### `push_up(my_dog, speed=80)` (preset_actions.py:195)

Push-up motion.

**Parameters**:
- `speed` (int): Movement speed. Default: 80

**Side effects**:
- Head moves down then up
- Executes 'push_up' action from action dict

**Duration**: ~2 seconds

---

#### `howling(my_dog, volume=100)` (preset_actions.py:201)

Howl animation with sound and RGB effect.

**Parameters**:
- `volume` (int): Howl volume. Default: 100

**Side effects**:
- Sits, tilts head down
- Raises body (half_sit)
- RGB strip set to cyan "speak" mode (bps=0.6)
- Plays 'howling' sound (2.34s duration)
- Head moves to -60° pitch
- Returns to sit

**Duration**: ~4 seconds

---

#### `attack_posture(my_dog)` (preset_actions.py:225)

Aggressive forward stance.

**Side effects**:
- Legs move to attacking position (speed 85)
- Body lowered front, raised back

**Duration**: ~0.2 seconds

---

#### `lick_hand(my_dog)` (preset_actions.py:234)

Lick extended paw animation.

**Side effects**:
- Sits, head down
- Raises left front paw
- Head moves to paw position (-22° yaw, -23° roll, -45° pitch)
- 3 cycles of leg/head wiggle (speed 90)
- Returns to sit

**Duration**: ~2 seconds

---

#### `waiting(my_dog, pitch_comp)` (preset_actions.py:273)

Idle waiting animation (random head movement).

**Parameters**:
- `pitch_comp` (float): Pitch offset

**Side effects**:
- Random head position from 4 options (small yaw/roll/pitch variations)
- Very slow movement (speed 5)

**Duration**: Variable (non-blocking, used in idle loops)

---

#### `feet_shake(my_dog, step=None)` (preset_actions.py:285)

Shake front feet.

**Parameters**:
- `step` (int): Number of shake cycles. Default: random 1-2

**Side effects**:
- Adjusts front leg angles dynamically
- Random leg pattern (left/right/both)
- Returns to sit

**Duration**: ~1-2 seconds

---

#### `sit_2_stand(my_dog, speed=75)` (preset_actions.py:326)

Smooth transition from sit to stand.

**Parameters**:
- `speed` (int): Transition speed. Default: 75

**Side effects**:
- 2-stage leg movement via intermediate position
- Uses action dict sit/stand positions

**Duration**: ~1 second

**Notes**: Used by ActionFlow for posture transitions. Speed must be >70 for stability.

---

#### `relax_neck(my_dog, pitch_comp=-35)` (preset_actions.py:342)

Neck relaxation exercise.

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: -35 (sitting)

**Side effects**:
- 21-frame circular head motion (yaw + roll + pitch sine waves)
- 10-frame alternating head tilts (left/right)
- Speed 80

**Duration**: ~2 seconds

---

#### `nod(my_dog, pitch_comp=-35, amplitude=20, step=2, speed=90)` (preset_actions.py:387)

Nod head up and down.

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: -35
- `amplitude` (float): Nod amplitude (degrees). Default: 20
- `step` (int): Number of nod cycles. Default: 2
- `speed` (int): Movement speed. Default: 90

**Side effects**: Cosine wave pitch motion

**Duration**: ~1 second per step

---

#### `think(my_dog, pitch_comp=0)` (preset_actions.py:402)

Thinking pose (head tilted up-left).

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: 0

**Side effects**:
- Head moves to [20° yaw, -15° roll, 15° pitch + comp]
- Speed 80

**Duration**: ~0.3 seconds

---

#### `recall(my_dog, pitch_comp=0)` (preset_actions.py:411)

Recall pose (head tilted up-right, opposite of think).

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: 0

**Side effects**:
- Head moves to [-20° yaw, 15° roll, 15° pitch + comp]
- Speed 80

**Duration**: ~0.3 seconds

---

#### `head_down_left(my_dog, pitch_comp=0)` (preset_actions.py:420)

Head down and left.

**Side effects**: Head to [25° yaw, 0° roll, -35° pitch + comp]

---

#### `head_down_right(my_dog, pitch_comp=0)` (preset_actions.py:429)

Head down and right.

**Side effects**: Head to [-25° yaw, 0° roll, -35° pitch + comp]

---

#### `fluster(my_dog, pitch_comp=0)` (preset_actions.py:437)

Flustered rapid head shake.

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: 0

**Side effects**:
- 5 cycles of 4-position head shake (speed 100)
- Rapid left-center-right-center pattern

**Duration**: ~1 second

---

#### `alert(my_dog, pitch_comp=0)` (preset_actions.py:465)

Alert stance (ears up, scanning).

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: 0

**Side effects**:
- Raises body slightly
- Head tilts up
- Scans left (1s pause)
- Scans right (1s pause)
- Returns to center

**Duration**: ~3 seconds

---

#### `surprise(my_dog, pitch_comp=0, status='sit')` (preset_actions.py:489)

Surprise reaction.

**Parameters**:
- `pitch_comp` (float): Pitch offset. Default: 0
- `status` (str): Current posture ('sit' or 'stand'). Default: 'sit'

**Side effects**:
- Rapid body raise (speed 100)
- Head tilts up
- 1s pause
- Returns to original posture

**Duration**: ~2 seconds

---

#### `stretch(my_dog)` (preset_actions.py:529)

Stretch animation (play bow).

**Side effects**:
- Front legs extend forward
- Head raised
- 5-frame oscillating motion (speed 55)
- Returns to sit via 2-stage transition

**Duration**: ~2 seconds

---

## Complete Actions Catalog

### Static Poses (ActionDict properties)

| Action Name | Type | Leg Angles | Description |
|-------------|------|------------|-------------|
| `stand` | legs | IK computed | Standing position (height=95mm, barycenter=-15mm) |
| `sit` | legs | `[30,60,-30,-60,80,-45,-80,45]` | Sitting position |
| `lie` | legs | `[45,-45,-45,45,45,-45,-45,45]` | Lying down |
| `lie_with_hands_out` | legs | `[-60,60,60,-60,45,-45,-45,45]` | Lying with front paws extended |
| `forward` | legs | Walk gait | One walk cycle forward |
| `backward` | legs | Walk gait | One walk cycle backward |
| `turn_left` | legs | Walk gait | One walk cycle turning left |
| `turn_right` | legs | Walk gait | One walk cycle turning right |
| `trot` | legs | Trot gait | One trot cycle |
| `stretch` | legs | `[-80,70,80,-70,-20,64,20,-64]` | Stretch pose |
| `push_up` | legs | 2 positions | Push-up motion (up, down) |
| `doze_off` | legs | 400+ frames | Slow dozing animation (head bob) |
| `half_sit` | legs | `[25,25,-25,-25,64,-45,-64,45]` | Half-sitting (used in howling) |

### Head Actions (ActionDict properties)

| Action Name | Type | Head Angles (YRP) | Description |
|-------------|------|-------------------|-------------|
| `nod_lethargy` | head | 21 frames | Lethargic nodding (roll + pitch sine) |
| `shake_head` | head | 21 frames | Head shake left-right (sine wave) |
| `tilting_head_left` | head | `[0,-25,15]` | Tilt head left |
| `tilting_head_right` | head | `[0,25,20]` | Tilt head right |
| `tilting_head` | head | 40 frames | Alternate tilt left-right |
| `head_bark` | head | 4 frames | Head motion during barking |
| `head_up_down` | head | 3 frames | Nod head up-down |

### Tail Actions (ActionDict properties)

| Action Name | Type | Tail Angles | Description |
|-------------|------|-------------|-------------|
| `wag_tail` | tail | `[[-30],[30]]` | Wag tail left-right |

---

## Implementation Notes

### Action Format

Actions in `ActionDict` return tuples: `(data, part)`

**Data format**:
- **Legs**: List of 8-element angle lists (degrees), one per frame. Example: `[[30,60,-30,-60,80,-45,-80,45]]`
- **Head**: List of 3-element [yaw, roll, pitch] lists (degrees). Example: `[[0,0,0],[10,0,0]]`
- **Tail**: List of 1-element [angle] lists (degrees). Example: `[[30],[0]]`

**Part**: String literal 'legs', 'head', or 'tail'

**Speed**: Not stored in action data. Passed to `do_action(speed=...)` at execution time.

---

### Action Execution Flow

1. **ActionDict**: User calls `dog.do_action('stand')` → looks up action in `actions_dict`
2. **Pidog.do_action()**: Retrieves tuple `(data, part)` → appends to appropriate buffer (legs/head/tail)
3. **Action Thread**: Pops first frame from buffer → writes to servos → waits for DPS-limited completion
4. **Repeat**: Until buffer empty

**Immediate vs Queued**:
- `do_action()` internally uses `immediately=False` (queues actions)
- To clear buffer first, call `dog.legs_stop()` before `do_action()`

---

### ActionFlow Execution

1. **add_action('scratch')**: Adds to action_queue
2. **action_handler thread**: Pops action, calls `run('scratch')`
3. **run()**:
   - Checks if posture change needed (scratch requires SIT)
   - Calls `change_poseture(SIT)` if needed
   - Executes "before" callback (if defined)
   - Executes main action function (`scratch(dog)`)
   - Waits for completion (`dog.wait_all_done()`)
   - Executes "after" callback (if defined)
4. **Status change**: Sets state to STANDBY when queue empty

**Standby Actions**: When in STANDBY, action_handler randomly executes 'waiting' or 'feet_left_right' (weighted random) every 2-6 seconds.

---

### Action Chaining / Interruption

**Chaining (Sequential)**:
```python
flow.add_action('sit', 'scratch', 'stand')
# Executes in order: sit → scratch → stand
```

**Interruption (Clear Queue)**:
```python
flow.add_action('forward', 'forward', 'forward')  # Walking...
flow.action_queue.queue.clear()  # Stop immediately
flow.add_action('sit')  # Sit instead
```

**Before/After Callbacks**:
- "before" executes before posture change
- "after" executes after main action

Example (from OPERATIONS dict):
```python
"howling": {
    "function": lambda self: howling(self.dog_obj),
    "after": "sit",  # Always sit after howling
    "poseture": Posetures.SIT,
}
```

---

## Code Patterns

### Pattern 1: Simple Action

```python
dog = Pidog()
dog.do_action('sit', speed=70)
dog.wait_all_done()
dog.do_action('wag_tail', speed=100)
```

### Pattern 2: Action Flow with Chaining

```python
from pidog import Pidog
from pidog.action_flow import ActionFlow

dog = Pidog()
flow = ActionFlow(dog)
flow.start()

# Queue multiple actions
flow.add_action('stand', 'forward', 'forward', 'sit')

# Wait for completion
flow.wait_actions_done()

flow.stop()
```

### Pattern 3: Custom Preset Action

```python
def my_custom_action(my_dog):
    # Set up leg positions
    leg_pos = [
        [30, 60, -30, -60, 80, -45, -80, 45],
        [45, 45, -45, -45, 70, -50, -70, 50],
    ]

    # Execute with head movement
    my_dog.legs_move(leg_pos, immediately=True, speed=70)
    my_dog.head_move([[0, 10, 0]], speed=80)
    my_dog.wait_all_done()

# Use it
dog = Pidog()
my_custom_action(dog)
```

### Pattern 4: Add to ActionFlow OPERATIONS

```python
# Extend OPERATIONS dict
ActionFlow.OPERATIONS['my_action'] = {
    "function": lambda self: my_custom_action(self.dog_obj),
    "poseture": Posetures.SIT,
}

# Now use via ActionFlow
flow.add_action('my_action')
```

---

## Gotchas

1. **Action Dict Returns Tuple**: `actions_dict['stand']` returns `(data, part)`, not just data. Must unpack: `data, part = actions_dict['stand']`.

2. **Gait Actions are Generators**: Actions like 'forward', 'backward' call `Walk.get_coords()` which generates ~240 coordinate frames. Executing once = one walk cycle (~2 seconds).

3. **Head Pitch Compensation**: Many preset actions use `pitch_comp` parameter. This is needed because sitting/standing changes head height relative to ground, so pitch must be adjusted. Typical values: -35 for sitting, 0 for standing.

4. **Speed Must Be > 70 for sit_2_stand**: Lower speeds cause instability. The function comment says "speed > 70" for safe transitions.

5. **ActionFlow Posture Tracking**: ActionFlow tracks `self.posture` and auto-transitions. If you call `dog.do_action('stand')` directly (bypassing ActionFlow), ActionFlow's posture state becomes stale.

6. **Before/After Callbacks Can Be Strings or Lambdas**: If string, looks up in OPERATIONS. If lambda, executes directly. Example: `"after": "sit"` vs `"after": lambda self: self.dog_obj.do_action('sit')`.

7. **Standby Actions Only in STANDBY State**: 'waiting' and 'feet_left_right' only execute when `thread_action_state == STANDBY`. If you want continuous idle animations, ensure queue is empty.

8. **Howling Duration is Hardcoded**: The `howling()` function has a `sleep(2.34)` matching the sound file duration. If you change the sound file, update the sleep value.

9. **RGB Effects Are Not Automatic**: Only `howling()` changes RGB strip mode. Most actions don't touch RGB — you must set it manually.

10. **Action Interruption Requires Manual Queue Clear**: There's no built-in "stop current action" method. Must manually clear `action_queue` and call `dog.body_stop()`.
