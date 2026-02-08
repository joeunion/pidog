# robot-hat: Actuators

<!-- Status: complete | Iteration: 1 -->

> Covers: `servo.py`, `motor.py`, `led.py`, `speaker.py`, `music.py`

## Purpose

Motor control (servo, DC motor), LED manipulation, and audio output (speaker playback, music/tone generation).

## Hardware

| Actuator | Type | Interface | Pins | Notes |
|----------|------|-----------|------|-------|
| Servo | PWM servo motor | PWM channels P0-P14 | - | Pulse width 500-2500µs, 50Hz |
| Motor | DC motor | PWM + GPIO direction | P12/P13 + D4/D5 | Two motors, mode 1 (TC1508S) or mode 2 (TC618S) |
| LED | Digital LED | GPIO | LED (GPIO26) | Onboard LED with blink support |
| Speaker | Audio output | I2S/Audio jack | GPIO12 enable | Supports WAV, MP3, FLAC, OGG, M4A, AAC, WMA |
| Music/Buzzer | Tone generator | PWM or Pygame | - | Note-based music playback, tone generation |

## API Reference

### Servo(PWM) (servo.py:6)

**Purpose**: Servo motor control with angle-based interface.

**Thread-safe**: No (inherits PWM limitations).

#### `__init__(channel: int|str, address=None, *args, **kwargs)`
Initialize servo on PWM channel 0-14 or "P0"-"P14". Sets 50 Hz frequency, 4095 period.

**Constants**:
- `MAX_PW = 2500`: Maximum pulse width (µs)
- `MIN_PW = 500`: Minimum pulse width (µs)
- `FREQ = 50`: Servo frequency (Hz)
- `PERIOD = 4095`: PWM period value

#### `angle(angle: float) -> None`
Set servo angle. Clamps to -90° to +90°. Maps angle to pulse width using `mapping()` function.

**Formula**: `pulse_width_µs = map(angle, -90, 90, 500, 2500)`

#### `pulse_width_time(pulse_width_time: float) -> None`
Set servo position by pulse width in microseconds (500-2500). Converts to PWM duty cycle.

**Calculation**: `duty_cycle = pulse_width_time / 20000 * PERIOD`

**Example**:
```python
from robot_hat import Servo
servo = Servo("P0")
servo.angle(0)    # Center position
servo.angle(90)   # Maximum clockwise
servo.angle(-90)  # Maximum counter-clockwise
```

---

### Motor (motor.py:7)

**Purpose**: DC motor control with speed and direction.

**Thread-safe**: No (PWM operations not thread-safe).

#### `__init__(pwm: PWM, dir: Pin|PWM, is_reversed=False, mode=None, freq=100)`
Initialize motor. Mode defaults to `__device__.motor_mode` (1 for v4.x, 2 for v5.x).

**Parameters**:
- `pwm`: PWM object for speed control
- `dir`: Pin object (mode 1) or PWM object (mode 2) for direction
- `is_reversed`: Invert direction if True
- `mode`: 1 (TC1508S) or 2 (TC618S)
- `freq`: PWM frequency (default 100 Hz)

**Motor Modes**:

| Mode | Chip | PWM Pin | Dir Pin | Forward | Backward | Stop | Brake |
|------|------|---------|---------|---------|----------|------|-------|
| 1 | TC1508S | PWM | GPIO | PWM + 1 | PWM + 0 | 0 + x | - |
| 2 | TC618S | PWM | PWM | PWM + 0 | 0 + PWM | 0 + 0 | 1 + 1 |

#### `speed(speed: float = None) -> float`
Get/set motor speed (-100 to +100). Positive = forward, negative = backward, 0 = stop.

**Implementation**:
- Mode 1: Sets PWM duty cycle and GPIO direction pin
- Mode 2: Sets one PWM to duty cycle, other to 0

#### `set_is_reverse(is_reverse: bool) -> None`
Set motor direction inversion.

**Example**:
```python
from robot_hat import Motor, PWM, Pin
motor = Motor(PWM("P13"), Pin("D4"))  # Mode 1
motor.speed(50)   # Forward at 50%
motor.speed(-50)  # Backward at 50%
motor.speed(0)    # Stop
```

---

### Motors (motor.py:119)

**Purpose**: Dual motor control for differential drive robots.

**Thread-safe**: No (uses Motor class).

#### `__init__(db=config_file, *args, **kwargs)`
Initialize both motors. Loads left/right motor IDs and reverse settings from config file.

