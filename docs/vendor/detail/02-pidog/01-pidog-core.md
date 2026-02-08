# pidog: Core (Pidog Class)

<!-- Status: COMPLETE | Iteration: 1 -->

> Covers: `pidog.py` — the main Pidog class (964 lines)

## Purpose

The `Pidog` class is the main hardware abstraction for the PiDog robot. It initializes all servos, sensors, and peripherals, manages threaded action execution, performs inverse kinematics calculations, and provides high-level control methods for locomotion and sensing.

## Hardware

| Component | Interface | I2C/GPIO | Initialization |
|-----------|-----------|----------|----------------|
| 8 leg servos | Robot (robot_hat) | I2C servo hat | Pins [2,3,7,8,0,1,10,11] |
| 3 head servos | Robot (robot_hat) | I2C servo hat | Pins [4,6,5] (yaw/roll/pitch) |
| 1 tail servo | Robot (robot_hat) | I2C servo hat | Pin [9] |
| IMU (SH3001) | Sh3001 class | 0x36 | 500Hz acc/gyro, 63Hz temp |
| RGB Strip (SLED1735) | RGBStrip class | 0x74 | 11 LEDs, breath mode |
| Dual Touch | DualTouch class | D2, D3 | Rear (D2), Front (D3) |
| Sound Direction | SoundDirection class | SPI0, GPIO6 | 360°, 20° resolution |
| Ultrasonic | Ultrasonic class | D0 (echo), D1 (trig) | Separate process |
| Sound effects | Music class | - | Plays MP3/WAV via pygame |

## API Reference

### Pidog Class (pidog.py:87)

#### `__init__(leg_pins=DEFAULT_LEGS_PINS, head_pins=DEFAULT_HEAD_PINS, tail_pin=DEFAULT_TAIL_PIN, leg_init_angles=None, head_init_angles=None, tail_init_angle=None)`

Initialize PiDog robot with all hardware components.

**Parameters**:
- `leg_pins` (list): 8 servo indices for legs. Default: `[2,3,7,8,0,1,10,11]`
- `head_pins` (list): 3 servo indices for head yaw/roll/pitch. Default: `[4,6,5]`
- `tail_pin` (list): 1 servo index for tail. Default: `[9]`
- `leg_init_angles` (list): Initial 8 leg angles (degrees). Default: lie position
- `head_init_angles` (list): Initial 3 head angles [yaw, roll, pitch]. Default: `[0,0,0]`
- `tail_init_angle` (list): Initial tail angle. Default: `[0]`

**Side effects**:
- Resets MCU via `utils.reset_mcu()`
- Starts 5 daemon threads: legs, head, tail, RGB, IMU
- Starts 1 process: ultrasonic sensor
- Initializes action buffer queues and thread locks

**Thread-safe**: No (constructor not thread-safe)

**Raises**:
- `OSError`: If I2C init fails (Robot or SH3001)

**Constants**:
```python
DEFAULT_LEGS_PINS = [2, 3, 7, 8, 0, 1, 10, 11]  # LH, LH, LF, LF, RH, RH, RF, RF
DEFAULT_HEAD_PINS = [4, 6, 5]  # Yaw, Roll, Pitch
DEFAULT_TAIL_PIN = [9]
HEAD_DPS = 300   # degrees per second
LEGS_DPS = 428
TAIL_DPS = 500
LEG = 42   # mm, upper leg length
FOOT = 76  # mm, lower leg length
BODY_LENGTH = 117  # mm
BODY_WIDTH = 98    # mm
HEAD_PITCH_OFFSET = 45  # degrees, mechanical offset
HEAD_YAW_MIN = -90
HEAD_YAW_MAX = 90
HEAD_ROLL_MIN = -70
HEAD_ROLL_MAX = 70
HEAD_PITCH_MIN = -45
HEAD_PITCH_MAX = 30
KP = 0.033  # PID proportional gain
KI = 0.0
KD = 0.0
```

---

### Servo Control Methods

#### `legs_move(target_angles, immediately=True, speed=50)` (pidog.py:531)

Queue leg servo movements to action buffer.

**Parameters**:
- `target_angles` (list of lists): Each element is 8-element list of leg angles (degrees). Example: `[[0,0,0,0,0,0,0,0]]`
- `immediately` (bool): If True, clear buffer before adding. Default: True
- `speed` (int): 0-100, affects delay between servo steps. Default: 50

**Thread-safe**: Yes (uses `legs_thread_lock`)

