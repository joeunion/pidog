# robot-hat: Infrastructure

<!-- Status: complete | Iteration: 1 -->

> Covers: `robot.py`, `config.py`, `filedb.py`, `device.py`, `utils.py`, `modules.py`, `version.py`, `llm.py`, `stt.py`, `tts.py`, `voice_assistant.py`

## Purpose

System infrastructure for robot coordination (Robot base class), persistent storage (Config, fileDB), hardware detection (Devices), utility functions, and voice assistant shims.

## API Reference

### Robot(_Basic_class) (robot.py:16)

**Purpose**: Base class for multi-servo robots with coordinated motion, offset calibration, and preset actions.

**Thread-safe**: No (servo operations not thread-safe).

#### `__init__(pin_list: list, db=config_file, name=None, init_angles=None, init_order=None, **kwargs)`
Initialize robot with servos.

**Parameters**:
- `pin_list`: List of PWM pin numbers (e.g., [0, 1, 2, 3] or ["P0", "P1", "P2", "P3"])
- `db`: Config file path (default: `~/.config/robot-hat/robot-hat.conf`)
- `name`: Robot name for offset storage (default: "other")
- `init_angles`: List of initial servo angles (default: [0] * num_servos)
- `init_order`: Servo initialization order (default: sequential). Prevents voltage sag from simultaneous moves.

**Class Attributes**:
- `move_list = {}`: Dict of preset actions. Subclass populates with motion sequences.
- `max_dps = 428`: Maximum degrees per second (60°/0.14s at 4.8V). Speed limiter.

**Offset Storage**: Loads servo offsets from config file as `{name}_servo_offset_list`. Persists calibration across reboots.

**Init Sequence**: Creates Servo objects for all pins, then moves servos to `init_angles` in `init_order` with 150ms delays between servos.

#### `new_list(default_value: int|float) -> list`
Create list of length `pin_num` with default value. Helper for angle lists.

#### `servo_write_raw(angle_list: list) -> None`
Set servo angles directly (no offset or direction adjustment). Low-level method.

#### `servo_write_all(angles: list) -> None`
Set servo angles with origin, offset, and direction applied.

**Formula**: `output_angle = direction[i] * (origin[i] + angles[i] + offset[i])`

#### `servo_move(targets: list, speed: int = 50, bpm: int = None) -> None`
Move servos to target angles with speed control. Core motion method.

**Parameters**:
- `targets`: List of target angles for each servo
- `speed`: Move speed 0-100 (default 50). Higher = faster.
- `bpm`: Beats per minute (overrides speed if set). For rhythmic motion.

**Speed Mapping**: `total_time_ms = -9.9 * speed + 1000` (linear, 0 speed = 1000ms, 100 speed = 10ms)

**Algorithm**:
1. Calculate delta angles: `delta[i] = targets[i] - current[i]`
2. Find max delta angle
3. Calculate total move time from speed or BPM
4. If max degrees/sec exceeds `max_dps` (428), recalculate time to stay within limit
5. Divide move into 10ms steps
6. Interpolate servo positions per step
7. Execute steps with 10ms delay (adjusted for servo write time)

**DPS Limiter**: If calculated max DPS > 428, increases total time to cap at 428 DPS (lines 182-188). Prevents servo damage.

#### `do_action(motion_name: str, step: int = 1, speed: int = 50) -> None`
Execute preset action from `move_list`.

**Parameters**:
- `motion_name`: Key in `move_list` dict
- `step`: Number of times to repeat action
- `speed`: Move speed 0-100

**move_list Format**: `{"action_name": [[angles1], [angles2], ...]}` where each sublist is servo angles for one frame.

#### `set_offset(offset_list: list) -> None`
Set servo offset calibration. Clamps offsets to ±20°. Persists to config file.

**Purpose**: Compensate for servo mounting errors, linkage tolerances, etc.

#### `calibration() -> None`
Move all servos to calibration position (`calibrate_position`). For manual calibration.

#### `reset(list: list = None) -> None`
Reset servos to origin (all 0°) or specified angles.

#### `soft_reset() -> None`
Reset servos to 0° without updating internal `servo_positions` state.

**Example**:
```python
from robot_hat import Robot

class MyRobot(Robot):
    move_list = {
        "wave": [
            [0, 45, 0, 0],    # Frame 1
            [0, 90, 0, 0],    # Frame 2
            [0, 45, 0, 0],    # Frame 3
            [0, 0, 0, 0],     # Frame 4
        ]
    }

robot = MyRobot([0, 1, 2, 3], name="MyRobot", init_angles=[0, 0, 0, 0])
robot.do_action("wave", step=3, speed=50)  # Wave 3 times
robot.set_offset([2, -3, 1, 0])  # Calibrate servos
robot.reset()  # Return to home
```

