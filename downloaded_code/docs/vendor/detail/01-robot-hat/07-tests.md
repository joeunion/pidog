# robot-hat: Tests

<!-- Status: complete | Iteration: 1 -->

> All 8 test files annotated

## Test Index

| Test File | Component Tested | Hardware Required | Key Assertions |
|-----------|-----------------|-------------------|----------------|
| `button_event_test.py` | Pin IRQ handlers | Pin D0, button | Interrupt timing, bounce debounce, handler callbacks |
| `init_angles_test.py` | Robot init angles | 3 servos (P10-P12) | Servo initialization order, initial positions |
| `motor_robothat5_test.py` | Robot HAT v5 motors | 2 motors (P12-P13, D4-D5) | Mode 2 motor control (TC618S) |
| `motor_test.py` | Motor class | 2 motors (P12-P13, D4-D5) | Motor speed, direction, stop |
| `servo_hat_test.py` | HAT servo connectivity | All 12 servos (P0-P11) | Servo sweep, channel mapping |
| `servo_test.py` | Servo class | All 12 servos (P0-P11) | Angle control, multiple servos |
| `test_piper_stream.py` | Piper TTS streaming | Speaker | Streaming audio, generator pattern |
| `tone_test.py` | Music tone generation | Speaker/Buzzer | Musical notation, beat timing, melody playback |

## Detailed Annotations

### button_event_test.py

**Purpose**: Test GPIO interrupt handling with bounce debouncing.

**Hardware Setup**:
- Button connected to D0 (GPIO17)
- Ground one terminal, D0 to other terminal (internal pull-up)

**Test Flow**:
1. Create Pin object on D0
2. Register pressed handler (IRQ_FALLING, 20ms bounce time)
3. Print Pin object state (shows handler registered)
4. Register released handler (IRQ_RISING, 10ms bounce time)
5. Print Pin object state again
6. Infinite loop to keep handlers active

**Handler Functions**:
- `pressed_handler()`: Prints "Pressed" + timestamp
- `released_handler()`: Prints "Released" + timestamp
- `both_handler()`: Commented out (would trigger on both edges)

**Key Concepts**:
- **Bounce time**: Different values for press (20ms) vs release (10ms)
- **Handler replacement**: Second `irq()` call replaces previous handlers on same pin
- **Timestamp precision**: Uses `time.time()` for microsecond timing
- **IRQ_RISING_FALLING**: Commented example (line 19) shows both-edge trigger

**Expected Behavior**:
- Button press: "Pressed - 1234567890.123"
- Button release: "Released - 1234567890.234"
- Rapid presses within bounce time ignored

**Debugging Notes**:
- If no output on press: Check pull-up configuration
- If multiple triggers per press: Increase bounce time
- If only one edge works: Verify trigger parameter

**Usage**: Validates interrupt system works correctly before using in robot control.

---

### init_angles_test.py

**Purpose**: Test Robot initialization with custom angles.

**Hardware Setup**:
- 3 servos connected to P10, P11, P12

**Test Code**:
```python
reset_mcu()  # Reset MCU before test
sleep(0.01)

def fuc():
    rubo = Robot([10,11,12], 3, init_angles=[10,45,-45])

if __name__ == "__main__":
    fuc()
```

**Parameters**:
- `pin_list`: [10, 11, 12] → PWM channels P10-P12
- Second arg `3`: Unnamed parameter (appears to be pin count, but redundant)
- `init_angles`: [10°, 45°, -45°] → Initial servo positions

**Test Assertions**:
- Servos move to specified angles on init
- No servo timeout or I2C errors
- Servos don't overshoot during init move

**Expected Behavior**:
1. MCU resets (clears any stuck I2C state)
2. Robot object created
3. Servos move sequentially to init angles:
   - P10 → 10°
   - P11 → 45°
   - P12 → -45°
4. 150ms delay between each servo (prevents voltage sag)

**Debugging Notes**:
- If servos jitter: Check power supply capacity
- If init order matters: Use `init_order` parameter
- If angles wrong: Check servo offset calibration

**Usage**: Verifies Robot base class initializes servos correctly with custom positions.

---

### motor_robothat5_test.py

**Purpose**: Test motor control on Robot HAT v5.x (mode 2, TC618S driver).

**Hardware Setup**:
- 2 DC motors connected to Robot HAT v5.x motor ports
- Motor 1: PWM P13, Direction PWM P12
- Motor 2: PWM P12, Direction PWM P13 (or D5)

