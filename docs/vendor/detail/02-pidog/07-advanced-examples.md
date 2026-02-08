# pidog: Advanced Examples

<!-- Status: COMPLETE | Iteration: 1 -->

> All 23 advanced examples: calibration, behaviors, voice assistant, LLM integration
> Source: `pidog/examples/`

## Example Index

| File | Purpose | Hardware Used | Key Patterns |
|------|---------|---------------|--------------|
| `0_calibration.py` | Interactive servo offset calibration (curses TUI) | All 12 servos | `set_leg_offsets()`, `servo_write_raw()`, curses |
| `1_wake_up.py` | Wake-up animation sequence | Legs, head, tail, RGB, speaker | `preset_actions.pant()`, `body_twisting()` |
| `2_function_demonstration.py` | Interactive action/sound demo menu (curses TUI) | All servos, speaker | `do_action()`, curses menu, sound listing |
| `3_patrol.py` | Obstacle avoidance patrol with bark | Ultrasonic, legs, head, tail, RGB, speaker | `read_distance()`, `bark()`, IK `legs_angle_calculation()` |
| `4_response.py` | Multi-sensor response (distance + touch) | Ultrasonic, touch, legs, head, tail, RGB, speaker | Sensor polling, `bark_action()`, sine wave head |
| `5_rest.py` | Sleep/wake cycle triggered by sound | Sound direction, legs, head, RGB, speaker | `ears.isdetected()`, `shake_head()`, doze_off |
| `6_be_picked_up.py` | Detect being picked up via IMU | IMU (accData), legs, tail, RGB, speaker | Accelerometer threshold, gravity detection |
| `7_face_track.py` | Track human faces with head movement | Camera (vilib), sound direction, head, tail, speaker | `Vilib.face_detect_switch()`, proportional tracking |
| `8_pushup.py` | Push-up exercise with barking | Legs, head, RGB, speaker | `preset_actions.push_up()`, `bark()` |
| `9_howling.py` | Howling animation | Legs, head, speaker | `preset_actions.howling()` |
| `10_balance.py` | Walk with IK balance control + keyboard | Legs, IMU | `Walk` class, `set_rpy()`, `set_pose()`, `pose2legs_angle()`, readchar |
| `11_keyboard_control.py` | Full keyboard control (curses TUI) | All servos, RGB, speaker | `preset_actions.*`, operation dispatch, head YRP control |
| `12_app_control.py` | Mobile app remote control | All servos, camera, ultrasonic, RGB, speaker | `SunFounderController`, joystick mapping, voice commands |
| `13_ball_track.py` | Track colored ball with head and body | Camera (vilib), legs, head | `Vilib.color_detect()`, proportional head tracking |
| `18.online_llm_test.py` | Text-based LLM chat (OpenAI) | None (text only) | `OpenAI.prompt()`, streaming response |
| `19_voice_active_dog_ollama.py` | Voice-active dog with local Ollama LLM | All servos, camera, mic, speaker, sensors | `VoiceActiveDog` + Ollama LLM config |
| `20_voice_active_dog_doubao_cn.py` | Voice-active dog with Doubao (Chinese) | All servos, camera, mic, speaker, sensors | `VoiceActiveDog` + Doubao LLM, Chinese TTS/STT |
| `20_voice_active_dog_gpt.py` | Voice-active dog with OpenAI GPT | All servos, camera, mic, speaker, sensors | `VoiceActiveDog` + OpenAI LLM config |
| `claude_pidog.py` | Voice-active dog with Claude (Anthropic) | All servos, camera, mic, speaker, sensors | `VoiceActiveDog` + Anthropic LLM, env var API key |
| `curses_utils.py` | Curses UI utility library (shared) | None | Color pairs, pad refresh, line clearing |
| `custom_actions.py` | Interactive servo angle editor (curses TUI) | All 12 servos | `legs_simple_move()`, `head_move_raw()`, live angle readback |
| `servo_zeroing.py` | Set all 12 servos to zero position | All 12 servos (via robot_hat) | `Servo(i).angle(0)`, `reset_mcu()` |
| `voice_active_dog.py` | Core VoiceActiveDog class (base for all LLM examples) | All servos, camera, mic, speaker, sensors | `VoiceAssistant` subclass, `ActionFlow`, sensor triggers |

---

## Detailed Walkthroughs

### `0_calibration.py` -- Servo Calibration Tool

**Purpose**: Interactive curses-based tool for calibrating servo offsets. Supports 90-degree and 60-degree calibration rulers.

**Hardware Used**: All 12 servos (raw servo write).

**Key Code Patterns**:

```python
# Servo offset precision
OFFSET_STEP = (180 / 2000) * (20000 / 4095)  # ~0.44 degrees per step

# Save offsets persistently
my_dog.set_leg_offsets(leg_offset, reset_list=legs_orignal_angles)
my_dog.set_head_offsets(head_offset)
my_dog.set_tail_offset(tail_offset)

# Raw servo write (bypasses action buffer)
my_dog.legs.servo_write_raw(leg_angles)
my_dog.head.servo_write_raw(head_angles)
my_dog.tail.servo_write_raw(tail_angle)
```

**Code Flow**:
1. Init Pidog, copy current offsets
2. Phase 1: Select calibration ruler type (90 or 60 degree) via arrow keys + Enter
3. Move all servos to reference positions based on ruler type
4. Phase 2: Calibration loop -- select servo (1-8 legs, 9/0/- head, = tail), adjust with W/A/S/D
5. Space to save, Ctrl+C to exit (prompts to save if unsaved)

