# robot-hat: Foundations

<!-- Status: complete | Iteration: 1 -->

> Covers: `basic.py`, `i2c.py`, `pin.py`, `pwm.py`

## Purpose

Foundation classes for GPIO, I2C bus communication, PWM signal generation, and debug logging. All hardware control classes inherit from `_Basic_class` for unified logging.

## Hardware

| Component | Bus | Address | Protocol | Chip | Pins |
|-----------|-----|---------|----------|------|------|
| PWM/ADC MCU | I2C-1 | 0x14, 0x15, 0x16 | I2C | STM32 72MHz | - |
| GPIO | - | - | gpiozero | BCM GPIO | D0-D16, SW, LED, etc |
| PWM Channels | I2C | 0x14-0x16 | I2C registers | STM32 timers | P0-P19 (20 channels) |

## API Reference

### _Basic_class (basic.py:7)

**Purpose**: Base class providing logging infrastructure for all robot-hat classes.

**Thread-safe**: No (logging instances are per-object).

#### `__init__(debug_level='warning')`
Initialize logging. `debug_level` accepts int (0-4) or str ('critical', 'error', 'warning', 'info', 'debug'). Creates timestamped logger with StreamHandler.

#### `debug_level` (property)
Get/set debug level. Accepts 0-4 or string names. Updates both logger and handler levels.

**Logging Methods**:
- `_debug(msg)`, `_info(msg)`, `_warning(msg)`, `_error(msg)`, `_critical(msg)`

**Debug Levels**:

| Level | Int | Name | Use Case |
|-------|-----|------|----------|
| 0 | CRITICAL | System failures |
| 1 | ERROR | Operation failures |
| 2 | WARNING | Default, unexpected conditions |
| 3 | INFO | State changes |
| 4 | DEBUG | Detailed I2C/GPIO traces |

---

### I2C(_Basic_class) (i2c.py:23)

**Purpose**: I2C bus communication with automatic retry on OSError.

**Thread-safe**: Commented-out multiprocessing.Value lock (line 29). Current implementation: No.

#### `__init__(address=None, bus=1, *args, **kwargs)`
Initialize I2C bus. If `address` is list, scans bus and selects first found device from list. Uses smbus2.SMBus.

**Parameters**:
- `address`: int or list of ints (e.g., [0x14, 0x15])
- `bus`: I2C bus number (default 1 on Raspberry Pi)

#### `RETRY` (class constant)
Value: 5. Number of retries for OSError (bus contention/transient failures).

#### `write(data: int|list|bytearray) -> None`
Write data to I2C device. Routes to:
- 1 byte → `_write_byte(data)`
- 2 bytes → `_write_byte_data(reg, data)`
- 3 bytes → `_write_word_data(reg, word)` (little-endian)
- 4+ bytes → `_write_i2c_block_data(reg, data[1:])`

#### `read(length=1) -> list`
Read `length` bytes using `_read_byte()` in loop. Returns list of ints.

#### `mem_write(data: int|list|bytearray, memaddr: int) -> None`
Write to register address. Converts int to little-endian byte list if needed. Calls `_write_i2c_block_data(memaddr, data)`.

#### `mem_read(length: int, memaddr: int) -> list`
Read `length` bytes from register `memaddr`. Returns list of ints.

#### `scan() -> list`
Scan I2C bus for devices using `i2cdetect -y {bus}` command. Returns list of addresses (e.g., [0x14, 0x15]).

#### `is_ready() -> bool`
Alias for `is_avaliable()` (typo in original). Checks if device address is present on bus.

#### `is_avaliable() -> bool`
Returns True if `self.address` found in `scan()` results.

**Private Methods** (decorated with `@_retry_wrapper`):
- `_write_byte(data)`, `_write_byte_data(reg, data)`, `_write_word_data(reg, data)`
- `_write_i2c_block_data(reg, data)`, `_read_byte()`, `_read_byte_data(reg)`
- `_read_word_data(reg)`, `_read_i2c_block_data(reg, num)`

All retry up to 5 times on OSError, return False on failure.

**I2C Addresses Used**:
- 0x14, 0x15, 0x16: PWM/ADC MCU (typical scan result: [0x14, 0x15])
- 0x53: ADXL345 accelerometer

---

### Pin(_Basic_class) (pin.py:7)

**Purpose**: GPIO pin manipulation using gpiozero.

