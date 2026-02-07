# robot-hat: Peripherals

<!-- Status: complete | Iteration: 1 -->

> Covers: Buzzer, RGB_LED (from `modules.py`)

## Purpose

Simple peripheral control for common robot components: RGB LED color output and buzzer tone generation.

## Hardware

| Peripheral | Type | Interface | Pins | Notes |
|------------|------|-----------|------|-------|
| RGB_LED | Common anode/cathode RGB LED | PWM (3 channels) | Any 3 PWM channels | Requires 3 PWM objects |
| Buzzer | Active or passive buzzer | PWM or GPIO | 1 PWM or 1 GPIO pin | Passive requires PWM, active uses GPIO |

## API Reference

### RGB_LED (modules.py:127)

**Purpose**: Control 3-pin RGB LED with color mixing via PWM duty cycles.

**Thread-safe**: No (uses PWM class).

#### `__init__(r_pin: PWM, g_pin: PWM, b_pin: PWM, common: int = 1)`
Initialize RGB LED.

**Parameters**:
- `r_pin`, `g_pin`, `b_pin`: PWM objects for red, green, blue channels
- `common`: `RGB_LED.ANODE` (1) for common anode, `RGB_LED.CATHODE` (0) for common cathode

**Common Types**:
- `RGB_LED.ANODE = 1`: LED cathodes connected to PWM pins, anode to VCC. PWM HIGH = LED OFF. Logic inverted.
- `RGB_LED.CATHODE = 0`: LED anodes connected to PWM pins, cathode to GND. PWM HIGH = LED ON. Standard logic.

**Raises**: TypeError if pins not PWM objects, ValueError if common not 0 or 1.

#### `color(color: str|int|tuple|list) -> None`
Set LED color.

**Color Formats**:
- Hex string: `"#FF0000"` or `"FF0000"` (24-bit RGB)
- Int: `0xFF0000` (24-bit RGB, R=bits 16-23, G=8-15, B=0-7)
- Tuple/list: `(255, 0, 0)` or `[255, 0, 0]` (RGB values 0-255)

**Common Anode Inversion**: If `common == ANODE`, inverts RGB values: `output = 255 - input` (lines 182-185).

**PWM Mapping**: Converts 0-255 RGB to 0-100% PWM duty cycle via `value / 255.0 * 100.0`.

**Example**:
```python
from robot_hat.modules import RGB_LED
from robot_hat import PWM

rgb = RGB_LED(PWM("P0"), PWM("P1"), PWM("P2"), common=RGB_LED.ANODE)

rgb.color("#FF0000")        # Red
rgb.color(0x00FF00)         # Green
rgb.color((0, 0, 255))      # Blue
rgb.color("#FFFF00")        # Yellow (R+G)
rgb.color(0xFFFFFF)         # White
rgb.color(0x000000)         # Off
```

**Color Mixing**:

| Color | Hex | RGB |
|-------|-----|-----|
| Red | #FF0000 | (255, 0, 0) |
| Green | #00FF00 | (0, 255, 0) |
| Blue | #0000FF | (0, 0, 255) |
| Yellow | #FFFF00 | (255, 255, 0) |
| Cyan | #00FFFF | (0, 255, 255) |
| Magenta | #FF00FF | (255, 0, 255) |
| White | #FFFFFF | (255, 255, 255) |
| Off | #000000 | (0, 0, 0) |

---

### Buzzer (modules.py:196)

**Purpose**: Control active or passive buzzer for tone generation.

**Thread-safe**: No (uses PWM or Pin class).

#### `__init__(buzzer: PWM|Pin)`
Initialize buzzer.

**Parameters**:
- `buzzer`: PWM object for passive buzzer (frequency control) or Pin object for active buzzer (on/off only)

**Buzzer Types**:
- **Passive buzzer**: Requires PWM signal at specific frequency to generate tone. Use PWM object. Frequency controllable.
- **Active buzzer**: Has internal oscillator, only needs on/off signal. Use Pin object. Fixed frequency (typically 2-4 kHz).