**Default Pins**:
- Motor 1: PWM P13, Direction D4
- Motor 2: PWM P12, Direction D5

**Config**: Stored in `~/.config/robot-hat/robot-hat.conf` or `/opt/robot_hat/default_motors.config`

#### `left`, `right` (properties)
Access left/right motors. Raises ValueError if motor ID not set (call `set_left_id()` first).

#### `[index]` (indexer)
Access motor by 1-based index: `motors[1]` or `motors[2]`.

#### `set_left_id(id: int) -> None`, `set_right_id(id: int) -> None`
Set motor ID (1 or 2). Persists to config file.

#### `set_left_reverse() -> bool`, `set_right_reverse() -> bool`
Toggle motor direction reversal. Returns new reversed state. Persists to config.

#### `speed(left_speed: float, right_speed: float) -> None`
Set both motor speeds simultaneously.

#### `forward(speed: float) -> None`, `backward(speed: float) -> None`
Move both motors in same direction.

#### `turn_left(speed: float) -> None`, `turn_right(speed: float) -> None`
Differential steering: left motor backward, right forward (or vice versa).

#### `stop() -> None`
Stop both motors (set speed to 0).

**Example**:
```python
from robot_hat import Motors
motors = Motors()
motors.set_left_id(1)
motors.set_right_id(2)
motors.forward(50)        # Drive forward
motors.turn_left(30)      # Turn left
motors.stop()
```

---

### LED (led.py:6)

**Purpose**: Simple LED control with blink support.

**Thread-safe**: Yes (uses threading.Thread for blink, with locks).

#### `__init__(pin: str = "LED") -> None`
Initialize LED on pin (default "LED" = GPIO26).

#### `on() -> None`
Turn LED on. Stops any active blink.

#### `off() -> None`
Turn LED off. Stops any active blink.

#### `toggle(skip_stop: bool = False) -> None`
Toggle LED state. If `skip_stop=False`, stops blink first.

#### `blink(times: int = 1, delay: float = 0.1, pause: float = 0) -> None`
Blink LED in background thread. Stops previous blink.

**Parameters**:
- `times`: Number of on/off cycles per pattern
- `delay`: Time per cycle (seconds)
- `pause`: Pause between patterns (seconds)

**Behavior**: Loops indefinitely: blink `times` cycles, pause, repeat.

#### `blink_stop() -> None`
Stop blink thread. Joins thread (blocking until stopped).

#### `close() -> None`
Stop blink, turn off LED, close pin.

**Example**:
```python
from robot_hat import LED
led = LED()
led.on()
time.sleep(1)
led.blink(times=3, delay=0.1, pause=0.5)  # Blink 3 times, pause, repeat
time.sleep(5)
led.close()
```

---

### Speaker (speaker.py:11)

**Purpose**: Multi-format audio file playback with background threading.

**Thread-safe**: Yes (uses threading.Lock for task management).

#### `__init__() -> None`
Initialize speaker. Enables speaker via `enable_speaker()`. Initializes pyaudio.

**Supported Formats**:
- soundfile handler: WAV, FLAC, OGG
- librosa handler: MP3, M4A, AAC, WMA

#### `play(file_path: str) -> str`
Play audio file in background thread. Returns unique task ID (UUID).

**Returns**: String task ID for use with pause/resume/stop.

#### `get_progress(task_id: str) -> dict`
Get playback progress.

**Returns**:
```python
{
    'position': int,        # Current frame
    'total': int,           # Total frames
    'progress': float,      # 0.0 to 1.0
    'time': float,          # Current time (seconds)
    'total_time': float,    # Total duration (seconds)
    'is_playing': bool      # Playback state
}
```

#### `pause(task_id: str) -> None`
Pause playback. Can be resumed.

#### `resume(task_id: str) -> None`
Resume paused playback.

#### `stop(task_id: str) -> bool`
Stop playback and cleanup resources. Returns False if task not found.

#### `list_tasks() -> list`
List all active task IDs.

#### `enable_speaker() -> None`, `disable_speaker() -> None`
Enable/disable speaker hardware (calls `utils.enable_speaker()`).

**Chinese Comments Translated**:
- Line 9: "Used to generate unique playback ID"
- Line 14: "Initialize speaker state"
- Line 15: "Enable speaker on startup"
- Line 17: "Initialize audio system"
- Line 20: "Playback task management (ID -> playback info)"
- Line 22: "Thread-safe lock"
- Line 25: "Supported formats"
- Line 36: "Destroy time: close speaker and audio resources"
- Line 46-55: Enable/disable speaker comments