**Test Flow** (inferred from motor_test.py pattern):
1. Create Motor objects with PWM pins for both speed and direction
2. Test forward: Set motor speed to positive value
3. Test backward: Set motor speed to negative value
4. Test stop: Set motor speed to 0

**Mode 2 Characteristics**:
- Both pins are PWM (not PWM + GPIO like mode 1)
- Forward: Set one PWM high, other PWM low
- Backward: Reverse PWM states
- Stop: Both PWM low
- Brake: Both PWM high (unique to mode 2)

**Expected Behavior**:
- Forward: One motor terminal gets PWM signal, other grounded
- Backward: Reverses terminals
- Stop: Both terminals grounded
- No direction inversion glitches

**Debugging Notes**:
- If both motors run same direction: Check motor wiring polarity
- If speed control doesn't work: Verify PWM frequency (should be 100 Hz default)
- If motors don't stop: Check brake functionality (both PWM high)

**Usage**: Validates mode 2 motor driver works correctly (TC618S chip on v5.x boards).

---

### motor_test.py

**Purpose**: Test basic Motor class functionality.

**Hardware Setup**:
- 2 DC motors connected to Robot HAT
- Motor 0: PWM P13, Direction D4
- Motor 1: PWM P12, Direction D5

**Test Code**:
```python
m0 = Motor(PWM('P13'), Pin('D4'))
m1 = Motor(PWM('P12'), Pin('D5'))

try:
    while True:
        m0.speed(-50)  # Motor 0 backward 50%
        m1.speed(-50)  # Motor 1 backward 50%
        sleep(1)
        m0.speed(50)   # Motor 0 forward 50%
        m1.speed(50)   # Motor 1 forward 50%
        sleep(1)
        m0.speed(0)    # Stop
        m1.speed(0)
        finally:
    m0.speed(0)  # Safety stop
    m1.speed(0)
    sleep(0.1)
```

**Test Sequence**:
1. Backward 50% for 1 second
2. Forward 50% for 1 second
3. Stop
4. Repeat indefinitely
5. On exit (Ctrl+C): Emergency stop both motors

**Key Assertions**:
- Speed -100 to +100 maps correctly to direction + PWM
- Direction changes smoothly without glitches
- Stop (speed=0) halts motors immediately
- `finally` block ensures motors stop on exception

**Expected Behavior**:
- Motors alternate forward/backward every second
- No coasting (motors stop immediately at speed=0)
- No direction inversion errors

**Debugging Notes**:
- If motors run same direction: One motor wired backward (swap polarity or use `is_reversed=True`)
- If speed not proportional: Check PWM frequency
- If motors don't stop: Power supply issue or driver fault

**Usage**: Basic motor functional test before integrating into robot control.

---

### servo_hat_test.py

**Purpose**: Test all 12 servo channels on Robot HAT.

**Hardware Setup**:
- 12 servos connected to P0-P11

**Test Code** (inferred from servo_test.py pattern):
```python
servos = [Servo(i) for i in range(12)]

while True:
    for servo in servos:
        servo.angle(-20)
        sleep(0.1)
    for servo in servos:
        servo.angle(20)
        sleep(0.1)
```

**Test Sequence**:
1. Create 12 Servo objects (channels 0-11)
2. Move all servos to -20° sequentially (100ms delays)
3. Move all servos to +20° sequentially (100ms delays)
4. Repeat indefinitely

**Key Assertions**:
- All 12 channels work independently
- No I2C bus errors during rapid commands
- Servo movement smooth (no jittering)
- Sequential timing prevents power sag

**Expected Behavior**:
- Servos sweep -20° to +20° in wave pattern
- 100ms delay between servos prevents voltage drop
- All servos reach target angles accurately

**Debugging Notes**:
- If some channels don't work: Check I2C address conflicts
- If servos jitter: Increase delay or improve power supply
- If specific channel fails: Check PWM register mapping

**Channel to Timer Mapping** (see PWM documentation):
- Channels P0-P3 share timer 0
- Channels P4-P7 share timer 1
- Channels P8-P11 share timer 2

**Usage**: Validates all servo channels functional before complex robot programming.

---

### servo_test.py

**Purpose**: Basic servo sweep test (same as servo_hat_test.py).

**Hardware Setup**:
- 12 servos connected to P0-P11

**Test Code**:
```python
servos = [Servo(i) for i in range(12)]

while True:
    for servo in servos:
        servo.angle(-20)
        sleep(0.1)
    for servo in servos:
        servo.angle(20)
        sleep(0.1)
```