---

### Config (config.py:4)

**Purpose**: INI-style configuration file management with section/option hierarchy.

**Thread-safe**: No (file I/O not locked).

#### `__init__(path: str, mode: str = None, owner: str = None, description: str = None)`
Initialize config file. Creates file/directory if not exists.

**Parameters**:
- `path`: Config file path
- `mode`: File permissions (e.g., "775")
- `owner`: File owner username
- `description`: Multi-line description (prepended as comments)

#### `__getitem__(key)`, `__setitem__(key, value)`
Dict-like access: `config['section']` returns dict of options.

#### `file_check_create(path, mode, owner, description) -> None`
Create config file and parent directories if not exist. Sets permissions and ownership via `chmod` and `chown` shell commands.

#### `_read(path: str) -> dict` (static)
Parse INI file into nested dict: `{section: {option: value}}`. Empty section name "" for options outside sections.

**Format**:
```ini
# Comment lines start with #
[section1]
option1 = value1
option2 = value2

[section2]
option3 = value3
```

#### `_write(path: str, dict: dict) -> None` (static)
Write nested dict to INI file. Preserves comments and empty lines. Adds new sections at end.

**Behavior**: Updates existing options in place, appends new options to sections, creates new sections at end.

#### `read() -> dict`
Read config file into `_dict`. Returns nested dict.

#### `write() -> None`
Write `_dict` to config file.