**Example**:
```python
from robot_hat.speaker import Speaker
import time

speaker = Speaker()
task1 = speaker.play("music.mp3")
task2 = speaker.play("sound.wav")

time.sleep(2)
speaker.pause(task1)
print(speaker.get_progress(task1))

time.sleep(2)
speaker.resume(task1)

time.sleep(5)
speaker.stop(task1)
speaker.stop(task2)
```

---

### Music(_Basic_class) (music.py:11)

**Purpose**: Music playback, sound effects, and tone generation using pygame.

**Thread-safe**: No (pygame mixer is not thread-safe).

#### `__init__() -> None`
Initialize pygame mixer. Enables speaker via `enable_speaker()`. Sets default time signature 4/4, tempo 120 BPM.

**Constants**:
- `FORMAT = pyaudio.paInt16`: Audio format for tone generation
- `CHANNELS = 1`: Mono audio
- `RATE = 44100`: Sample rate (Hz)
- `NOTE_BASE_FREQ = 440`: A4 frequency for MIDI calculations
- `NOTE_BASE_INDEX = 69`: MIDI note number for A4
- `NOTES`: List of note names (MIDI compatible, index 0-108)

**Key Signatures**:
- Sharp keys: `KEY_G_MAJOR` (1) through `KEY_C_SHARP_MAJOR` (7)
- Flat keys: `KEY_F_MAJOR` (-1) through `KEY_C_FLAT_MAJOR` (-7)

**Note Values**:
- `WHOLE_NOTE = 1`, `HALF_NOTE = 1/2`, `QUARTER_NOTE = 1/4`, `EIGHTH_NOTE = 1/8`, `SIXTEENTH_NOTE = 1/16`

#### `time_signature(top: int = None, bottom: int = None) -> tuple`
Get/set time signature. Default: (4, 4).

#### `key_signature(key: int|str = None) -> int`
Get/set key signature. Accepts int (-7 to 7) or string ("#", "##", "b", "bb", etc.).

#### `tempo(tempo: float = None, note_value: float = QUARTER_NOTE) -> tuple`
Get/set tempo in BPM. Default: 120 BPM, quarter note = 1 beat.

**Returns**: (tempo, note_value)

#### `beat(beat: float) -> float`
Calculate beat duration in seconds from current tempo.

**Formula**: `seconds = beat / note_value * (60 / tempo)`

#### `note(note: int|str, natural: bool = False) -> float`
Get frequency of a note.

**Parameters**:
- `note`: MIDI note number (0-108) or name (e.g., "C4", "A#3")
- `natural`: If True, ignore key signature

**Formula**: `freq = 440 * 2^((note - 69) / 12)`

**Returns**: Frequency in Hz.

#### `sound_play(filename: str, volume: int = None) -> None`
Play sound effect file synchronously (blocks until complete).

