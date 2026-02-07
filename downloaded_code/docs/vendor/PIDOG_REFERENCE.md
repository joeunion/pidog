# PiDog Vendor Library Reference

> Dense reference for Claude context loading. Tables over prose. Every hardware detail, API signature, pin number.
> For detailed implementation docs, see `detail/` subdirectories.

---

## Hardware Map

### Servo Map (12 Servos)

| # | Name | Pin | Channel | Range (deg) | Default (deg) | Purpose | Speed |
|---|------|-----|---------|-------------|---------------|---------|-------|
| 0 | <!-- TODO --> | | | | | | |
| 1 | <!-- TODO --> | | | | | | |
| 2 | <!-- TODO --> | | | | | | |
| 3 | <!-- TODO --> | | | | | | |
| 4 | <!-- TODO --> | | | | | | |
| 5 | <!-- TODO --> | | | | | | |
| 6 | <!-- TODO --> | | | | | | |
| 7 | <!-- TODO --> | | | | | | |
| 8 | <!-- TODO --> | | | | | | |
| 9 | <!-- TODO --> | | | | | | |
| 10 | <!-- TODO --> | | | | | | |
| 11 | <!-- TODO --> | | | | | | |

### Sensor Table

| Sensor | Type | Bus | Address | Protocol | Data Format | Update Rate |
|--------|------|-----|---------|----------|-------------|-------------|
| IMU (SH3001) | <!-- TODO --> | | | | | |
| Ultrasonic | <!-- TODO --> | | | | | |
| Dual Touch | <!-- TODO --> | | | | | |
| Sound Direction | <!-- TODO --> | | | | | |

### LED Strip

| Property | Value |
|----------|-------|
| Type | <!-- TODO --> |
| I2C Address | <!-- TODO --> |
| LED Count | <!-- TODO --> |
| Available Patterns | <!-- TODO --> |

### GPIO Pin Map

| Pin Label | GPIO # | Connected To | Direction | Notes |
|-----------|--------|--------------|-----------|-------|
| D0 | <!-- TODO --> | | | |
| D1 | <!-- TODO --> | | | |
| D2 | <!-- TODO --> | | | |
| D3 | <!-- TODO --> | | | |
| D4 | <!-- TODO --> | | | |
| D5 | <!-- TODO --> | | | |
| D6 | <!-- TODO --> | | | |
| D7 | <!-- TODO --> | | | |
| D8 | <!-- TODO --> | | | |
| D9 | <!-- TODO --> | | | |

---

## Architecture

### 3-Tier Dependency Chain

<!-- TODO: Document dependency chain: robot-hat → pidog → voice-assistant/brain -->

### Threading Model

| Thread | Owner | Purpose | Lock(s) |
|--------|-------|---------|---------|
| <!-- TODO --> | | | |

### Data Flow

<!-- TODO: Text-based data flow diagram -->

---

## API Quick Reference

### robot-hat Library

#### Hardware Foundation

<!-- TODO: Pin, PWM, I2C, _Basic classes -->

#### Actuators

<!-- TODO: Servo, Motor, LED, Speaker, Music -->

#### Sensors

<!-- TODO: ADC, Ultrasonic, ADXL345, Grayscale -->

#### Peripherals

<!-- TODO: Buzzer, RGB_LED -->

#### Infrastructure

<!-- TODO: Robot, Config, fileDB, Devices, utils, modules -->

### pidog Library

#### Pidog Core

<!-- TODO: Pidog class methods -->

#### Actions System

<!-- TODO: ActionDict, ActionFlow, preset_actions -->

#### Locomotion

<!-- TODO: Walk, Trot gait methods -->

#### Sensors & Peripherals

<!-- TODO: SH3001, RGBStrip, SoundDirection, DualTouch -->

#### LLM Integration

<!-- TODO: anthropic_llm, voice_assistant bridge -->

### voice-assistant Library

#### VoiceAssistant Core

<!-- TODO: VoiceAssistant lifecycle methods -->

#### STT (Speech-to-Text)

<!-- TODO: Vosk STT -->

#### TTS (Text-to-Speech)

<!-- TODO: Piper, eSpeak, pico2wave, OpenAI TTS -->

#### LLM Base

<!-- TODO: LLM base class, HTTP API -->

#### Audio Internals

<!-- TODO: _audio_player, _keyboard_input, _utils, _logger -->

---

## Actions Catalog

### Preset Actions

| Name | Type | Description | Body Parts Used | Duration |
|------|------|-------------|-----------------|----------|
| <!-- TODO: Extract all from preset_actions.py and actions_dictionary.py --> | | | | |

### Action Flow System

<!-- TODO: How ActionFlow sequences work, chaining, interruption -->

---

## Gait Reference

### Walk Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| <!-- TODO --> | | |

### Trot Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| <!-- TODO --> | | |

### IK Constants

| Constant | Value | Description |
|----------|-------|-------------|
| Leg Length | <!-- TODO --> | |
| Foot Length | <!-- TODO --> | |
| Body Width | <!-- TODO --> | |
| Body Length | <!-- TODO --> | |

---

## Audio Pipeline

### TTS Engines

| Engine | Package | Quality | Speed | Offline | Notes |
|--------|---------|---------|-------|---------|-------|
| Piper | <!-- TODO --> | | | | |
| eSpeak | <!-- TODO --> | | | | |
| pico2wave | <!-- TODO --> | | | | |
| OpenAI TTS | <!-- TODO --> | | | | |

### Audio Format Requirements

| Property | Value |
|----------|-------|
| Sample Rate | <!-- TODO --> |
| Bit Depth | <!-- TODO --> |
| Channels | <!-- TODO --> |
| Format | <!-- TODO --> |

---

## Voice Assistant Lifecycle

### State Machine

<!-- TODO: States, transitions, triggers -->

### Triggers

| Trigger | Type | Description |
|---------|------|-------------|
| <!-- TODO --> | | |

### Hook Points

| Hook | When | Parameters |
|------|------|------------|
| <!-- TODO --> | | |

---

## Gotchas

### Hardware
<!-- TODO -->

### Threading
<!-- TODO -->

### Audio
<!-- TODO -->

### GPIO / Cleanup
<!-- TODO -->

### Camera
<!-- TODO -->

### Servo Calibration
<!-- TODO -->