**Side effects**: Appends to `legs_action_buffer`, consumed by `_legs_action_thread`

---

#### `head_move(target_yrps, roll_comp=0, pitch_comp=0, immediately=True, speed=50)` (pidog.py:547)

Queue head movements using yaw/roll/pitch coordinates with compensation.

**Parameters**:
- `target_yrps` (list of lists): Each element is [yaw, roll, pitch] in degrees
- `roll_comp` (float): Roll compensation offset (degrees). Default: 0
- `pitch_comp` (float): Pitch compensation offset (degrees). Default: 0
- `immediately` (bool): If True, clear buffer before adding. Default: True
- `speed` (int): 0-100. Default: 50

**Thread-safe**: Yes (uses `head_thread_lock`)

**Notes**: Internally converts YRP to servo angles via `head_rpy_to_angle()`, which applies mechanical transformations and clamps to hardware limits.

---

#### `head_move_raw(target_angles, immediately=True, speed=50)` (pidog.py:558)

Queue head movements using raw servo angles (bypasses YRP conversion).

**Parameters**:
- `target_angles` (list of lists): Each element is [yaw_servo, roll_servo, pitch_servo]
- `immediately` (bool): If True, clear buffer before adding. Default: True
- `speed` (int): 0-100. Default: 50

**Thread-safe**: Yes (uses `head_thread_lock`)

**Notes**: Still applies `HEAD_PITCH_OFFSET` (45°) and clamps to hardware limits.

---

#### `tail_move(target_angles, immediately=True, speed=50)` (pidog.py:565)

Queue tail movements.

**Parameters**:
- `target_angles` (list of lists): Each element is [tail_angle]. Example: `[[30]]`
- `immediately` (bool): If True, clear buffer before adding. Default: True
- `speed` (int): 0-100. Default: 50

**Thread-safe**: Yes (uses `tail_thread_lock`)

---

#### `legs_simple_move(angles_list, speed=90)` (pidog.py:326)

Direct non-threaded leg movement (bypasses action buffer).

**Parameters**:
- `angles_list` (list): 8 leg angles (degrees)
- `speed` (int): 0-100. Default: 90

**Thread-safe**: No (direct servo write)

**Side effects**: Writes to servos immediately, sleeps based on speed

**Notes**: Used internally by kinematics methods. Not recommended for application code.

---

### Body Position Methods

#### `do_action(action_name, step_count=1, speed=50, pitch_comp=0)` (pidog.py:917)

Execute a named action from the action dictionary.

**Parameters**:
- `action_name` (str): Action key from `actions_dict`. Examples: 'stand', 'sit', 'forward', 'wag_tail'
- `step_count` (int): Repeat count for locomotion actions. Default: 1
- `speed` (int): 0-100. Default: 50
- `pitch_comp` (float): Pitch compensation for head actions. Default: 0

**Thread-safe**: Yes

**Side effects**: Appends to appropriate action buffer (legs/head/tail depending on action)

**Raises**:
- `KeyError`: If action_name not in `actions_dict`

**Available actions**: See `02-actions-system.md` for full list.

---

#### `stop_and_lie(speed=85)` (pidog.py:615)

Emergency stop all movements and return to lie position.

**Parameters**:
- `speed` (int): 0-100. Default: 85

**Thread-safe**: Yes

**Side effects**: Clears all action buffers, moves to lie position, blocks until complete

---

#### `legs_stop()` (pidog.py:510)

Clear leg action buffer and wait for completion.

**Thread-safe**: Yes (uses `legs_thread_lock`)

**Blocks**: Until leg buffer empty

---

#### `head_stop()` (pidog.py:515)

Clear head action buffer and wait for completion.

**Thread-safe**: Yes (uses `head_thread_lock`)

**Blocks**: Until head buffer empty

---

#### `tail_stop()` (pidog.py:520)

Clear tail action buffer and wait for completion.

**Thread-safe**: Yes (uses `tail_thread_lock`)

**Blocks**: Until tail buffer empty

---

#### `body_stop()` (pidog.py:525)

Clear all action buffers (legs + head + tail) and wait for completion.

**Thread-safe**: Yes

**Blocks**: Until all buffers empty

---

### Inverse Kinematics

#### `legs_angle_calculation(coords)` (pidog.py:867) [classmethod]

Convert 4 leg cartesian coordinates to 8 servo angles.

