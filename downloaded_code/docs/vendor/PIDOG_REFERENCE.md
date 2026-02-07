# PiDog Vendor Library Reference

> Dense reference for Claude context loading. Tables over prose. Every hardware detail, API signature, pin number.
> For detailed implementation docs, see `detail/` subdirectories.

---

## 1. Hardware Map

### 1.1 Servo Map (12 Servos)

| # | Name | PWM Pin | Leg/Part | Range (deg) | Default (deg) | Purpose | Max DPS | Calibration Notes |
|---|------|---------|----------|-------------|---------------|---------|---------|-------------------|
| 0 | Left hind upper | P2 | Legs[0] | -90 to 90 | 45 (lie) | Upper hind-left leg | 428 | Even index = upper |
| 1 | Left hind lower | P3 | Legs[1] | -90 to 90 | -45 (lie) | Lower hind-left leg | 428 | Odd index = lower |
| 2 | Left front upper | P7 | Legs[2] | -90 to 90 | -45 (lie) | Upper front-left leg | 428 | |
| 3 | Left front lower | P8 | Legs[3] | -90 to 90 | 45 (lie) | Lower front-left leg | 428 | |
| 4 | Right hind upper | P0 | Legs[4] | -90 to 90 | 45 (lie) | Upper hind-right leg | 428 | Right-side auto-inverted by IK |
| 5 | Right hind lower | P1 | Legs[5] | -90 to 90 | -45 (lie) | Lower hind-right leg | 428 | |
| 6 | Right front upper | P10 | Legs[6] | -90 to 90 | -45 (lie) | Upper front-right leg | 428 | |
| 7 | Right front lower | P11 | Legs[7] | -90 to 90 | 45 (lie) | Lower front-right leg | 428 | |
| 8 | Head yaw | P4 | Head[0] | -90 to 90 | 0 | Left/right head turn | 300 | Positive = left |
| 9 | Tail | P9 | Tail[0] | -90 to 90 | 0 | Wag left/right | 500 | |
| 10 | Head roll | P6 | Head[1] | -70 to 70 | 0 | Tilt left/right | 300 | Positive = tilt right |
| 11 | Head pitch | P5 | Head[2] | -45 to 30 | 0 | Up/down nod | 300 | +45deg mechanical offset; 0deg raw = nose 45deg up |

**Pin Arrays:**
```
DEFAULT_LEGS_PINS = [2, 3, 7, 8, 0, 1, 10, 11]   # LH-upper, LH-lower, LF-upper, LF-lower, RH-upper, RH-lower, RF-upper, RF-lower
DEFAULT_HEAD_PINS = [4, 6, 5]                       # yaw, roll, pitch
DEFAULT_TAIL_PIN  = [9]
```

**Servo Constants:**
```
Servo.MAX_PW = 2500    # us max pulse width
Servo.MIN_PW = 500     # us min pulse width
Servo.FREQ = 50        # Hz (20ms period)
Servo.PERIOD = 4095    # PWM period register value
Robot.max_dps = 428    # degrees/sec limit (60deg/0.14s at 4.8V)
```

**Angle Formula:** `pulse_width_us = map(angle, -90, 90, 500, 2500)`
**Output Formula:** `final_angle = direction[i] * (origin[i] + position[i] + offset[i])`

### 1.2 Sensor Table

| Sensor | Model | Bus | Address/Pin | Protocol | Data Format | Update Rate | Notes |
|--------|-------|-----|-------------|----------|-------------|-------------|-------|
| IMU | SH3001 | I2C-1 | 0x36 | I2C register | 16-bit acc+gyro, chip_id=0x61 | 500Hz default (read at 20Hz by thread) | acc +/-2g (1G=16384), gyro +/-2000deg/s |
| Ultrasonic | HC-SR04 | GPIO | D0 (echo), D1 (trig) | Trigger/Echo pulse | float cm, -1 on timeout | ~100Hz (separate process) | 2-400cm range, 20ms timeout |
| Dual Touch | Capacitive | GPIO | D2 (rear), D3 (front) | Pull-up digital | 'N','L','R','LS','RS' | Poll-based | 0.5s slide window |
| Sound Direction | TR16F064B | SPI0 + GPIO6 | SPI bus 0, GPIO6 busy | SPI 10MHz | int 0-355deg, -1 no detect | Event-driven (poll busy pin) | 20deg resolution, 18 positions |

**IMU Registers (SH3001):**

| Address | Purpose |
|---------|---------|
| 0x00-0x0D | ACC/GYRO/TEMP XYZ data (16-bit, 2 bytes/axis) |
| 0x0F | CHIP_ID (0x61) |
| 0x20-0x21 | TEMP_CONF (ODR, enable) |
| 0x22-0x26 | ACC_CONF (ODR, range +/-2/4/8/16g, filter) |
| 0x28-0x2B | GYRO_CONF (ODR, range +/-125/250/500/1000/2000deg/s, filter) |

**IMU Scaling:**
```
KP = 0.033   # PID proportional gain (balance)
KI = 0.0
KD = 0.0
ACC_RANGE = 2g, 1G = 16384 units
GYRO_RANGE = 2000 deg/s
```

### 1.3 LED Strip

| Property | Value |
|----------|-------|
| Chip | SLED1735 |
| I2C Address | 0x74 |
| LED Count | 11 |
| Update Rate | 20Hz (50ms MIN_DELAY) |
| Color Format | 8-bit RGB per LED; name ('red','cyan'), hex ('#ff0000'), RGB list [r,g,b], int (0xRRGGBB) |
| Styles | 'monochromatic', 'breath', 'boom', 'bark', 'speak', 'listen' |
| Thread | Dedicated daemon thread, `_rgb_strip_thread()` |

**Animation Modes:**
- `breath`: Gaussian x cosine (breathing pulse)
- `boom`: Gaussian spreading from center
- `speak`: Gaussian oscillating in/out
- `listen`: Gaussian sweeping left-right
- `monochromatic`: Solid color, all LEDs same
- `bark`: Quick flash pattern

**Frame Calculation:** `max_frames = int(1 / bps / 0.05)`

### 1.4 GPIO Pin Map

| Pin Label | GPIO # | Connected To | Direction | Notes |
|-----------|--------|--------------|-----------|-------|
| D0 | 17 | Ultrasonic Echo | IN | PiDog ultrasonic |
| D1 | 4 | Ultrasonic Trig | OUT | PiDog ultrasonic |
| D2 | 27 | Touch Rear | IN (pull-up) | DualTouch sw1 |
| D3 | 22 | Touch Front | IN (pull-up) | DualTouch sw2 |
| D4 | 23 | Motor direction | OUT | Motor 1 dir (unused on PiDog) |
| D5 | 24 | Motor direction | OUT | Motor 2 dir (unused on PiDog) |
| D9 | 6 | Sound Direction Busy | IN | SoundDirection busy_pin |
| D10 | 12 | General / Board Type | - | Also BOARD_TYPE detection |
| D11 | 13 | General / BLEINT | - | Bluetooth interrupt |
| D12 | 19 | General | - | |
| D13 | 16 | General / RST | - | |
| D14 | 26 | General / LED | OUT | Onboard LED |
| D15 | 20 | General / BLERST | - | Bluetooth reset |
| D16 | 21 | General | - | |
| SW/USER | 25 | Button | IN | Onboard button |
| MCURST | 5 | MCU Reset | OUT | Reset I2C MCU; toggle LOW 10ms -> HIGH 10ms |

**GPIO Aliases:** "D1" and "D7" both map to GPIO 4. "SW" and "USER" both to GPIO 25. "LED" and "D14" both to GPIO 26.

### 1.5 I2C Address Map

| Address | Device | Bus | Library | Notes |
|---------|--------|-----|---------|-------|
| 0x14 | PWM/ADC MCU (primary) | I2C-1 | robot-hat | STM32 72MHz, 20 PWM + 8 ADC |
| 0x15 | PWM/ADC MCU (alt) | I2C-1 | robot-hat | Alternate address |
| 0x16 | PWM/ADC MCU (alt) | I2C-1 | robot-hat | Alternate address |
| 0x36 | SH3001 IMU | I2C-1 | pidog | Accelerometer + gyroscope |
| 0x53 | ADXL345 | I2C-1 | robot-hat | 3-axis accelerometer (not used on PiDog) |
| 0x74 | SLED1735 RGB Strip | I2C-1 | pidog | 11 LED strip controller |

### 1.6 PWM Channel Map

| Channel | Timer | Servo/Use | Notes |
|---------|-------|-----------|-------|
| P0 | Timer 0 | Right hind upper (Legs[4]) | Timer 0: P0-P3 share prescaler/period |
| P1 | Timer 0 | Right hind lower (Legs[5]) | |
| P2 | Timer 0 | Left hind upper (Legs[0]) | |
| P3 | Timer 0 | Left hind lower (Legs[1]) | |
| P4 | Timer 1 | Head yaw (Head[0]) | Timer 1: P4-P7 share prescaler/period |
| P5 | Timer 1 | Head pitch (Head[2]) | |
| P6 | Timer 1 | Head roll (Head[1]) | |
| P7 | Timer 1 | Left front upper (Legs[2]) | |
| P8 | Timer 2 | Left front lower (Legs[3]) | Timer 2: P8-P11 share prescaler/period |
| P9 | Timer 2 | Tail (Tail[0]) | |
| P10 | Timer 2 | Right front upper (Legs[6]) | |
| P11 | Timer 2 | Right front lower (Legs[7]) | |
| P12-P13 | Timer 3 | Motor speed (unused on PiDog) | |
| P14-P15 | Timer 3 | Available | |
| P16-P17 | Timer 4 | Available | |
| P18 | Timer 5 | Available | |
| P19 | Timer 6 | Available | |

**Timer Register Map:**

| Register | Purpose |
|----------|---------|
| 0x20-0x33 | Channel 0-19 pulse width (0-65535) |
| 0x40-0x43 | Timer 0-3 prescaler (1-65535) |
| 0x44-0x47 | Timer 0-3 period (1-65535) |
| 0x50-0x52 | Timer 4-6 prescaler |
| 0x54-0x56 | Timer 4-6 period |

**PWM Clock:** 72MHz. Formula: `actual_freq = 72000000 / prescaler / period`

---

## 2. Architecture Overview

### 2.1 Three-Tier Dependency Chain

```
Layer 1: robot-hat (v2.5.1)
  Hardware abstraction: GPIO, I2C, PWM, Servo, Motor, ADC, Speaker, Music
  Config: fileDB, Config, Robot base class
  Shims: re-exports sunfounder_voice_assistant modules

Layer 2: pidog (v1.3.10a1)
  Robot control: Pidog class (extends Robot), 12 servos, IK, actions
  Sensors: SH3001 IMU, RGB strip, DualTouch, SoundDirection
  Gaits: Walk (8-section), Trot (2-section)
  LLM: Anthropic adapter, bridge modules

Layer 3: sunfounder_voice_assistant (v1.0.1)
  Orchestrator: VoiceAssistant (trigger-driven main loop)
  STT: Vosk (wake word + streaming recognition)
  TTS: Piper (default), eSpeak, pico2wave, OpenAI TTS
  LLM: OpenAI-compatible HTTP client + provider presets
  Audio: AudioPlayer (PyAudio), KeyboardInput
```

**Import Chain:**
```
pidog imports robot_hat (Robot, Servo, PWM, Pin, Music, ADC, Ultrasonic)
pidog re-exports robot_hat.llm, robot_hat.stt, robot_hat.tts, robot_hat.voice_assistant
robot_hat re-exports sunfounder_voice_assistant.llm, .stt, .tts, .voice_assistant
robot_hat.tts wraps sunfounder TTS classes + adds enable_speaker() in __init__
```

### 2.2 Threading Model