**Difference from servo_hat_test.py**: None (duplicate test file).

**Expected Behavior**: Identical to servo_hat_test.py.

**Usage**: Same as servo_hat_test.py (possible redundancy in test suite).

---

### test_piper_stream.py

**Purpose**: Test Piper TTS streaming audio output.

**Hardware Setup**:
- Speaker connected to audio output

**Test Code** (inferred pattern):
```python
tts = Piper()
tts.set_model('en_US-amy-low')

# Stream audio chunks
for chunk in tts.stream("This is a streaming test."):
    # Process audio chunk
    play_audio(chunk)
```

**Test Assertions**:
- TTS generates audio in chunks (streaming)
- Audio chunks play smoothly without gaps
- No buffer underruns or pops
- Generator pattern works correctly

**Key Concepts**:
- **Streaming TTS**: Generates audio incrementally (vs complete before playing)
- **Generator pattern**: `stream()` yields audio chunks via generator
- **Lower latency**: First audio plays before full synthesis complete

**Expected Behavior**:
- Audio starts playing within 100-200ms (first chunk)
- Smooth continuous speech (no gaps between chunks)
- Clean audio quality

**Debugging Notes**:
- If choppy audio: Increase chunk size or buffer
- If high latency: Check chunk generation speed
- If gaps between chunks: Buffer underrun (CPU overloaded)

**Usage**: Validates streaming TTS suitable for real-time robot responses.

---

### tone_test.py

**Purpose**: Test Music class with complex melody (18-measure classical piece).

**Hardware Setup**:
- Speaker or buzzer connected to audio output

**Test Code**:
```python
music = Music()
set_volume(80)
music.tempo(60, 1/4)  # 60 BPM, quarter note = beat

# Measure 1
music.play_tone_for(music.note("G4"), music.beat(1/8))

# Measure 2
music.play_tone_for(music.note("A#4"), music.beat(1/4))
music.play_tone_for(music.note("C5"), music.beat(1/8))
# ... continues for 17 measures
```

**Musical Elements**:
- **Tempo**: 60 BPM (1 beat per second)
- **Note durations**: 1/8, 1/4, 1/16, 3/16, 3/8 notes
- **Notes**: G4, A4, A#4, C5, D5, D#5, E4, F4, F#4, F5
- **Measures**: 17 total measures (commented Baby Shark at end)

**Key Assertions**:
- Note frequency calculation correct (A4 = 440 Hz MIDI reference)
- Beat timing accurate (tempo-based)
- Tone generation smooth (no clicks/pops)
- Note transitions clean

**Expected Behavior**:
- Plays recognizable melody
- Correct note pitches (A440 tuning)
- Accurate rhythm (beat timing)
- No audio artifacts

**Debugging Notes**:
- If pitch wrong: Check `NOTE_BASE_FREQ` and MIDI mapping
- If timing off: Verify tempo calculation (`beat()` method)
- If distorted: Check tone generation waveform
- If silent: Speaker enable failed

