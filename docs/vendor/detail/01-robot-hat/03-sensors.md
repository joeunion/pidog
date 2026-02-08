# robot-hat: Sensors

<!-- Status: complete | Iteration: 1 -->

> Covers: `adc.py`, and sensor classes (Ultrasonic, ADXL345, Grayscale from `modules.py`)

## Purpose

Analog-to-digital conversion and sensor interfaces for distance measurement (ultrasonic), acceleration (ADXL345), and line tracking (grayscale array).

## Hardware

| Sensor | Type | Bus | Address | Protocol | Data Format | Range |
|--------|------|-----|---------|----------|-------------|-------|
| ADC | 12-bit ADC | I2C-1 | 0x14, 0x15 | I2C register | 0-4095 (0-3.3V) | 8 channels (A0-A7) |
| Ultrasonic | HC-SR04 | GPIO | - | Trigger/Echo pulse | cm (float) | 2-400 cm, timeout 20ms |
| ADXL345 | 3-axis accelerometer | I2C-1 | 0x53 | I2C register | ±256 g (int) | X, Y, Z axes |
| Grayscale | IR reflectance array | ADC | - | ADC channels | 0-4095 | 3 channels (left, center, right) |

## API Reference

### ADC(I2C) (adc.py:5)

**Purpose**: Read analog voltage from 8-channel 12-bit ADC on Robot HAT.

**Thread-safe**: No (inherits I2C limitations).

#### `__init__(chn: int|str, address=None, *args, **kwargs)`
Initialize ADC channel. Accepts 0-7 or "A0"-"A7". Default address: [0x14, 0x15].

**Channel Mapping**: Hardware channels are reversed in software. Channel 0 reads physical channel 7 (line 35: `chn = 7 - chn`).

#### `read() -> int`
Read ADC value (0-4095). 12-bit resolution.

**Implementation**:
- Writes `[chn | 0x10, 0, 0]` to I2C device
- Reads 2 bytes (MSB, LSB)
- Returns `(msb << 8) + lsb`

#### `read_voltage() -> float`
Read ADC value and convert to voltage (0-3.3V).

**Formula**: `voltage = value * 3.3 / 4095`

**Example**:
```python
from robot_hat import ADC
adc = ADC("A0")
value = adc.read()           # 0-4095
voltage = adc.read_voltage()  # 0-3.3V
```

**Accuracy**: 12-bit resolution = 3.3V / 4096 steps ≈ 0.8 mV per step.

---

### Ultrasonic (modules.py:10)

**Purpose**: HC-SR04 ultrasonic distance sensor interface.

**Thread-safe**: No (uses time-sensitive GPIO pulse timing).

#### `__init__(trig: Pin, echo: Pin, timeout=0.02)`
Initialize ultrasonic sensor.

**Parameters**:
- `trig`: Pin object for trigger signal (output)
- `echo`: Pin object for echo signal (input, pull-down)
- `timeout`: Maximum read timeout in seconds (default 20ms)

**Pin Setup**: Auto-closes and reconfigures pins. Echo pin set to IN with PULL_DOWN.

#### `SOUND_SPEED` (class constant)
Value: 343.3 m/s (speed of sound in air at 20°C).

#### `_read() -> float`
Single distance measurement. Returns distance in cm, or -1 on timeout, -2 on pulse error.

**Timing**:
1. Trigger: LOW 1ms → HIGH 10µs → LOW
2. Wait for echo HIGH (timeout if >20ms)
3. Measure echo pulse duration
4. Calculate: `distance_cm = duration * 343.3 / 2 * 100`

#### `read(times: int = 10) -> float`
Read distance with retry. Attempts up to `times` readings, returns first valid result (not -1). Returns -1 if all attempts timeout.

#### `close() -> None`
Close trigger and echo pins.

**Example**:
```python
from robot_hat.modules import Ultrasonic
from robot_hat import Pin

us = Ultrasonic(trig=Pin("D2"), echo=Pin("D3"))
distance = us.read()  # cm
print(f"Distance: {distance} cm")
us.close()
```

**Range**: 2-400 cm typical. Returns -1 if no echo (out of range or no obstacle).

---

### ADXL345(I2C) (modules.py:63)

**Purpose**: ADXL345 3-axis accelerometer interface.

**Thread-safe**: No (inherits I2C limitations).

#### `__init__(*args, address: int = 0x53, bus: int = 1, **kwargs)`
Initialize ADXL345 on I2C address 0x53.

