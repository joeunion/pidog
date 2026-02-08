# pidog: Basic Examples

<!-- Status: COMPLETE | Iteration: 1 -->

> All 13 basic examples: full annotated walkthroughs
> Source: `pidog/basic_examples/`

## Example Index

| File | Purpose | Hardware Used | Key Patterns |
|------|---------|---------------|--------------|
| `1_pidog_init.py` | Initialize Pidog with default or custom servo angles | All servos (12) | `Pidog()` constructor with init angles |
| `2_legs_control.py` | Control leg servos directly via action buffer | 8 leg servos | `legs_move()`, `wait_legs_done()`, immediate vs queued |
| `3_head_control.py` | Control head servos with raw and relative angles | 3 head servos, 8 leg servos | `head_move()`, `head_move_raw()`, `pitch_comp` |
| `4_tail_control.py` | Control tail servo with wag pattern | 1 tail servo, 8 leg servos | `tail_move()`, `wait_tail_done()` |
| `5_stop_actions.py` | Stop actions and manage buffer lifecycle | All servos | `body_stop()`, `wait_all_done()`, `close()` |
| `6_do_preset_actions.py` | Execute named preset actions | All servos | `do_action()`, `step_count`, concurrent actions |
| `7_sound_effect.py` | Play built-in sound effects | I2S speaker | `speak()`, working directory, sudo required |
| `8_ultrasonic_read.py` | Read ultrasonic distance sensor | Ultrasonic (D0/D1) | `read_distance()`, separate process |
| `9_rgb_control.py` | Control RGB LED strip styles | RGB strip (I2C 0x74) | `rgb_strip.set_mode()`, color formats |
| `10_imu_read.py` | Read IMU accelerometer and gyroscope | IMU SH3001 (I2C 0x36) | `accData`, `gyroData`, background thread |
| `11_sound_direction_read.py` | Read sound direction sensor | Sound direction (SPI) | `ears.isdetected()`, `ears.read()` |
| `12_dual_touch_read.py` | Read dual touch sensor states | Touch sensors (D2/D3) | `dual_touch.read()`, 5 return states |
| `13_camera_easy_use.py` | Camera with face detection via vilib | Camera (picamera2) | `Vilib.camera_start()`, `face_detect_switch()` |

---

## 1. `1_pidog_init.py` -- Initialization

**Purpose**: Demonstrates how to instantiate a `Pidog` object with default or custom initial servo angles.

**Hardware Used**: All 12 servos (8 legs, 3 head, 1 tail), IMU, RGB strip, ultrasonic (all initialized by constructor).

**Key Code Patterns**:

```python
from pidog import Pidog

# Default init (lie position)
# my_dog = Pidog()

# Custom initial angles
my_dog = Pidog(
    leg_init_angles=[25, 25, -25, -25, 70, -45, -70, 45],
    head_init_angles=[0, 0, -25],
    tail_init_angle=[0]
)
```

**Code Flow**:
1. Import `Pidog` class
2. Instantiate with custom leg/head/tail initial angles
3. Constructor resets MCU, starts 5 daemon threads + 1 ultrasonic process
4. Servos move to specified initial positions

**Gotchas**:
- Leg angle order: `[LF_upper, LF_lower, RF_upper, RF_lower, LH_upper, LH_lower, RH_upper, RH_lower]`
- Head angle order: `[yaw, roll, pitch]`
- Constructor blocks while MCU resets (~0.5s)
- No `close()` call -- servos hold position until program exits or power off

---

## 2. `2_legs_control.py` -- Legs Control

**Purpose**: Demonstrates direct leg servo control using the action buffer system with single and multiple action frames.

**Hardware Used**: 8 leg servos.

**Key Code Patterns**:

```python
# Single action frame (8 angles = 1 position)
single_action = [[45, 10, -45, -10, 45, 10, -45, -10]]
my_dog.legs_move(single_action, speed=30)

# Queue a second action (immediately=False)
single_action_2 = [[45, 35, -45, -35, 80, 70, -80, -70]]
my_dog.legs_move(single_action_2, immediately=False, speed=20)

# Wait for buffer to drain
my_dog.wait_legs_done()

# Multiple action frames (alternating positions = animation)
multiple_actions = [
    [90, -30, -90, 30, 80, 70, -80, -70],
    [45, 35, -45, -35, 80, 70, -80, -70]
]
# Loop: continuously push to buffer
while True:
    my_dog.legs_move(multiple_actions, immediately=False, speed=75)
    time.sleep(0.1)
```