**Parameters**:
- `coords` (list): 4 coordinate pairs `[[y1, z1], [y2, z2], [y3, z3], [y4, z4]]` in mm

**Returns**: List of 8 leg angles (degrees)

**Thread-safe**: Yes (no state mutation)

**Notes**:
- Uses two-link IK with `LEG=42mm`, `FOOT=76mm`
- Leg order: left-hind, right-hind, left-front, right-front
- Angles auto-inverted for right-side legs (odd indices)
- Formula: `foot_angle = foot_angle - 90` (mechanical offset)

**Example**:
```python
# All legs at y=0, z=80 (standing height)
angles = Pidog.legs_angle_calculation([[0, 80], [0, 80], [0, 80], [0, 80]])
# Returns 8 angles ready for legs_move()
```

---

#### `pose2legs_angle()` (pidog.py:786)

Convert current pose (position + RPY Euler angles) to leg servo angles.

**Returns**: List of 8 leg angles (degrees)

**Thread-safe**: No (reads `self.pose`, `self.rpy`, `self.legpoint_struc`)

**Side effects**: None

**Notes**:
- Uses `pose2coords()` to compute body-relative leg positions
- Applies rotation matrices for roll/pitch/yaw
- Uses `fieldcoord2polar()` for IK with pitch compensation

---

#### `set_pose(x=None, y=None, z=None)` (pidog.py:698)

Set target body position (center of mass).

**Parameters**:
- `x` (float): X offset (mm). Default: None (no change)
- `y` (float): Y offset (mm). Default: None (no change)
- `z` (float): Z height (mm). Default: None (no change)

**Thread-safe**: No (mutates `self.pose`)

**Side effects**: Updates `self.pose` matrix. Call `pose2legs_angle()` to compute angles.

---

#### `set_rpy(roll=None, pitch=None, yaw=None, pid=False)` (pidog.py:706)

Set target body orientation (Euler angles).

**Parameters**:
- `roll` (float): Roll angle (degrees). Default: None (no change)
- `pitch` (float): Pitch angle (degrees). Default: None (no change)
- `yaw` (float): Yaw angle (degrees). Default: None (no change)
- `pid` (bool): If True, apply PID correction using IMU feedback. Default: False

**Thread-safe**: No (mutates `self.rpy`)

**Side effects**:
- Updates `self.rpy` (converted to radians internally)
- If `pid=True`, updates PID integral/error state

**Notes**: PID uses `self.roll` and `self.pitch` from IMU thread (updated at 20Hz).

---

#### `set_legs(legs_list)` (pidog.py:738)

Set individual leg endpoint positions (body-relative).

**Parameters**:
- `legs_list` (list): 4 coordinate pairs `[[y1, z1], [y2, z2], [y3, z3], [y4, z4]]`

**Thread-safe**: No (mutates `self.legpoint_struc`)

**Side effects**: Updates `self.legpoint_struc` matrix. Call `pose2legs_angle()` to compute angles.

---

### Sensor Methods

#### `read_distance()` (pidog.py:265)

Read ultrasonic distance sensor.

**Returns**: float, distance in cm (rounded to 2 decimals). Returns -1.0 if no echo.

**Thread-safe**: Yes (reads `multiprocessing.Value`)

**Notes**: Updated at ~100Hz by separate process. Non-blocking read.

---

#### IMU Properties (pidog.py:444-507)

IMU data updated by `_imu_thread` at 20Hz (50ms sleep).

**Attributes**:
- `self.roll` (float): Roll angle (degrees), updated continuously
- `self.pitch` (float): Pitch angle (degrees), updated continuously
- `self.accData` (list): Raw accelerometer [ax, ay, az] (units: 1G = 16384)
- `self.gyroData` (list): Raw gyroscope [gx, gy, gz] (units: °/s)

**Thread-safe**: Read-only access safe. Do not write to these attributes.

**Calibration**: IMU auto-calibrates offset on init (1 second sampling).

---

#### `dual_touch.read()` (via DualTouch object)

Read touch sensors.

**Returns**: str, one of:
- `'N'`: No touch
- `'L'`: Rear touch (left)
- `'R'`: Front touch (right)
- `'LS'`: Rear-to-front slide (left-swipe)
- `'RS'`: Front-to-rear slide (right-swipe)

**Thread-safe**: Yes

**Notes**: Slide detection requires touches within 0.5s interval.

---

#### `ears.read()` (via SoundDirection object)

Read sound direction sensor.

