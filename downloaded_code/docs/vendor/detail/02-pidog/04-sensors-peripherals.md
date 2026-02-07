# pidog: Sensors & Peripherals

<!-- Status: COMPLETE | Iteration: 1 -->

> Covers: `sh3001.py` (647 lines), `rgb_strip.py` (488 lines), `sound_direction.py` (73 lines), `dual_touch.py` (48 lines)

## Purpose

Hardware drivers for PiDog sensors and peripherals: IMU (accelerometer+gyroscope), RGB LED strip, sound direction detector, and dual touch sensors.

## Hardware Specifications

| Component | Model | I2C/GPIO | Address | Resolution | Update Rate |
|-----------|-------|----------|---------|------------|-------------|
| IMU | SH3001 | I2C | 0x36 | 16-bit acc/gyro | 500Hz (default) |
| RGB Strip | SLED1735 | I2C | 0x74 | 8-bit RGB | 11 LEDs @ 20Hz |
| Touch Sensors | Capacitive | GPIO | D2 (rear), D3 (front) | Binary + slide | Poll-based |
| Sound Direction | TR16F064B | SPI + GPIO | SPI0, GPIO6 | 20° steps | Event-driven |

## API Reference

### Sh3001 Class (sh3001.py:40)

**I2C Address**: 0x36
**Chip ID**: 0x61

#### `__init__(db="sh3001.config")`
Initialize IMU. Configures: acc (500Hz, ±2g), gyro (500Hz, ±2000°/s), temp (63Hz).

#### `sh3001_getimudata(aram, axis)` → acc/gyro data with calibration
- `aram`: 'acc', 'gyro', 'all'
- `axis`: 'x', 'y', 'z', 'xy', 'xz', 'yz', 'xyz'
- Units: Raw (acc: 1G=16384, gyro: 1°/s=16.4)

#### `sh3001_gettempdata()` → float (°C)
Range: -40°C to 85°C, ±2°C accuracy

#### `calibrate(aram, stopfunc, waitfunc)`
- `aram='acc'`: Rotate device 720° all axes, Ctrl+C to save
- `aram='gyro'`: Keep stationary, 500 samples (5s)

#### `set_offset(offset_list)` → Save offsets to config

### Key SH3001 Registers

| Address | Name | Purpose |
|---------|------|---------|
| 0x00-0x0D | ACC/GYRO/TEMP_XYZ | Data output (16-bit, 2 bytes/axis) |
| 0x0F | CHIP_ID | Device ID (0x61) |
| 0x22-0x26 | ACC_CONF | ODR, range (±2/4/8/16g), filter |
| 0x28-0x2B | GYRO_CONF | ODR, range (±125/250/500/1000/2000°/s), filter |
| 0x20-0x21 | TEMP_CONF | ODR (500/250/125/63Hz), enable |

---

### RGBStrip Class (rgb_strip.py:7)

**I2C Address**: 0x74
**LED Count**: 11
**Update Rate**: 20Hz (50ms MIN_DELAY)

#### `__init__(addr=0x74, nums=8)`
Initialize SLED1735 chip. Default 8 LEDs (PiDog uses 11).

#### `set_mode(style='breath', color='white', bps=1, brightness=1)`
**Styles**: 'monochromatic', 'breath', 'boom', 'bark', 'speak', 'listen'
**Colors**: Name ('red', 'cyan'), hex ('#ff0000'), RGB list [r,g,b], int (0xRRGGBB)
**bps**: Beats per second (animation speed)
**brightness**: 0.0-1.0 multiplier

#### `show()` → Display frame (called by thread)
Recalculates frames if `is_changed=True`, displays current frame, sleeps 50ms.

#### `close()` → Turn off LEDs

#### `display(image)` → Write raw RGB (internal)
`image`: List of 11 × [r,g,b] (0-255)

---

### SoundDirection Class (sound_direction.py:36)