| Thread | Owner | Target | Purpose | Update Rate | Lock | Exit |
|--------|-------|--------|---------|-------------|------|------|
| `legs_thread` | Pidog | `_legs_action_thread()` | Pop legs_action_buffer, write servos | DPS-limited | `legs_thread_lock` | `exit_flag=True` |
| `head_thread` | Pidog | `_head_action_thread()` | Pop head_action_buffer, write servos | DPS-limited | `head_thread_lock` | `exit_flag=True` |
| `tail_thread` | Pidog | `_tail_action_thread()` | Pop tail_action_buffer, write servos | DPS-limited | `tail_thread_lock` | `exit_flag=True` |
| `rgb_strip_thread` | Pidog | `_rgb_strip_thread()` | Call rgb_strip.show() | 20Hz (50ms) | - | `rgb_thread_run=False` |
| `imu_thread` | Pidog | `_imu_thread()` | Read IMU, compute roll/pitch | 20Hz (50ms) | - | `exit_flag=True` |
| `wake_word_thread` | Vosk STT | `wait_for_wake_word()` | Background wake word detection | Continuous | - | `stop_listening_event` |
| `Keyboard Input Thread` | KeyboardInput | `main()` | Background stdin reading | 100ms poll | - | `running=False` |
| Audio playback threads | AudioPlayer | `play_async()` | Background audio output | Continuous | - | `stop_event` |

**Processes:**

| Process | Owner | Target | Purpose | Rate | Exit |
|---------|-------|--------|---------|------|------|
| `sensory_process` | Pidog | `sensory_process_work()` | Read ultrasonic sensor | ~100Hz (10ms) | `terminate()` |

**All Pidog threads are daemon threads** -- exit when main thread exits.

**Locks:**
- `legs_thread_lock`: Protects `legs_action_buffer`
- `head_thread_lock`: Protects `head_action_buffer`
- `tail_thread_lock`: Protects `tail_action_buffer`
- `sensory_lock`: Protects `distance` shared value (multiprocessing.Value)

### 2.3 Data Flow

```
Sensors:
  Ultrasonic (process) ---[multiprocessing.Value]--> Pidog.read_distance() --> float cm
  IMU (imu_thread) ------[self.roll, self.pitch]---> Pidog.roll, Pidog.pitch
  DualTouch (polling) ----[GPIO read]---------------> dual_touch.read() --> 'N'/'L'/'R'/'LS'/'RS'
  SoundDirection (polling)-[SPI read]---------------> ears.read() --> int degrees
  Camera (picamera2) -----[CameraPool]--------------> frame capture

Actuators:
  Brain --> do_action(name) --> ActionDict[name] --> (data, part)
                            --> legs_action_buffer / head_action_buffer / tail_action_buffer
  Action threads pop buffer --> Robot.servo_move() --> I2C --> PWM --> Servos

  Brain --> rgb_strip.set_mode() --> rgb_strip_thread --> I2C --> SLED1735

Audio Pipeline:
  Microphone --> sounddevice.RawInputStream --> Vosk KaldiRecognizer --> text
  text --> LLM (Claude API) --> response text
  response text --> parse_response() --> TTS (Piper) --> AudioPlayer --> Speaker
```

### 2.4 Key Class Hierarchy

```
_Basic_class                          # robot_hat: logging base
  +-- I2C                            # I2C bus communication
  |   +-- PWM                        # PWM signal generation
  |   |   +-- Servo                  # Servo motor control
  |   +-- ADC                        # Analog-to-digital
  |   +-- ADXL345                    # Accelerometer
  +-- Pin                            # GPIO pin
  +-- Robot                          # Multi-servo robot base (offsets, move_list, do_action)
  +-- Music                          # Tone/music via pygame
  +-- LED                            # Onboard LED

_Base                                 # voice_assistant: logger mixin
  +-- Piper                          # Neural TTS
  +-- Espeak                         # Formant TTS
  +-- Pico2Wave                      # Concatenative TTS
  +-- OpenAI_TTS                     # Cloud TTS
  +-- AudioPlayer                    # PyAudio output

LLM                                   # voice_assistant: OpenAI-compat HTTP client
  +-- OpenAI, Deepseek, Grok, etc.  # Provider presets
  +-- Ollama                         # Local LLM (overrides add_message, decode_stream)

Anthropic(LLM)                       # pidog: Claude API adapter

Pidog                                 # pidog: main robot class (uses Robot for legs/head/tail)
  .legs (Robot)                      # 8 leg servos
  .head (Robot)                      # 3 head servos
  .tail (Robot)                      # 1 tail servo
  .imu (Sh3001)
  .rgb_strip (RGBStrip)
  .dual_touch (DualTouch)
  .ears (SoundDirection)

VoiceAssistant                        # voice_assistant: trigger-driven main loop
  .llm (LLM)
  .tts (Piper)
  .stt (Vosk)

ActionDict                            # pidog: action data dictionary
ActionFlow                            # pidog: action sequencing with posture tracking
```

---

## 3. API Quick Reference

### 3.1 robot-hat Library

#### Hardware Foundation

```python
# _Basic_class (basic.py)
_Basic_class(debug_level='warning')
_Basic_class.debug_level -> int|str                        # Get/set log level (0-4 or name)

# I2C (i2c.py) -- inherits _Basic_class
I2C(address=None, bus=1)                                   # address: int or list[int]
I2C.RETRY = 5                                              # Retries on OSError
I2C.write(data: int|list|bytearray) -> None                # Write (auto-detects 1/2/3/4+ bytes)
I2C.read(length=1) -> list[int]                            # Read bytes
I2C.mem_write(data, memaddr: int) -> None                  # Write to register
I2C.mem_read(length: int, memaddr: int) -> list[int]       # Read from register
I2C.scan() -> list[int]                                    # Scan bus for devices
I2C.is_ready() -> bool                                     # Device present on bus
I2C.is_avaliable() -> bool                                 # Alias (typo in original)

# Pin (pin.py) -- inherits _Basic_class
Pin(pin: int|str, mode=None, pull=None, active_state=None)
Pin.OUT = 0x01; Pin.IN = 0x02
Pin.PULL_UP = 0x11; Pin.PULL_DOWN = 0x12; Pin.PULL_NONE = None
Pin.IRQ_FALLING = 0x21; Pin.IRQ_RISING = 0x22; Pin.IRQ_RISING_FALLING = 0x23
Pin.setup(mode, pull=None, active_state=None) -> None
Pin.value(value: bool = None) -> int                       # Get/set; auto-switches mode
Pin.on() -> int; Pin.high() -> int                         # Set HIGH
Pin.off() -> int; Pin.low() -> int                         # Set LOW
Pin.irq(handler, trigger, bouncetime=200, pull=None) -> None  # handler() no args
Pin.close() -> None; Pin.deinit() -> None; Pin.name() -> str

# PWM (pwm.py) -- inherits I2C
PWM(channel: int|str, address=None)                        # 0-19 or "P0"-"P19"
PWM.CLOCK = 72000000.0                                     # 72MHz MCU
PWM.freq(freq: float = None) -> float                      # Get/set Hz (default 50)
PWM.prescaler(prescaler: int = None) -> int                # Get/set (1-65535)
PWM.period(arr: int = None) -> int                         # Get/set (1-65535)
PWM.pulse_width(pw: int = None) -> int                     # Get/set clock ticks
PWM.pulse_width_percent(percent: float = None) -> float    # Get/set 0-100%
```

#### Actuators

```python
# Servo (servo.py) -- inherits PWM
Servo(channel: int|str, address=None)                      # Channels 0-14
Servo.MAX_PW = 2500; Servo.MIN_PW = 500; Servo.FREQ = 50; Servo.PERIOD = 4095
Servo.angle(angle: float) -> None                          # -90 to +90, clamped
Servo.pulse_width_time(pw_us: float) -> None               # 500-2500 microseconds

# Motor (motor.py)
Motor(pwm: PWM, dir: Pin|PWM, is_reversed=False, mode=None, freq=100)
Motor.speed(speed: float = None) -> float                  # -100 to +100
Motor.set_is_reverse(is_reverse: bool) -> None

# Motors (motor.py) -- dual motor control
Motors(db=config_file)
Motors.left -> Motor; Motors.right -> Motor                # Properties
Motors.speed(left: float, right: float) -> None
Motors.forward(speed) -> None; Motors.backward(speed) -> None
Motors.turn_left(speed) -> None; Motors.turn_right(speed) -> None
Motors.stop() -> None

# LED (led.py)
LED(pin='LED')
LED.on() -> None; LED.off() -> None
LED.toggle(skip_stop=False) -> None
LED.blink(times=1, delay=0.1, pause=0) -> None             # Background thread, loops forever
LED.blink_stop() -> None; LED.close() -> None

# Speaker (speaker.py) -- thread-safe
Speaker()
Speaker.play(file_path: str) -> str                        # Returns UUID task_id
Speaker.get_progress(task_id: str) -> dict                 # {position, total, progress, time, total_time, is_playing}
Speaker.pause(task_id) -> None; Speaker.resume(task_id) -> None
Speaker.stop(task_id) -> bool; Speaker.list_tasks() -> list
Speaker.enable_speaker() -> None; Speaker.disable_speaker() -> None

# Music (music.py) -- inherits _Basic_class
Music()
Music.time_signature(top=None, bottom=None) -> tuple
Music.key_signature(key=None) -> int                       # -7 to 7 or str
Music.tempo(tempo=None, note_value=QUARTER_NOTE) -> tuple
Music.beat(beat: float) -> float                           # Returns seconds
Music.note(note: int|str, natural=False) -> float          # Returns Hz
Music.sound_play(filename, volume=None) -> None            # Blocking
Music.sound_play_threading(filename, volume=None) -> None  # Non-blocking
Music.music_play(filename, loops=1, start=0.0, volume=None) -> None
Music.music_set_volume(value: int) -> None                 # 0-100
Music.music_stop() -> None; Music.music_pause() -> None; Music.music_resume() -> None
Music.play_tone_for(freq: float, duration: float) -> None
Music.get_tone_data(freq: float, duration: float) -> bytes
```

#### Sensors

```python
# ADC (adc.py) -- inherits I2C
ADC(chn: int|str, address=None)                            # 0-7 or "A0"-"A7"
ADC.read() -> int                                          # 0-4095 (12-bit)
ADC.read_voltage() -> float                                # 0-3.3V

# Ultrasonic (modules.py)
Ultrasonic(trig: Pin, echo: Pin, timeout=0.02)
Ultrasonic.SOUND_SPEED = 343.3                             # m/s
Ultrasonic.read(times=10) -> float                         # cm, -1 on timeout
Ultrasonic.close() -> None

# ADXL345 (modules.py) -- inherits I2C
ADXL345(address=0x53, bus=1)
ADXL345.X = 0; ADXL345.Y = 1; ADXL345.Z = 2
ADXL345.read(axis=None) -> float|list                      # Single axis or [x,y,z] in g

# Grayscale_Module (modules.py)
Grayscale_Module(pin0: ADC, pin1: ADC, pin2: ADC, reference=None)
Grayscale_Module.LEFT = 0; Grayscale_Module.MIDDLE = 1; Grayscale_Module.RIGHT = 2
Grayscale_Module.reference(ref=None) -> list               # Get/set thresholds
Grayscale_Module.read(channel=None) -> int|list            # ADC values
Grayscale_Module.read_status(datas=None) -> list           # [0,1,0] (0=white, 1=black)
```

#### Peripherals

```python
# RGB_LED (modules.py)
RGB_LED(r_pin: PWM, g_pin: PWM, b_pin: PWM, common=1)
RGB_LED.ANODE = 1; RGB_LED.CATHODE = 0
RGB_LED.color(color: str|int|tuple|list) -> None           # '#FF0000', 0xFF0000, (255,0,0)

# Buzzer (modules.py)
Buzzer(buzzer: PWM|Pin)                                    # PWM=passive, Pin=active
Buzzer.on() -> None; Buzzer.off() -> None
Buzzer.freq(freq: float) -> None                           # Passive only
Buzzer.play(freq: float, duration=None) -> None            # Passive only, blocking
```

#### Infrastructure

