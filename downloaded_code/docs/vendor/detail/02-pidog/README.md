# pidog Library Documentation

<!-- Status: COMPLETE | Iteration: 1 -->

## Overview

The `pidog` library is the core control library for the SunFounder PiDog robot. It provides hardware abstraction, kinematics, gaits, actions, and LLM integration.

**Version**: 1.3.10a1

## Library Architecture

```
pidog/
├── pidog.py              # Core: hardware init, servos, kinematics, IK
├── actions_dictionary.py # Action definitions (stand, sit, walk, etc.)
├── action_flow.py        # Action sequencing and posture management
├── preset_actions.py     # Complex multi-step action implementations
├── walk.py               # Walk gait algorithm (8-section)
├── trot.py               # Trot gait algorithm (2-section)
├── sh3001.py             # IMU sensor driver (accelerometer + gyroscope)
├── rgb_strip.py          # LED strip controller (11 LEDs, I2C)
├── sound_direction.py    # Sound localization (360°, 20° resolution, SPI)
├── dual_touch.py         # Touch sensors (rear/front, GPIO)
├── anthropic_llm.py      # Claude API adapter
├── llm.py                # Re-exports robot_hat.llm
├── stt.py                # Re-exports robot_hat.stt
├── tts.py                # Re-exports robot_hat.tts
└── voice_assistant.py    # Re-exports robot_hat.voice_assistant
```

## Hardware Specifications

### Servo Layout

```
              4 (head pitch)
            5,  6 (head yaw, head roll)
              |
       3,2 --[ ]-- 7,8  (front legs)
             [ ]
       1,0 --[ ]-- 10,11 (hind legs)
              |
             9 (tail)
            /
```

### Servo Indexing

| Index | Body Part | Range (degrees) | Notes |
|-------|-----------|-----------------|-------|
| 0 | Left hind leg (upper) | -90 to 90 | Even indices = upper leg |
| 1 | Left hind leg (lower) | -90 to 90 | Odd indices = lower leg |
| 2 | Left front leg (upper) | -90 to 90 | |
| 3 | Left front leg (lower) | -90 to 90 | |
| 4 | Right hind leg (upper) | -90 to 90 | |
| 5 | Right hind leg (lower) | -90 to 90 | |
| 6 | Right front leg (upper) | -90 to 90 | |
| 7 | Right front leg (lower) | -90 to 90 | |
| 8 | Head yaw | -90 to 90 | Left/right turn |
| 9 | Tail | -90 to 90 | Wag |
| 10 | Head roll | -70 to 70 | Tilt left/right |
| 11 | Head pitch | -45 to 30 | Up/down |

### Physical Dimensions (mm)

| Constant | Value | Description |
|----------|-------|-------------|
| `LEG` | 42 | Upper leg length |
| `FOOT` | 76 | Lower leg length |
| `BODY_LENGTH` | 117 | Front to back |
| `BODY_WIDTH` | 98 | Left to right |

### Peripheral Hardware

| Peripheral | I2C Address | GPIO Pins | Protocol |
|------------|-------------|-----------|----------|
| RGB Strip (SLED1735) | 0x74 | - | I2C |
| IMU (SH3001) | 0x36 | - | I2C |
| Ultrasonic | - | D0 (echo), D1 (trig) | GPIO |
| Touch Sensors | - | D2 (rear), D3 (front) | GPIO |
| Sound Direction | - | GPIO 6 (busy), SPI0 | SPI |

## Servo Speed Constants

| Component | DPS (degrees/sec) | Use |
|-----------|-------------------|-----|
| `HEAD_DPS` | 300 | Head movements |
| `LEGS_DPS` | 428 | Walking, standing |
| `TAIL_DPS` | 500 | Tail wagging |

## Inverse Kinematics Constants

- **PID Balance**: `KP=0.033`, `KI=0.0`, `KD=0.0`
- **Acceleration Sensitivity**: 2g range, 1G = 16384 units
- **Gyroscope Range**: 2000 °/s

## File Index

| Source File | Documented In | Status |
|-------------|--------------|--------|
| `__init__.py` | (exports) | ✅ Done |
| `pidog.py` | 01-pidog-core.md | ✅ Done |
| `actions_dictionary.py` | 02-actions-system.md | ✅ Done |
| `action_flow.py` | 02-actions-system.md | ✅ Done |
| `preset_actions.py` | 02-actions-system.md | ✅ Done |
| `walk.py` | 03-locomotion.md | ✅ Done |
| `trot.py` | 03-locomotion.md | ✅ Done |
| `sh3001.py` | 04-sensors-peripherals.md | ✅ Done |
| `rgb_strip.py` | 04-sensors-peripherals.md | ✅ Done |
| `sound_direction.py` | 04-sensors-peripherals.md | ✅ Done |
| `dual_touch.py` | 04-sensors-peripherals.md | ✅ Done |
| `anthropic_llm.py` | 05-llm-integration.md | ✅ Done |
| `llm.py` | 05-llm-integration.md | ✅ Done |
| `stt.py` | 05-llm-integration.md | ✅ Done |
| `tts.py` | 05-llm-integration.md | ✅ Done |
| `voice_assistant.py` | 05-llm-integration.md | ✅ Done |
| `version.py` | (metadata) | ✅ Done |

## Quick Start

