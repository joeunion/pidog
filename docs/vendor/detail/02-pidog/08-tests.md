# pidog: Tests

<!-- Status: COMPLETE | Iteration: 1 -->

> All 11 test files annotated
> Source: `pidog/test/`

## Test Index

| Test File | Component Tested | Hardware Required | Key Assertions |
|-----------|-----------------|-------------------|----------------|
| `angry_bark.py` | Bark animation with IK leg positions | All leg servos, head, speaker | IK `legs_angle_calculation()`, sound + motion sync |
| `cover_photo.py` | Posed photo position with rainbow RGB | All leg servos, head, RGB strip | Direct RGB `display()`, raw thread control |
| `dual_touch_test.py` | Dual touch sensor raw values and states | Touch sensors (D2, D3) | Raw GPIO values + TouchStyle enum |
| `imu_test.py` | IMU calibration and continuous read | SH3001 IMU (I2C 0x36) | Offset calibration, raw data read |
| `power_test.py` | Long-running power/endurance test | All servos, RGB, IMU, ultrasonic | Thread enumeration, continuous action |
| `rgb_strip_test.py` | RGB strip direct hardware test | RGB strip (I2C 0x74) | Direct `RGBStrip` class, manual `show()` |
| `sound_direction_test.py` | Sound direction sensor read | Sound direction (SPI, GPIO6) | Direct `SoundDirection` class |
| `stand_test.py` | Basic stand action | All leg servos | Minimal stand + close |
| `tail.py` | Tail wag action | Tail servo | `wag_tail` action, wait + close |
| `ultrasonic_iic_test.py` | Ultrasonic via I2C (smbus) | Ultrasonic (I2C 0x57) | Raw I2C read, 3-byte distance calculation |
| `ultrasonic_test.py` | Ultrasonic via GPIO (robot_hat) | Ultrasonic (D0 echo, D1 trig) | Direct `Ultrasonic` class read |

---

## Detailed Annotations

### `angry_bark.py` -- Bark Animation Test

**Purpose**: Tests a single bark animation cycle: stand, move to bark position (IK-computed), play angry sound, return to normal.

**Hardware Required**: All 12 servos, I2S speaker (for sound).

**Test Flow**:
1. Init Pidog, stand at speed 90
2. Sleep 1s
3. Compute two leg positions using IK:
   - `f1`: forward-leaning bark position (`legs_angle_calculation([[0,100],[0,100],[30,90],[30,90]])`)
   - `f2`: pulled-back position (`legs_angle_calculation([[-20,90],[-20,90],[0,90],[0,90]])`)
4. Play "angry" sound
5. Move to f1 (lunge forward) + head pitch up
6. Move to f2 (pull back) + head pitch neutral
7. Close

**Key Code**:
```python
f1 = my_dog.legs_angle_calculation([[0, 100], [0, 100], [30, 90], [30, 90]])
f2 = my_dog.legs_angle_calculation([[-20, 90], [-20, 90], [0, 90], [0, 90]])

my_dog.speak("angry")
my_dog.legs_move([f1], immediately=True, speed=95)
my_dog.head_move([h1], immediately=True, speed=95)
my_dog.wait_all_done()
my_dog.legs_move([f2], immediately=True, speed=95)
my_dog.head_move([h2], immediately=True, speed=95)
my_dog.wait_all_done()
```

**Expected Behavior**: Dog stands, lunges forward with head up while playing "angry" sound, then pulls back.

**Debugging Notes**:
- `legs_angle_calculation()` takes `[[x, y]]` per leg (4 legs), returns 8 servo angles
- Input format: `[[x, y], [x, y], [x, y], [x, y]]` for LF, RF, LH, RH
- If servos don't move: check I2C connection, calibration offsets
- If no sound: must run with `sudo` for I2S access

---

### `cover_photo.py` -- Cover Photo Pose

**Purpose**: Sets the dog into a photogenic pose with rainbow RGB strip colors. Used for product photography.

**Hardware Required**: All leg servos, head servos, RGB strip.

**Test Flow**:
1. Init Pidog
2. Define 11 RGB colors (rainbow gradient)
3. **Stop the RGB thread** manually (`my_dog.rgb_thread_run = False`)
4. Write colors directly to strip (`my_dog.rgb_strip.display(rgb_colors)`)
5. Move to posed position: head tilted, one front paw raised