```python
# Robot (robot.py) -- inherits _Basic_class
Robot(pin_list, db=config_file, name=None, init_angles=None, init_order=None)
Robot.max_dps = 428                                        # Degrees/sec limit
Robot.move_list = {}                                       # Preset actions dict
Robot.new_list(default_value) -> list                      # Helper: [default]*pin_num
Robot.servo_write_raw(angle_list) -> None                  # Direct, no offset
Robot.servo_write_all(angles) -> None                      # With origin+offset+direction
Robot.servo_move(targets, speed=50, bpm=None) -> None      # Interpolated move
Robot.do_action(motion_name, step=1, speed=50) -> None     # Execute from move_list
Robot.set_offset(offset_list) -> None                      # Calibration, clamps +/-20deg
Robot.calibration() -> None                                # Move to calibrate_position
Robot.reset(list=None) -> None; Robot.soft_reset() -> None

# Config (config.py)
Config(path, mode=None, owner=None, description=None)
Config.get(section, option, default=None) -> str
Config.set(section, option, value) -> None
Config.read() -> dict; Config.write() -> None

# fileDB (filedb.py)
fileDB(db, mode=None, owner=None)
fileDB.get(name, default_value=None) -> str                # All values are strings
fileDB.set(name, value) -> None

# Devices (device.py)
Devices()                                                  # Auto-detects HAT version
# Attrs: name, product_id, product_ver, uuid, vendor, spk_en, motor_mode
# v4.x: spk_en=20, motor_mode=1. v5.x: spk_en=12, motor_mode=2

# utils.py functions
set_volume(value: int) -> None                             # 0-100, via amixer
mapping(x, in_min, in_max, out_min, out_max) -> float      # Linear map
get_ip(ifaces=['wlan0','eth0']) -> str|False
reset_mcu() -> None                                        # Toggle GPIO5 LOW->HIGH
get_battery_voltage() -> float                             # ADC A4 * 3 (voltage divider)
enable_speaker() -> None; disable_speaker() -> None
```

### 3.2 pidog Library

#### Pidog Core

```python
# Pidog (pidog.py)
Pidog(leg_pins=DEFAULT_LEGS_PINS, head_pins=DEFAULT_HEAD_PINS, tail_pin=DEFAULT_TAIL_PIN,
      leg_init_angles=None, head_init_angles=None, tail_init_angle=None)

# Constants
Pidog.HEAD_DPS = 300; Pidog.LEGS_DPS = 428; Pidog.TAIL_DPS = 500
Pidog.LEG = 42; Pidog.FOOT = 76; Pidog.BODY_LENGTH = 117; Pidog.BODY_WIDTH = 98  # mm
Pidog.HEAD_PITCH_OFFSET = 45
Pidog.HEAD_YAW_MIN = -90; Pidog.HEAD_YAW_MAX = 90
Pidog.HEAD_ROLL_MIN = -70; Pidog.HEAD_ROLL_MAX = 70
Pidog.HEAD_PITCH_MIN = -45; Pidog.HEAD_PITCH_MAX = 30

# Servo Control
Pidog.legs_move(target_angles: list[list], immediately=True, speed=50) -> None   # Thread-safe
Pidog.head_move(target_yrps: list[list], roll_comp=0, pitch_comp=0, immediately=True, speed=50) -> None
Pidog.head_move_raw(target_angles: list[list], immediately=True, speed=50) -> None
Pidog.tail_move(target_angles: list[list], immediately=True, speed=50) -> None
Pidog.legs_simple_move(angles_list: list, speed=90) -> None  # Direct, non-threaded

# Actions
Pidog.do_action(action_name: str, step_count=1, speed=50, pitch_comp=0) -> None

# Stop/Lie
Pidog.stop_and_lie(speed=85) -> None                       # Emergency stop, return to lie
Pidog.legs_stop() -> None; Pidog.head_stop() -> None; Pidog.tail_stop() -> None
Pidog.body_stop() -> None                                  # All three

# Wait/Status
Pidog.wait_legs_done() -> None; Pidog.wait_head_done() -> None
Pidog.wait_tail_done() -> None; Pidog.wait_all_done() -> None
Pidog.is_legs_done() -> bool; Pidog.is_head_done() -> bool
Pidog.is_tail_done() -> bool; Pidog.is_all_done() -> bool

# Inverse Kinematics
Pidog.legs_angle_calculation(coords: list) -> list         # classmethod; [[y,z]*4] -> 8 angles
Pidog.pose2legs_angle() -> list                            # Current pose -> 8 angles
Pidog.set_pose(x=None, y=None, z=None) -> None
Pidog.set_rpy(roll=None, pitch=None, yaw=None, pid=False) -> None
Pidog.set_legs(legs_list: list) -> None                    # [[y,z]*4]

# Sensors
Pidog.read_distance() -> float                             # cm, -1 on timeout
Pidog.roll -> float; Pidog.pitch -> float                  # Degrees, 20Hz update
Pidog.accData -> list; Pidog.gyroData -> list               # Raw IMU
Pidog.dual_touch.read() -> str                             # 'N','L','R','LS','RS'
Pidog.ears.isdetected() -> bool; Pidog.ears.read() -> int  # 0-355 degrees

# RGB
Pidog.rgb_strip.set_mode(style, color, bps=1, brightness=1) -> None
Pidog.rgb_strip.close() -> None

# Audio
Pidog.speak(name: str, volume=100) -> None|False           # Non-blocking sound effect
Pidog.speak_block(name: str, volume=100) -> None|False     # Blocking sound effect

# Calibration
Pidog.set_leg_offsets(cali_list, reset_list=None) -> None
Pidog.set_head_offsets(cali_list) -> None
Pidog.set_tail_offset(cali_list) -> None

# Lifecycle
Pidog.close() -> None                                      # Graceful shutdown (5s timeout)
Pidog.close_all_thread() -> None                           # Set exit_flag only
Pidog.get_battery_voltage() -> float
```

#### Actions System

```python
# ActionDict (actions_dictionary.py)
ActionDict()
ActionDict.__getitem__(item: str) -> tuple                 # Returns (data, part)
ActionDict.set_height(height: int) -> None                 # 20-95 mm
ActionDict.set_barycenter(offset: int) -> None             # -60 to 60 mm

# ActionFlow (action_flow.py)
ActionFlow(dog_obj: Pidog)
ActionFlow.run(action: str) -> None                        # Execute from OPERATIONS
ActionFlow.add_action(*actions: str) -> None               # Queue actions
ActionFlow.set_status(status: ActionStatus) -> None
ActionFlow.wait_actions_done() -> None
ActionFlow.start() -> None; ActionFlow.stop() -> None
ActionFlow.change_poseture(poseture: Posetures) -> None    # STAND/SIT/LIE
ActionFlow.set_head_pitch_init(pitch: float) -> None

# Enums
Posetures.STAND = 0; Posetures.SIT = 1; Posetures.LIE = 2
ActionStatus.STANDBY = 'standby'; ActionStatus.THINK = 'think'
ActionStatus.ACTIONS = 'actions'; ActionStatus.ACTIONS_DONE = 'actions_done'
```

#### Locomotion

```python
# Walk (walk.py)
Walk(fb: int, lr: int)                                     # FORWARD=1/BACKWARD=-1, LEFT=-1/STRAIGHT=0/RIGHT=1
Walk.get_coords() -> list                                  # 193 frames of [[y,z]*4]
Walk.SECTION_COUNT = 8; Walk.STEP_COUNT = 6
Walk.LEG_STEP_HEIGHT = 20; Walk.LEG_STEP_WIDTH = 80        # mm
Walk.Z_ORIGIN = 80; Walk.TURNING_RATE = 0.3

# Trot (trot.py)
Trot(fb: int, lr: int)                                     # Same direction constants as Walk
Trot.get_coords() -> list                                  # 6 frames of [[y,z]*4]
Trot.SECTION_COUNT = 2; Trot.STEP_COUNT = 3
Trot.LEG_STEP_HEIGHT = 20; Trot.LEG_STEP_WIDTH = 100       # mm
Trot.Z_ORIGIN = 80; Trot.TURNING_RATE = 0.5
```

#### Sensors & Peripherals (pidog)

```python
# Sh3001 (sh3001.py)
Sh3001(db='sh3001.config')                                 # I2C 0x36
Sh3001.sh3001_getimudata(aram, axis) -> data               # 'acc'/'gyro'/'all', 'x'/'y'/'z'/'xyz'
Sh3001.sh3001_gettempdata() -> float                       # Celsius
Sh3001.calibrate(aram, stopfunc, waitfunc) -> None
Sh3001.set_offset(offset_list) -> None

# RGBStrip (rgb_strip.py)
RGBStrip(addr=0x74, nums=8)                                # PiDog uses 11 LEDs
RGBStrip.set_mode(style='breath', color='white', bps=1, brightness=1) -> None
RGBStrip.show() -> None                                    # Called by thread
RGBStrip.display(image: list) -> None                      # Raw RGB: [[r,g,b]*11]
RGBStrip.close() -> None

# SoundDirection (sound_direction.py)
SoundDirection(busy_pin=6)                                 # SPI0, GPIO6
SoundDirection.read() -> int                               # 0-355 degrees, -1 if none
SoundDirection.isdetected() -> bool                        # True if busy pin low
SoundDirection.close() -> None

# DualTouch (dual_touch.py)
DualTouch(sw1='D2', sw2='D3')                              # Pull-up GPIO
DualTouch.read() -> str                                    # 'N'/'L'/'R'/'LS'/'RS'
DualTouch.close() -> None
```

#### LLM Integration (pidog)

```python
# Anthropic (anthropic_llm.py) -- inherits sunfounder LLM
Anthropic(api_key=None, model='claude-sonnet-4-20250514', max_tokens=1024)
Anthropic.add_message(role: str, content: str, image_path=None) -> None
Anthropic.chat(stream=False, **kwargs) -> requests.Response
Anthropic.decode_stream_response(line: str) -> str|None
Anthropic._non_stream_response(response) -> str
```

### 3.3 voice-assistant Library

#### VoiceAssistant Core

```python
VoiceAssistant(
    llm: LLM,                         # Required
    name='Buddy',                      # Substituted into instructions via {name}
    with_image=True,                   # Init picamera2
    tts_model='en_US-ryan-low',        # Piper model
    stt_language='en-us',              # Vosk language
    keyboard_enable=True,              # Stdin trigger
    wake_enable=True,                  # Wake word trigger
    wake_word=['hey buddy'],           # Wake phrases
    answer_on_wake='Hi there',         # Spoken on wake
    welcome='Hi, I\'m Buddy...',       # Spoken on start
    instructions='You are a helpful assistant, named {name}.',
    disable_think=False,               # Skip chain-of-thought
    round_cooldown=1.0                 # Seconds between rounds
)

# Lifecycle
VoiceAssistant.run() -> None                               # Entry point, blocks
VoiceAssistant.main() -> None                              # Core event loop
VoiceAssistant.listen() -> str|None                        # Record after wake
VoiceAssistant.think(text: str, disable_image=False) -> str  # LLM call
VoiceAssistant.capture_image(path: str) -> None
VoiceAssistant.init_camera() -> None; VoiceAssistant.close_camera() -> None

# Triggers
VoiceAssistant.add_trigger(fn: Callable[[], tuple[bool, bool, str]]) -> None
VoiceAssistant.trigger_wake_word() -> tuple[bool, bool, str]
VoiceAssistant.trigger_keyboard_input() -> tuple[bool, bool, str]

# Hooks (all no-op by default, override in subclass)
VoiceAssistant.on_start() -> None
VoiceAssistant.on_wake() -> None
VoiceAssistant.on_heard(text: str) -> None
VoiceAssistant.before_listen() -> None
VoiceAssistant.after_listen(stt_result: str) -> None
VoiceAssistant.before_think(text: str) -> None
VoiceAssistant.after_think(text: str) -> None
VoiceAssistant.parse_response(text: str) -> str            # Return '' to skip TTS
VoiceAssistant.before_say(text: str) -> None
VoiceAssistant.after_say(text: str) -> None
VoiceAssistant.on_finish_a_round() -> None
VoiceAssistant.on_stop() -> None
```

#### STT (Vosk)

```python
Vosk(language=None, samplerate=None, device=None, log=None)

# Core
Vosk.init() -> None                                        # Load/download model
Vosk.is_ready() -> bool                                    # Recognizer loaded
Vosk.set_language(language: str, init=True) -> None
Vosk.set_wake_words(wake_words: list[str]) -> None
Vosk.close() -> None

# Listening
Vosk.listen(stream=False, device=None, samplerate=None, timeout=None) -> str|Generator
  # Stream yields: {"done": bool, "partial": str, "final": str}
Vosk.listen_until_silence(silence_threshold=2.0) -> str    # VAD-like
Vosk.stop_listening() -> None

# Wake Word
Vosk.start_listening_wake_words() -> None                  # Background thread
Vosk.is_waked() -> bool
Vosk.heard_wake_word() -> bool                             # Single-shot check (blocks)
Vosk.wait_until_heard(wake_words=None) -> str              # Blocking loop

# Model Management
Vosk.update_model_list() -> None                           # Network fetch
Vosk.download_model(lang, progress_callback=None, max_retries=5) -> None
Vosk.is_model_downloaded(lang) -> bool
Vosk.get_model_path(lang) -> Path                          # /opt/vosk_models/{name}

# File STT
Vosk.stt(filename: str, stream=False) -> str|Generator
```