```python
from pidog import Pidog

# Initialize robot
dog = Pidog()

# Stand up
dog.do_action('stand', speed=70)

# Walk forward
dog.do_action('forward', step_count=5, speed=90)

# Read sensors
distance = dog.read_distance()  # Ultrasonic
roll, pitch = dog.roll, dog.pitch  # IMU
touch = dog.dual_touch.read()  # Touch

# Cleanup
dog.close()
```

## Key Design Patterns

1. **Threaded Action Buffers**: Legs, head, tail each have action buffer queues processed by dedicated threads
2. **Immediate vs Queued**: `immediately=True` clears buffer before adding new actions
3. **Speed Control**: 0-100 scale affects delay between servo steps, not DPS
4. **Inverse Kinematics**: Convert cartesian leg positions to servo angles via `legs_angle_calculation()`
5. **Process Isolation**: Ultrasonic runs in separate process to avoid I2C conflicts

## See Also

- `01-pidog-core.md` - Pidog class API reference
- `02-actions-system.md` - Action dictionary and flow control
- `03-locomotion.md` - Walk and trot gait algorithms
- `04-sensors-peripherals.md` - IMU, RGB, touch, sound direction
- `05-llm-integration.md` - Claude API and voice assistant
- `06-basic-examples.md` - 13 basic examples (init, servos, sensors)
- `07-advanced-examples.md` - 23 advanced examples (behaviors, LLM, voice)
- `08-tests.md` - 11 hardware test files

## Examples Index

| Example File | Documented In | Status |
|-------------|--------------|--------|
| `basic_examples/1_pidog_init.py` | 06-basic-examples.md | Done |
| `basic_examples/2_legs_control.py` | 06-basic-examples.md | Done |
| `basic_examples/3_head_control.py` | 06-basic-examples.md | Done |
| `basic_examples/4_tail_control.py` | 06-basic-examples.md | Done |
| `basic_examples/5_stop_actions.py` | 06-basic-examples.md | Done |
| `basic_examples/6_do_preset_actions.py` | 06-basic-examples.md | Done |
| `basic_examples/7_sound_effect.py` | 06-basic-examples.md | Done |
| `basic_examples/8_ultrasonic_read.py` | 06-basic-examples.md | Done |
| `basic_examples/9_rgb_control.py` | 06-basic-examples.md | Done |
| `basic_examples/10_imu_read.py` | 06-basic-examples.md | Done |
| `basic_examples/11_sound_direction_read.py` | 06-basic-examples.md | Done |
| `basic_examples/12_dual_touch_read.py` | 06-basic-examples.md | Done |
| `basic_examples/13_camera_easy_use.py` | 06-basic-examples.md | Done |
| `examples/0_calibration.py` | 07-advanced-examples.md | Done |
| `examples/1_wake_up.py` | 07-advanced-examples.md | Done |
| `examples/2_function_demonstration.py` | 07-advanced-examples.md | Done |
| `examples/3_patrol.py` | 07-advanced-examples.md | Done |
| `examples/4_response.py` | 07-advanced-examples.md | Done |
| `examples/5_rest.py` | 07-advanced-examples.md | Done |
| `examples/6_be_picked_up.py` | 07-advanced-examples.md | Done |
| `examples/7_face_track.py` | 07-advanced-examples.md | Done |
| `examples/8_pushup.py` | 07-advanced-examples.md | Done |
| `examples/9_howling.py` | 07-advanced-examples.md | Done |
| `examples/10_balance.py` | 07-advanced-examples.md | Done |
| `examples/11_keyboard_control.py` | 07-advanced-examples.md | Done |
| `examples/12_app_control.py` | 07-advanced-examples.md | Done |
| `examples/13_ball_track.py` | 07-advanced-examples.md | Done |
| `examples/18.online_llm_test.py` | 07-advanced-examples.md | Done |
| `examples/19_voice_active_dog_ollama.py` | 07-advanced-examples.md | Done |
| `examples/20_voice_active_dog_doubao_cn.py` | 07-advanced-examples.md | Done |
| `examples/20_voice_active_dog_gpt.py` | 07-advanced-examples.md | Done |
| `examples/claude_pidog.py` | 07-advanced-examples.md | Done |
| `examples/curses_utils.py` | 07-advanced-examples.md | Done |
| `examples/custom_actions.py` | 07-advanced-examples.md | Done |
| `examples/servo_zeroing.py` | 07-advanced-examples.md | Done |
| `examples/voice_active_dog.py` | 07-advanced-examples.md | Done |

## Tests Index

| Test File | Documented In | Status |
|-----------|--------------|--------|
| `test/angry_bark.py` | 08-tests.md | Done |
| `test/cover_photo.py` | 08-tests.md | Done |
| `test/dual_touch_test.py` | 08-tests.md | Done |
| `test/imu_test.py` | 08-tests.md | Done |
| `test/power_test.py` | 08-tests.md | Done |
| `test/rgb_strip_test.py` | 08-tests.md | Done |
| `test/sound_direction_test.py` | 08-tests.md | Done |
| `test/stand_test.py` | 08-tests.md | Done |
| `test/tail.py` | 08-tests.md | Done |
| `test/ultrasonic_iic_test.py` | 08-tests.md | Done |
| `test/ultrasonic_test.py` | 08-tests.md | Done |