**Servo Selection Keys**:

| Key | Servo |
|-----|-------|
| 1-8 | Leg servos (LF_u, LF_l, RF_u, RF_l, LH_u, LH_l, RH_u, RH_l) |
| 9 | Head yaw |
| 0 | Head roll |
| - | Head pitch |
| = | Tail |

**Gotchas**:
- Requires interactive terminal (curses) -- cannot run via script
- Offsets constrained to +/-20 degrees
- Uses `servo_write_raw()` which bypasses the action buffer system
- Offsets persist in config file (`~/.config/pidog/pidog.conf`)
- Must run from the `examples/` directory (imports `curses_utils` locally)

---

### `1_wake_up.py` -- Wake Up Animation

**Purpose**: Plays a wake-up sequence: stretch, twist, sit, wag tail, pant.

**Hardware Used**: All leg servos, head, tail, RGB strip, speaker (via pant).

**Key Code Patterns**:

```python
from pidog.preset_actions import pant, body_twisting

my_dog = Pidog(head_init_angles=[0, 0, -30])  # Head starts pitched down

def wake_up():
    my_dog.rgb_strip.set_mode('listen', color='yellow', bps=0.6, brightness=0.8)
    my_dog.do_action('stretch', speed=50)
    my_dog.head_move([[0, 0, 30]]*2, immediately=True)  # head up during stretch
    my_dog.wait_all_done()

    body_twisting(my_dog)       # Twist body side to side
    my_dog.wait_all_done()

    my_dog.do_action('sit', speed=25)
    my_dog.wait_legs_done()
    my_dog.do_action('wag_tail', step_count=10, speed=100)
    pant(my_dog, pitch_comp=-30, volume=80)  # Panting animation with sound
    my_dog.wait_all_done()

    # Hold: slow wag + breathe pink
    my_dog.do_action('wag_tail', step_count=10, speed=30)
    my_dog.rgb_strip.set_mode('breath', 'pink', bps=0.5)
    while True:
        sleep(1)
```

**Code Flow**:
1. Init with head pitched down (-30)
2. Yellow RGB, stretch action
3. Body twist
4. Sit, wag fast, pant with sound
5. Hold: slow wag, pink breathing LED, sleep forever

**Gotchas**:
- `pant()` includes both head animation AND sound playback
- `body_twisting()` is a complex multi-step preset action function
- `head_move([[0,0,30]]*2)` sends the same target twice (ensures the buffer has something to process)

---

### `2_function_demonstration.py` -- Interactive Demo Menu

**Purpose**: Curses-based menu to select and run any preset action or sound effect by number.

**Hardware Used**: All servos, speaker.

**Key Code Patterns**:

```python
actions = [
    ['stand', 0, 50],       # [name, head_pitch_adjust, speed]
    ['sit', -30, 50],
    ['trot', 0, 95],
    ['forward', 0, 98],
    # ... 15 actions total
]

STANDUP_ACTIONS = ['trot', 'forward', 'backward', 'turn_left', 'turn_right']

def do_function(index):
    my_dog.body_stop()
    name, head_pitch_adjust, speed = actions[index]
    # Auto-transition: if moving action requires standing, stand first
    if name in STANDUP_ACTIONS and actions[last_index][0] not in STANDUP_ACTIONS:
        my_dog.do_action('stand', speed=60)
    my_dog.do_action(name, step_count=10, speed=speed, pitch_comp=last_head_pitch)
```

**Code Flow**:
1. Init Pidog, scan `../sounds/` for sound effects
2. Display numbered list of actions (1-15) and sounds (16+)
3. User types number + Enter to execute
4. Action runs 10 repetitions with auto-state transitions

**Gotchas**:
- Auto-transitions between postures (e.g., must stand before walking)
- `head_pitch_adjust=-1` means "keep last pitch" (no change)
- Sound effects loaded dynamically from filesystem
- Each action repeats 10 times (`step_count=10`)

---

### `3_patrol.py` -- Obstacle Avoidance Patrol

**Purpose**: Walk forward, detect obstacles with ultrasonic, bark when too close.

**Hardware Used**: Ultrasonic sensor, all servos, RGB strip, speaker.

**Key Code Patterns**:

```python
DANGER_DISTANCE = 15  # cm

# Use IK to calculate standing angles
stand = my_dog.legs_angle_calculation([[0, 80], [0, 80], [30, 75], [30, 75]])

def patrol():
    distance = round(my_dog.read_distance(), 2)
    if distance > 0 and distance < DANGER_DISTANCE:
        # DANGER: stop, bark, wait for clear
        my_dog.body_stop()
        head_yaw = my_dog.head_current_angles[0]  # Remember current head position
        my_dog.rgb_strip.set_mode('bark', 'red', bps=2)
        bark(my_dog, [head_yaw, 0, 0])
        while distance < DANGER_DISTANCE:
            distance = round(my_dog.read_distance(), 2)
            time.sleep(0.01)
    else:
        # SAFE: walk forward, look around, wag
        my_dog.rgb_strip.set_mode('breath', 'white', bps=0.5)
        my_dog.do_action('forward', step_count=2, speed=98)
        my_dog.do_action('shake_head', step_count=1, speed=80)
        my_dog.do_action('wag_tail', step_count=5, speed=99)
```