**Audio Format:** 16-bit int16, mono, 1024 block size, device default sample rate (typically 16kHz)

#### TTS Engines

```python
# Piper (tts/piper.py) -- default engine
Piper(model=None)
Piper.say(text: str, stream=True) -> None                  # Speak to speaker
Piper.tts(text: str, file: str) -> None                    # Synthesize to WAV
Piper.stream(text: str) -> None                            # Stream via AudioPlayer
Piper.set_model(model: str) -> None                        # Load/download model
Piper.download_model(model, force=False, progress_callback=None) -> None
Piper.is_model_downloaded(model) -> bool
Piper.available_models(country=None) -> list[str]
Piper.available_countrys() -> list[str]
Piper.get_language() -> str

# Espeak (tts/espeak.py)
Espeak()                                                   # Requires espeak binary
Espeak.say(words: str) -> None                             # Synth to /tmp then play
Espeak.tts(words: str, file_path: str) -> None
Espeak.set_amp(amp: int) -> None                           # 0-200, default 100
Espeak.set_speed(speed: int) -> None                       # 80-260 WPM, default 175
Espeak.set_gap(gap: int) -> None                           # 0-200, default 5
Espeak.set_pitch(pitch: int) -> None                       # 0-99, default 50

# Pico2Wave (tts/pico2wave.py)
Pico2Wave(lang=None)                                       # Requires pico2wave binary
Pico2Wave.say(words: str) -> None                          # FIRE-AND-FORGET (background &)
Pico2Wave.set_lang(lang: str) -> None                      # en-US,en-GB,de-DE,es-ES,fr-FR,it-IT

# OpenAI_TTS (tts/openai_tts.py)
OpenAI_TTS(voice=Voice.ALLOY, model=Model.GPT_4O_MINI_TTS, api_key=None, gain=1.5)
OpenAI_TTS.say(words: str, instructions=None, stream=True) -> None
OpenAI_TTS.tts(words, output_file='/tmp/openai_tts.wav', instructions=None, stream=False) -> bool
OpenAI_TTS.set_voice(voice) -> None; OpenAI_TTS.set_model(model) -> None
OpenAI_TTS.set_api_key(api_key: str) -> None               # Rejects None
OpenAI_TTS.set_gain(gain: float) -> None                   # Rejects int
```

#### LLM Base

```python
LLM(api_key=None, model=None, url=None, base_url=None, max_messages=20, authorization=Authorization.BEARER)

# Config
LLM.set_api_key(api_key: str) -> None
LLM.set_base_url(base_url: str) -> None                    # Appends /chat/completions
LLM.set_model(model: str) -> None
LLM.set_max_messages(max_messages: int) -> None
LLM.set(name: str, value) -> None                          # Extra params (temperature, etc.)
LLM.set_instructions(instructions: str) -> None            # Adds system message (ADDITIVE)
LLM.set_welcome(welcome: str) -> None                      # Adds assistant message

# Messages
LLM.add_message(role, content, image_path=None) -> None    # FIFO eviction at max_messages
LLM.get_base64_from_image(path) -> str
LLM.get_base_64_url_from_image(path) -> str

# Chat
LLM.prompt(msg: str|list, image_path=None, stream=False, **kwargs) -> str|Generator
LLM.chat(stream=False, **kwargs) -> requests.Response
LLM.decode_stream_response(line: str) -> str|None          # OpenAI SSE format
LLM._stream_response(response) -> Generator[str]
LLM._non_stream_response(response) -> str                  # Does NOT save to history

# Provider Presets (all inherit LLM, set base_url)
OpenAI(api_key, model)           # https://api.openai.com/v1
Deepseek(api_key, model)        # https://api.deepseek.com
Grok(api_key, model)            # https://api.x.ai/v1
Doubao(api_key, model)          # https://ark.cn-beijing.volces.com/api/v3
Qwen(api_key, model)            # https://dashscope.aliyuncs.com/compatible-mode/v1
Gemini(api_key, model)          # https://generativelanguage.googleapis.com/v1beta/openai
Ollama(ip='localhost', model)   # http://{ip}:11434/api/chat (overrides add_message, decode_stream)
```

#### Audio Internals

```python
# AudioPlayer (_audio_player.py)
AudioPlayer(sample_rate=22050, channels=1, gain=1.0, format=paInt16,
            timeout=None, enable_buffering=True, buffer_size=8192)
AudioPlayer.play(audio_bytes: bytes) -> None               # With optional buffering
AudioPlayer.flush_buffer() -> None                         # Play remaining buffer (double-gain bug)
AudioPlayer.play_file(file_path: str, chunk_size=4096) -> None  # WAV only
AudioPlayer.play_async(audio_bytes: bytes) -> None         # Background thread
AudioPlayer.play_file_async(file_path, chunk_size=1024) -> None
AudioPlayer.stop() -> None
AudioPlayer.set_gain(gain: float) -> None; AudioPlayer.get_gain() -> float
AudioPlayer.is_available() -> bool                         # Static: PyAudio importable?
# Context manager: __enter__ opens stream, __exit__ cleans up

# KeyboardInput (_keyboard_input.py)
KeyboardInput()
KeyboardInput.start() -> None                              # Background stdin reader
KeyboardInput.is_result_ready() -> bool
KeyboardInput.stop() -> None
```

---

## 4. Actions Catalog

### 4.1 ActionDict Preset Actions (Leg Poses)

| Action Name | Part | Angles / Generator | Frames | Description |
|-------------|------|--------------------|--------|-------------|
| `stand` | legs | IK computed (height=95mm, barycenter=-15mm) | 1 | Standing position |
| `sit` | legs | `[30,60,-30,-60,80,-45,-80,45]` | 1 | Sitting position |
| `lie` | legs | `[45,-45,-45,45,45,-45,-45,45]` | 1 | Lying down |
| `lie_with_hands_out` | legs | `[-60,60,60,-60,45,-45,-45,45]` | 1 | Lying, front paws extended |
| `forward` | legs | Walk gait (FORWARD, STRAIGHT) | 193 | One walk cycle forward |
| `backward` | legs | Walk gait (BACKWARD, STRAIGHT) | 193 | One walk cycle backward |
| `turn_left` | legs | Walk gait (FORWARD, LEFT) | 193 | One walk cycle turning left |
| `turn_right` | legs | Walk gait (FORWARD, RIGHT) | 193 | One walk cycle turning right |
| `trot` | legs | Trot gait (FORWARD, STRAIGHT) | 6 | One trot cycle |
| `stretch` | legs | `[-80,70,80,-70,-20,64,20,-64]` | 1 | Stretch pose |
| `push_up` | legs | 2 positions (up, down) | 2 | Push-up motion |
| `doze_off` | legs | Slow dozing animation | 400+ | Head bob while dozing |
| `half_sit` | legs | `[25,25,-25,-25,64,-45,-64,45]` | 1 | Half-sitting (used in howling) |

### 4.2 ActionDict Head Actions

| Action Name | Part | Head YRP | Frames | Description |
|-------------|------|----------|--------|-------------|
| `nod_lethargy` | head | Sine roll+pitch | 21 | Lethargic nodding |
| `shake_head` | head | Sine yaw | 21 | Head shake left-right |
| `tilting_head_left` | head | `[0,-25,15]` | 1 | Tilt head left |
| `tilting_head_right` | head | `[0,25,20]` | 1 | Tilt head right |
| `tilting_head` | head | Alternating tilt | 40 | Alternate tilt left-right |
| `head_bark` | head | Quick up-down | 4 | Head motion during barking |
| `head_up_down` | head | Nod up-down | 3 | Head nod |

### 4.3 ActionDict Tail Actions

| Action Name | Part | Tail Angles | Frames | Description |
|-------------|------|-------------|--------|-------------|
| `wag_tail` | tail | `[[-30],[30]]` | 2 | Wag tail left-right |

### 4.4 ActionFlow OPERATIONS (Complex Actions)

| Action Name | Required Posture | Function | Before | After | Description |
|-------------|-----------------|----------|--------|-------|-------------|
| `forward` | STAND | `do_action('forward')` speed=98 | - | - | Walk forward |
| `backward` | STAND | `do_action('backward')` speed=98 | - | - | Walk backward |
| `turn left` | STAND | `do_action('turn_left')` speed=98 | - | - | Turn left |
| `turn right` | STAND | `do_action('turn_right')` speed=98 | - | - | Turn right |
| `stop` | - | No-op | - | - | Stop movement |
| `lie` | LIE | `do_action('lie')` speed=70 | - | - | Lie down |
| `stand` | STAND | `do_action('stand')` speed=65 | - | - | Stand up |
| `sit` | SIT | `do_action('sit')` speed=70 | - | - | Sit down |
| `bark` | - | `bark()` | - | - | Single bark + head tilt |
| `bark harder` | STAND | `bark_action()` | - | attack_posture | Aggressive bark + lunge |
| `pant` | - | `pant()` | - | - | Panting animation |
| `wag tail` | - | `do_action('wag_tail')` speed=100 | - | wag again | Wag tail |
| `shake head` | - | `shake_head()` | - | - | Shake head left-right |
| `stretch` | SIT | `stretch()` | - | sit | Play bow stretch |
| `doze off` | LIE | `do_action('doze_off')` speed=95 | - | - | Dozing animation |
| `push up` | STAND | `push_up()` | - | - | Push-up motion |
| `howling` | SIT | `howling()` | - | sit | Howl with RGB + sound |
| `twist body` | STAND | `body_twisting()` | - | sit | Body twist |
| `scratch` | SIT | `scratch()` | - | - | Scratch with hind leg |
| `handshake` | SIT | `hand_shake()` | - | - | Raise paw, shake 8x |
| `high five` | SIT | `high_five()` | - | - | Raise paw high, slam |
| `lick hand` | SIT | `lick_hand()` | - | - | Lick extended paw |
| `waiting` | - | `waiting()` | - | - | Idle head movement (speed 5) |
| `feet shake` | SIT | `feet_shake()` | - | - | Shake front feet |
| `relax neck` | SIT | `relax_neck()` | - | - | Circular head motion |
| `nod` | SIT | `nod()` | - | - | Nod head up-down |
| `think` | SIT | `think()` | - | - | Head tilted up-left |
| `recall` | SIT | `recall()` | - | - | Head tilted up-right |
| `fluster` | SIT | `fluster()` | - | - | Rapid head shake (speed 100) |
| `surprise` | SIT | `surprise()` | - | - | Rapid body raise + head up |

### 4.5 Preset Action Functions (preset_actions.py)