**Thread-safe**: gpiozero handles GPIO state, but concurrent mode switches on same pin are unsafe.

#### `__init__(pin: int|str, mode=None, pull=None, active_state: bool=None, *args, **kwargs)`
Initialize GPIO pin. Converts pin names (e.g., "D0", "LED") to GPIO numbers via `_dict`.

**Parameters**:
- `pin`: GPIO number (int) or name (str, e.g., "D0", "SW", "LED")
- `mode`: `Pin.OUT` (0x01) or `Pin.IN` (0x02), or None (default OUT)
- `pull`: `Pin.PULL_UP` (0x11), `Pin.PULL_DOWN` (0x12), `Pin.PULL_NONE` (None)
- `active_state`: If False, inverts logic (HIGH=0, LOW=1)

#### Pin Name Mapping (`_dict`)

| Name | GPIO | Purpose |
|------|------|---------|
| D0 | 17 | General digital I/O |
| D1 | 4 | General digital I/O |
| D2 | 27 | General digital I/O |
| D3 | 22 | General digital I/O |
| D4 | 23 | Motor direction |
| D5 | 24 | Motor direction |
| D9 | 6 | General digital I/O |
| D10 | 12 | General digital I/O |
| D11 | 13 | General digital I/O |
| D12 | 19 | General digital I/O |
| D13 | 16 | General digital I/O |
| D14 | 26 | General digital I/O |
| D15 | 20 | General digital I/O |
| D16 | 21 | General digital I/O |
| SW / USER | 25 | Button |
| LED | 26 | Onboard LED |
| MCURST | 5 | MCU reset |
| BOARD_TYPE | 12 | Board detection |
| RST | 16 | General reset |
| BLEINT | 13 | Bluetooth interrupt |
| BLERST | 20 | Bluetooth reset |
| CE | 8 | Chip enable |

#### `setup(mode, pull=None, active_state=None) -> None`
Reconfigure pin mode. Closes existing GPIO object and creates new OutputDevice or InputDevice.

#### `value(value: bool = None) -> int`
Get/set pin value. If mode is OUT and `value` is None, switches to IN before reading. If mode is IN and `value` is not None, switches to OUT before writing.

#### `on() -> int`, `high() -> int`
Set pin to 1. Returns 1.

#### `off() -> int`, `low() -> int`
Set pin to 0. Returns 0.

#### `irq(handler: callable, trigger: int, bouncetime=200, pull=None) -> None`
Set interrupt handler. Creates gpiozero.Button with bounce time in seconds.

**Triggers**:
- `Pin.IRQ_FALLING` (0x21): Trigger on falling edge (button press)
- `Pin.IRQ_RISING` (0x22): Trigger on rising edge (button release)
- `Pin.IRQ_RISING_FALLING` (0x23): Trigger on both edges

**Handler Signature**: `handler()` (no arguments).

#### `close() -> None`
Close GPIO pin. Releases gpiozero resources.

#### `deinit() -> None`
Close pin and pin factory. More thorough cleanup than `close()`.

#### `name() -> str`
Returns pin name (e.g., "GPIO17").

**Implementation Note**: Uses gpiozero.OutputDevice for OUT, gpiozero.InputDevice for IN, gpiozero.Button for IRQ. Auto-switches mode when reading OUT or writing IN.

---

### PWM(I2C) (pwm.py:8)

**Purpose**: PWM signal generation via I2C-controlled MCU.

**Thread-safe**: Inherits I2C retry mechanism. Shared timer state across channels on same timer (see timer mapping).

#### `__init__(channel: int|str, address=None, *args, **kwargs)`
Initialize PWM channel. Accepts 0-19 or "P0"-"P19". Default address: [0x14, 0x15, 0x16].

**Channel to Timer Mapping**:

| Channels | Timer Index | Prescaler Reg | Period Reg |
|----------|-------------|---------------|------------|
| P0-P3 | 0 | 0x40 | 0x44 |
| P4-P7 | 1 | 0x41 | 0x45 |
| P8-P11 | 2 | 0x42 | 0x46 |
| P12-P15 | 3 | 0x43 | 0x47 |
| P16-P17 | 4 | 0x50 | 0x54 |
| P18 | 5 | 0x51 | 0x55 |
| P19 | 6 | 0x52 | 0x56 |