**Returns**: int, angle in degrees (0-355), or -1 if no detection. Minimum resolution: 20°.

**Thread-safe**: Yes

**Notes**: Must call `ears.isdetected()` first to check if sound detected before reading.

---

#### `rgb_strip.set_mode(style, color, bps, brightness)` (via RGBStrip object)

Set RGB LED strip display mode.

**Parameters**:
- `style` (str): One of 'monochromatic', 'breath', 'boom', 'bark', 'speak', 'listen'
- `color` (str): Color name ('red', 'cyan', etc.), hex string ('#ff00ff'), RGB tuple, or int
- `bps` (float): Beats per second (animation speed). Default: 1.0
- `brightness` (float): 0.0 to 1.0. Default: 1.0

**Thread-safe**: Yes (attribute mutation only, no immediate I2C)

**Side effects**: Sets parameters for RGB thread to display. Changes take effect on next frame (50ms).

---

### Audio Methods

#### `speak(name, volume=100)` (pidog.py:626)

Play sound effect (non-blocking).

**Parameters**:
- `name` (str): Filename (without extension) in `SOUND_DIR`, or full path
- `volume` (int): 0-100. Default: 100

**Thread-safe**: Yes (spawns thread)

**Side effects**: Kills pulseaudio processes to fix VNC sound issues

**Search order**:
1. `name` as full path
2. `SOUND_DIR + name + '.mp3'`
3. `SOUND_DIR + name + '.wav'`

**Returns**: False if file not found, None otherwise

---

#### `speak_block(name, volume=100)` (pidog.py:650)

Play sound effect (blocking).

**Parameters**: Same as `speak()`

**Thread-safe**: No (blocks current thread)

**Side effects**: Blocks until audio finishes playing

---

### Wait Methods

#### `wait_legs_done()` (pidog.py:934)

Block until leg action buffer empty.

**Thread-safe**: Yes

**Blocks**: Until `legs_action_buffer` empty

---

#### `wait_head_done()` (pidog.py:938)

Block until head action buffer empty.

**Thread-safe**: Yes

**Blocks**: Until `head_action_buffer` empty

---

#### `wait_tail_done()` (pidog.py:942)

Block until tail action buffer empty.

**Thread-safe**: Yes

**Blocks**: Until `tail_action_buffer` empty

---

#### `wait_all_done()` (pidog.py:946)

Block until all action buffers empty (legs + head + tail).

**Thread-safe**: Yes

**Blocks**: Until all buffers empty

---

#### `is_legs_done()` (pidog.py:951)

Check if leg action buffer empty.

**Returns**: bool, True if buffer empty

**Thread-safe**: Yes (non-blocking check)

---

#### `is_head_done()` (pidog.py:954)

Check if head action buffer empty.

**Returns**: bool, True if buffer empty

**Thread-safe**: Yes (non-blocking check)

---

#### `is_tail_done()` (pidog.py:957)

Check if tail action buffer empty.

**Returns**: bool, True if buffer empty

**Thread-safe**: Yes (non-blocking check)

---

#### `is_all_done()` (pidog.py:960)

Check if all action buffers empty.

**Returns**: bool, True if all buffers empty

**Thread-safe**: Yes (non-blocking check)

---

### Calibration Methods

#### `set_leg_offsets(cali_list, reset_list=None)` (pidog.py:675)

Set servo calibration offsets for legs.

**Parameters**:
- `cali_list` (list): 8 offset values (degrees)
- `reset_list` (list): 8 angles to set after offset applied. Default: None (reset to [0]*8)

**Thread-safe**: No (direct servo write)

**Side effects**: Updates servo offset database, writes to servos immediately

---

#### `set_head_offsets(cali_list)` (pidog.py:685)

Set servo calibration offsets for head.

**Parameters**:
- `cali_list` (list): 3 offset values (degrees)

**Thread-safe**: No (direct servo write)

**Side effects**: Updates servo offset database, moves head to [0,0,0]

---

#### `set_tail_offset(cali_list)` (pidog.py:691)

Set servo calibration offset for tail.

**Parameters**:
- `cali_list` (list): 1 offset value (degrees)

**Thread-safe**: No (direct servo write)

**Side effects**: Updates servo offset database, resets tail to 0

---

### Lifecycle Methods

#### `close()` (pidog.py:272)

Gracefully shutdown robot and cleanup resources.

**Thread-safe**: No (should be called from main thread)