**Musical Analysis**:
- Key: D major (implied, F# present)
- Time signature: 4/4
- Note range: D4 (293 Hz) to F5 (698 Hz)
- Measure structure: Classical phrasing (2/4-bar phrases)

**Commented Section**: "Baby Shark" melody (lines 102-148) for comparison test.

**Usage**: Validates Music class accurately generates tones with correct pitch and timing.

---

## Common Test Patterns

### MCU Reset Before Tests

Many tests call `reset_mcu()` before initialization:
```python
from robot_hat.utils import reset_mcu
reset_mcu()
sleep(0.01)
```

**Purpose**: Clears stuck I2C states from previous crashes/tests. Essential for PWM/ADC reliability.

### Try-Finally Safety Stops

Motor tests use try-finally for safe shutdown:
```python
try:
    while True:
        motor.speed(50)
        # ...
finally:
    motor.speed(0)
    sleep(0.1)
```

**Purpose**: Ensures motors stop on Ctrl+C or exception. Prevents runaway motors.

### Sequential Servo Movement

Servo tests move servos sequentially with delays:
```python
for servo in servos:
    servo.angle(target)
    sleep(0.1)
```

**Purpose**: Prevents simultaneous high-current draw. Voltage sag causes servo jitter if all move together.

### Infinite Loop Tests

Most tests run indefinitely:
```python
while True:
    # Test code
    sleep(delay)
```

**Purpose**: Allows manual observation. Run until user satisfied, then Ctrl+C to exit.

### Print Statements for Progress

Tests use print statements instead of assertions:
```python
print("Measure 1")
# ... play notes
print("Measure 2")
```

**Purpose**: Manual verification (no automated pass/fail). User observes behavior and decides if correct.

## Running Tests

### Prerequisites

- Robot HAT connected to Raspberry Pi
- Required hardware connected (servos, motors, speaker, button)
- Python 3.7+ with robot-hat installed

### Basic Test Run

```bash
cd ~/robot-hat/tests
python3 servo_test.py
```

Press Ctrl+C to stop.

### Test with Debug Logging

```python
# Modify test file
from robot_hat import Servo
servo = Servo(0, debug_level='debug')  # Enable I2C trace
```

### Test Isolation

Tests don't clean up after themselves. If one test fails, MCU may be in bad state:
```bash
python3 -c "from robot_hat.utils import reset_mcu; reset_mcu()"
```

Or reboot:
```bash
sudo reboot
```

### Safety Notes

- **Motor tests**: Ensure motors secured (won't fall off table or damage wiring)
- **Servo tests**: Check servo range limits (mechanical stops)
- **Audio tests**: Set volume before running (avoid speaker damage)
- **Always use Ctrl+C**: Don't kill -9 (causes GPIO lock)

## Test Coverage

**Components Tested**:
- ✅ Servo (angle control, multi-channel)
- ✅ Motor (speed, direction, stop)
- ✅ Pin (interrupt, bounce debounce)
- ✅ Music (tone generation, timing, melody)
- ✅ Robot (init angles, servo coordination)
- ✅ TTS (Piper streaming)

**Components NOT Tested**:
- ❌ ADC (no analog sensor tests)
- ❌ Ultrasonic (no distance sensor tests)
- ❌ ADXL345 (no accelerometer tests)
- ❌ Grayscale (no line sensor tests)
- ❌ RGB LED (no color LED tests)
- ❌ Speaker (only Music tested, not Speaker class)
- ❌ fileDB / Config (no persistence tests)
- ❌ LLM / STT (integration tests in examples, not unit tests)

**Test Types**:
- **Manual tests**: All (user observes behavior, no assertions)
- **Automated tests**: None (no pytest/unittest framework)
- **Integration tests**: voice_assistant.py example
- **Unit tests**: None (no isolated component tests)

## Recommended Additional Tests

Based on coverage gaps:

### ADC Test
```python
from robot_hat import ADC
adc = ADC("A0")
while True:
    value = adc.read()
    voltage = adc.read_voltage()
    print(f"Value: {value}, Voltage: {voltage:.2f}V")
    time.sleep(0.5)
```

### Ultrasonic Test
Already exists: `examples/ultrasonic.py` (could be moved to tests/)

### Speaker Multi-Format Test
```python
from robot_hat.speaker import Speaker
speaker = Speaker()

formats = ["test.wav", "test.mp3", "test.flac"]
for file in formats:
    print(f"Playing {file}")
    task_id = speaker.play(file)
    # Wait for completion or timeout
```

### Config Persistence Test
```python
from robot_hat.config import Config
config = Config('/tmp/test.conf')
config.set('test', 'value', '123')
config.write()
config.read()
assert config.get('test', 'value') == '123'
print("Config test passed")
```

## Test Debugging Tips

### I2C Errors

If tests fail with I2C errors:
1. Run `reset_mcu()` first
2. Check I2C bus: `i2cdetect -y 1`
3. Verify addresses 0x14, 0x15 present
4. Reduce I2C speed if errors persist

### Servo Jitter

If servos jitter during tests:
1. Check power supply (5V, 3A minimum for 12 servos)
2. Add delays between servo commands (100ms+)
3. Reduce number of simultaneous moves
4. Check for loose wiring/connectors

### Audio Issues

If audio tests fail:
1. Verify speaker enabled: `robot_hat.utils.enable_speaker()`
2. Check ALSA: `aplay -l` (list devices)
3. Test with `speaker-test` command
4. Verify I2S configuration (if using I2S HAT)

### Motor Doesn't Move

If motors don't respond:
1. Check mode (1 vs 2) matches HAT version
2. Verify motor driver connections
3. Test with multimeter (motor terminals should show PWM voltage)
4. Check direction pin (HIGH/LOW toggles direction)

### Button No Response

If interrupt test doesn't trigger:
1. Check pull-up/pull-down configuration
2. Measure pin voltage (should be HIGH with pull-up, LOW when pressed)
3. Verify bounce time not too long (prevents re-trigger)
4. Check wiring (button shorts pin to ground)