**Code Flow**:
1. Init Pidog
2. Move to half-stand position (single action, immediate)
3. Queue push-up preparation position (not immediate -- waits for half-stand)
4. Wait until both complete
5. Loop: continuously push alternating push-up frames into buffer

**Gotchas**:
- `immediately=True` (default): clears buffer first, action starts right away
- `immediately=False`: appends to buffer, executes after current actions finish
- `speed` is 0-100 scale -- affects delay between interpolation steps, NOT servo DPS
- The `while True` loop adds frames faster than they execute; buffer grows but thread processes them sequentially
- Each action frame is 8 values: `[LF_u, LF_l, RF_u, RF_l, LH_u, LH_l, RH_u, RH_l]`

---

## 3. `3_head_control.py` -- Head Control

**Purpose**: Demonstrates both raw and compensated head servo control, showing the difference between `head_move_raw()` and `head_move()`.

**Hardware Used**: 3 head servos (yaw, roll, pitch), 8 leg servos (for sit position).

**Key Code Patterns**:

```python
# Move to sit position first (so head angles make sense)
sit_action = [[30, 60, -30, -60, 80, -45, -80, 45]]
my_dog.legs_move(sit_action, speed=30)
my_dog.wait_legs_done()

# Raw head control (absolute servo angles)
# my_dog.head_move_raw([[0, 0, -30]], speed=80)

# Compensated head control (relative angles + pitch compensation)
my_dog.head_move([[0, 0, 0]], pitch_comp=-30, speed=80)
# These two are equivalent: head_move_raw([[0,0,-30]]) == head_move([[0,0,0]], pitch_comp=-30)

# Multiple head positions (yaw/roll/pitch test pattern)
head_test_actions = [
    [0, 0, 0], [90, 0, 0], [0, 0, 0], [-90, 0, 0], [0, 0, 0],   # yaw sweep
    [0, 0, 0], [0, 60, 0], [0, 0, 0], [0, -60, 0], [0, 0, 0],    # roll sweep
    [0, 0, 0], [0, 0, 45], [0, 0, 0], [0, 0, -60], [0, 0, 0],    # pitch sweep
]
while True:
    my_dog.head_move(head_test_actions, pitch_comp=-30, speed=50)
    my_dog.wait_head_done()
```

**Code Flow**:
1. Sit the dog (legs to sit position, wait)
2. Move head to level position using `head_move()` with `pitch_comp=-30` (compensates for body tilt in sit)
3. Loop through yaw/roll/pitch test sweep pattern

**Gotchas**:
- `pitch_comp` offsets the pitch to keep head level regardless of body tilt
- When sitting, body tilts ~30 degrees, so `pitch_comp=-30` keeps head horizontal
- Head angle order: `[yaw, roll, pitch]`
- Yaw range: -90 to 90, Roll range: -70 to 70, Pitch range: -45 to 30

---

## 4. `4_tail_control.py` -- Tail Control

**Purpose**: Demonstrates tail servo control with a wag pattern using the tail action buffer.

**Hardware Used**: 1 tail servo, 8 leg servos (for stand position).

**Key Code Patterns**:

```python
# Stand first
stand_action = [[25, 35, -25, -35, 35, 35, -35, -35]]
my_dog.legs_move(stand_action, speed=30)
my_dog.wait_legs_done()

# Wag tail (alternating positions)
wag_tail_actions = [[-30], [30]]
while True:
    my_dog.tail_move(wag_tail_actions, speed=100)
    my_dog.wait_tail_done()
```

**Code Flow**:
1. Stand up (legs)
2. Wait for stand to complete
3. Loop: push two-frame wag pattern, wait, repeat

**Gotchas**:
- Tail angles are 1-element lists: `[[angle]]`
- `tail_move()` uses same buffer pattern as legs/head
- Tail DPS is 500 (fastest of all servos)
- Tail range: -90 to 90 degrees

---

## 5. `5_stop_actions.py` -- Stop Actions and Buffer Management

**Purpose**: Demonstrates action buffer lifecycle: filling, monitoring, stopping, and clean shutdown.