**Raises**: TypeError if buzzer not PWM or Pin.

#### `on() -> None`
Turn buzzer on.
- Passive (PWM): Sets duty cycle to 50%
- Active (Pin): Sets pin HIGH

#### `off() -> None`
Turn buzzer off.
- Passive (PWM): Sets duty cycle to 0%
- Active (Pin): Sets pin LOW

#### `freq(freq: float) -> None`
Set buzzer frequency (passive buzzer only).

**Raises**: TypeError if called on active buzzer (Pin object).

**Parameters**:
- `freq`: Frequency in Hz (use `Music.note()` to convert note names to Hz)

#### `play(freq: float, duration: float = None) -> None`
Play tone at frequency (passive buzzer only).

**Parameters**:
- `freq`: Frequency in Hz
- `duration`: Duration in seconds, or None for continuous play

**Behavior**: Sets frequency, turns on, waits `duration/2`, turns off, waits `duration/2` (50% duty cycle for duration).

**Raises**: TypeError if called on active buzzer.

**Example - Passive Buzzer**:
```python
from robot_hat.modules import Buzzer
from robot_hat import PWM, Music

buzzer = Buzzer(PWM("P8"))
music = Music()

# Play note C4 for 0.5 seconds
freq = music.note("C4")
buzzer.play(freq, 0.5)

# Play frequency directly
buzzer.freq(1000)  # 1 kHz
buzzer.on()
time.sleep(1)
buzzer.off()
```

**Example - Active Buzzer**:
```python
from robot_hat.modules import Buzzer
from robot_hat import Pin

buzzer = Buzzer(Pin("D8"))

# Simple beep pattern
for _ in range(3):
    buzzer.on()
    time.sleep(0.1)
    buzzer.off()
    time.sleep(0.1)
```

**Example - Musical Scale**:
```python
music = Music()
buzzer = Buzzer(PWM("P8"))

notes = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
for note in notes:
    freq = music.note(note)
    buzzer.play(freq, 0.3)
```

---

## Implementation Notes

**RGB LED Common Type Detection**: No auto-detection. Must specify `common` parameter based on LED hardware. Most RGB LEDs are common anode.

**RGB PWM Frequency**: RGB_LED doesn't set PWM frequency. Uses default 50 Hz from PWM class. For flicker-free LED, increase frequency to 100-500 Hz before creating RGB_LED object.

**Buzzer PWM Duty Cycle**: Passive buzzer uses 50% duty cycle (line 215). This is standard for square wave tones. Changing duty cycle affects timbre but not pitch.

**Buzzer Play Duration**: `play()` splits duration 50/50 between on and off (lines 252-253). This creates tone burst with defined rhythm. For continuous tone, use `freq()` + `on()` + `time.sleep()` + `off()`.

**Music Integration**: Buzzer designed to work with Music class. `Music.note()` converts note names to frequencies, `Buzzer.play()` generates tones.

## Code Patterns

**RGB Status Indicator**:
```python
rgb = RGB_LED(PWM("P0"), PWM("P1"), PWM("P2"), common=RGB_LED.ANODE)

# Status colors
STATUS_IDLE = "#00FF00"     # Green
STATUS_ACTIVE = "#0000FF"   # Blue
STATUS_ERROR = "#FF0000"    # Red
STATUS_WARNING = "#FFFF00"  # Yellow

rgb.color(STATUS_IDLE)
# ... robot operation ...
rgb.color(STATUS_ACTIVE)
# ... error occurs ...
rgb.color(STATUS_ERROR)
```

**RGB Breathing Effect**:
```python
import math

rgb = RGB_LED(PWM("P0"), PWM("P1"), PWM("P2"), common=RGB_LED.ANODE)

# Breathing red LED
for i in range(360):
    brightness = int((math.sin(math.radians(i)) + 1) * 127.5)
    rgb.color((brightness, 0, 0))
    time.sleep(0.01)
```