**Key Code**:
```python
rgb_colors = [
    [255, 0, 0],     # LED 0: red
    [255, 69, 0],    # LED 1: orange-red
    # ... 11 colors total (rainbow)
    [255, 20, 147],  # LED 10: pink
]
# Stop RGB thread to take manual control
my_dog.rgb_thread_run = False
my_dog.rgb_strip_thread.join()

# Direct pixel write
my_dog.rgb_strip.display(rgb_colors)

# Posed leg position (one paw raised)
f_up = [[30, 60, -15, 5, 80, -45, -80, 38]]
my_dog.head_move([[-25, 20, 0]], pitch_comp=-20)
my_dog.legs_move(f_up, immediately=False, speed=80)
```

**Expected Behavior**: Dog in sit-like pose with one front paw raised, head tilted to side, rainbow LED strip.

**Debugging Notes**:
- Must stop RGB thread before using `display()` directly -- thread would overwrite
- `display()` takes a list of 11 `[R, G, B]` arrays
- No `close()` call -- this is a hold-for-photo script
- Commented-out sections show handshake animation for reference

---

### `dual_touch_test.py` -- Touch Sensor Test

**Purpose**: Tests the dual touch sensor by displaying raw GPIO values and interpreted touch style.

**Hardware Required**: Touch sensors on GPIO D2 (rear) and D3 (front).

**Test Flow**:
1. Init `DualTouch('D2', 'D3')` directly (not through Pidog)
2. Loop at 50ms: read raw left/right GPIO values + interpreted result
3. Print inline with carriage return

**Key Code**:
```python
from pidog.dual_touch import DualTouch, TouchStyle

touch = DualTouch('D2', 'D3')
while True:
    left_val = touch.touch_L.value()   # Raw GPIO 0/1
    right_val = touch.touch_R.value()  # Raw GPIO 0/1
    result = touch.read()               # Interpreted string
    style = TouchStyle(result).name     # Enum name
    print(f"\r\033[KLeft: {left_val} | Right: {right_val} | {style}({result})")
    sleep(0.05)
```

**Expected Behavior**:

| Action | Left val | Right val | Result | Style |
|--------|----------|-----------|--------|-------|
| No touch | 0 | 0 | 'N' | N |
| Touch rear | 1 | 0 | 'L' | REAR |
| Touch front | 0 | 1 | 'R' | FRONT |
| Slide rear->front | - | - | 'RS' | REAR_TO_FRONT |
| Slide front->rear | - | - | 'LS' | FRONT_TO_REAR |

**Debugging Notes**:
- Uses `DualTouch` directly (not via Pidog class) -- does not init servos/IMU
- `\033[K` clears to end of line for clean overwrite
- If values stuck at 0: check GPIO connections D2/D3
- If always 1: check for pull-up/pull-down configuration

---

### `imu_test.py` -- IMU Calibration and Test

**Purpose**: Calibrates the SH3001 IMU offsets and then displays continuous readings.

**Hardware Required**: SH3001 IMU (I2C address 0x36).

**Test Flow**:
1. Init `Sh3001` directly (not through Pidog)
2. Calibration phase: read 10 samples, average to compute offsets
3. Offset calculation: target is `[-16384, 0, 0]` for acc (gravity on X) and `[0, 0, 0]` for gyro
4. Display loop: read IMU data + apply offsets, print

**Key Code**:
```python
from pidog.sh3001 import Sh3001

config_file = '%s/.config/pidog/pidog.conf' % UserHome
imu = Sh3001(db=config_file)

# Calibration: 10 samples
for _ in range(10):
    data = imu._sh3001_getimudata()
    accData, gyroData = data
    _ax += accData[0]
    # ...

# Compute offsets (at rest, X axis points down)
imu_acc_offset[0] = round(-16384 - _ax / 10, 0)  # Expected: -16384 (1G)
imu_acc_offset[1] = round(0 - _ay / 10, 0)       # Expected: 0
imu_acc_offset[2] = round(0 - _az / 10, 0)       # Expected: 0

# Continuous read with offsets applied
while True:
    data = imu._sh3001_getimudata()
    accData, gyroData = data
    accData = [accData[i] + imu_acc_offset[i] for i in range(3)]
```

**Expected Behavior**:
- Calibration: ~1 second
- After calibration, at rest: acc ~ `[-16384, 0, 0]`, gyro ~ `[0, 0, 0]`
- Tilting the sensor changes acc values; rotating changes gyro

**Debugging Notes**:
- `_sh3001_getimudata()` returns `False` on I2C error -- check bus connection
- Config file path resolves `SUDO_USER` for correct home directory when running with sudo
- Gravity reference: 1G = -16384 raw units on the axis pointing down
- Dog must be level and stationary during calibration
- Uses private method `_sh3001_getimudata()` -- not part of public API