**Hardware Used**: 8 leg servos, 3 head servos.

**Key Code Patterns**:

```python
try:
    # Prepare position
    my_dog.legs_move(push_up_prepare_action, speed=30)
    my_dog.head_move([[0, 0, 0]], pitch_comp=-10, speed=80)
    my_dog.wait_all_done()  # Wait for ALL body parts

    # Fill buffers with 20 repetitions
    for _ in range(20):
        my_dog.legs_move(push_up_action, immediately=False, speed=50)
        my_dog.head_move(head_up_down_action, pitch_comp=-10, immediately=False, speed=50)

    print(f"legs buffer length (start): {len(my_dog.legs_action_buffer)}")
    time.sleep(5)
    print(f"legs buffer length (5s): {len(my_dog.legs_action_buffer)}")

    my_dog.body_stop()  # Clear ALL action buffers
    print(f"legs buffer length (stop): {len(my_dog.legs_action_buffer)}")

except KeyboardInterrupt:
    pass
finally:
    my_dog.close()  # Stop + lie + close threads
```

**Code Flow**:
1. Move to push-up preparation position
2. Fill leg and head buffers with 20 push-up cycles
3. Print buffer length at start
4. Wait 5 seconds (some actions drain)
5. Print buffer length after 5s (smaller)
6. Call `body_stop()` to clear all buffers
7. Print buffer length after stop (0)
8. `close()` in finally block

**Key API**:

| Method | Effect |
|--------|--------|
| `wait_all_done()` | Block until legs, head, AND tail buffers are empty |
| `body_stop()` | Clear all action buffers (legs, head, tail) immediately |
| `stop_and_lie()` | `body_stop()` + reset to lie pose |
| `close()` | `stop_and_lie()` + terminate all threads |

**Gotchas**:
- Always use `try/finally` with `close()` for clean shutdown
- `body_stop()` stops instantly but servos remain at their last position
- `close()` should be called once; threads are daemon threads but explicit cleanup is safer
- Buffer is a `deque` -- `len()` gives current pending action count

---

## 6. `6_do_preset_actions.py` -- Preset Actions

**Purpose**: Demonstrates the high-level `do_action()` API for executing named preset actions from the actions dictionary.

**Hardware Used**: All servos (legs, head, tail).

**Key Code Patterns**:

```python
try:
    my_dog.do_action("stand", speed=60)
    my_dog.wait_all_done()

    my_dog.do_action("push_up", step_count=10, speed=60)
    my_dog.wait_all_done()

    my_dog.do_action("half_sit", speed=60)
    my_dog.wait_all_done()

    # Concurrent actions: tail and head run simultaneously
    my_dog.do_action("wag_tail", step_count=80, speed=90)
    my_dog.do_action("tilting_head", step_count=5, speed=20)
    my_dog.wait_head_done()
    my_dog.body_stop()
finally:
    my_dog.close()
```

**Code Flow**:
1. Stand, wait
2. Push up 10 times, wait
3. Half sit, wait
4. Start wagging tail (80 steps) AND tilting head (5 steps) concurrently
5. Wait for head to finish, then stop everything

**Gotchas**:
- `do_action()` queues to the appropriate buffer (legs/head/tail) based on action definition
- `step_count` repeats the action pattern N times
- Actions affecting different body parts (tail + head) run concurrently since they use separate buffer threads
- Action names: `"stand"`, `"sit"`, `"lie"`, `"forward"`, `"backward"`, `"turn_left"`, `"turn_right"`, `"push_up"`, `"wag_tail"`, `"tilting_head"`, etc.

---

## 7. `7_sound_effect.py` -- Sound Effects

**Purpose**: Plays all built-in sound effects from the `sounds/` directory.

**Hardware Used**: I2S amplifier/speaker (requires sudo).

**Key Code Patterns**:

```python
# CRITICAL: Change working directory for relative path to ../sounds
abspath = os.path.abspath(os.path.dirname(__file__))
os.chdir(abspath)

my_dog = Pidog()

# Play a single sound
# my_dog.speak("angry")

# Iterate all sounds
for name in os.listdir('../sounds'):
    name = name.split('.')[0]  # Remove file extension
    my_dog.speak(name)
    # my_dog.speak(name, volume=50)  # Optional volume 0-100
    time.sleep(3)
```