**Side effects**:
- Stops and returns to lie position (5s timeout)
- Joins all threads (legs, head, tail, RGB, IMU)
- Terminates ultrasonic process
- Closes GPIO pins (touch, sound direction, ultrasonic)

**Blocks**: Up to 5 seconds waiting for lie position

**Notes**: Installs temporary SIGINT handler to prevent Ctrl+C interruption during cleanup.

---

#### `close_all_thread()` (pidog.py:269)

Set exit flag to stop all threads (does not block or cleanup).

**Thread-safe**: Yes

**Side effects**: Sets `self.exit_flag = True`, threads exit on next iteration

**Notes**: Internal method, prefer `close()` for full cleanup.

---

### Utility Methods

#### `get_battery_voltage()` (pidog.py:963)

Read battery voltage from ADC.

**Returns**: float, voltage in volts (rounded to 2 decimals)

**Thread-safe**: Yes

---

#### `action_threads_start()` (pidog.py:355)

Start all daemon threads (legs, head, tail, RGB, IMU).

**Thread-safe**: No (constructor only)

**Side effects**: Spawns 5 daemon threads

**Notes**: Called automatically by `__init__()`. Can be called manually after `close_all_thread()`.

---

#### `sensory_process_start()` (pidog.py:606)

Start ultrasonic sensor process.

**Thread-safe**: No

**Side effects**: Spawns separate process running `sensory_process_work()`

**Notes**: Called automatically by `__init__()`. Terminates previous process if exists.

---

## Implementation Notes

### Initialization Sequence

1. `utils.reset_mcu()` — Reset I2C servo controller
2. Create `ActionDict` instance (action definitions)
3. Initialize kinematics state (`pose`, `rpy`, leg matrices)
4. Initialize `Robot` objects for legs (8 servos), head (3 servos), tail (1 servo)
   - Sets DPS limits (`LEGS_DPS=428`, `HEAD_DPS=300`, `TAIL_DPS=500`)
   - Moves servos to init angles in specific order (even indices first: 0,2,4,6,1,3,5,7)
5. Initialize `Sh3001` IMU (I2C 0x36)
6. Initialize `RGBStrip` (I2C 0x74, 11 LEDs)
7. Initialize `DualTouch` (GPIO D2, D3)
8. Initialize `SoundDirection` (SPI0, GPIO6)
9. Initialize `Music` (pygame audio)
10. Start 5 daemon threads via `action_threads_start()`
11. Start ultrasonic process via `sensory_process_start()`

**Total startup time**: ~1-2 seconds

**Failure handling**:
- I2C failures (Robot, IMU, RGB) print error, raise `OSError`
- GPIO failures (touch, sound, ultrasonic) print error, continue (component disabled)

---

### Threading Architecture

| Thread | Target | Purpose | Update Rate | Exit Condition |
|--------|--------|---------|-------------|----------------|
| `legs_thread` | `_legs_action_thread()` | Pop from `legs_action_buffer`, write servos | DPS-limited | `exit_flag=True` |
| `head_thread` | `_head_action_thread()` | Pop from `head_action_buffer`, write servos, clamp angles | DPS-limited | `exit_flag=True` |
| `tail_thread` | `_tail_action_thread()` | Pop from `tail_action_buffer`, write servos | DPS-limited | `exit_flag=True` |
| `rgb_strip_thread` | `_rgb_strip_thread()` | Call `rgb_strip.show()` | 20Hz (50ms) | `rgb_thread_run=False` |
| `imu_thread` | `_imu_thread()` | Read IMU, compute roll/pitch, calibrate on startup | 20Hz (50ms) | `exit_flag=True` |

**Process**:
| Process | Target | Purpose | Update Rate | Exit Condition |
|---------|--------|---------|-------------|----------------|
| `sensory_process` | `sensory_process_work()` | Read ultrasonic sensor | ~100Hz (10ms) | Manual terminate |

**Locks**:
- `legs_thread_lock`: Protects `legs_action_buffer`
- `head_thread_lock`: Protects `head_action_buffer`
- `tail_thread_lock`: Protects `tail_action_buffer`
- `sensory_lock`: Protects `distance` shared value (multiprocessing.Value)

**All threads are daemon threads** — exit when main thread exits (unless blocked in `close()`).

---

### Servo Indexing

**Physical Layout**:
```
Legs: [0,1] = left-hind, [2,3] = left-front, [4,5] = right-hind, [6,7] = right-front
Head: [0] = yaw (left/right), [1] = roll (tilt), [2] = pitch (up/down)
Tail: [0] = wag (left/right)
```