**Parameters**:
- `filename`: Path to sound file
- `volume`: 0-100, or None (don't change volume)

#### `sound_play_threading(filename: str, volume: int = None) -> None`
Play sound effect in background thread (non-blocking).

#### `music_play(filename: str, loops: int = 1, start: float = 0.0, volume: int = None) -> None`
Play music file.

**Parameters**:
- `filename`: Path to music file
- `loops`: 0 = loop forever, 1 = play once, 2 = twice, etc.
- `start`: Start time in seconds
- `volume`: 0-100, or None

#### `music_set_volume(value: int) -> None`
Set music volume (0-100).

#### `music_stop() -> None`, `music_pause() -> None`, `music_resume() -> None`, `music_unpause() -> None`
Control music playback.

#### `sound_length(filename: str) -> float`
Get sound effect duration in seconds.

#### `get_tone_data(freq: float, duration: float) -> bytes`
Generate tone waveform data for playback.

**Parameters**:
- `freq`: Frequency in Hz
- `duration`: Duration in seconds

**Returns**: Packed binary waveform data (16-bit PCM).

#### `play_tone_for(freq: float, duration: float) -> None`
Play tone for specified duration.

**Example**:
```python
from robot_hat import Music
import time

music = Music()
music.tempo(120)
music.key_signature(1)  # G major

# Play note C4 for 0.5 seconds
freq = music.note("C4")
music.play_tone_for(freq, 0.5)

# Play sound effect
music.sound_play("beep.wav", volume=80)

# Play background music
music.music_play("song.mp3", loops=0, volume=50)  # Loop forever
time.sleep(10)
music.music_stop()
```

**NOTES Array**: MIDI-compatible note names from index 0-108. First 21 entries are None (below audible range). A0 starts at index 21 (27.5 Hz), C8 at index 108 (4186 Hz).

## Implementation Notes

**Servo Pulse Width Mapping**: Angle -90° maps to 500µs, 0° to 1500µs, +90° to 2500µs. Standard RC servo protocol (20ms period = 50 Hz).

**Motor Mode Selection**: Device detection via `/proc/device-tree/hat/uuid` determines motor mode. v4.x uses TC1508S (mode 1), v5.x uses TC618S (mode 2).

**Speaker Hardware Enable**: Must call `enable_speaker()` to set GPIO pin high (pin 12 for v5.x, pin 20 for v4.x) before audio output. Library auto-enables on Speaker/Music initialization.

**Audio Format Handling**: Speaker class uses soundfile for lossless formats (WAV, FLAC, OGG), librosa for compressed formats (MP3, M4A, AAC, WMA). librosa is slower but more compatible.

**Background Playback**: Speaker uses threading for async playback with UUID-based task management. Music uses pygame mixer for single music stream + multiple sound effects.

**Tone Generation**: Music class generates sine waves using pyaudio for buzzer/tone playback. Credit: Aditya Shankar & Gringo Suave (StackOverflow).

## Code Patterns

**Servo Calibration**:
```python
servo = Servo("P0")
for angle in range(-90, 91, 10):
    servo.angle(angle)
    time.sleep(0.5)
```

**Differential Drive**:
```python
motors = Motors()
motors.set_left_id(1)
motors.set_right_id(2)

# Drive forward
motors.forward(50)

# Arc turn (one motor faster)
motors.speed(30, 50)

# Spin turn (opposite directions)
motors.turn_left(50)
```

**LED Status Indicator**:
```python
led = LED()
led.blink(times=1, delay=0.5)  # Slow blink = idle
led.blink(times=3, delay=0.1)  # Fast triple blink = active
led.on()  # Solid = error
```

**Multi-Track Audio**:
```python
speaker = Speaker()
music_id = speaker.play("background.mp3")
effect_id = speaker.play("beep.wav")

# Monitor music progress
while True:
    progress = speaker.get_progress(music_id)
    if progress['progress'] >= 1.0:
        break
    time.sleep(0.1)
```

**Musical Scale**:
```python
music = Music()
music.key_signature("#")  # G major

scale = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
for note_name in scale:
    freq = music.note(note_name)
    music.play_tone_for(freq, 0.5)
```

## Gotchas

**Servo Angle Clamping**: Angles outside -90° to +90° are silently clamped (lines 36-38). No error raised.

**Motor Speed Sign**: `speed()` accepts -100 to +100, but internally uses `abs(speed)` and separate direction bit (line 90). Setting speed=-50 then speed=50 without intermediate 0 may cause abrupt direction change.

**Motor Mode Mismatch**: Passing Pin to dir parameter with mode=2, or PWM with mode=1, raises TypeError (lines 45-60). Device auto-detection usually correct, but manual override may fail.

**LED Blink Thread**: `blink()` creates daemon thread. If main program exits before `led.close()`, thread may not clean up properly. Always call `close()` or use context manager.

**Speaker File Not Found**: `play()` raises FileNotFoundError if file doesn't exist (line 142). Check path before calling.

**Speaker Format Auto-Detection**: Format determined by file extension (line 59). Incorrect extension (e.g., .mp3 file named .wav) will fail to load.

**Music pygame Warnings**: pygame prints "Hello from pygame community" message. Line 65-67 suppress this via warnings filter.

**Music Volume Independence**: Sound effect volume and music volume are separate. Sound object volumes are also independent (line 179-182 comments). Setting music volume doesn't affect sound effects.

**Tone Play_tone_for**: Doesn't stop stream after playback (line 327-328 commented out). May accumulate unclosed streams. Use Music object as singleton.

**Speaker Task ID**: Returned UUID is string. Store it to control playback. Losing task ID means can't stop/pause that playback (must track in `list_tasks()`).

**Speaker Chunk Size**: Fixed 1024 frames (line 95). Large files may lag on slow Pi models. Consider reducing chunk size for better responsiveness.

**NOTES Array Indexing**: Direct index access (e.g., `Music.NOTES[60]`) is valid but fragile. Use `note("C4")` method for name-based lookup (line 158).

**Motor Config Persistence**: Motor ID and reverse settings persist across reboots via fileDB. Changing wiring requires calling `set_left_id()` / `set_right_id()` again.