**Code Flow**:
1. Change working directory to script location (required for relative sound path)
2. Init Pidog
3. List all files in `../sounds/` directory
4. Strip extension, play each sound with 3s delay

**Gotchas**:
- **Must run with `sudo`** for I2S audio access
- Working directory must be set correctly -- sounds are at `../sounds/` relative to `basic_examples/`
- `speak(name)` takes filename without extension (e.g., `"angry"` not `"angry.mp3"`)
- Sound effects have different durations; fixed `time.sleep(3)` may cut short or leave silence
- Available sounds: angry, confused, etc. (depends on files in `sounds/` directory)

---

## 8. `8_ultrasonic_read.py` -- Ultrasonic Distance

**Purpose**: Continuously reads distance from the ultrasonic sensor.

**Hardware Used**: Ultrasonic sensor (D0=echo, D1=trig).

**Key Code Patterns**:

```python
my_dog = Pidog()
while True:
    distance = my_dog.read_distance()
    distance = round(distance, 2)
    print(f"Distance: {distance} cm")
    time.sleep(0.5)
```

**Code Flow**:
1. Init Pidog (starts ultrasonic in separate process)
2. Loop: read distance, print, sleep 0.5s

**Gotchas**:
- Ultrasonic runs in a **separate process** (not thread) to avoid I2C bus conflicts
- Returns float in centimeters
- Values < 1 cm or very large values indicate no object / out of range
- Polling rate: ~2Hz is typical; faster polling is possible but returns cached values from the process

---

## 9. `9_rgb_control.py` -- RGB LED Strip

**Purpose**: Demonstrates RGB LED strip control with different styles, colors, and parameters.

**Hardware Used**: RGB strip (SLED1735, I2C address 0x74, 11 LEDs).

**Key Code Patterns**:

```python
# Style + named color
my_dog.rgb_strip.set_mode(style="breath", color='pink')

# Style + RGB list
my_dog.rgb_strip.set_mode(style="listen", color=[0, 255, 255])

# Style + hex color
my_dog.rgb_strip.set_mode(style="boom", color="#a10a0a")

# With brightness and BPS (beats per second)
my_dog.rgb_strip.set_mode(style="boom", color="#a10a0a", bps=2.5, brightness=0.5)

# Turn off
my_dog.rgb_strip.close()
```

**Code Flow**:
1. Init Pidog
2. Cycle through styles: breath (pink), listen (cyan), boom (red), boom (red + half brightness + faster)
3. Turn off, repeat

**Color Formats**:

| Format | Example | Notes |
|--------|---------|-------|
| Named string | `'pink'`, `'red'`, `'cyan'` | Predefined: white, black, red, yellow, green, blue, cyan, magenta, pink |
| RGB list | `[0, 255, 255]` | 0-255 per channel |
| Hex string | `'#a10a0a'` | Standard hex color |

**Styles**: `"breath"`, `"boom"`, `"bark"`, `"speak"`, `"listen"`

**Gotchas**:
- `bps` = beats per second (animation speed)
- `brightness` = 0.0 to 1.0 multiplier
- RGB strip runs in its own daemon thread
- `close()` turns off LEDs but does not stop thread

---

## 10. `10_imu_read.py` -- IMU (Accelerometer + Gyroscope)

**Purpose**: Continuously reads SH3001 IMU data (accelerometer and gyroscope).

**Hardware Used**: SH3001 IMU (I2C address 0x36).

**Key Code Patterns**:

```python
my_dog = Pidog()
while True:
    ax, ay, az = my_dog.accData
    gx, gy, gz = my_dog.gyroData
    print(f"accData: {ax}, {ay}, {az}       gyroData: {gx}, {gy}, {gz}")
    time.sleep(0.2)
```

**Code Flow**:
1. Init Pidog (starts IMU thread)
2. Loop: read `accData` and `gyroData`, print, sleep

**Data Format**:

| Property | Values | Units | Notes |
|----------|--------|-------|-------|
| `accData` | `[ax, ay, az]` | Raw (1G = -16384) | Accelerometer direction is **opposite** to actual acceleration |
| `gyroData` | `[gx, gy, gz]` | Raw (2000 deg/s range) | Angular velocity |