---

### `power_test.py` -- Power/Endurance Test

**Purpose**: Long-running test that continuously exercises servos (trot, wag tail, shake head) with RGB strip to test power consumption and stability.

**Hardware Required**: All servos, RGB strip, IMU, ultrasonic.

**Test Flow**:
1. Init Pidog
2. Print active thread count and names (diagnostic)
3. Set RGB to "boom" red
4. Stand for 54 steps (long initial stand)
5. Loop: trot 2 steps, wag tail 10 steps, shake head 5 steps, sleep 1s

**Key Code**:
```python
active_threads = threading.active_count()
print(f"active_threads: {active_threads}")
for thread in threading.enumerate():
    print(f"{thread.name}")

my_dog.rgb_strip.set_mode("boom", "red")
my_dog.do_action("stand", step_count=54, speed=SPEED)

while True:
    my_dog.do_action("trot", step_count=2, speed=SPEED)
    my_dog.do_action("wag_tail", step_count=10, speed=SPEED)
    my_dog.do_action("shake_head", step_count=5, pitch_comp=-10, speed=SPEED)
    time.sleep(1)
```

**Expected Behavior**: Dog continuously trots, wags tail, and shakes head indefinitely. Useful for:
- Battery runtime testing
- Thermal testing (servo overheating)
- Thread stability over long runs

**Debugging Notes**:
- Thread enumeration: expect 5+ daemon threads (legs, head, tail, RGB, IMU)
- Speed 100 is maximum -- tests worst-case power draw
- Commented-out sections show alternative test patterns (stand/lie cycling, distance reading)
- KeyboardInterrupt calls `close()` for cleanup
- No timeout -- runs until manual stop or battery dies

---

### `rgb_strip_test.py` -- RGB Strip Direct Test

**Purpose**: Tests the RGB strip hardware directly using `RGBStrip` class (not through Pidog).

**Hardware Required**: RGB strip (SLED1735, I2C address 0x74).

**Test Flow**:
1. Init `RGBStrip(0x74, 11)` directly
2. Cycle through 4 color/brightness/bps configurations
3. For each: set mode, call `show()` in a 3-second loop

**Key Code**:
```python
from pidog.rgb_strip import RGBStrip

strip = RGBStrip(0X74, 11)  # I2C address, LED count

mode_list = [
    {"color": "red",   "brightness": 0.8, "bps": 1},
    {"color": "green", "brightness": 0.2, "bps": 2},
    {"color": "blue",  "brightness": 0.5, "bps": 3},
    {"color": "white", "brightness": 0.5, "bps": 4},
]

for mode in mode_list:
    strip.set_mode('breath', **mode)
    start_time = time.time()
    while ((time.time() - start_time) <= 3):
        strip.show()  # Must call show() in a loop to animate
```

**Expected Behavior**:
- Red breathing at 1 Hz (bright) for 3s
- Green breathing at 2 Hz (dim) for 3s
- Blue breathing at 3 Hz (medium) for 3s
- White breathing at 4 Hz (medium) for 3s

**Debugging Notes**:
- Uses `RGBStrip` directly -- no Pidog init, no daemon thread
- **Must call `show()` in a loop** -- this is the raw API; Pidog wraps this in a thread
- If nothing happens: check I2C address 0x74 (`i2cdetect -y 1`)
- 11 LEDs, all same color in breath mode

---

### `sound_direction_test.py` -- Sound Direction Sensor Test

**Purpose**: Tests the sound direction sensor directly.

**Hardware Required**: Sound direction module (SPI0, GPIO 6 busy pin).

**Test Flow**:
1. Init `SoundDirection()` directly
2. Loop: check `isdetected()`, if true read angle

**Key Code**:
```python
from pidog.sound_direction import SoundDirection

sd = SoundDirection()
while True:
    if sd.isdetected():
        print(f"Sound detected at {sd.read()} degrees")
    sleep(0.2)
```

**Expected Behavior**: Prints direction (0-359 degrees, 20-degree resolution) when sound is detected. 0 = front of sensor.

**Debugging Notes**:
- Uses `SoundDirection` directly -- no Pidog init
- 0.2s polling rate
- Clap or tap near the sensor to trigger
- If never triggers: check SPI0 enabled, GPIO 6 connection
- `isdetected()` is edge-triggered -- cleared after `read()`

---

### `stand_test.py` -- Basic Stand Test