| Function | Parameters | Duration | Key Behavior |
|----------|-----------|----------|--------------|
| `scratch(my_dog)` | - | ~3s | Sit, raise right paw, tilt head, 10 scratches (speed 94) |
| `hand_shake(my_dog)` | - | ~2s | Raise left paw, 8 shake cycles (speed 90) |
| `high_five(my_dog)` | - | ~1.5s | Raise paw high, slam down (speed 94) |
| `pant(my_dog, yrp, pitch_comp, speed, volume)` | speed=80, vol=100 | ~1s | Play 'pant' sound, 6 head cycles |
| `body_twisting(my_dog)` | - | ~2s | Complex leg movements (speed 50) |
| `bark_action(my_dog, yrp, speak, volume)` | vol=100 | ~0.3s | Body lunge forward + head up + sound |
| `shake_head(my_dog, yrp)` | - | ~0.5s | 3-position head movement (speed 92) |
| `shake_head_smooth(my_dog, pitch_comp, amplitude, speed)` | amp=40, speed=90 | ~1s | 15-frame sine wave |
| `bark(my_dog, yrp, pitch_comp, roll_comp, volume)` | vol=100 | ~1s | Head up 25deg, 'single_bark_1' sound |
| `push_up(my_dog, speed)` | speed=80 | ~2s | Head down/up + push_up action |
| `howling(my_dog, volume)` | vol=100 | ~4s | Sit, head up, RGB cyan speak, 'howling' 2.34s |
| `attack_posture(my_dog)` | - | ~0.2s | Aggressive stance (speed 85) |
| `lick_hand(my_dog)` | - | ~2s | Sit, raise paw, head to paw, 3 wiggle cycles |
| `waiting(my_dog, pitch_comp)` | - | Variable | Random head position from 4 options (speed 5) |
| `feet_shake(my_dog, step)` | step=random 1-2 | ~1-2s | Random front leg pattern |
| `sit_2_stand(my_dog, speed)` | speed=75 | ~1s | 2-stage smooth transition; speed must be >70 |
| `relax_neck(my_dog, pitch_comp)` | pitch_comp=-35 | ~2s | 21-frame circular + 10-frame tilt |
| `nod(my_dog, pitch_comp, amplitude, step, speed)` | amp=20, step=2, speed=90 | ~1s/step | Cosine wave pitch |
| `think(my_dog, pitch_comp)` | - | ~0.3s | Head to [20,-15,15+comp] (speed 80) |
| `recall(my_dog, pitch_comp)` | - | ~0.3s | Head to [-20,15,15+comp] (speed 80) |
| `fluster(my_dog, pitch_comp)` | - | ~1s | 5 cycles of 4-pos head shake (speed 100) |
| `alert(my_dog, pitch_comp)` | - | ~3s | Raise body, scan left (1s), right (1s), center |
| `surprise(my_dog, pitch_comp, status)` | status='sit' | ~2s | Rapid body raise, head up, 1s pause |
| `stretch(my_dog)` | - | ~2s | Front legs extend, head raised, 5 oscillations |

### 4.6 Action Flow System

**Execution Flow:**
1. `add_action('scratch')` -- enqueue
2. `action_handler` thread pops from queue, calls `run('scratch')`
3. `run()` checks posture requirement, calls `change_poseture()` if needed
4. Executes "before" callback (if defined)
5. Executes main function
6. Waits for completion (`dog.wait_all_done()`)
7. Executes "after" callback (if defined)
8. Returns to STANDBY when queue empty

**Standby Behavior:** When idle, randomly executes 'waiting' or 'feet_left_right' every 2-6 seconds.

**Posture Transitions:** `change_poseture()` uses `sit_2_stand()` for SIT->STAND (smooth 2-stage). Other transitions use direct `do_action()`.

---

## 5. Gait Reference

### 5.1 Walk Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SECTION_COUNT` | 8 | 4 legs x 2 (step + break) |
| `STEP_COUNT` | 6 | Frames per section |
| `LEG_ORDER` | `[1,0,4,0,2,0,3,0]` | 1-indexed; 0=break. Sequence: LH, break, RF, break, LF, break, RH, break |
| `LEG_STEP_HEIGHT` | 20 mm | Vertical lift during step |
| `LEG_STEP_WIDTH` | 80 mm | Horizontal stride length |
| `CENTER_OF_GRAVIRTY` | -15 mm | Body COM offset |
| `Z_ORIGIN` | 80 mm | Standing height |
| `TURNING_RATE` | 0.3 | Inside leg stride scale (30%) |
| `LEG_POSITION_OFFSETS` | `[-10,-10,20,20]` | Per-leg forward/back bias (mm) |
| Total frames per cycle | 193 | Includes breaks and interpolation |
| Ground contact | 3-4 legs | Always stable |

**Y-motion:** Cosine wave (ease-in/out). `y = origin + (stride * (cos(theta) - fb) / 2 * fb)`
**Z-motion:** Linear rise to `Z_ORIGIN - STEP_HEIGHT`, then return.

### 5.2 Trot Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SECTION_COUNT` | 2 | 2 diagonal pairs |
| `STEP_COUNT` | 3 | Frames per section |
| `LEG_RAISE_ORDER` | `[[1,4],[2,3]]` | 1-indexed diagonal pairs: LH+RF, then LF+RH |
| `LEG_STEP_HEIGHT` | 20 mm | Vertical lift |
| `LEG_STEP_WIDTH` | 100 mm | Stride length (larger than walk) |
| `CENTER_OF_GRAVITY` | -17 mm | More rearward than walk |
| `Z_ORIGIN` | 80 mm | Standing height |
| `TURNING_RATE` | 0.5 | Inside leg stride scale (50%, higher than walk) |
| `LEG_STAND_OFFSET` | 5 mm | Leg stance width |
| Total frames per cycle | 6 | ~40x faster than walk per frame |
| Ground contact | 2 legs | Diagonal pair (requires speed >80 for stability) |

### 5.3 IK Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `LEG` | 42 mm | Upper leg segment length |
| `FOOT` | 76 mm | Lower leg segment length |
| `BODY_LENGTH` | 117 mm | Front to back |
| `BODY_WIDTH` | 98 mm | Left to right |
| Max leg extension | 118 mm | LEG + FOOT |
| Min leg extension | 34 mm | abs(LEG - FOOT) |
| Default standing height | 80 mm | Z_ORIGIN (well within range) |

**Leg Index Mapping:**
- Leg 1 = Left Hind (LH) = servo indices [0, 1]
- Leg 2 = Left Front (LF) = servo indices [2, 3]
- Leg 3 = Right Hind (RH) = servo indices [4, 5]
- Leg 4 = Right Front (RF) = servo indices [6, 7]

### 5.4 Speed Control

**Speed parameter (0-100)** affects inter-frame delay, NOT DPS:
- `speed=100`: ~5ms delay + servo DPS limit
- `speed=50`: ~30ms delay
- `speed=0`: ~50ms delay

**Speed formula:** `total_time_ms = -9.9 * speed + 1000`

**Real-world estimates** (at speed=100, ~10ms/frame):
- Walk: 0.41 mm/frame = ~4.1 cm/sec
- Trot: 16.67 mm/frame = ~167 cm/sec (theoretical, servo-limited by LEGS_DPS=428)

---

## 6. Audio Pipeline

### 6.1 TTS Engines Comparison

| Engine | Type | Quality | Latency | Offline | Streaming | Dependencies | Model Path |
|--------|------|---------|---------|---------|-----------|--------------|------------|
| **Piper** | Neural ONNX | High | 200-500ms first chunk | Yes | Yes | piper, onnxruntime, PyAudio | /opt/piper_models/ |
| **eSpeak** | Formant | Low (robotic) | <50ms | Yes | No | espeak binary | System binary |
| **pico2wave** | Concatenative | Medium | ~100ms | Yes | No | pico2wave binary, aplay | System binary |
| **OpenAI TTS** | Cloud neural | Very High | 500-1000ms (network) | No | Yes | requests, PyAudio, API key | N/A |

**Default for PiDog:** Piper with model `en_US-ryan-low`

### 6.2 Audio Format Requirements

| Property | STT (Vosk) | TTS (Piper) | Speaker (robot-hat) |
|----------|-----------|-------------|---------------------|
| Sample Rate | Device default (16kHz typical) | Model-dependent (22050 typical) | 44100 (Music) |
| Bit Depth | 16-bit int16 | 16-bit int16 | 16-bit int16 (Music FORMAT) |
| Channels | 1 (mono) | 1 (mono) | 1 (mono, Music CHANNELS) |
| Block Size | 1024 frames | Variable chunks | 1024 frames (Speaker) |
| Format | Raw PCM via sounddevice | WAV or streaming bytes | WAV, FLAC, OGG, MP3, M4A, AAC, WMA |

### 6.3 Speaker Control

| Function | Description |
|----------|-------------|
| `enable_speaker()` | Set GPIO pin HIGH (pin 12 v5.x, pin 20 v4.x); plays 0.5s silence to fill buffer |
| `disable_speaker()` | Set GPIO pin LOW |
| `set_volume(value)` | `sudo amixer -M sset 'PCM' {value}%` (0-100) |

**Auto-enable:** Speaker/Music `__init__()` and robot_hat TTS wrappers call `enable_speaker()` automatically.

### 6.4 AudioPlayer Details

| Property | Value |
|----------|-------|
| Default sample rate | 22050 Hz |
| Default format | pyaudio.paInt16 |
| Buffer threshold | 512 bytes (hardcoded, ignores constructor buffer_size) |
| Chunk size (play) | 2048 bytes (2KB) |
| Gain | 1.0 default; 1.5 for OpenAI TTS |

---

## 7. Voice Assistant Lifecycle

### 7.1 State Machine

```
IDLE ---------> LISTENING ---------> THINKING ---------> SPEAKING ---------> COOLDOWN --> IDLE
 |                |                    |                    |                    |
 | poll triggers  | stt.listen()       | llm.prompt()       | tts.say()          | sleep(cooldown)
 | every 10ms     | stream=True        | stream=True        |                    |
 |                |                    | capture_image()     |                    |
```

States are implicit in main loop position. `self.running` is the only control flag.

### 7.2 Trigger System

| Trigger | Type | Returns | Description |
|---------|------|---------|-------------|
| `trigger_wake_word` | Built-in | `(True, False, message)` | Checks stt.is_waked(), speaks answer_on_wake, records speech |
| `trigger_keyboard_input` | Built-in | `(True, True, text)` | Checks keyboard_input.is_result_ready(), returns typed line |
| Custom triggers | `add_trigger(fn)` | `(bool, bool, str)` | User-defined; (triggered, disable_image, message) |

**Trigger Signature:** `() -> tuple[bool, bool, str]`
- `triggered`: Whether this trigger fired
- `disable_image`: Skip camera capture for this round
- `message`: User input text to send to LLM

**Exclusive Trigger Protocol:**
If a trigger's bound method has `__self__.is_active()` returning `True`, wake word listening is skipped. Allows conversation-mode triggers to own the microphone.

### 7.3 Hook Points (12 Hooks)

| Hook | Signature | When Called | Typical Override Use |
|------|-----------|------------|---------------------|
| `on_start()` | `() -> None` | Once at start of `main()` | Initialize hardware |
| `on_wake()` | `() -> None` | After wake word detected, before listening | Play sound, animate |
| `before_listen()` | `() -> None` | Before STT starts recording | Pause other audio |
| `after_listen(stt_result: str)` | `(str) -> None` | After STT completes | Resume audio |
| `on_heard(text: str)` | `(str) -> None` | After speech transcribed | Log, process commands |
| `before_think(text: str)` | `(str) -> None` | Before LLM call | Show thinking animation |
| `after_think(text: str)` | `(str) -> None` | After LLM response received | Process actions |
| `parse_response(text: str)` | `(str) -> str` | After think(), before TTS | Strip action lines; return '' to skip TTS |
| `before_say(text: str)` | `(str) -> None` | Before TTS speaks | Start mouth animation |
| `after_say(text: str)` | `(str) -> None` | After TTS finishes | Stop mouth animation |
| `on_finish_a_round()` | `() -> None` | After speak completes | Update state, log |
| `on_stop()` | `() -> None` | During cleanup in run() finally | Release resources |

### 7.4 Full Round Sequence

```
1. main() starts -> on_start() -> tts.say(welcome)
2. LOOP:
   a. Check for exclusive triggers (is_active() protocol)
   b. If wake_enable and no exclusive: stt.start_listening_wake_words()
   c. If keyboard_enable: keyboard_input.start()
   d. Poll triggers every 10ms until one fires
   e. Stop wake word / keyboard listeners
   f. think(message):
      - before_think(text)
      - capture_image('./img_input.jpeg') if with_image
      - llm.prompt(stream=True)
      - after_think(result)
   g. response_text = parse_response(result)
   h. If response_text != '':
      - before_say(text)
      - tts.say(text)
      - after_say(text)
   i. on_finish_a_round()
   j. sleep(round_cooldown)
   k. Go to 2.a
```

---

## 8. Key Gotchas

### Hardware