**Warning**: Channels sharing a timer share prescaler and period. Changing frequency on one channel affects all channels on that timer.

#### `CLOCK` (class constant)
Value: 72000000.0 (72 MHz MCU clock).

#### `freq(freq: float = None) -> float`
Get/set frequency (Hz). Calculates optimal prescaler and period (arr) to minimize error. Default: 50 Hz (servo standard).

**Formula**: `actual_freq = CLOCK / prescaler / period`

#### `prescaler(prescaler: int = None) -> int`
Get/set prescaler (1-65535). Writes to MCU register. Affects all channels on same timer.

#### `period(arr: int = None) -> int`
Get/set period (1-65535). Writes to MCU register. Affects all channels on same timer.

**Global Timer State**: `timer` list (line 5) stores `{"arr": value}` for each of 7 timers. Shared across all PWM instances.

#### `pulse_width(pulse_width: int = None) -> int`
Get/set pulse width in clock ticks (0-65535). Writes to channel register (0x20 + channel).

#### `pulse_width_percent(pulse_width_percent: float = None) -> float`
Get/set pulse width as percentage of period (0-100). Converts to ticks via `pulse_width = percent / 100 * period`.

**Register Map**:

| Register | Purpose | Range |
|----------|---------|-------|
| 0x20-0x33 | Channel 0-19 pulse width | 0-65535 |
| 0x40-0x43 | Timer 0-3 prescaler | 1-65535 |
| 0x44-0x47 | Timer 0-3 period | 1-65535 |
| 0x50-0x52 | Timer 4-6 prescaler | 1-65535 |
| 0x54-0x56 | Timer 4-6 period | 1-65535 |

**Example**:
```python
pwm = PWM("P0")
pwm.freq(1000)  # 1 kHz
pwm.pulse_width_percent(50)  # 50% duty cycle
```

## Implementation Notes

**Initialization Order**:
1. I2C bus initialized first (scans for devices at [0x14, 0x15, 0x16])
2. PWM inherits I2C, sets default 50 Hz frequency
3. Pin uses gpiozero, independent of I2C

**Retry Mechanism**: I2C operations retry 5 times on OSError. If all retries fail, returns False.

**Timer Sharing**: PWM channels grouped by timer. Channels P0-P3 share timer 0, so setting frequency on P0 affects P1-P3.

**GPIO Pin Factory**: gpiozero uses singleton pin factory. Call `pin.deinit()` to reset factory, or reuse Pin objects.

## Code Patterns

**Debug Logging**:
```python
from robot_hat import PWM
pwm = PWM(0, debug_level='debug')  # See I2C register writes
```

**I2C Address Scanning**:
```python
from robot_hat import I2C
i2c = I2C([0x14, 0x15])  # Auto-selects first found address
print(f"Connected to: 0x{i2c.address:02X}")
```

**GPIO Interrupt**:
```python
from robot_hat import Pin
btn = Pin("SW", mode=Pin.IN, pull=Pin.PULL_UP)
btn.irq(lambda: print("Pressed!"), trigger=Pin.IRQ_FALLING, bouncetime=50)
```

**PWM Frequency Calculation**:
```python
pwm = PWM("P0")
pwm.freq(1000)  # Library calculates prescaler/period for 1kHz
print(f"Prescaler: {pwm.prescaler()}, Period: {pwm.period()}")
```

## Gotchas

**PWM Timer Sharing**: Setting frequency on P0 will change frequency on P1-P3. Allocate channels from different timers if independent frequencies needed.

**Pin Mode Auto-Switch**: Calling `pin.value()` on OUT pin switches to IN. Calling `pin.value(1)` on IN pin switches to OUT. Explicit `setup()` recommended if mode consistency critical.

**I2C Address List**: If I2C address is list and no devices found, uses first address in list by default (line 50). No error raised.

**Global Timer State**: `timer` list is module-level global. Multiple PWM objects share state. Not multiprocessing-safe.

**GPIO Pin Names**: "D1" and "D7" both map to GPIO 4 (line 31, 37). "SW" and "USER" both map to GPIO 25. "LED" and "D14" both map to GPIO 26. Use consistent names.

**I2C Retry**: OSError retries silently. Check return value of write/read operations (False indicates failure after 5 retries).

**gpiozero Cleanup**: Always call `pin.close()` or `pin.deinit()` to release GPIO resources. Unclosed pins may cause "pin already in use" errors.