**Code Flow**:
1. Stand up
2. Loop: read distance
3. If obstacle < 15cm: stop, red LED, bark, wait for clear
4. If safe: white LED, walk forward 2 steps, shake head, wag tail

**Gotchas**:
- `legs_angle_calculation()` converts `[x, y]` foot positions to 8 servo angles via IK
- `my_dog.head_current_angles[0]` reads the current yaw for bark direction
- `bark()` from `preset_actions` includes sound + head movement animation
- Distance check `> 0` filters out invalid readings

---

### `4_response.py` -- Multi-Sensor Response

**Purpose**: Responds to both ultrasonic proximity and touch sensor input with appropriate behaviors.

**Hardware Used**: Ultrasonic, touch sensors, all servos, RGB strip, speaker.

**Key Code Patterns**:

```python
from pidog.preset_actions import bark_action

def lean_forward():
    my_dog.speak('angry', volume=80)
    bark_action(my_dog)  # Physical bark movement (no sound)
    sleep(0.2)
    bark_action(my_dog)

def head_nod(step):
    angs = []
    for i in range(20):
        r = round(10*sin(i*0.314), 2)   # Sinusoidal roll
        p = round(20*sin(i*0.314) + 10, 2)  # Sinusoidal pitch
        angs.append([0, r, p])
    my_dog.head_move(angs*step, immediately=False, speed=80)

def alert():
    while True:
        # Obstacle < 15cm: bark and back up
        if my_dog.read_distance() < 15 and my_dog.read_distance() > 1:
            my_dog.rgb_strip.set_mode('bark', color='red', bps=2)
            my_dog.do_action('backward', step_count=1, speed=95)
            lean_forward()

        # Touch detected: nod and wag
        if my_dog.dual_touch.read() != 'N':
            if len(my_dog.head_action_buffer) < 2:  # Don't overflow buffer
                head_nod(1)
                my_dog.do_action('wag_tail', step_count=10, speed=80)
                my_dog.rgb_strip.set_mode('listen', color="#8A2BE2", bps=0.35)
        else:
            my_dog.rgb_strip.set_mode('breath', color='pink', bps=1)
            my_dog.tail_stop()
```

**Code Flow**:
1. Stand up with pink breathing LED
2. Loop: check distance and touch
3. If too close: red LED, back up, bark action with angry sound
4. If touched: purple LED, nod head (sine wave pattern), wag tail
5. If nothing: pink LED, stop tail

**Gotchas**:
- `bark_action()` is the physical movement only (no sound); `speak('angry')` plays separately
- Sine wave head nod creates smooth oscillating roll/pitch pattern
- Buffer overflow prevention: only add head nod if `< 2` actions pending
- `distance < 15 and distance > 1`: filters invalid ultrasonic readings

---

### `5_rest.py` -- Sleep/Wake Cycle

**Purpose**: Dog lies down and sleeps; wakes up when sound is detected, looks around confused, then goes back to sleep.

**Hardware Used**: Sound direction sensor, all servos, RGB strip, speaker.

**Key Code Patterns**:

```python
from pidog.preset_actions import shake_head

def is_sound():
    if my_dog.ears.isdetected():
        direction = my_dog.ears.read()
        return direction != 0
    return False

def rest():
    my_dog.do_action('lie', speed=50)
    my_dog.wait_all_done()

    while True:
        # Sleep phase: pink LED, doze off animation
        my_dog.rgb_strip.set_mode('breath', 'pink', bps=0.3)
        my_dog.head_move([[0,0,-40]], immediately=True, speed=5)
        my_dog.do_action('doze_off', speed=92)
        sleep(1)
        is_sound()  # Clear any servo-noise false detections

        # Wait until sound detected
        while is_sound() is False:
            my_dog.do_action('doze_off', speed=92)
            sleep(0.2)

        # Wake: stand, look around, tilt head confused, shake head, lie back down
        my_dog.rgb_strip.set_mode('boom', 'yellow', bps=1)
        my_dog.body_stop()
        sleep(0.1)
        my_dog.do_action('stand', speed=80)
        my_dog.head_move([[0, 0, 0]], immediately=True, speed=80)
        my_dog.wait_all_done()
        loop_around(60, 1, 60)  # Look left/right
        my_dog.speak('confused_3', volume=80)
        my_dog.do_action('tilting_head_left', speed=80)
        shake_head(my_dog)
        my_dog.do_action('lie', speed=50)
        my_dog.wait_all_done()
```

**Code Flow**:
1. Lie down
2. Sleep loop: doze off animation, pink LED
3. Clear sound detection noise from servos
4. Poll for sound
5. On sound: stand up, look around, confused sound, tilt head, shake head
6. Lie down again, repeat

**Gotchas**:
- `is_sound()` clears the detection flag -- calling it again immediately returns False
- After servo movements, the first `is_sound()` call is a dummy to clear noise artifacts
- Direction 0 is filtered out (front-facing sound, often noise)

---

### `6_be_picked_up.py` -- Pickup Detection

**Purpose**: Detects when the dog is lifted off the ground using the IMU accelerometer.

**Hardware Used**: IMU (accelerometer), legs, tail, RGB strip, speaker.

**Key Code Patterns**:

```python
def be_picked_up():
    isUp = False
    upflag = False
    downflag = False
    stand()

    while True:
        ax = my_dog.accData[0]  # X-axis acceleration

        # Gravity: 1G = -16384
        if ax < -18000:  # Down: acceleration > 1G (in gravity direction)
            if upflag == False:
                upflag = True
            if downflag == True:
                isUp = False
                downflag = False
                stand()  # Put down -> stand back up

        if ax > -13000:  # Up: acceleration < 1G (against gravity)
            if upflag == True:
                isUp = True
                upflag = False
                fly()  # Picked up -> play excited animation
            if downflag == False:
                downflag = True
        sleep(0.02)
```

**Code Flow**:
1. Stand up
2. Loop: read accelerometer X-axis
3. If `ax < -18000` (pushed down during pickup): set upflag
4. If `ax > -13000` (tilted/lifted, gravity reduced): trigger fly() animation (legs out, red LED, "woohoo" sound)
5. When put down (ax returns to normal): stand back up

**Gotchas**:
- Gravity at rest: `ax ~ -16384` (1G pointing down through X-axis)
- Threshold `-18000` = stronger than gravity (initial push)
- Threshold `-13000` = weaker than gravity (being lifted)
- State machine with `upflag`/`downflag` prevents repeated triggers
- `fly()` uses `legs.servo_move()` directly for a splayed-out pose

---

### `7_face_track.py` -- Face Tracking

**Purpose**: Tracks detected human faces by moving the head, and barks when first seeing a person. Combines camera face detection with sound direction.

**Hardware Used**: Camera (vilib), sound direction, head servos, tail, speaker.

**Key Code Patterns**:

```python
from vilib import Vilib
from pidog.preset_actions import bark

Vilib.camera_start(vflip=False, hflip=False)
Vilib.display(local=False, web=True)
Vilib.face_detect_switch(True)

my_dog.do_action('sit', speed=50)
my_dog.head_move([[yaw, 0, pitch]], pitch_comp=-40, immediately=True, speed=80)

while True:
    # Sound direction: turn head toward sound
    if my_dog.ears.isdetected():
        direction = my_dog.ears.read()
        if direction > 0 and direction < 160:
            yaw = -direction
        elif direction > 200 and direction < 360:
            yaw = 360 - direction
        my_dog.head_move([[yaw, 0, pitch]], pitch_comp=-40, speed=80)

    # Face tracking: proportional control
    ex = Vilib.detect_obj_parameter['human_x'] - 320  # Error from center
    ey = Vilib.detect_obj_parameter['human_y'] - 240
    people = Vilib.detect_obj_parameter['human_n']

    if people > 0 and flag == False:
        flag = True
        bark(my_dog, [yaw, 0, 0], pitch_comp=-40, volume=80)

    if ex > 15 and yaw > -80:
        yaw -= 0.5 * int(ex/30.0+0.5)   # Proportional yaw adjustment
    elif ex < -15 and yaw < 80:
        yaw += 0.5 * int(-ex/30.0+0.5)

    my_dog.head_move([[yaw, 0, pitch]], pitch_comp=-40, immediately=True, speed=100)
    sleep(0.05)
```

**Code Flow**:
1. Start camera, enable face detection
2. Sit, set head level with `pitch_comp=-40` (compensates for sit tilt)
3. Loop: check sound direction, turn toward it
4. Read face position error from center
5. Bark once when first seeing a person
6. Proportional tracking: adjust yaw/pitch based on face position error
7. 20Hz update rate

**Gotchas**:
- Camera center is (320, 240) -- subtract to get error
- Proportional gain: `0.5 * int(error/30 + 0.5)` -- step function with ~15px dead zone
- `pitch_comp=-40` because dog is sitting (body tilted)
- Sound direction 0-160 maps to negative yaw (right), 200-360 maps to positive yaw (left)
- `flag` prevents repeated barking while face is visible

---

### `8_pushup.py` -- Push-Up Exercise

**Purpose**: Performs continuous push-ups with barking sound.

**Hardware Used**: Leg servos, head servos, RGB strip, speaker.

**Key Code Patterns**:

```python
from pidog.preset_actions import push_up, bark

my_dog.legs_move([[45, -25, -45, 25, 80, 70, -80, -70]], speed=50)  # Prep position
my_dog.head_move([[0, 0, -20]], speed=90)
my_dog.wait_all_done()

bark(my_dog, [0, 0, -20])  # Bark twice before starting
bark(my_dog, [0, 0, -20])

my_dog.rgb_strip.set_mode("speak", color="blue", bps=2)
while True:
    push_up(my_dog, speed=92)
    bark(my_dog, [0, 0, -40])
    sleep(0.4)
```

**Code Flow**:
1. Move to push-up preparation position
2. Level head with pitch -20
3. Bark twice
4. Blue LED animation
5. Loop: push-up + bark

---

### `9_howling.py` -- Howling Animation

**Purpose**: Plays the howling preset action in a loop.

**Hardware Used**: Legs (sit), head, speaker.

**Key Code Patterns**:

```python
from pidog.preset_actions import howling

my_dog.do_action('sit', speed=50)
my_dog.head_move([[0, 0, 0]], pitch_comp=-40, immediately=True, speed=80)

while True:
    howling(my_dog)
```

**Gotchas**:
- `howling()` is a complex preset that includes head tilt up + howl sound
- Dog must be sitting first
- `pitch_comp=-40` levels head for sit position

---

### `10_balance.py` -- IK Balance with Keyboard Control

**Purpose**: Walk with inverse kinematics body pose control and PID balance. Keyboard controls direction and body height.

**Hardware Used**: 8 leg servos, IMU (for PID balance).

**Key Code Patterns**:

```python
from pidog.walk import Walk
import readchar

# Pre-compute walk coordinate sets
stand_coords = [[[-15, 95], [-15, 95], [5, 90], [5, 90]]]
forward_coords = Walk(fb=Walk.FORWARD, lr=Walk.STRAIGHT).get_coords()
backward_coords = Walk(fb=Walk.BACKWARD, lr=Walk.STRAIGHT).get_coords()
turn_left_coords = Walk(fb=Walk.FORWARD, lr=Walk.LEFT).get_coords()
turn_right_coords = Walk(fb=Walk.FORWARD, lr=Walk.RIGHT).get_coords()

current_pose = {'x': 0, 'y': 0, 'z': 80}
current_rpy = {'roll': 0, 'pitch': 0, 'yaw': 0}

def move_thread():
    while thread_start:
        for coord in current_coords:
            my_dog.set_rpy(**current_rpy, pid=True)  # PID balance enabled
            my_dog.set_pose(**current_pose)
            my_dog.set_legs(coord)
            angles = my_dog.pose2legs_angle()  # IK calculation
            my_dog.legs.servo_move(angles, speed=98)
```

**Controls**:

| Key | Action |
|-----|--------|
| W | Forward |
| S | Backward |
| A | Turn left |
| D | Turn right |
| E | Stand |
| R | Raise body (+1 to z, max 90) |
| F | Lower body (-1 to z, min 30) |
| Ctrl+C | Exit |

**Code Flow**:
1. Stand up
2. Start movement thread
3. Keyboard loop: read key, update `current_coords` or `current_pose`
4. Movement thread continuously: set RPY (with PID), set pose, set legs, compute IK, move servos

**Gotchas**:
- Uses the low-level IK pipeline: `set_rpy()` -> `set_pose()` -> `set_legs()` -> `pose2legs_angle()`
- `pid=True` in `set_rpy()` enables IMU-based balance compensation
- `Walk` class generates coordinate sets for different gait directions
- Body height `z` range: 30-90 mm
- Requires `readchar` package (not curses)

---

### `11_keyboard_control.py` -- Full Keyboard Control

**Purpose**: Comprehensive keyboard control with curses TUI showing a virtual keyboard layout. Supports actions, head control, and preset behaviors.

**Hardware Used**: All servos, RGB strip, speaker.

**Key Code Patterns**:

```python
# Key-to-operation dispatch
KEYS = {
    "w": {"pos": [5, 15], "tip": ["Forward", ""], "operation": "forward"},
    "W": {"pos": [5, 15], "tip_upper": "Trot", "operation": "trot"},
    # ... 40+ key bindings
}
OPERATIONS = {
    "forward": {
        "function": lambda: my_dog.do_action('forward', speed=98),
        "status": STATUS_STAND,
        "head_pitch": STAND_HEAD_PITCH,
    },
    "bark": {
        "function": lambda: bark(my_dog, head_yrp, pitch_comp=head_pitch_init),
    },
    # ... 20+ operations
}

# Head control (direct YRP manipulation)
if key in ('uiojklmUIOJKL'):
    if key == 'i': head_yrp[2] = HEAD_ANGLE      # Pitch up
    elif key == 'k': head_yrp[2] = -HEAD_ANGLE    # Pitch down
    elif key == 'j': head_yrp[0] = HEAD_ANGLE     # Yaw left
    elif key == 'l': head_yrp[0] = -HEAD_ANGLE    # Yaw right
    # Uppercase = 2x angle
```

**Key Layout Summary**:

| Row | Keys | Function |
|-----|------|----------|
| Number row | 1-5 | Doze off, Push up, Howling, Body twist, Scratch |
| Q row | q/w/W/e/r/t | Bark, Forward/Trot, Pant, Wag tail, Handshake |
| A row | a/s/d/f/g | Turn left, Backward, Turn right, Shake head, High five |
| Z row | z/x/c/v | Lie, Stand, Sit, Stretch |
| Right side | u/i/o/j/k/l/m | Head roll/pitch/yaw control, reset |

**Gotchas**:
- Uppercase letters trigger different operations (e.g., `w`=forward, `W`=trot)
- Status management prevents invalid transitions (must stand before walking)
- `body_stop()` called between key changes to prevent action conflicts
- Non-blocking key read with 10ms timeout
- Imports `from pidog.preset_actions import *` for all action functions

---

### `12_app_control.py` -- Mobile App Control

**Purpose**: Remote control via SunFounder mobile app with joystick, voice, and button controls.

**Hardware Used**: All servos, camera, ultrasonic, RGB strip, speaker, WiFi.

**Key Code Patterns**:

```python
from sunfounder_controller import SunFounderController

sc = SunFounderController()
sc.set_name('Mydog')
sc.set_type('Pidog')
sc.start()

# Left joystick -> movement
k_value = sc.get('K')  # Returns [x, y] or None
ka = atan2(ky, kx) * 180 / pi  # Convert to angle
kr = sqrt(kx**2 + ky**2)       # Convert to radius
if kr > 100:
    if ka > 45 and ka < 135:    command = "forward"
    elif ka > 135 or ka < -135: command = "turn left"
    # ...

# Right joystick -> head control
q_value = sc.get('Q')  # Returns [x, y]
yaw = map(qx, 100, -100, -90, 90)
pitch = map(qy, -100, 100, -30, 30)

# Voice commands
voice_command = sc.get('J')  # Returns string or None

# Buttons
sc.get('N')  # Bark button
sc.get('O')  # Wag tail toggle
sc.get('E')  # Sit
sc.get('F')  # Stand
```