#### `get(section: str, option: str, default=None) -> str`
Get option value. Creates section/option with default if not exists (doesn't write to file until `write()` called).

#### `set(section: str, option: str, value) -> None`
Set option value in memory. Call `write()` to persist.

**Example**:
```python
from robot_hat.config import Config

config = Config('/opt/robot-hat/my_robot.conf', mode='775', owner='pi',
                description='My Robot Configuration\nVersion 1.0')

config.set('servos', 'count', '12')
config.set('servos', 'frequency', '50')
config.set('battery', 'voltage', '7.4')
config.write()

# Read back
config.read()
servo_count = int(config.get('servos', 'count', default='0'))
```

---

### fileDB (filedb.py:17)

**Purpose**: Simple key-value file database (flat, no sections).

**Thread-safe**: No (file I/O not locked).

#### `__init__(db: str, mode: str = None, owner: str = None)`
Initialize database file. Creates file/directory if not exists.

**File Format**: `key = value` lines, `#` for comments.

#### `file_check_create(file_path, mode, owner) -> None`
Create file and parent directories if not exist. Sets permissions and ownership.

**Default Header**: `"# robot-hat config and calibration value of robots\n\n"`

#### `get(name: str, default_value=None) -> str`
Get value by key name. Returns `default_value` if key not found.

#### `set(name: str, value) -> None`
Set key-value pair. Creates key if not exists, updates if exists.

**Example**:
```python
from robot_hat.filedb import fileDB

db = fileDB('/opt/robot-hat/calibration.db', mode='774', owner='pi')
db.set('servo_0_offset', '2.5')
db.set('servo_1_offset', '-1.3')

offset_0 = float(db.get('servo_0_offset', default_value='0'))
```

**Difference from Config**: fileDB is flat (no sections), simpler format. Config has sections/options hierarchy, INI format.

---

### Devices (device.py:3)

**Purpose**: Detect Robot HAT hardware version via device tree.

**Thread-safe**: Yes (reads static device tree).

#### `__init__() -> None`
Auto-detect HAT hardware from `/proc/device-tree/`. Populates attributes based on UUID.

**Attributes**:
- `name`: Product name (e.g., "SunFounder Robot HAT")
- `product_id`: Product ID (hex)
- `product_ver`: Product version (hex)
- `uuid`: HAT UUID string
- `vendor`: Vendor name
- `spk_en`: Speaker enable pin (12 for v5.x, 20 for v4.x)
- `motor_mode`: Motor driver mode (1 for v4.x, 2 for v5.x)

**Known UUIDs**:
- `"9daeea78-0000-076e-0032-582369ac3e02"`: Robot HAT v5.x (1902v50)

**Device Database** (lines 9-20):
```python
DEVICES = {
    "robot_hat_v4x": {
        "uuid": None,
        "speaker_enbale_pin": 20,  # Typo in original
        "motor_mode": 1,
    },
    "robot_hat_v5x": {
        "uuid": "9daeea78-0000-076e-0032-582369ac3e02",
        "speaker_enbale_pin": 12,
        "motor_mode": 2,
    }
}
```

**Fallback**: If no UUID match, defaults to v4.x values (spk_en=20, motor_mode=1).

**Example**:
```python
from robot_hat.device import Devices

device = Devices()
print(f"HAT: {device.name}")
print(f"Version: O{device.product_id}V{device.product_ver}")
print(f"Motor mode: {device.motor_mode}")
print(f"Speaker pin: {device.spk_en}")
```

**Usage in Library**: `__init__.py` creates global `__device__` instance (line 20). Other modules access via `from . import __device__`.

---

### utils.py Functions (utils.py)

**Purpose**: Utility functions for color printing, system commands, hardware control, and math.

#### `print_color(msg, end='\n', file=sys.stdout, flush=False, color='') -> None`
Print colored text using ANSI escape codes.

**Color Constants**: `GRAY`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `PURPLE`, `DARK_GREEN`, `WHITE`

**Wrappers**: `info()`, `debug()`, `warn()`, `error()` use predefined colors.

#### `set_volume(value: int) -> None`
Set system volume (0-100) via `amixer` command.

**Command**: `sudo amixer -M sset 'PCM' {value}%`

#### `command_exists(cmd: str) -> bool`, `is_installed(cmd: str) -> bool`
Check if command exists in PATH using `which`. Both are equivalent (duplicate implementations).

#### `run_command(cmd: str, user=None, group=None) -> tuple`
Run shell command, return `(status, output)`.

**Returns**: `(exit_code, stdout_string)`

#### `mapping(x, in_min, in_max, out_min, out_max) -> float`
Map value from input range to output range (Arduino-style).

**Formula**: `output = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min`

#### `get_ip(ifaces=['wlan0', 'eth0']) -> str|False`
Get IP address of network interface. Returns first found IP or False.

**Parameters**: `ifaces` can be string or list of interface names.

#### `reset_mcu() -> None`
Reset onboard MCU by toggling MCURST pin (GPIO 5). Useful if MCU stuck in I2C loop.

**Timing**: LOW 10ms → HIGH 10ms.

#### `get_battery_voltage() -> float`
Read battery voltage from ADC channel A4.

**Formula**: `voltage = adc.read_voltage() * 3` (assumes 3:1 voltage divider).

**Global ADC Object**: Reuses single `_adc_obj` to avoid repeated initialization (line 169-173).

#### `get_username() -> str`
Get current username from `$SUDO_USER` or `$LOGNAME` environment variables.

#### `set_pin(pin: int, value: bool) -> None`
Set GPIO pin value using `pinctrl` or `raspi-gpio` command.

**Command**: `{tool} set {pin} op {'dh' if value else 'dl'}`

#### `enable_speaker() -> None`, `disable_speaker() -> None`
Enable/disable speaker by setting GPIO pin high/low (pin from `__device__.spk_en`).

**Speaker Enable Side Effect**: `enable_speaker()` plays 0.5s silent audio via `play` command to fill buffer and prevent speaker overheating (line 211).

#### `check_executable(executable: str) -> bool`
Check if executable exists using `distutils.spawn.find_executable()`.

#### `redirect_error_2_null() -> int`, `cancel_redirect_error(old_stderr: int) -> None`
Redirect stderr to /dev/null (suppress library warnings). Returns old stderr fd.

#### `ignore_stderr()` (context manager)
Context manager to temporarily suppress stderr.

**Example**:
```python
from robot_hat.utils import *

# Colored logging
info("Robot started")
warn("Battery low")
error("Sensor failure")

# Map sensor to motor
sensor_value = 512  # ADC reading 0-1023
motor_speed = mapping(sensor_value, 0, 1023, -100, 100)

# Get IP for status display
ip = get_ip(['wlan0', 'eth0'])
print(f"IP: {ip}")

# Reset stuck MCU
reset_mcu()

# Check battery
voltage = get_battery_voltage()
if voltage < 6.0:
    warn(f"Battery low: {voltage}V")
```

---

### modules.py

**Purpose**: Exports Ultrasonic, ADXL345, RGB_LED, Buzzer, Grayscale_Module classes.

**Content**: See 03-sensors.md and 04-peripherals.md for class documentation.

---

### version.py

**Purpose**: Library version string.

**Content**: `__version__ = '2.5.1'`

---

### Shim / Bridge Modules

#### llm.py (llm.py)

**Purpose**: Re-export LLM classes from `sunfounder_voice_assistant.llm`.

**Exports**: `LLM`, `Deepseek`, `Grok`, `Doubao`, `Gemini`, `Qwen`, `OpenAI`, `Ollama`

**Usage**: `from robot_hat.llm import OpenAI` instead of `from sunfounder_voice_assistant.llm import OpenAI`

#### stt.py (stt.py)

**Purpose**: Re-export STT classes from `sunfounder_voice_assistant.stt`.

**Content**: `from sunfounder_voice_assistant.stt import *` (imports all STT classes, typically Vosk-based)

#### tts.py (tts.py)

**Purpose**: Wrapper for TTS classes that auto-enables speaker.

**Classes**: `Piper`, `Pico2Wave`, `Espeak`, `OpenAI_TTS`

**Behavior**: Each class wraps corresponding `sunfounder_voice_assistant.tts` class and calls `enable_speaker()` in `__init__`.

**Example**:
```python
from robot_hat.tts import Piper

tts = Piper(model="en_US-ryan-low")  # Auto-enables speaker
tts.say("Hello world")
```

#### voice_assistant.py (voice_assistant.py)

**Purpose**: Re-export VoiceAssistant from `sunfounder_voice_assistant.voice_assistant`.

**Content**: `from sunfounder_voice_assistant.voice_assistant import VoiceAssistant`

---

## Implementation Notes

**Robot Servo Initialization Order**: `init_order` parameter prevents voltage sag. Servos draw high current during initial movement. Sequential init with 150ms delays (line 92) prevents brownout.

**Robot Speed Limiter**: `max_dps = 428` enforces hardware limit (60° in 0.14s = 428 dps at 4.8V). Code recalculates move time if speed exceeds limit (lines 182-188).

**Robot Servo Positions**: Three angle systems:
1. `servo_positions`: Current positions (raw angles)
2. `origin_positions`: Home position offsets
3. `offset`: Calibration offsets (persisted in config)
4. Final angle: `direction * (origin + position + offset)`

**Config vs fileDB**: Config for hierarchical settings (INI format), fileDB for flat key-value (simpler). Config preserves comments, fileDB doesn't.

**Device Detection**: Reads `/proc/device-tree/hat*/uuid` to identify HAT version. Device tree populated by HAT EEPROM. If no HAT detected, defaults to v4.x compatibility mode.

**Utils Global State**: `_adc_obj` module-level global (line 21) for battery voltage reading. Reused to avoid ADC reinitialization overhead.

**Speaker Enable**: GPIO pin must be set high before audio output. TTS classes auto-enable. Speaker/Music classes auto-enable. Raw audio playback requires manual `enable_speaker()`.

**Shim Pattern**: llm.py, stt.py, voice_assistant.py are thin re-exports for import convenience. tts.py adds speaker enable logic on top of re-export.

## Code Patterns

**Robot Subclass with Preset Actions**:
```python
from robot_hat import Robot

class QuadrupedRobot(Robot):
    SERVOS = {
        'fl_hip': 0, 'fl_knee': 1,
        'fr_hip': 2, 'fr_knee': 3,
        'rl_hip': 4, 'rl_knee': 5,
        'rr_hip': 6, 'rr_knee': 7,
    }

    move_list = {
        "stand": [[0, -30, 0, -30, 0, -30, 0, -30]],
        "sit": [[0, 30, 0, 30, 0, 30, 0, 30]],
        "walk": [
            [10, -30, -10, -30, -10, -30, 10, -30],  # Frame 1
            [-10, -30, 10, -30, 10, -30, -10, -30],  # Frame 2
        ]
    }

    def __init__(self):
        super().__init__(
            pin_list=list(self.SERVOS.values()),
            name="Quadruped",
            init_angles=[0, 0, 0, 0, 0, 0, 0, 0],
            init_order=[0, 2, 4, 6, 1, 3, 5, 7]  # Hips first, then knees
        )

    def walk_forward(self, steps=10):
        self.do_action("walk", step=steps, speed=70)

robot = QuadrupedRobot()
robot.do_action("stand")
robot.walk_forward(steps=20)
robot.do_action("sit")
```

**Config for Multi-Robot Setup**:
```python
config = Config('/opt/robot-hat/robots.conf')

# Store robot-specific settings
config.set('robot_1', 'type', 'quadruped')
config.set('robot_1', 'servo_count', '8')
config.set('robot_1', 'name', 'Rex')

config.set('robot_2', 'type', 'arm')
config.set('robot_2', 'servo_count', '6')
config.set('robot_2', 'name', 'Arm-1')

config.write()

# Load robot settings
config.read()
robot_type = config.get('robot_1', 'type')
servo_count = int(config.get('robot_1', 'servo_count', default='0'))
```

**fileDB for Calibration Data**:
```python
db = fileDB('/opt/robot-hat/calibration.db', mode='774', owner=User)

# Save servo offsets
for i in range(12):
    db.set(f'servo_{i}_offset', str(servo_offsets[i]))

# Load servo offsets
offsets = []
for i in range(12):
    offset = float(db.get(f'servo_{i}_offset', default_value='0'))
    offsets.append(offset)
```

**Device-Specific Motor Setup**:
```python
from robot_hat import Motor, PWM, Pin
from robot_hat.device import Devices

device = Devices()
motor = Motor(PWM("P13"), Pin("D4"), mode=device.motor_mode)
# Auto-selects TC1508S (mode 1) or TC618S (mode 2) based on HAT version
```

**Colored Status Logger**:
```python
from robot_hat.utils import info, warn, error
import time

info("Robot initialization...")
time.sleep(1)

try:
    # Robot operation
    info("Operation started")
except Exception as e:
    error(f"Operation failed: {e}")
else:
    info("Operation completed successfully")
```

**Mapping Analog Sensor to Action**:
```python
from robot_hat import ADC
from robot_hat.utils import mapping

# Potentiometer on A0 controls servo angle
pot = ADC("A0")
servo = Servo("P0")

while True:
    pot_value = pot.read()  # 0-4095
    angle = mapping(pot_value, 0, 4095, -90, 90)
    servo.angle(angle)
    time.sleep(0.05)
```

## Gotchas

**Robot Servo Speed Limits**: Setting `speed=100` doesn't mean instant movement. Speed capped by `max_dps = 428`. Large angle changes still take time.

**Robot move_list Format**: Must be list of lists: `[[angles]]`. Single list `[angles]` will iterate angles individually, not as frame. Correct: `{"action": [[1,2,3]]}`, Wrong: `{"action": [1,2,3]}`.

**Config Section Names**: Empty string `""` is valid section for options outside `[section]` blocks. Access via `config['']`.

**Config Write Requirement**: `set()` modifies in-memory dict only. Must call `write()` to persist. Easy to forget.

**fileDB Value Types**: All values stored as strings. Must convert: `int(db.get(...))`, `float(db.get(...))`, `eval(db.get(...))` for lists.

**Device Detection Failure**: If no HAT detected, `Devices()` uses v4.x defaults silently. No error raised. Check `device.uuid` to verify detection.

**Device spk_en Typo**: Typo in original code: `"speaker_enbale_pin"` (line 12). Attribute correctly named `spk_en` (line 60).

**Utils reset_mcu**: Toggles GPIO 5 (MCURST). If GPIO 5 used for other purpose, reset will fail or cause side effects.

**Utils enable_speaker**: Runs `play -n trim 0.0 0.5` command (line 211). Requires `sox` package installed. Fails silently if missing.

**Utils get_battery_voltage**: Assumes 3:1 voltage divider on A4. Only works if battery connected to correct pin. Returns wrong value if divider ratio different.

**Utils Global ADC**: `_adc_obj` at module level (line 21). First call to `get_battery_voltage()` creates ADC("A4") and reuses forever. If A4 needed for other purpose, conflict.

**Shim Import Order**: TTS classes call `enable_speaker()` in `__init__`. If speaker already enabled elsewhere, redundant but harmless. If disabled afterward, TTS won't work.

**Config File Permissions**: `mode` parameter uses octal (e.g., `'775'`). Passed to `chmod` as string. Invalid modes fail silently.

**Robot Offset Clamping**: `set_offset()` clamps to ±20° (line 242). Larger offsets silently reduced. If >20° correction needed, indicates mechanical problem.

**Robot Init Angles Mismatch**: If `len(init_angles) != len(pin_list)`, raises ValueError (line 82). But if `init_order` has wrong length or indices, fails at runtime (line 90-92).

**Config _write Behavior**: Preserves comments and order for existing options. New sections appended at end. Can cause unexpected file layout after many edits.

**fileDB Line Parsing**: Assumes `key = value` format. Keys containing `=` will fail to parse correctly (line 98 splits only once).

**Utils Color Constants**: ANSI codes don't work on all terminals (e.g., Windows cmd.exe without ANSI support). Use cross-platform logging library for portability.

**Robot servo_move Timing**: Uses `time.time()` for step delays (line 202). Not real-time. Jitter from Python GIL, OS scheduling. For precise timing, use RTOS or hardware timer.