**Purpose**: Minimal test that makes the dog stand for 3 seconds then close.

**Hardware Required**: All leg servos.

**Test Flow**:
1. Init Pidog
2. `do_action("stand", speed=95)`
3. Sleep 3 seconds
4. `close()`

**Key Code**:
```python
my_dog = Pidog()
my_dog.do_action("stand", speed=SPEED)
sleep(3)
my_dog.close()
```

**Expected Behavior**: Dog goes from lie position to standing in ~1 second, holds for 3 seconds, lies down and closes.

**Debugging Notes**:
- Simplest possible servo test -- if this fails, check: I2C, power, calibration
- `close()` returns to lie position then terminates threads
- Speed 95 is near-maximum

---

### `tail.py` -- Tail Wag Test

**Purpose**: Tests tail wagging action.

**Hardware Required**: Tail servo (pin 9).

**Test Flow**:
1. Init Pidog
2. `do_action("wag_tail", step_count=40, speed=100)`
3. `wait_all_done()`
4. `close()`

**Key Code**:
```python
my_dog = Pidog()
my_dog.do_action("wag_tail", step_count=40, speed=SPEED)
my_dog.wait_all_done()
my_dog.close()
```

**Expected Behavior**: Tail wags back and forth 40 times at maximum speed, then stops and closes.

**Debugging Notes**:
- 40 wag cycles at speed 100 takes ~20 seconds
- Tail DPS is 500 (fastest servo)
- If no movement: check servo pin 9 connection
- Tail range: -90 to 90 degrees (wag alternates between negative and positive)

---

### `ultrasonic_iic_test.py` -- Ultrasonic I2C Test

**Purpose**: Tests the ultrasonic sensor using raw I2C protocol via smbus (bypasses robot_hat abstraction).

**Hardware Required**: Ultrasonic sensor with I2C interface (address 0x57).

**Test Flow**:
1. Init smbus on bus 1
2. Sleep 1s to avoid 121 IO Error
3. Loop: send trigger command (write byte 1), wait 200ms, read 3 bytes, compute distance

**Key Code**:
```python
import smbus

bus = smbus.SMBus(1)
time.sleep(1)  # Required to avoid IO Error 121

address = 0x57

while True:
    bus.write_byte(address, 1)             # Trigger measurement
    time.sleep(0.2)                         # Wait for echo
    data = bus.read_i2c_block_data(address, 0, 3)  # Read 3 bytes
    distance = (data[0] * 65535 + data[1] * 256 + data[2]) / 10000
    print(f"distance: {distance:.2f}")
```

**Distance Calculation**: `(byte0 * 65535 + byte1 * 256 + byte2) / 10000` -- result in centimeters.

**Expected Behavior**: Prints distance in cm at ~3Hz (0.2s echo wait + read time).

**Debugging Notes**:
- Address 0x57 is the I2C ultrasonic (not standard GPIO HC-SR04)
- **Must sleep 1s after bus init** to avoid Error 121 (device not ready)
- 200ms echo wait is the recommended minimum
- 3-byte read: MSB first, 24-bit distance value
- If Error 121: device not on bus; run `i2cdetect -y 1` to verify
- Commented-out section shows alternative using `robot_hat.I2C` wrapper

---

### `ultrasonic_test.py` -- Ultrasonic GPIO Test

**Purpose**: Tests the ultrasonic sensor using the robot_hat `Ultrasonic` class (GPIO trigger/echo, not I2C).

**Hardware Required**: Ultrasonic sensor (D1=trigger, D0=echo).

**Test Flow**:
1. Init `Ultrasonic(Pin("D1"), Pin("D0"))` directly
2. Loop: read distance, print, sleep 1s

**Key Code**:
```python
from robot_hat import Ultrasonic, Pin

ultrasonic = Ultrasonic(Pin("D1"), Pin("D0"))
while True:
    distance = ultrasonic.read()
    print(f"Distance: {distance} cm")
    time.sleep(1)
```

**Expected Behavior**: Prints distance in cm at 1Hz.

**Debugging Notes**:
- Uses GPIO trigger/echo (standard HC-SR04 protocol)
- `Pin("D1")` = trigger, `Pin("D0")` = echo
- This is the same sensor accessed differently than I2C test
- Pidog's `read_distance()` wraps this in a **separate process** to avoid I2C bus conflicts; this test runs in-process
- Commented-out section shows alternative using `Pidog.read_distance()` (separate process version)
- 1Hz poll rate is conservative; sensor supports faster reads but noise increases