**Code Flow**:
1. Init SunFounderController, Pidog, camera
2. Set video stream URL
3. Loop: poll all controller inputs (joysticks, buttons, voice)
4. Map joystick angles to movement commands
5. Execute command via same dispatch system as keyboard control
6. Report ultrasonic distance to app display

**Gotchas**:
- Requires `sunfounder_controller` package
- Video stream at `http://<ip>:9000/mjpg`
- Joystick deadzone: `kr > 100` threshold
- Voice commands have fuzzy matching aliases (e.g., "bark" / "park", "wag tail" / "wake tail")
- COMMANDS dict includes multiple aliases for each action to handle STT errors

---

### `13_ball_track.py` -- Color Ball Tracking

**Purpose**: Tracks a colored ball (default: red) using the camera and moves toward it.

**Hardware Used**: Camera (vilib), legs, head servos.

**Key Code Patterns**:

```python
Vilib.color_detect(color="red")  # Options: red, green, blue, yellow, orange, purple

while True:
    ball_x = Vilib.detect_obj_parameter['color_x'] - 320
    ball_y = Vilib.detect_obj_parameter['color_y'] - 240
    width = Vilib.detect_obj_parameter['color_w']

    # Proportional head tracking
    if ball_x > 15 and yaw > -80:
        yaw -= STEP  # STEP = 0.5
    elif ball_x < -15 and yaw < 80:
        yaw += STEP

    my_dog.head_move([[yaw, 0, pitch]], immediately=True, speed=100)

    # Body movement based on ball position
    if width == 0:          # Lost ball -> reset
        pitch = 0; yaw = 0
    elif width < 300:       # Ball far away -> move toward it
        if yaw < -30:       my_dog.do_action('turn_right', speed=98)
        elif yaw > 30:      my_dog.do_action('turn_left', speed=98)
        else:                my_dog.do_action('forward', speed=98)
```

**Code Flow**:
1. Start camera, enable red color detection, stand
2. Loop: read ball position and width
3. Proportional head tracking (0.5 deg/step)
4. If ball width < 300 (far away): turn or walk toward it
5. If ball width = 0 (lost): reset head to center

**Gotchas**:
- `color_w` = detected blob width in pixels; 0 means not detected, larger = closer
- Threshold 300 for width means "close enough to stop"
- Head tracking step is 0.5 degrees per iteration at 50Hz = 25 deg/s max tracking speed
- Dead zone: +/-15 pixels horizontally, +/-25 pixels vertically

---

### `18.online_llm_test.py` -- LLM Text Chat

**Purpose**: Minimal text-based chat with OpenAI GPT-4o (no robot control).

**Hardware Used**: None (text-only).

**Key Code Patterns**:

```python
from pidog.llm import OpenAI
from secret import OPENAI_API_KEY

llm = OpenAI(api_key=OPENAI_API_KEY, model="gpt-4o")
llm.set_max_messages(20)       # Conversation history limit
llm.set_instructions(INSTRUCTIONS)
llm.set_welcome(WELCOME)

while True:
    input_text = input(">>> ")
    # Streaming response
    response = llm.prompt(input_text, stream=True)
    for next_word in response:
        if next_word:
            print(next_word, end="", flush=True)
    print("")
```

**Gotchas**:
- Requires `secret.py` file with `OPENAI_API_KEY`
- Uses `pidog.llm.OpenAI` wrapper (not openai package directly)
- Streaming: `prompt(text, stream=True)` returns an iterator
- Non-streaming: `prompt(text)` returns full string
- `set_max_messages(20)` limits context window to last 20 messages

---

### `19_voice_active_dog_ollama.py` -- Voice Active Dog (Ollama)

**Purpose**: Runs the full VoiceActiveDog with local Ollama LLM (no cloud API needed).

**Hardware Used**: All servos, camera, microphone, speaker, ultrasonic, touch sensors.

**Key Code Patterns**:

```python
from pidog.llm import Ollama as LLM
from voice_active_dog import VoiceActiveDog

llm = LLM(ip="localhost", model="llama3.2:3b")

vad = VoiceActiveDog(
    llm,
    name="Buddy",
    too_close=10,
    like_touch_styles=[TouchStyle.FRONT_TO_REAR],
    hate_touch_styles=[TouchStyle.REAR_TO_FRONT],
    with_image=False,           # No multimodal with basic Ollama
    stt_language="en-us",
    tts_model="en_US-ryan-low",
    keyboard_enable=True,
    wake_enable=True,
    wake_word=["hey buddy"],
    answer_on_wake="Hi there",
    instructions=INSTRUCTIONS,
    disable_think=True,         # Ollama-specific: disable thinking
)
vad.run()
```

**Configuration**:

| Parameter | Value | Notes |
|-----------|-------|-------|
| LLM | Ollama (local) | Can run on Pi or LAN computer |
| Model | llama3.2:3b | Any Ollama model works |
| STT | Vosk (en-us) | Local speech recognition |
| TTS | Piper (en_US-ryan-low) | Local text-to-speech |
| Image | Disabled | Requires multimodal model |
| Wake word | "hey buddy" | |

**Gotchas**:
- Ollama must be running (`ollama serve`) on localhost or specified IP
- `disable_think=True` is specific to Ollama (some models generate think tokens)
- `with_image=False` because basic Ollama models don't support vision
- IP can be remote LAN address if Ollama runs on a more powerful machine