**Pin Mapping**:
```python
DEFAULT_LEGS_PINS = [2, 3, 7, 8, 0, 1, 10, 11]
# Servo hat pins:  LH-upper, LH-lower, LF-upper, LF-lower, RH-upper, RH-lower, RF-upper, RF-lower

DEFAULT_HEAD_PINS = [4, 6, 5]
# Servo hat pins:  yaw, roll, pitch

DEFAULT_TAIL_PIN = [9]
```

**Angle Conventions**:
- Positive leg angles: outward from body
- Right-side legs: angles auto-inverted by IK (odd indices)
- Head yaw: positive = left, negative = right
- Head roll: positive = tilt right, negative = tilt left
- Head pitch: positive = up, negative = down (plus 45° mechanical offset)

---

## Code Patterns

### Pattern 1: Queued Actions

```python
dog = Pidog()

# Queue multiple actions (FIFO)
dog.legs_move([[45, -45, -45, 45, 45, -45, -45, 45]], immediately=False, speed=70)
dog.legs_move([[0, 0, 0, 0, 0, 0, 0, 0]], immediately=False, speed=70)

# Wait for completion
dog.wait_legs_done()
```

### Pattern 2: Immediate Actions (Clear Buffer)

```python
# This clears buffer and executes immediately
dog.legs_move([[45, -45, -45, 45, 45, -45, -45, 45]], immediately=True, speed=90)
```

### Pattern 3: Action Dictionary

```python
# Use predefined actions
dog.do_action('stand', speed=70)
dog.wait_all_done()
dog.do_action('forward', step_count=5, speed=95)
```

### Pattern 4: Inverse Kinematics

```python
# Convert leg coordinates to angles
coords = [[0, 80], [0, 80], [0, 80], [0, 80]]  # All legs at y=0, z=80mm
angles = Pidog.legs_angle_calculation(coords)
dog.legs_move([angles], speed=70)
```

### Pattern 5: Pose Control with RPY

```python
dog.set_pose(x=0, y=0, z=85)  # Set body height
dog.set_rpy(roll=10, pitch=0, yaw=0)  # Tilt right 10°
angles = dog.pose2legs_angle()  # Compute leg angles
dog.legs_move([angles], speed=60)
```

### Pattern 6: PID Balance

```python
dog.target_rpy = [0, 0, 0]  # Desired orientation
while True:
    dog.set_rpy(roll=0, pitch=0, pid=True)  # PID correction using IMU
    angles = dog.pose2legs_angle()
    dog.legs_move([angles], immediately=True, speed=80)
    sleep(0.05)
```

---

## Gotchas

1. **Head Pitch Offset**: Head pitch has a 45° mechanical offset. Raw angle 0° = nose pointed up 45°. Use `head_move()` (not `head_move_raw()`) to avoid this.

2. **Speed vs DPS**: The `speed` parameter (0-100) affects delay between movements, NOT the servo angular velocity. DPS is fixed per component (HEAD_DPS=300, LEGS_DPS=428, TAIL_DPS=500).

3. **Immediate Flag**: `immediately=True` clears the action buffer. If you want smooth continuous motion, use `immediately=False` and queue multiple actions.

4. **Thread Safety**: Most methods are thread-safe for reading (sensors, state) but NOT for writing (calibration, direct servo writes). Do not call calibration methods during actions.

5. **Ultrasonic Process**: The ultrasonic sensor runs in a separate process, not a thread. This is to avoid I2C conflicts. If ultrasonic fails, the process crashes silently — check `read_distance()` returns -1.0.

6. **IMU Calibration**: The IMU calibrates offsets during the first 1 second of `_imu_thread`. Do not move the robot during initialization.

7. **Close Timeout**: `close()` has a 5-second timeout to return to lie position. If servos are stuck, it will raise `TimeoutError`. This prevents infinite hangs.

8. **Servo Indexing**: Leg servo indices are NOT sequential by leg. Pattern: `[LH-upper, LH-lower, LF-upper, LF-lower, RH-upper, RH-lower, RF-upper, RF-lower]`. Use action dict or IK methods to avoid manual indexing.

9. **RGB Update Rate**: RGB changes take up to 50ms to appear (20Hz update rate). Do not expect instant color changes.

10. **Sound File Lookup**: `speak()` searches 3 locations (full path, name.mp3, name.wav). It fails silently (returns False) if file not found — no exception raised.