**Registers**:
- `_REG_DATA_X = 0x32`: X-axis data (2 bytes)
- `_REG_DATA_Y = 0x34`: Y-axis data (2 bytes)
- `_REG_DATA_Z = 0x36`: Z-axis data (2 bytes)
- `_REG_POWER_CTL = 0x2D`: Power control

**Axis Constants**:
- `ADXL345.X = 0`, `ADXL345.Y = 1`, `ADXL345.Z = 2`

#### `read(axis: int = None) -> float|list`
Read acceleration.

**Parameters**:
- `axis`: 0 (X), 1 (Y), 2 (Z), or None for all axes

**Returns**: Float for single axis, list `[x, y, z]` for all axes.

**Units**: g (gravitational acceleration, 9.8 m/s²). Range: ±256 g (configured via register 0x31).

#### `_read(axis: int) -> float`
Internal read implementation. Performs two reads (first always returns 0, line 112 comment: "First read value is always 0, so read twice"). Converts 16-bit two's complement to signed value.

**Data Format**:
- 2 bytes per axis: LSB at register addr, MSB at addr+1
- MSB bit 7 = sign bit
- Conversion: If sign bit set, value = `-((raw[1] ^ 255) + 1) * 256 + raw[0]` (lines 116-122)

**Example**:
```python
from robot_hat.modules import ADXL345

accel = ADXL345()
x, y, z = accel.read()  # Read all axes
print(f"X: {x}g, Y: {y}g, Z: {z}g")

x_only = accel.read(ADXL345.X)  # Read X axis only
```

**Calibration**: No built-in calibration. For precise measurements, sample at rest and subtract offset.

---

### Grayscale_Module (modules.py:257)

**Purpose**: 3-channel grayscale line tracking sensor (IR reflectance array).

**Thread-safe**: No (uses ADC class).

#### `__init__(pin0: ADC, pin1: ADC, pin2: ADC, reference: list = None)`
Initialize grayscale module with 3 ADC channels.

**Parameters**:
- `pin0`, `pin1`, `pin2`: ADC objects for left, middle, right sensors
- `reference`: List of 3 reference values for black/white threshold (default: [1000, 1000, 1000])

**Channel Constants**:
- `Grayscale_Module.LEFT = 0`
- `Grayscale_Module.MIDDLE = 1`
- `Grayscale_Module.RIGHT = 2`

#### `reference(ref: list = None) -> list`
Get/set reference threshold values. Must be list of 3 ints.

#### `read(channel: int = None) -> int|list`
Read ADC value(s).

**Parameters**:
- `channel`: 0 (LEFT), 1 (MIDDLE), 2 (RIGHT), or None for all channels

**Returns**: Int for single channel, list `[left, middle, right]` for all channels.

#### `read_status(datas: list = None) -> list`
Read line status (black/white).

**Parameters**:
- `datas`: Optional pre-read ADC values. If None, calls `read()`.

**Returns**: List of 3 ints: 0 = white (data > reference), 1 = black (data ≤ reference).

**Example**:
```python
from robot_hat.modules import Grayscale_Module
from robot_hat import ADC

gs = Grayscale_Module(ADC("A0"), ADC("A1"), ADC("A2"))

# Calibrate on white surface
white_values = gs.read()
gs.reference([v - 200 for v in white_values])  # Threshold 200 below white

# Read line status
status = gs.read_status()  # e.g., [0, 1, 0] = line under center sensor
```

**Typical Values**:
- White surface: 3000-4000
- Black surface: 200-1000
- Threshold: Set 500-1000 below white value

---

## Implementation Notes

**ADC Channel Reversal**: Hardware channels are numbered 0-7, but software inverts this (channel 0 reads physical channel 7). This may be PCB layout-related. Use consistent channel naming throughout project.

**Ultrasonic Timeout**: Default 20ms timeout allows max range ~3.4m (343 m/s * 0.02s / 2). For longer distances, increase timeout parameter.

**Ultrasonic Retry**: `read(times=10)` retries on timeout (-1 return). This handles transient echoes/noise. Adjust `times` parameter for reliability vs speed tradeoff.

**ADXL345 Double Read**: Comment on line 112 states "第一次读的值总是为0，所以多读取一次" ("First read value is always 0, so read twice"). This is device-specific quirk. Both reads perform full register setup (lines 109-110, 113-114).

**ADXL345 Resolution**: Register 0x31 sets range. Current implementation uses default (likely ±2g or ±16g). Check datasheet for precision requirements. Value divided by 256.0 (line 123) suggests 256 LSB/g scaling.

**Grayscale Reference**: Default [1000, 1000, 1000] is arbitrary. Calibration required for each robot/surface combination. Calibrate on both white and black, set threshold midpoint.