---

### `20_voice_active_dog_doubao_cn.py` -- Voice Active Dog (Doubao, Chinese)

**Purpose**: Runs VoiceActiveDog with Doubao (ByteDance) LLM for Chinese language interaction.

**Hardware Used**: All servos, camera, microphone, speaker, ultrasonic, touch sensors.

**Key Code Patterns**:

```python
from pidog.llm import Doubao as LLM

llm = LLM(api_key=API_KEY, model="doubao-seed-1-6-250615")

vad = VoiceActiveDog(
    llm,
    name="旺财",
    tts_model="zh_CN-huayan-x_low",
    stt_language="cn",
    with_image=True,
    wake_word=["旺财"],
    answer_on_wake="汪汪",
    instructions=INSTRUCTIONS,  # Chinese system prompt
)
```

**Gotchas**:
- Chinese TTS model: `zh_CN-huayan-x_low`
- Chinese STT language: `"cn"`
- System prompt is entirely in Chinese
- `with_image=True` because Doubao supports multimodal
- Requires `DOUBAO_API_KEY` in `secret.py`

---

### `20_voice_active_dog_gpt.py` -- Voice Active Dog (OpenAI GPT)

**Purpose**: Runs VoiceActiveDog with OpenAI GPT-4o-mini.

**Hardware Used**: All servos, camera, microphone, speaker, ultrasonic, touch sensors.

**Key Code Patterns**:

```python
from pidog.llm import OpenAI as LLM

llm = LLM(api_key=API_KEY, model="gpt-4o-mini")
vad = VoiceActiveDog(llm, with_image=True, ...)
```

**Gotchas**:
- Same structure as Ollama variant but with cloud API
- `with_image=True` because GPT-4o-mini supports vision
- Requires `OPENAI_API_KEY` in `secret.py`
- Uses same `INSTRUCTIONS` and response format (`RESPONSE_TEXT\nACTIONS: ...`)

---

### `claude_pidog.py` -- Voice Active Dog (Claude/Anthropic)

**Purpose**: Runs VoiceActiveDog with Anthropic's Claude as the brain. Gets API key from environment variable.

**Hardware Used**: All servos, camera, microphone, speaker, ultrasonic, touch sensors.

**Key Code Patterns**:

```python
from pidog.anthropic_llm import Anthropic as LLM

API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not API_KEY:
    print('Error: ANTHROPIC_API_KEY environment variable not set')
    sys.exit(1)

llm = LLM(api_key=API_KEY, model='claude-sonnet-4-20250514')

vad = VoiceActiveDog(
    llm,
    with_image=True,
    keyboard_enable=False,
    wake_word=['hey buddy'],
    answer_on_wake='Woof!',
    instructions=INSTRUCTIONS,  # Dog personality prompt
)
```

**Gotchas**:
- Uses `pidog.anthropic_llm.Anthropic` (custom wrapper, not stock anthropic SDK)
- API key from environment: `ANTHROPIC_API_KEY=sk-ant-... sudo -E python3 claude_pidog.py`
- `-E` flag preserves environment variables when using sudo
- `keyboard_enable=False` (voice-only)
- Personality prompt emphasizes being a dog: short responses, action-oriented

---

### `curses_utils.py` -- Curses Utility Library

**Purpose**: Shared utility module providing color constants, pad refresh, and line clearing for all curses-based examples.

**Hardware Used**: None (terminal utilities).

**Key Code Patterns**:

```python
# Default pad dimensions
PAD_Y = 40
PAD_X = 80

# Color pair constants (initialized by init_preset_color_pairs())
BLACK = WHITE = CYAN = YELLOW = RED = GREEN = BLUE = MAGENTA = WHITE_BLUE = None

def init_preset_color_pairs():
    """Must call after curses.start_color()"""
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    BLACK = curses.color_pair(1)
    # ... 9 color pairs total

def pad_refresh(pad):
    """Refresh pad within terminal bounds"""
    y, x = pad.getbegyx()
    h, w = pad.getmaxyx()
    y_2 = min(y+h, curses.LINES-1)
    x_2 = min(x+w, curses.COLS-1)
    pad.refresh(0, 0, y, x, y_2, x_2)

def clear_line(pad, line, xlen=None, color_pair=None):
    """Clear a single line in a pad"""
```

**Gotchas**:
- Must call `init_preset_color_pairs()` after `curses.start_color()` and `curses.use_default_colors()`
- Globals: `PAD_Y`, `PAD_X` are overridden by importing scripts
- `pad_refresh()` clips to terminal size to avoid curses errors
- Imported by: `0_calibration.py`, `2_function_demonstration.py`, `11_keyboard_control.py`, `custom_actions.py`

---

### `custom_actions.py` -- Interactive Servo Angle Editor

**Purpose**: Curses-based tool for manually adjusting individual servo angles in real time. Similar to calibration but edits angles (not offsets).

**Hardware Used**: All 12 servos.

**Key Code Patterns**:

```python
# Read current servo angles
def get_current_angles():
    leg_angles = list.copy(my_dog.leg_current_angles)
    head_angles = list.copy(my_dog.head_current_angles)
    tail_angle = list.copy(my_dog.tail_current_angles)

# Direct servo control (no action buffer)
my_dog.legs_simple_move(leg_angles)     # Direct leg servo write
my_dog.head_move_raw([head_angles], True, 80)  # Raw head angles
my_dog.tail_move([tail_angle], True, 80)       # Direct tail
```