**SPI**: Bus 0, Device 0, 10MHz
**GPIO**: Pin 6 (busy signal)
**Resolution**: 20° (360° / 18 positions)

#### `__init__(busy_pin=6)`
Initialize SPI and GPIO.

#### `read()` → int (0-355°) or -1
Returns angle in degrees. Must call `isdetected()` first.

#### `isdetected()` → bool
True if busy pin low (sound detected).

#### `close()` → Release resources

**Protocol**: Master sends 6 bytes (ignored), receives 16-bit angle in bytes 4-5 (little-endian).

---

### DualTouch Class (dual_touch.py:13)

**GPIOs**: D2 (rear), D3 (front), pull-up enabled
**Slide Window**: 0.5s

#### `__init__(sw1='D2', sw2='D3')`
Initialize touch pins.

#### `read()` → TouchStyle
- `'N'`: No touch
- `'L'`: Rear touch
- `'R'`: Front touch
- `'LS'`: Rear → front slide
- `'RS'`: Front → rear slide

**Slide Detection**: Second touch within 0.5s of first.

#### `close()` → Release GPIO

---

## Implementation Notes

### IMU Calibration
**Acc**: Rotate through all orientations, record min/max, offset = (max+min)/2.
**Gyro**: Stationary for 5s, offset = average of 500 samples.

### RGB Animation
Generates frames: `max_frames = int(1 / bps / 0.05)`
Styles use Gaussian distribution: `A×exp(-(x-u)²/(2σ²))/(√(2π)σ) + offset`
- `breath`: Gaussian × cosine (breathing)
- `boom`: Gaussian spreading from center
- `speak`: Gaussian oscillating in/out
- `listen`: Gaussian sweeping left-right

### Sound Direction
Angle conversion: `(360 + 160 - raw) % 360` (zeroing to forward-facing reference).

### Touch Slide State Machine
```
IDLE → Touch L → AFTER_L (0.5s window) → Touch R → Return 'LS'
IDLE → Touch R → AFTER_R (0.5s window) → Touch L → Return 'RS'
```

---

## Code Patterns

### IMU Reading
```python
dog = Pidog()
roll, pitch = dog.roll, dog.pitch  # 20Hz updates
acc = dog.accData  # [ax, ay, az]
gyro = dog.gyroData  # [gx, gy, gz]
```

### RGB Control
```python
dog.rgb_strip.set_mode('breath', 'pink', bps=1.5, brightness=1.0)
dog.rgb_strip.set_mode('speak', 'cyan')  # Change color
dog.rgb_strip.close()  # Turn off
```

### Sound Direction
```python
while True:
    if dog.ears.isdetected():
        angle = dog.ears.read()
        dog.head_move([[angle, 0, 0]], speed=90)
    sleep(0.1)
```

### Touch Interaction
```python
touch = dog.dual_touch.read()
if touch == 'LS':
    dog.do_action('forward')
elif touch == 'RS':
    dog.do_action('backward')
```

---

## Gotchas

1. **IMU Axes Inverted**: `ay` and `az` negated in Pidog code for body-relative coordinates.
2. **RGB Not Instant**: `set_mode()` takes effect within 50ms (next `show()` call).
3. **Sound Requires Busy Check**: Must call `isdetected()` before `read()`.
4. **Touch Polling**: Touches <50ms may be missed (poll rate dependent).
5. **Slide Timeout**: 0.5s max between touches for slide detection.
6. **IMU Calibration Must Save**: Call `imu.set_offset()` to persist, else lost on reboot.
7. **RGB Frame Calc CPU-Intensive**: Changing `bps`/`color` recalculates all frames (~100ms lag on Pi Zero).
8. **Sound Polling Only**: No interrupts, worst-case 100ms latency at 10Hz polling.
9. **IMU Calibrates on Startup**: Don't move robot during first 1s.
10. **RGB I2C Address Fixed**: 0x74 not software-configurable, avoid I2C conflicts.