**Grayscale Status Inversion**: Line 317: `0 if data > reference else 1`. Returns 0 for white (high ADC), 1 for black (low ADC). IR sensors read higher on reflective surfaces.

## Code Patterns

**ADC Battery Voltage Monitoring**:
```python
# Example from utils.py:get_battery_voltage()
adc = ADC("A4")
raw_voltage = adc.read_voltage()
battery_voltage = raw_voltage * 3  # Voltage divider (3:1 ratio)
```

**Ultrasonic Obstacle Avoidance**:
```python
us = Ultrasonic(Pin("D2"), Pin("D3"))
while True:
    distance = us.read()
    if distance > 0 and distance < 20:
        print("Obstacle detected!")
        # Stop motors
    time.sleep(0.1)
```

**ADXL345 Tilt Detection**:
```python
accel = ADXL345()
x, y, z = accel.read()

# Detect tilt (assuming flat Z = 1g)
if abs(z - 1.0) > 0.3:
    print("Robot tilted!")

# Detect orientation
if x > 0.7:
    print("Tilted right")
elif x < -0.7:
    print("Tilted left")
```

**Grayscale Line Following**:
```python
gs = Grayscale_Module(ADC("A0"), ADC("A1"), ADC("A2"))
gs.reference([2000, 2000, 2000])  # Set after white calibration

status = gs.read_status()  # [left, middle, right]

if status == [0, 1, 0]:
    # Line centered - go straight
    motors.forward(50)
elif status == [1, 1, 0]:
    # Line on left - turn left
    motors.turn_left(30)
elif status == [0, 1, 1]:
    # Line on right - turn right
    motors.turn_right(30)
elif status == [0, 0, 0]:
    # Lost line - stop or search
    motors.stop()
```

**Grayscale Calibration Routine**:
```python
# Place robot on white surface
white = gs.read()
print(f"White: {white}")

# Place robot on black line
input("Place on black line, press Enter")
black = gs.read()
print(f"Black: {black}")

# Set threshold midpoint
threshold = [(w + b) // 2 for w, b in zip(white, black)]
gs.reference(threshold)
print(f"Threshold: {threshold}")
```

## Gotchas

**ADC Channel Reversal**: Software channel 0 = hardware channel 7. If wiring diagram shows "A0 - left sensor", connect to hardware pin labeled A0, access as `ADC("A0")` (which reads hardware channel 7). Confusing but intentional.

**ADC Read Sequence**: Must write command `[chn | 0x10, 0, 0]` before reading (line 47). Direct I2C read without write will fail or return stale data.

**Ultrasonic Timeout Return**: Returns -1 on timeout, -2 on pulse error. Check for negative values before using distance. `if distance > 0: ...` handles both error cases.

**Ultrasonic Pin Requirements**: Trig must be output-capable, echo must be input-capable. Using same pin for both won't work. Hardware limitation of HC-SR04 protocol.

**Ultrasonic Interference**: Multiple ultrasonic sensors can interfere. Space sensors >10cm apart, or pulse sequentially with delays.

**ADXL345 First Read Zero**: Always returns 0 on first read after register write (line 112 comment). Code compensates with double-read. Don't optimize out second read.

**ADXL345 Sign Bit Handling**: Two's complement conversion on lines 116-121. Bit manipulation: `raw[1] ^ 128 ^ 127` inverts bits, `(raw_1 + 1) * -1` negates. Fragile code, don't modify.

**ADXL345 Scaling**: Division by 256.0 (line 123) implies 256 LSB/g scale factor. If ADXL345 configured differently (via register 0x31), this won't match. Check datasheet for DATA_FORMAT register.

**Grayscale ADC Overlap**: If grayscale uses ADC channels also used elsewhere (e.g., battery monitoring on A4), ensure no simultaneous access. ADC class is not thread-safe.

**Grayscale Reference Persistence**: Reference values not saved to config. Robot must recalibrate on each boot, or implement persistent storage (fileDB).

**Grayscale Ambient Light**: IR sensors affected by ambient light. Performance degrades in bright sunlight. Use shielding or filter IR wavelength (typically 940nm).

**Ultrasonic Temperature Dependency**: Sound speed varies with temperature (~0.6 m/s per °C). Constant 343.3 m/s assumes 20°C. For precision, adjust: `speed = 331.3 + 0.606 * temp_celsius`.

**Multiple ADC Instances**: Creating multiple `ADC("A0")` objects shares same I2C address but separate channel register. No conflict, but wasteful. Reuse objects when possible.