**Code Flow**:
1. Init Pidog, sit position
2. Read current angles from servos
3. Display curses TUI with servo diagram
4. Select servo (1-8, 9, 0, -, =), adjust with W/A/S/D
5. Uses `legs_simple_move()` for direct control

**Gotchas**:
- `legs_simple_move()` writes angles directly (no buffer, no interpolation)
- `leg_current_angles`, `head_current_angles`, `tail_current_angles` are live readbacks
- Same OFFSET_STEP precision as calibration tool
- Does NOT save to config -- for real-time experimentation only

---

### `servo_zeroing.py` -- Zero All Servos

**Purpose**: Resets all 12 servos to their zero position (useful for assembly/verification).

**Hardware Used**: All 12 servos (via robot_hat directly, not Pidog class).

**Key Code Patterns**:

```python
from robot_hat import Servo
from robot_hat.utils import reset_mcu

reset_mcu()
sleep(1)

for i in range(12):
    print(f"Servo {i} set to zero")
    Servo(i).angle(10)   # Brief 10-degree nudge
    sleep(0.1)
    Servo(i).angle(0)    # Set to zero
    sleep(0.1)

while True:
    sleep(1)  # Hold position
```

**Code Flow**:
1. Reset MCU
2. For each servo 0-11: nudge to 10 degrees, then set to 0
3. Hold forever (servos maintain position)

**Gotchas**:
- Uses `robot_hat.Servo` directly (not Pidog class)
- The 10-degree nudge before zeroing helps verify the servo is responding
- No `Pidog` init -- doesn't start threads/sensors
- Good for verifying hardware connections after assembly

---

### `voice_active_dog.py` -- VoiceActiveDog Class (Core)

**Purpose**: Core class that all LLM voice examples use. Extends `VoiceAssistant` with PiDog hardware integration, sensor triggers, and action parsing.

**Hardware Used**: All servos, camera, microphone, speaker, ultrasonic, touch sensors, RGB strip.

**Key Code Patterns**:

```python
from pidog.voice_assistant import VoiceAssistant
from pidog.action_flow import ActionFlow, ActionStatus, Posetures

class VoiceActiveDog(VoiceAssistant):
    VOICE_ACTIONS = ["bark", "bark harder", "pant", "howling"]

    def __init__(self, *args, too_close=10, like_touch_styles=..., hate_touch_styles=..., **kwargs):
        super().__init__(*args, **kwargs)
        self.init_pidog()
        self.add_trigger(self.is_too_close)        # Ultrasonic trigger
        self.add_trigger(self.is_touch_triggered)   # Touch trigger

    def init_pidog(self):
        self.dog = Pidog()
        self.action_flow = ActionFlow(self.dog)

    # VoiceAssistant lifecycle hooks:
    def on_start(self):         # Called when run() starts
        self.action_flow.start()
        self.action_flow.change_poseture(Posetures.SIT)

    def before_listen(self):    # Before listening for speech
        self.action_flow.set_status(ActionStatus.STANDBY)
        self.dog.rgb_strip.set_mode('breath', 'cyan', 1)

    def on_heard(self, text):   # After STT transcription
        self.action_flow.set_status(ActionStatus.THINK)

    def parse_response(self, text):  # Parse LLM response
        result = text.strip().split('ACTIONS: ')
        response_text = result[0].strip()
        actions = result[1].strip().split(', ') if len(result) > 1 else ['stop']
        self.action_flow.add_action(*actions)
        return response_text

    def before_say(self, text): # Before TTS speaks
        self.dog.rgb_strip.set_mode('breath', 'pink', 1)

    def after_say(self, text):  # After TTS finishes
        self.action_flow.wait_actions_done()
        self.action_flow.change_poseture(Posetures.SIT)

    def on_stop(self):          # Cleanup
        self.action_flow.stop()
        self.dog.close()
```

**Trigger System**:

```python
def is_too_close(self) -> tuple[bool, bool, str]:
    """Returns (triggered, disable_image, message)"""
    distance = self.dog.read_distance()
    if distance < self.too_close and distance > 1:
        return True, True, f'<<<Ultrasonic sense too close: {distance}cm>>>'
    return False, False, ''

def is_touch_triggered(self) -> tuple[bool, bool, str]:
    touch = self.dog.dual_touch.read()
    if touch in self.like_touch_styles:
        return True, True, f'<<<Touch style you like: {TouchStyle(touch).name}>>>'
    elif touch in self.hate_touch_styles:
        return True, True, f'<<<Touch style you hate: {TouchStyle(touch).name}>>>'
    return False, False, ''
```

**VoiceAssistant Lifecycle**:

```
on_start() -> [loop: before_listen() -> STT -> on_heard() -> before_think() -> LLM ->
               parse_response() -> before_say() -> TTS -> after_say() -> on_finish_a_round()]
               -> on_stop()
```

**Gotchas**:
- `parse_response()` splits on `"ACTIONS: "` -- LLM must use this exact format
- Triggers run between listen cycles; return `(triggered, disable_image, message)`
- `disable_image=True` skips camera frame for that prompt (e.g., when too close to see properly)
- `VOICE_ACTIONS` list (bark, pant, howling) -- response text is skipped for these
- `ActionFlow` manages posture state machine and queues actions for execution
- All LLM config variants (Ollama, GPT, Claude, Doubao) just instantiate this class with different LLM objects
