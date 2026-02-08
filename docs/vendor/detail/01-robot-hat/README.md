# robot-hat Library Documentation

<!-- Status: complete | Iteration: 1 -->

## Overview

robot-hat is a hardware abstraction library for SunFounder's Robot HAT v4.x and v5.x boards. Version 2.5.1 provides Python interfaces for GPIO, PWM, servos, motors, ADC, I2C, audio, and voice assistant capabilities on Raspberry Pi.

**Hardware Targets:**
- Robot HAT v4.x (motor mode 1, speaker enable pin 20)
- Robot HAT v5.x (motor mode 2, speaker enable pin 12)

**Key Features:**
- 20 PWM channels (P0-P19) via onboard MCU at 72MHz
- 8 ADC channels (A0-A7, 12-bit resolution, 0-3.3V)
- I2C bus at addresses 0x14, 0x15, 0x16
- Servo control with offset calibration
- Motor drivers (TC1508S mode 1, TC618S mode 2)
- Voice assistant framework (STT via Vosk, TTS via Piper, LLM integration)
- Persistent configuration via fileDB and Config

**Dependencies:**
- gpiozero, smbus2, pyaudio, pygame, soundfile, librosa, picamera2
- sunfounder_voice_assistant (external package for LLM/STT/TTS)

## Library Architecture

```
robot_hat/
├── Foundations: basic.py, i2c.py, pin.py, pwm.py
├── Actuators: servo.py, motor.py, led.py, speaker.py, music.py
├── Sensors: adc.py, modules.py (Ultrasonic, ADXL345, Grayscale_Module)
├── Peripherals: modules.py (RGB_LED, Buzzer)
└── Infrastructure: robot.py, config.py, filedb.py, device.py, utils.py, version.py
    └── Shims: llm.py, stt.py, tts.py, voice_assistant.py (re-export sunfounder_voice_assistant)
```

## File Index

| Source File | Documented In | Status |
|-------------|--------------|--------|
| `__init__.py` | (exports) | complete |
| `basic.py` | 01-foundations.md | complete |
| `i2c.py` | 01-foundations.md | complete |
| `pin.py` | 01-foundations.md | complete |
| `pwm.py` | 01-foundations.md | complete |
| `adc.py` | 03-sensors.md | complete |
| `servo.py` | 02-actuators.md | complete |
| `motor.py` | 02-actuators.md | complete |
| `led.py` | 02-actuators.md | complete |
| `speaker.py` | 02-actuators.md | complete |
| `music.py` | 02-actuators.md | complete |
| `config.py` | 05-infrastructure.md | complete |
| `filedb.py` | 05-infrastructure.md | complete |
| `device.py` | 05-infrastructure.md | complete |
| `robot.py` | 05-infrastructure.md | complete |
| `utils.py` | 05-infrastructure.md | complete |
| `modules.py` | 04-peripherals.md | complete |
| `version.py` | 05-infrastructure.md | complete |
| `llm.py` | 05-infrastructure.md | complete |
| `stt.py` | 05-infrastructure.md | complete |
| `tts.py` | 05-infrastructure.md | complete |
| `voice_assistant.py` | 05-infrastructure.md | complete |

## Examples Index

| Example File | Documented In | Status |
|-------------|--------------|--------|
| `led_test.py` | 06-examples.md | complete |
| `pin_input.py` | 06-examples.md | complete |
| `ultrasonic.py` | 06-examples.md | complete |
| `llm_deepseek.py` | 06-examples.md | complete |
| `llm_doubao.py` | 06-examples.md | complete |
| `llm_doubao_with_image.py` | 06-examples.md | complete |
| `llm_gemini.py` | 06-examples.md | complete |
| `llm_grok.py` | 06-examples.md | complete |
| `llm_ollama.py` | 06-examples.md | complete |
| `llm_ollama_with_image.py` | 06-examples.md | complete |
| `llm_openai.py` | 06-examples.md | complete |
| `llm_openai_with_image.py` | 06-examples.md | complete |
| `llm_others.py` | 06-examples.md | complete |
| `llm_qwen.py` | 06-examples.md | complete |
| `stt_vosk_stream.py` | 06-examples.md | complete |
| `stt_vosk_wake_word.py` | 06-examples.md | complete |
| `stt_vosk_wake_word_thread.py` | 06-examples.md | complete |
| `stt_vosk_without_stream.py` | 06-examples.md | complete |
| `tts_espeak.py` | 06-examples.md | complete |
| `tts_openai.py` | 06-examples.md | complete |
| `tts_pico2wave.py` | 06-examples.md | complete |
| `tts_piper.py` | 06-examples.md | complete |
| `voice_assistant.py` | 06-examples.md | complete |

## Tests Index

| Test File | Documented In | Status |
|-----------|--------------|--------|
| `button_event_test.py` | 07-tests.md | complete |
| `init_angles_test.py` | 07-tests.md | complete |
| `motor_robothat5_test.py` | 07-tests.md | complete |
| `motor_test.py` | 07-tests.md | complete |
| `servo_hat_test.py` | 07-tests.md | complete |
| `servo_test.py` | 07-tests.md | complete |
| `test_piper_stream.py` | 07-tests.md | complete |
| `tone_test.py` | 07-tests.md | complete |