- **PWM Timer Sharing:** Channels P0-P3 share Timer 0 prescaler/period. Changing frequency on P0 affects P1-P3. Same for P4-P7 (Timer 1), P8-P11 (Timer 2). All PiDog servos default to 50Hz.
- **Servo Angle Clamping:** Angles outside -90 to +90 silently clamped. No error raised.
- **Head Pitch Offset:** 45deg mechanical offset. Raw angle 0 = nose pointed up 45deg. Use `head_move()` not `head_move_raw()`.
- **Robot Offset Clamp:** `set_offset()` clamps to +/-20deg. Larger offsets indicate mechanical problems.
- **Ultrasonic in Separate Process:** Not a thread -- avoids I2C conflicts. If process crashes silently, `read_distance()` returns -1.0.
- **IMU Calibrates on Startup:** Do not move robot during first 1 second (gyro offset sampling).
- **IMU Axes Inverted:** `ay` and `az` negated in Pidog code for body-relative coordinates.
- **RGB Not Instant:** `set_mode()` takes effect within 50ms (next `show()` call). Frame recalculation can take ~100ms on Pi Zero.
- **RGB I2C Address Fixed:** 0x74 not software-configurable.
- **Sound Direction Requires Busy Check:** Must call `isdetected()` before `read()`.
- **Touch Slide Timeout:** 0.5s max between touches for slide detection. Touches <50ms may be missed.
- **ADC Channel Reversal:** Software channel 0 reads hardware channel 7. Use `ADC("A0")` consistently.
- **ADXL345 Double Read:** First read always returns 0 (device quirk). Code compensates.
- **Speaker Enable Required:** GPIO pin must be set HIGH before audio output. TTS/Speaker/Music auto-enable.
- **GPIO Pin Aliases Overlap:** "D1" and "D7" both map to GPIO 4. "LED" and "D14" both to GPIO 26.
- **Motor Speed Direction Change:** Setting speed=-50 then speed=50 without intermediate 0 may cause abrupt direction change.

### Threading

- **Speed vs DPS:** The `speed` parameter (0-100) affects delay between movements, NOT servo angular velocity. DPS is fixed: HEAD_DPS=300, LEGS_DPS=428, TAIL_DPS=500.
- **Immediate Flag:** `immediately=True` clears the action buffer. For smooth continuous motion, use `immediately=False` and queue.
- **Action Threads are Daemon:** Exit when main thread exits. Always call `close()` for proper cleanup.
- **Pin Mode Auto-Switch:** Calling `pin.value()` on OUT pin switches to IN. Explicit `setup()` recommended.
- **Global Timer State:** PWM `timer` list is module-level global. Not multiprocessing-safe.
- **`self.running` Not Locked:** VoiceAssistant's running flag read from multiple threads without locks. Works under CPython GIL only.
- **Round Cooldown Blocks Main Thread:** `sleep(round_cooldown)` blocks everything including trigger polling.
- **servo_move Timing:** Uses `time.time()` for step delays. Not real-time. Jitter from Python GIL.

### API

- **ActionDict Returns Tuple:** `actions_dict['stand']` returns `(data, part)`, not just data. Must unpack.
- **Gait Actions Are Generators:** 'forward', 'backward' generate ~193 coordinate frames. One execution = one walk cycle (~2 seconds).
- **ActionFlow Posture Tracking:** If you call `dog.do_action('stand')` directly (bypassing ActionFlow), posture state becomes stale.
- **move_list Format:** Must be list of lists: `[[angles]]`. Single list `[angles]` will fail. Correct: `{"action": [[1,2,3]]}`.
- **fileDB Values Are Strings:** Must convert: `int(db.get(...))`, `float(db.get(...))`.
- **Config Write Required:** `set()` modifies in-memory dict only. Must call `write()` to persist.
- **System Messages Can Be Evicted:** With `max_messages=20`, after 19 exchanges, system message at index 0 gets popped. Long conversations lose instructions.
- **Non-Streaming LLM Does Not Save History:** `_non_stream_response()` does not add assistant message to history. Streaming mode does.
- **Empty Content Replaced:** Anthropic adapter replaces empty strings with "Hello" (API requirement).
- **`set_instructions` Is Additive:** Each call adds another system message. No deduplication.
- **`prompt()` With List Replaces History:** Passing `msg` as a list replaces `self.messages` entirely.
- **API_KEY Authorization Produces No Header:** The `LLM.chat()` only checks for `BEARER`. Using `API_KEY` sends no auth header.

### Audio

- **STT Network Required at Construction:** `Vosk.__init__()` fetches model list from `alphacephei.com`. No offline fallback.
- **Wake Word Is Exact Match:** "hey buddy" will not match "hey buddy please". Entire utterance must equal wake word.
- **Recognizer Is Shared State:** Same KaldiRecognizer for wake word and post-wake listening. Stop listening before switching.
- **`listen(stream=False)` Blocks Indefinitely:** Without timeout, blocks forever if no speech detected.
- **Piper Model Directory Permissions:** `/opt/piper_models` created with `chmod 0o777` and `chown 1000:1000`. Hardcoded UID.
- **Vosk Model Path Requires Root:** Default `/opt/vosk_models` needs write access (sudo).
- **pico2wave say() Is Fire-and-Forget:** Background `aplay &` means no way to detect when playback finishes.
- **OpenAI TTS set_gain Rejects int:** `set_gain(2)` raises ValueError. Must pass `2.0`.
- **AudioPlayer flush_buffer Double-Gain Bug:** `play()` applies gain before buffering. `flush_buffer()` applies gain again to remaining data.
- **AudioPlayer buffer_size Parameter Unused:** Constructor's `buffer_size=8192` stored but never read. Play threshold hardcoded at 512 bytes.
- **Piper Chinese Punctuation Aggressive:** Chinese commas replaced with `. ` (period+space), changing sentence structure.
- **Speaker File Not Found:** `Speaker.play()` raises FileNotFoundError. `Pidog.speak()` returns False silently.
- **eSpeak Command Injection:** f-string interpolation into shell command. Words with `"` or shell metacharacters can break.
- **`check_executable` Deprecated:** Uses `distutils.spawn.find_executable`, removed in Python 3.13.

### Camera