**RGB Color Wheel**:
```python
def hsv_to_rgb(h, s, v):
    """Convert HSV to RGB. h: 0-360, s/v: 0-1"""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h/360, s, v)
    return (int(r*255), int(g*255), int(b*255))

rgb = RGB_LED(PWM("P0"), PWM("P1"), PWM("P2"), common=RGB_LED.ANODE)

for hue in range(0, 360, 5):
    rgb.color(hsv_to_rgb(hue, 1.0, 1.0))
    time.sleep(0.05)
```

**Buzzer Alarm Pattern**:
```python
buzzer = Buzzer(PWM("P8"))

# Two-tone alarm
for _ in range(10):
    buzzer.play(800, 0.2)   # Low tone
    buzzer.play(1200, 0.2)  # High tone
```

**Buzzer Startup Sound**:
```python
buzzer = Buzzer(PWM("P8"))
music = Music()

# Ascending arpeggio
for note in ["C4", "E4", "G4", "C5"]:
    buzzer.play(music.note(note), 0.15)
time.sleep(0.1)
buzzer.off()
```

**Buzzer Morse Code**:
```python
buzzer = Buzzer(Pin("D8"))  # Active buzzer

def dot():
    buzzer.on()
    time.sleep(0.1)
    buzzer.off()
    time.sleep(0.1)

def dash():
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()
    time.sleep(0.1)

# SOS: ... --- ...
for _ in range(3): dot()
time.sleep(0.2)
for _ in range(3): dash()
time.sleep(0.2)
for _ in range(3): dot()
```

## Gotchas

**RGB LED Common Type Mismatch**: If LED doesn't light or colors inverted, wrong `common` parameter. Try toggling between `ANODE` and `CATHODE`.

**RGB LED Brightness**: PWM channels on same timer share frequency (see PWM documentation). Allocate R, G, B to different timers (e.g., P0, P4, P8) to avoid interference.

**RGB LED Power Limits**: Each PWM channel can sink/source limited current (~20 mA per STM32 pin). High brightness on multiple LEDs may exceed limits. Use transistor driver if >3 LEDs.

**RGB Color Accuracy**: 8-bit color (0-255) mapped to PWM duty cycle. At low duty cycles (<5%), nonlinearity causes color shift. Gamma correction may be needed for accurate colors.

**Buzzer Passive vs Active**: Active buzzer has fixed frequency, can't play melodies. Passive buzzer requires PWM, can play any frequency. Check hardware before selecting class (PWM vs Pin).

**Buzzer Volume**: Volume not controllable via software. Passive buzzer volume depends on duty cycle (50% is standard). Active buzzer volume fixed. Use external amplifier for variable volume.

**Buzzer Frequency Limits**: Human hearing: 20 Hz - 20 kHz. Practical buzzer range: 100 Hz - 10 kHz. Some passive buzzers have resonant frequency (~2-4 kHz) where loudest.

**Buzzer Play Duration**: `play(freq, duration)` blocks for `duration` seconds (line 252-253). Not suitable for background tones. Use threading or `freq()` + `on()` for async.

**RGB LED Color Space**: Hex/int colors use sRGB color space. PWM duty cycle is linear, but LED brightness is nonlinear. Perceived brightness doesn't match numerical values (e.g., 50% PWM ≠ 50% perceived brightness).

**PWM Frequency Conflicts**: If RGB LED PWM channels share timer with servo or motor, frequency changes will affect RGB LED. Allocate from independent timers or accept 50 Hz flicker.

**Buzzer MCU Load**: Generating tones via PWM uses MCU timer. Multiple buzzers on same timer will conflict. Use different timers or Music class (pygame-based) for polyphony.

**RGB LED Pin Selection**: PWM channels P15-P19 may have limited availability (reserved for servos in some robots). Check pin allocation before wiring RGB LED.

**Buzzer Blocking**: Both `play()` and `time.sleep()` are blocking. For responsive robot, use threads or async libraries.

**RGB LED Color Mixing**: PWM-based color mixing assumes independent channels. Crosstalk or shared ground can cause color errors. Use separate grounds for each channel if color accuracy critical.