**Gotchas**:
- Data is refreshed continuously in a background thread
- Gravity: 1G = -16384 on the axis pointing down
- Accelerometer reads **opposite** to actual acceleration direction
- At rest on level surface: `ax ~ -16384`, `ay ~ 0`, `az ~ 0` (x-axis points down)
- IMU sampling: 500Hz (acc/gyro), 63Hz (temp)

---

## 11. `11_sound_direction_read.py` -- Sound Direction

**Purpose**: Detects sound direction using the SPI-based sound direction module.

**Hardware Used**: Sound direction sensor (SPI0, GPIO 6 busy pin).

**Key Code Patterns**:

```python
my_dog = Pidog()
while True:
    if my_dog.ears.isdetected():
        direction = my_dog.ears.read()
        print(f"sound direction: {direction}")
```

**Code Flow**:
1. Init Pidog
2. Loop: check if sound detected, if so read azimuth angle

**Gotchas**:
- `ears.isdetected()` returns `bool` -- whether the module detected a sound
- `ears.read()` returns `int` 0-359 -- azimuth in degrees (20-degree resolution)
- Direction 0 = front of dog
- No sleep in loop -- runs as fast as possible (busy poll)
- Sound detection is event-based; `isdetected()` clears after read
- Servo movements generate noise that triggers false detections -- clean up with a dummy `isdetected()`/`read()` call after moving

---

## 12. `12_dual_touch_read.py` -- Dual Touch Sensors

**Purpose**: Continuously reads the dual touch sensor state (head petting detection).

**Hardware Used**: Dual touch sensors (D2=rear, D3=front).

**Key Code Patterns**:

```python
my_dog = Pidog()
while True:
    touch_status = my_dog.dual_touch.read()
    print(f"touch_status: {touch_status}")
    time.sleep(0.5)
```

**Return Values**:

| Value | Meaning |
|-------|---------|
| `'N'` | No touch |
| `'L'` | Left (rear) touched |
| `'LS'` | Left (rear) slide |
| `'R'` | Right (front) touched |
| `'RS'` | Right (front) slide |

**Gotchas**:
- "Left" = rear sensor (D2), "Right" = front sensor (D3)
- Slide detection requires touching one sensor then the other in sequence
- Returns string, not enum (though `TouchStyle` enum exists for comparison)
- Polling at 0.5s may miss quick touches; 50ms is better for responsive detection

---

## 13. `13_camera_easy_use.py` -- Camera and Face Detection

**Purpose**: Starts the camera with face detection using the vilib library (not pidog directly).

**Hardware Used**: Camera (picamera2 via vilib).

**Key Code Patterns**:

```python
from vilib import Vilib

try:
    # Start camera (all vilib methods are @staticmethod)
    Vilib.camera_start(vflip=False, hflip=False)
    # Enable web display (accessible at http://<pi-ip>:9000/mjpg)
    Vilib.display(local=False, web=True)
    # Enable face detection
    Vilib.face_detect_switch(True)
    time.sleep(1)

    while True:
        n = Vilib.detect_obj_parameter['human_n']
        print(f"\r {n:^3} faces are found.", end='', flush=True)
        time.sleep(1)

except KeyboardInterrupt:
    pass
finally:
    Vilib.camera_close()
```

**Code Flow**:
1. Start camera with optional flip
2. Enable web stream (MJPEG at port 9000)
3. Enable face detection
4. Loop: read face count from `detect_obj_parameter` dict
5. Cleanup: close camera

**Key `detect_obj_parameter` Fields**:

| Key | Type | Description |
|-----|------|-------------|
| `'human_n'` | int | Number of faces detected |
| `'human_x'` | int | X coordinate of first face (pixels) |
| `'human_y'` | int | Y coordinate of first face (pixels) |
| `'color_x'` | int | X of detected color blob |
| `'color_y'` | int | Y of detected color blob |
| `'color_w'` | int | Width of detected color blob |

**Gotchas**:
- vilib is a **separate library**, not part of pidog -- uses `@staticmethod` methods (no instance needed)
- `Vilib.camera_start()` is required before any detection
- Camera resolution is 640x480 (center at 320, 240)
- `local=True` opens a desktop window (requires display), `web=True` starts MJPEG server
- Camera format is XBGR8888 (set by VoiceAssistant)
- Always call `Vilib.camera_close()` in cleanup