- **Camera Format:** XBGR8888 (VoiceAssistant's picamera2 choice). CameraPool converts to BGR for OpenCV/face_recognition.
- **Image Path Hardcoded:** `think()` always writes to `./img_input.jpeg` relative to CWD.
- **Camera Owned by VoiceAssistant:** Vision cannot run if VoiceAssistant is not started.

### GPIO / Cleanup

- **Never use `kill -9` on GPIO processes.** SIGKILL without cleanup corrupts SD card. Use Ctrl+C or cleanup.py.
- **gpiozero Cleanup:** Always call `pin.close()` or `pin.deinit()`. Unclosed pins cause "pin already in use" errors.
- **MCU Reset:** `reset_mcu()` toggles GPIO 5. If GPIO 5 used elsewhere, causes side effects.
- **enable_speaker Requires sox:** Runs `play -n trim 0.0 0.5`. Fails silently if `sox` not installed.
- **Device Detection Failure Silent:** If no HAT detected, `Devices()` uses v4.x defaults. No error raised.

### Servo Calibration

- **Offsets Persist via fileDB:** Stored in `~/.config/robot-hat/robot-hat.conf`. Survives reboot (if not on overlay FS).
- **Calibration Range:** +/-20deg max offset. Larger values indicate mechanical misalignment.
- **Init Order Matters:** Servo init with 150ms delays prevents voltage sag brownout. Even indices (upper legs) initialized first: [0,2,4,6,1,3,5,7].
- **Close Timeout:** `Pidog.close()` has 5-second timeout for lie position. May raise TimeoutError if servos stuck.

---

## 9. Initialization Sequences

### 9.1 Pidog Initialization Sequence

```
1.  utils.reset_mcu()                      -- Reset I2C servo controller (GPIO5 LOW 10ms -> HIGH 10ms)
2.  ActionDict()                           -- Create action definitions
3.  Initialize kinematics state            -- pose, rpy, leg matrices
4.  Robot(pin_list=LEGS_PINS, name='pidog_legs')  -- 8 leg servos
    a. I2C scan for addresses [0x14, 0x15, 0x16]
    b. Create 8 Servo objects on pins [2,3,7,8,0,1,10,11]
    c. Set max_dps = 428
    d. Load offsets from config file
    e. Move to init_angles in order [0,2,4,6,1,3,5,7] with 150ms delays
5.  Robot(pin_list=HEAD_PINS, name='pidog_head')  -- 3 head servos
    a. Same I2C setup, pins [4,6,5]
    b. Set max_dps = 300
    c. Move to [0,0,0]
6.  Robot(pin_list=TAIL_PIN, name='pidog_tail')   -- 1 tail servo
    a. Same I2C setup, pin [9]
    b. Set max_dps = 500
    c. Move to [0]
7.  Sh3001(db='sh3001.config')             -- IMU init (I2C 0x36)
    a. Configure acc: 500Hz, +/-2g
    b. Configure gyro: 500Hz, +/-2000deg/s
    c. Configure temp: 63Hz
8.  RGBStrip(addr=0x74, nums=11)           -- LED strip init
    a. Initialize SLED1735 chip
    b. Set default breath mode
9.  DualTouch(sw1='D2', sw2='D3')          -- Touch sensor init
10. SoundDirection(busy_pin=6)             -- Sound direction init (SPI0)
11. Music()                                -- Pygame audio init, enable speaker
12. action_threads_start()                 -- Start 5 daemon threads:
    a. _legs_action_thread
    b. _head_action_thread
    c. _tail_action_thread
    d. _rgb_strip_thread
    e. _imu_thread (calibrates offsets during first 1s)
13. sensory_process_start()                -- Start ultrasonic process
```

**Total startup time:** ~1-2 seconds
**Failure handling:** I2C failures raise `OSError`. GPIO failures print error, continue (component disabled).

### 9.2 VoiceAssistant Initialization Sequence

```
1.  Piper(model=tts_model)                -- Create TTS, may download model (~15-100MB)
2.  Vosk(language=stt_language)            -- Create STT
    a. Fetch model list from https://alphacephei.com/vosk/models/model-list.json (10s timeout)
    b. Download model if needed to /opt/vosk_models/
    c. Create KaldiRecognizer
3.  llm.set_instructions(instructions)     -- Add system prompt
4.  stt.set_wake_words(wake_word)
5.  If wake_enable: register trigger_wake_word
6.  If keyboard_enable: create KeyboardInput(), register trigger_keyboard_input
7.  If with_image: init_camera()           -- Start picamera2 at 640x480
```

### 9.3 Pidog Shutdown Sequence (close())

```
1.  Install temporary SIGINT handler       -- Prevent Ctrl+C during cleanup
2.  stop_and_lie(speed=85)                 -- 5-second timeout
    a. Clear all action buffers
    b. Move to lie position
    c. Block until complete or timeout
3.  Set exit_flag = True                   -- Signal all threads to stop
4.  Join legs_thread, head_thread, tail_thread, rgb_thread, imu_thread
5.  Terminate sensory_process (ultrasonic)
6.  Close GPIO pins (touch, sound direction, ultrasonic)
7.  Restore original SIGINT handler
```

---

## 10. Configuration & Persistence

### 10.1 Config File Locations

| File | Purpose | Format | Library |
|------|---------|--------|---------|
| `~/.config/robot-hat/robot-hat.conf` | Servo offsets, motor config | INI (key=value with sections) | robot-hat Config/fileDB |
| `sh3001.config` | IMU calibration offsets | key=value | pidog Sh3001 |
| `/opt/vosk_models/{model_name}/` | Vosk STT models | Directory | voice-assistant |
| `/opt/piper_models/{model}.onnx` | Piper TTS models | ONNX + JSON | voice-assistant |

### 10.2 Offset Storage Format

```
# In ~/.config/robot-hat/robot-hat.conf
pidog_legs_servo_offset_list = [2.0, -1.5, 0.5, 0.0, -2.0, 1.0, 0.5, -0.5]
pidog_head_servo_offset_list = [0.0, 1.0, -0.5]
pidog_tail_servo_offset_list = [0.0]
```

### 10.3 Robot HAT Device Database

| HAT Version | UUID | Speaker Pin | Motor Mode | Detection |
|-------------|------|-------------|------------|-----------|
| v4.x | None (default) | GPIO 20 | 1 (TC1508S) | Fallback if no UUID match |
| v5.x | `9daeea78-0000-076e-0032-582369ac3e02` | GPIO 12 | 2 (TC618S) | `/proc/device-tree/hat*/uuid` |

---

## 11. Walk Gait Algorithm Detail

### 11.1 Walk Cycle Structure

```
Section | Leg Moving      | Other Legs  | Duration
--------|-----------------|-------------|----------
   0    | None (break)    | All ground  | 6 frames
   1    | Leg 1 (LH)      | 3 ground    | 6 frames
   2    | None (break)    | All ground  | 6 frames
   3    | Leg 4 (RF)      | 3 ground    | 6 frames
   4    | None (break)    | All ground  | 6 frames
   5    | Leg 2 (LF)      | 3 ground    | 6 frames
   6    | None (break)    | All ground  | 6 frames
   7    | Leg 3 (RH)      | 3 ground    | 6 frames
```

**Leg Order:** `[1, 0, 4, 0, 2, 0, 3, 0]` (1-indexed, 0 = break)

### 11.2 Walk Coordinate Functions

**Y-coordinate (forward/back):**
```
Stepping leg: y = leg_origin + (leg_step_width * (cos(theta) - fb) / 2 * fb)
  where theta = step * pi / (STEP_COUNT - 1)
  Cosine creates smooth acceleration/deceleration (ease-in/out)

Ground legs: Linear drag back LEG_STEP_WIDTH / (SECTION_COUNT - 1) per section
  Net result: Body moves forward while legs "pedal" backward
```

**Z-coordinate (up/down):**
```
Stepping leg: z = Z_ORIGIN - (LEG_STEP_HEIGHT * step / (STEP_COUNT - 1))
  Linear rise (constant vertical velocity)

Ground legs: Fixed at Z_ORIGIN
```

### 11.3 Walk Timing Diagram

```
Time: 0--6--12-18-24-30-36-42-48 (frames)
LH:   ^^^-------------------
LF:   ---------^^^----------
RH:   -------------------^^^
RF:   ---^^^-----------------
       ^=stepping  -=ground
```

### 11.4 Trot Cycle Structure

```
Section | Legs Moving       | Other Legs  | Duration
--------|-------------------|-------------|----------
   0    | 1,4 (LH + RF)    | 2,3 ground  | 3 frames (diagonal pair)
   1    | 2,3 (LF + RH)    | 1,4 ground  | 3 frames (diagonal pair)
```

### 11.5 Trot Timing Diagram

```
Time: 0-3-6 (frames)
LH:   ^^^---
LF:   ---^^^
RH:   ---^^^
RF:   ^^^---
```

### 11.6 Turning Mechanics

**Walk turning:** `TURNING_RATE = 0.3`
- Left turn: LH and RH (left side) move at 30% stride, LF and RF (right side) at 100%
- Right turn: opposite

**Trot turning:** `TURNING_RATE = 0.5`
- Same pattern but 50% stride on inside legs (wider turns)

**Center of gravity shifts with direction:**
- Forward: COM shifts back (-15mm walk, -17mm trot)
- Turning: COM shifts laterally for balance

---

## 12. Anthropic Claude API Integration

### 12.1 API Details

| Property | Value |
|----------|-------|
| Endpoint | `https://api.anthropic.com/v1/messages` |
| Auth Header | `x-api-key: {api_key}` |
| Version Header | `anthropic-version: 2023-06-01` |
| Default Model | `claude-sonnet-4-20250514` |
| Default Max Tokens | 1024 |
| Message Format | System prompt separate from messages array |

### 12.2 Claude vs OpenAI Message Format Differences

| Feature | OpenAI Format | Claude (Anthropic) Format |
|---------|--------------|---------------------------|
| System messages | In `messages` array | Separate `system` field |
| Image format | `image_url` with URL or base64 | `source.data` with base64 + `media_type` |
| Streaming event | `data: {"choices":[{"delta":{"content":"..."}}]}` | `data: {"type":"content_block_delta","delta":{"text":"..."}}` |
| API key header | `Authorization: Bearer {key}` | `x-api-key: {key}` |
| Version header | None required | `anthropic-version: 2023-06-01` required |
| Done signal | `data: [DONE]` | `data: {"type":"message_stop"}` |

### 12.3 Message History Management

- **Max messages:** Inherited from LLM base (default 20)
- **Trimming:** When `len(messages) > max_messages`, oldest message removed via `messages.pop(0)`
- **System prompt:** Stored separately, NOT counted toward message limit
- **Empty content:** Replaced with "Hello" (Claude API requirement)
- **Image media type:** Auto-detected from file extension (`.jpg` -> `image/jpeg`)

---

## 13. Pidog Body Coordinate System

### 13.1 Physical Layout

```
              Head [yaw, roll, pitch]
                |
       LF [2,3]--[BODY]--RF [6,7]  (front)
                 |    |
       LH [0,1]--[BODY]--RH [4,5]  (hind)
                |
              Tail [9]
```

### 13.2 Angle Conventions

| Part | Positive Direction | Negative Direction |
|------|-------------------|-------------------|
| Head yaw | Turn left | Turn right |
| Head roll | Tilt right | Tilt left |
| Head pitch | Nose up | Nose down |
| Leg upper (even) | Outward from body | Inward |
| Leg lower (odd) | Extension | Flexion |
| Tail | Left | Right |

### 13.3 Coordinate System (IK)

| Axis | Positive Direction | Units |
|------|-------------------|-------|
| X | Right | mm |
| Y | Forward (gait code) | mm |
| Z | Down (gait code, inverted from standard) | mm |

**IK Two-Link Calculation:**
```python
# Input: (y, z) foot position relative to hip, in mm
# Constants: LEG=42mm (upper), FOOT=76mm (lower)
# Output: (upper_angle, lower_angle) in degrees

# The IK uses law of cosines:
# distance = sqrt(y^2 + z^2)
# foot_angle = acos((LEG^2 + FOOT^2 - distance^2) / (2*LEG*FOOT))
# Upper angle derived from geometry + foot_angle offset
# Mechanical offset: foot_angle = foot_angle - 90
```

### 13.4 Pose Control API

```python
# Set body position (center of mass)
dog.set_pose(x=0, y=0, z=85)        # z=85mm standing height

# Set body orientation (Euler angles)
dog.set_rpy(roll=10, pitch=0, yaw=0)  # Tilt right 10deg

# Optional: PID balance using IMU feedback
dog.set_rpy(roll=0, pitch=0, pid=True)

# Set individual leg endpoints
dog.set_legs([[0,80], [0,80], [0,80], [0,80]])  # [y,z] per leg

# Compute and execute
angles = dog.pose2legs_angle()
dog.legs_move([angles], speed=60)
```

---

## 14. Sound Effects Library

### 14.1 Built-in Sounds

Sound files located in `SOUND_DIR` (pidog package directory).

| Name | Format | Duration | Used By |
|------|--------|----------|---------|
| `single_bark_1` | MP3/WAV | ~0.5s | `bark()` |
| `pant` | MP3/WAV | ~1s | `pant()` |
| `howling` | MP3/WAV | 2.34s | `howling()` |

**Sound Lookup Order:**
1. `name` as full path
2. `SOUND_DIR + name + '.mp3'`
3. `SOUND_DIR + name + '.wav'`

**Returns:** `False` if file not found, `None` otherwise (no exception).

### 14.2 Audio Playback Methods

| Method | Blocking | Thread-Safe | Source |
|--------|----------|-------------|--------|
| `Pidog.speak(name, volume)` | No | Yes (spawns thread) | Sound files |
| `Pidog.speak_block(name, volume)` | Yes | No | Sound files |
| `Music.sound_play(filename, volume)` | Yes | No (pygame) | Any audio file |
| `Music.sound_play_threading(filename, volume)` | No | No | Any audio file |
| `Speaker.play(file_path)` | No (background) | Yes (threading.Lock) | WAV, FLAC, OGG, MP3, M4A, AAC, WMA |

**Note:** `Pidog.speak()` kills pulseaudio processes first to fix VNC sound issues.

---

## 15. Piper TTS Models (English)

### 15.1 en_US Voice Options

| Voice | Qualities Available | Notes |
|-------|-------------------|-------|
| amy | low, medium | |
| arctic | medium | |
| bryce | medium | |
| danny | low | |
| hfc_female | medium | |
| hfc_male | medium | |
| joe | medium | |
| john | medium | |
| kathleen | low | |
| kristin | medium | |
| kusal | medium | |
| l2arctic | medium | |
| lessac | low, medium, high | Most quality options |
| libritts | high | |
| libritts_r | medium | |
| ljspeech | medium, high | |
| norman | medium | |
| reza_ibrahim | medium | |
| **ryan** | **low**, medium, high | **PiDog default: en_US-ryan-low** |
| sam | medium | |

### 15.2 Quality Tiers

| Quality | Typical Size | Speed | Description |
|---------|-------------|-------|-------------|
| x_low | ~15MB | Fastest | Lowest quality |
| low | ~20-30MB | Fast | Acceptable quality (PiDog default) |
| medium | ~60-80MB | Moderate | Good balance |
| high | ~100-150MB | Slowest | Best quality |

**Model storage:** `/opt/piper_models/{model}.onnx` + `/opt/piper_models/{model}.onnx.json`

### 15.3 Supported Locales (40 total)

`ar_JO`, `ca_ES`, `cs_CZ`, `cy_GB`, `da_DK`, `de_DE`, `el_GR`, `en_GB`, `en_US`, `es_ES`, `es_MX`, `fa_IR`, `fi_FI`, `fr_FR`, `hu_HU`, `is_IS`, `it_IT`, `ka_GE`, `kk_KZ`, `lb_LU`, `lv_LV`, `ml_IN`, `ne_NP`, `nl_BE`, `nl_NL`, `no_NO`, `pl_PL`, `pt_BR`, `pt_PT`, `ro_RO`, `ru_RU`, `sk_SK`, `sl_SI`, `sr_RS`, `sv_SE`, `sw_CD`, `tr_TR`, `uk_UA`, `vi_VN`, `zh_CN`

---

## 16. LLM Provider Presets

| Class | Base URL | Auth | Notes |
|-------|----------|------|-------|
| `OpenAI` | `https://api.openai.com/v1` | Bearer | Standard OpenAI |
| `Deepseek` | `https://api.deepseek.com` | Bearer | DeepSeek API |
| `Grok` | `https://api.x.ai/v1` | Bearer | xAI Grok |
| `Doubao` | `https://ark.cn-beijing.volces.com/api/v3` | Bearer | ByteDance |
| `Qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Bearer | Alibaba |
| `Gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` | Bearer | Google (OpenAI-compat) |
| `Ollama` | `http://{ip}:11434/api/chat` | None needed | Local; overrides add_message + decode_stream |

**Ollama Image Format (differs from OpenAI):**
```python
# Ollama: {"role": "user", "content": "...", "images": ["base64data"]}
# OpenAI: {"role": "user", "content": [{"type": "text", ...}, {"type": "image_url", ...}]}
```

**Ollama Stream Format (differs from OpenAI):**
```python
# Ollama: {"message": {"content": "token"}}      # JSON per line
# OpenAI: data: {"choices": [{"delta": {"content": "token"}}]}  # SSE format
```

---

## 17. Vosk Wake Word Detection Details

### 17.1 Detection Flow

```
1. start_listening_wake_words() spawns wake_word_thread
2. Thread calls heard_wake_word() in a loop (100ms sleep between)
3. heard_wake_word() calls listen(stream=False) -- BLOCKS until utterance completes
4. Completed utterance compared (lowercased) to each string in self.wake_words
5. Match means EXACT equality -- no fuzzy matching, no substring
6. On match: self.waked = True, thread exits
7. Main loop polls is_waked() -> fires trigger_wake_word()
8. trigger_wake_word() stops listening, calls on_wake(), speaks answer_on_wake
9. Calls listen() to record full user utterance
10. Returns (True, False, message) to main loop
```

### 17.2 Key Insight

Wake word detection reuses the full Vosk recognizer. It transcribes complete utterances and compares as strings. Implications:
- Wake word must be the ENTIRE utterance, not a prefix
- "hey buddy please help" will NOT trigger "hey buddy"
- Background noise producing any text will not match (good)
- Multi-word wake words like "hey buddy" require Vosk to transcribe exactly that phrase

### 17.3 Recognizer State Sharing

The same `KaldiRecognizer` is used for both wake word detection and post-wake speech recognition. The `trigger_wake_word` correctly calls `stop_listening()` before starting full recording. If these overlap, recognizer state corrupts.

---

## 18. ActionFlow Posture State Machine

### 18.1 Postures

| Posture | Enum Value | Head Pitch Compensation | Standing Height |
|---------|------------|------------------------|-----------------|
| STAND | 0 | 0 deg | 95mm |
| SIT | 1 | -35 deg (typical) | N/A |
| LIE | 2 | -45 deg (typical) | N/A |

### 18.2 Posture Transitions

| From | To | Method | Notes |
|------|----|--------|-------|
| LIE | STAND | `do_action('stand')` | Direct |
| LIE | SIT | `do_action('sit')` | Direct |
| SIT | STAND | `sit_2_stand()` | 2-stage smooth; speed must be >70 |
| SIT | LIE | `do_action('lie')` | Direct |
| STAND | SIT | `do_action('sit')` | Direct |
| STAND | LIE | `do_action('lie')` | Direct |

### 18.3 ActionFlow Thread States

| State | Value | Description |
|-------|-------|-------------|
| STANDBY | 'standby' | Idle, may run random waiting animations |
| THINK | 'think' | Brain is processing |
| ACTIONS | 'actions' | Executing queued actions |
| ACTIONS_DONE | 'actions_done' | All actions completed |

---

## 19. Common Code Patterns

### 19.1 Basic Robot Operation

```python
from pidog import Pidog

dog = Pidog()
dog.do_action('stand', speed=70)
dog.wait_all_done()
dog.do_action('forward', step_count=5, speed=90)
dog.wait_all_done()
distance = dog.read_distance()
roll, pitch = dog.roll, dog.pitch
touch = dog.dual_touch.read()
dog.close()
```

### 19.2 ActionFlow with Chaining

```python
from pidog import Pidog
from pidog.action_flow import ActionFlow

dog = Pidog()
flow = ActionFlow(dog)
flow.start()
flow.add_action('stand', 'forward', 'forward', 'sit')
flow.wait_actions_done()
flow.stop()
```

### 19.3 Voice Assistant with Anthropic

```python
from pidog import Pidog
from pidog.anthropic_llm import Anthropic
from pidog.voice_assistant import VoiceAssistant
import os

dog = Pidog()
llm = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'], model='claude-sonnet-4-20250514')
llm.set_instructions("You are PiDog, a friendly robot dog. Respond with ACTIONS: lines.")

va = VoiceAssistant(llm=llm, name='PiDog', wake_word=['hey pidog'],
                    tts_model='en_US-ryan-low', stt_language='en-us')
va.run()
```

### 19.4 Custom Trigger (Exclusive Protocol)

```python
class ConversationTrigger:
    def __init__(self):
        self._active = False
        self._message = None

    def is_active(self):
        return self._active  # When True, wake word listener is skipped

    def __call__(self):
        if self._message:
            msg = self._message
            self._message = None
            return (True, False, msg)
        return (False, False, '')

trigger = ConversationTrigger()
va.add_trigger(trigger)  # trigger.__self__.is_active() checked by main loop
```

### 19.5 RGB Strip Control

```python
dog.rgb_strip.set_mode('breath', 'pink', bps=1.5, brightness=1.0)
dog.rgb_strip.set_mode('speak', 'cyan')     # Used during howling
dog.rgb_strip.set_mode('listen', 'blue')    # Used during listening
dog.rgb_strip.close()                        # Turn off
```

### 19.6 IK and Pose Control

```python
# Standing at specific height
coords = [[0, 85], [0, 85], [0, 85], [0, 85]]  # y=0, z=85mm per leg
angles = Pidog.legs_angle_calculation(coords)
dog.legs_move([angles], speed=70)

# Body tilt with pose API
dog.set_pose(x=0, y=0, z=85)
dog.set_rpy(roll=10, pitch=-5, yaw=0)
angles = dog.pose2legs_angle()
dog.legs_move([angles], speed=60)
```

### 19.7 Sensor Polling Loop

```python
while True:
    # Ultrasonic
    dist = dog.read_distance()
    if 0 < dist < 20:
        dog.do_action('bark', speed=90)

    # Touch
    touch = dog.dual_touch.read()
    if touch == 'L':
        dog.do_action('wag tail')
    elif touch == 'LS':
        dog.do_action('forward', step_count=3)

    # Sound direction
    if dog.ears.isdetected():
        angle = dog.ears.read()
        dog.head_move([[angle, 0, 0]], speed=90)

    # IMU
    if abs(dog.pitch) > 30:
        print("Robot tilted!")

    time.sleep(0.1)
```

### 19.8 Monkey-Patching STT

```python
va = VoiceAssistant(llm=llm)
# Replace Vosk with custom STT after construction
va.stt = MoonshineStt()
va.stt.set_wake_words(["hey pidog"])
# MoonshineStt must implement: listen(), start_listening_wake_words(),
# is_waked(), stop_listening(), close(), set_wake_words()
va.run()
```

---

## 20. I2C Communication Details

### 20.1 I2C Retry Mechanism

All I2C operations retry up to 5 times on `OSError`. The `@_retry_wrapper` decorator handles bus contention and transient failures. If all retries fail, operations return `False` (not raise).

**Write dispatch by data length:**
| Byte Count | Method | Register Use |
|------------|--------|-------------|
| 1 byte | `_write_byte(data)` | No register |
| 2 bytes | `_write_byte_data(reg, data)` | First byte = register |
| 3 bytes | `_write_word_data(reg, word)` | Little-endian word |
| 4+ bytes | `_write_i2c_block_data(reg, data[1:])` | First byte = register |

**ADC Read Sequence:**
```python
# Must write command before reading (stale data otherwise):
adc.write([chn | 0x10, 0, 0])    # Command: read channel
msb, lsb = adc.read(2)           # Read 2 bytes
value = (msb << 8) + lsb         # 12-bit result (0-4095)
```

### 20.2 I2C Bus Scan

```python
i2c = I2C([0x14, 0x15, 0x16])   # Auto-selects first found address
# Uses `i2cdetect -y {bus}` command
# If no devices found, uses first address in list (no error raised)
```

---

## 21. DualTouch State Machine

```
State Diagram:
  IDLE --[touch D2]--> AFTER_L --[0.5s timeout]--> return 'L'
  IDLE --[touch D3]--> AFTER_R --[0.5s timeout]--> return 'R'
  AFTER_L --[touch D3 within 0.5s]--> return 'LS' (rear-to-front slide)
  AFTER_R --[touch D2 within 0.5s]--> return 'RS' (front-to-rear slide)
  No touch --> return 'N'
```

**GPIO Configuration:** Both pins use pull-up resistors. Touch = pin goes LOW.

---

## 22. SoundDirection Protocol

### 22.1 SPI Communication

```python
# SPI: Bus 0, Device 0, 10MHz
# Busy pin: GPIO 6 (active LOW = sound detected)

# Read sequence:
if busy_pin.value() == 0:     # Sound detected
    tx = [0x00] * 6           # Master sends 6 dummy bytes
    rx = spi.xfer2(tx)        # Receive 6 bytes
    raw_angle = rx[4] | (rx[5] << 8)  # Little-endian 16-bit in bytes 4-5
    angle = (360 + 160 - raw_angle) % 360  # Adjust to forward-facing reference
```

### 22.2 Angle Resolution

| Raw Value Range | Angle Step | Total Positions |
|----------------|------------|-----------------|
| 0-355 degrees | 20 degrees | 18 positions |

**Forward reference:** Raw angle 160deg is mapped to 0deg (forward-facing).

---

## 23. RGB Strip Animation Details

### 23.1 SLED1735 Chip Interface

```python
# I2C address: 0x74
# Write raw frame: display(image)
# image = [[r,g,b], [r,g,b], ...] * 11 LEDs
# Each color value: 0-255
```

### 23.2 Animation Frame Generation

**Gaussian distribution base:**
```
value = A * exp(-(x - u)^2 / (2 * sigma^2)) / (sqrt(2*pi) * sigma) + offset
```

| Style | Description | Parameters |
|-------|-------------|------------|
| monochromatic | All LEDs same solid color | No animation |
| breath | Gaussian x cosine across all LEDs | Pulsing brightness |
| boom | Gaussian spreading outward from center LED | Expanding ring |
| bark | Quick flash pattern | Fast on/off |
| speak | Gaussian oscillating in/out from edges | Speaking mouth |
| listen | Gaussian sweep left to right | Scanning effect |

**Frame timing:** `max_frames = int(1 / bps / 0.05)` where 0.05s = 50ms per frame (20Hz)

Example: `bps=1.0` -> `max_frames = int(1/1/0.05) = 20` frames per cycle

### 23.3 Color Name Map

| Name | RGB |
|------|-----|
| `'red'` | [255, 0, 0] |
| `'green'` | [0, 255, 0] |
| `'blue'` | [0, 0, 255] |
| `'cyan'` | [0, 255, 255] |
| `'yellow'` | [255, 255, 0] |
| `'magenta'` | [255, 0, 255] |
| `'white'` | [255, 255, 255] |
| `'pink'` | [255, 128, 128] |
| `'orange'` | [255, 165, 0] |

---

## 24. Battery Monitoring

```python
# ADC channel A4 with 3:1 voltage divider
# Formula: battery_voltage = adc.read_voltage() * 3
# ADC range: 0-3.3V -> Battery range: 0-9.9V
# Typical 7.4V LiPo: reads ~2.47V on ADC -> 7.4V calculated

# Global ADC object reused (module-level singleton in utils.py)
voltage = dog.get_battery_voltage()  # or utils.get_battery_voltage()
if voltage < 6.0:
    print("Battery low!")
```

---

## 25. Music Theory Constants

### 25.1 Note System

```python
Music.NOTE_BASE_FREQ = 440     # A4 frequency (Hz)
Music.NOTE_BASE_INDEX = 69     # MIDI note number for A4
# Formula: freq = 440 * 2^((note - 69) / 12)

# Note durations
Music.WHOLE_NOTE = 1
Music.HALF_NOTE = 1/2
Music.QUARTER_NOTE = 1/4
Music.EIGHTH_NOTE = 1/8
Music.SIXTEENTH_NOTE = 1/16

# Beat duration: seconds = beat / note_value * (60 / tempo)
# Default: tempo=120 BPM, quarter note = 1 beat
# Quarter note at 120 BPM = 0.5 seconds
```

### 25.2 Key Signatures

| Key | Value | Sharps/Flats |
|-----|-------|-------------|
| KEY_G_MAJOR | 1 | 1 sharp (F#) |
| KEY_D_MAJOR | 2 | 2 sharps |
| KEY_A_MAJOR | 3 | 3 sharps |
| KEY_E_MAJOR | 4 | 4 sharps |
| KEY_B_MAJOR | 5 | 5 sharps |
| KEY_F_SHARP_MAJOR | 6 | 6 sharps |
| KEY_C_SHARP_MAJOR | 7 | 7 sharps |
| KEY_F_MAJOR | -1 | 1 flat (Bb) |
| KEY_B_FLAT_MAJOR | -2 | 2 flats |
| KEY_E_FLAT_MAJOR | -3 | 3 flats |
| KEY_A_FLAT_MAJOR | -4 | 4 flats |
| KEY_D_FLAT_MAJOR | -5 | 5 flats |
| KEY_G_FLAT_MAJOR | -6 | 6 flats |
| KEY_C_FLAT_MAJOR | -7 | 7 flats |

### 25.3 NOTES Array

MIDI-compatible note names from index 0-108:
- Indices 0-20: None (below audible range)
- Index 21: A0 (27.5 Hz)
- Index 60: C4 (261.6 Hz, middle C)
- Index 69: A4 (440 Hz, tuning standard)
- Index 108: C8 (4186 Hz)

---

## 26. Version Information

| Library | Version | Python | Notes |
|---------|---------|--------|-------|
| robot-hat | 2.5.1 | 3.x | HAT v4.x and v5.x support |
| pidog | 1.3.10a1 | 3.x | Alpha release |
| sunfounder_voice_assistant | 1.0.1 | 3.x | |
| Vosk models | varies | - | Downloaded to /opt/vosk_models/ |
| Piper models | varies | - | Downloaded to /opt/piper_models/ |

---

*For detailed implementation documentation, see:*
- `detail/01-robot-hat/` -- robot-hat library (foundations, actuators, sensors, peripherals, infrastructure)
- `detail/02-pidog/` -- pidog library (core, actions, locomotion, sensors, LLM)
- `detail/03-voice-assistant/` -- voice-assistant library (core, STT, TTS, LLM, audio internals)
