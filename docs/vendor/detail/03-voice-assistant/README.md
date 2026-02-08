# sunfounder_voice_assistant Library Documentation

<!-- Status: COMPLETE | Iteration: 1 -->

## Overview

`sunfounder_voice_assistant` (v1.0.1) is a modular voice assistant framework that integrates speech-to-text (Vosk), text-to-speech (Piper/eSpeak/pico2wave/OpenAI), and LLM backends (OpenAI-compatible HTTP API) into a single event-driven loop. The `VoiceAssistant` class orchestrates a trigger-based main loop: it polls registered trigger functions (wake word, keyboard, custom) and when triggered, runs a listen-think-speak cycle with pluggable hooks at every stage.

**Version:** 1.0.1
**Package:** `sunfounder_voice_assistant`
**Top-level export:** `VoiceAssistant` (from `voice_assistant.py`)

## Architecture

```
VoiceAssistant (voice_assistant.py)
  |
  |-- STT (stt/vosk.py)          -- Vosk-based speech recognition
  |     |-- sounddevice           -- Microphone input
  |     |-- KaldiRecognizer       -- Vosk recognizer
  |
  |-- TTS (tts/piper.py)         -- Default: Piper neural TTS
  |     |-- AudioPlayer           -- PyAudio output
  |     |-- PiperVoice            -- ONNX inference
  |
  |-- LLM (llm/llm.py)           -- OpenAI-compatible HTTP chat
  |     |-- requests              -- HTTP streaming
  |
  |-- picamera2                   -- Optional camera (with_image=True)
  |-- KeyboardInput               -- Optional stdin trigger
```

### Event Flow (One Round)

```
1. main() starts → on_start() → tts.say(welcome)
2. Loop:
   a. Start wake word listener thread (if wake_enable and no exclusive trigger)
   b. Start keyboard listener thread (if keyboard_enable)
   c. Poll triggers every 10ms until one fires
   d. Stop wake word / keyboard listeners
   e. think(message) → before_think() → capture_image → llm.prompt(stream=True) → after_think()
   f. parse_response(result) → subclass can strip actions
   g. before_say() → tts.say(text) → after_say()
   h. on_finish_a_round()
   i. sleep(round_cooldown)
   j. Go to 2.a
```

### Trigger System

Triggers are callable functions with signature `() -> tuple[bool, bool, str]`:
- `triggered: bool` -- whether this trigger fired
- `disable_image: bool` -- skip camera capture for this round
- `message: str` -- the user input text

Built-in triggers:
- `trigger_wake_word` -- listens for wake word, then records speech
- `trigger_keyboard_input` -- polls stdin for typed input

Custom triggers can be added via `add_trigger(fn)`.

### Exclusive Trigger Protocol

If a trigger's bound method has an `is_active()` method on its `__self__`, and that returns `True`, the main loop skips starting the wake word listener. This allows conversation-mode triggers to own the microphone exclusively.

### Threading Model

| Thread | Owner | Purpose |
|--------|-------|---------|
| Main thread | `VoiceAssistant.main()` | Trigger polling, think, speak |
| `wake_word_thread` | `Vosk.start_listening_wake_words()` | Background wake word detection |
| `Keyboard Input Thread` | `KeyboardInput.start()` | Background stdin reading |
| Audio playback threads | `AudioPlayer.play_async()` | Background audio output |

All STT microphone I/O runs via `sounddevice.RawInputStream` callback threads (managed by PortAudio). The main loop is single-threaded for think/speak -- no concurrent LLM calls.

## File Index

| Source File | Documented In | Status |
|-------------|--------------|--------|
| `__init__.py` | (exports `VoiceAssistant` defaults) | COMPLETE |
| `voice_assistant.py` | [01-voice-assistant-core.md](01-voice-assistant-core.md) | COMPLETE |
| `_base.py` | [01-voice-assistant-core.md](01-voice-assistant-core.md) | COMPLETE |
| `stt/vosk.py` | [02-stt.md](02-stt.md) | COMPLETE |
| `stt/__init__.py` | [02-stt.md](02-stt.md) | COMPLETE |
| `tts/piper.py` | [03-tts.md](03-tts.md) | COMPLETE |
| `tts/espeak.py` | [03-tts.md](03-tts.md) | COMPLETE |
| `tts/pico2wave.py` | [03-tts.md](03-tts.md) | COMPLETE |
| `tts/openai_tts.py` | [03-tts.md](03-tts.md) | COMPLETE |
| `tts/piper_models.py` | [03-tts.md](03-tts.md) | COMPLETE |
| `tts/__init__.py` | [03-tts.md](03-tts.md) | COMPLETE |
| `llm/llm.py` | [04-llm.md](04-llm.md) | COMPLETE |
| `llm/__init__.py` | [04-llm.md](04-llm.md) | COMPLETE |
| `_audio_player.py` | [05-audio-internals.md](05-audio-internals.md) | COMPLETE |
| `_keyboard_input.py` | [05-audio-internals.md](05-audio-internals.md) | COMPLETE |
| `_utils.py` | [05-audio-internals.md](05-audio-internals.md) | COMPLETE |
| `_logger.py` | [05-audio-internals.md](05-audio-internals.md) | COMPLETE |
| `_version.py` | (metadata: `__version__ = "1.0.1"`) | COMPLETE |

## Module Defaults (from `__init__.py`)

These module-level constants serve as default constructor arguments for `VoiceAssistant`:

| Constant | Default Value | Purpose |
|----------|---------------|---------|
| `NAME` | `"Buddy"` | Assistant name |
| `WITH_IMAGE` | `True` | Enable camera/vision |
| `TTS_MODEL` | `"en_US-ryan-low"` | Default Piper voice model |
| `STT_LANGUAGE` | `"en-us"` | Default Vosk language |
| `KEYBOARD_ENABLE` | `True` | Enable keyboard input trigger |
| `WAKE_ENABLE` | `True` | Enable wake word detection |
| `WAKE_WORD` | `["hey buddy"]` | Default wake phrases |
| `ANSWER_ON_WAKE` | `"Hi there"` | Spoken on wake word detection |
| `WELCOME` | `"Hi, I'm Buddy..."` | Spoken on startup |
| `INSTRUCTIONS` | `"You are a helpful assistant, named Buddy."` | LLM system prompt |

## Key Integration Points for PiDog

PiDog's `AutonomousDog` (in `pidog_brain/autonomous_dog.py`) subclasses or wraps `VoiceAssistant`:

1. **STT replacement**: After `VoiceAssistant.run()` starts, `self.voice_dog.stt` is monkey-patched with `MoonshineStt()` to replace Vosk
2. **Camera sharing**: `VoiceAssistant.picam2` is accessed via `CameraPool` for face/person detection
3. **Hook overrides**: `on_wake`, `on_heard`, `before_think`, `after_think`, `parse_response`, `on_finish_a_round` are overridden to integrate brain state machine
4. **Custom triggers**: Conversation-mode triggers are added via `add_trigger()` with the exclusive trigger protocol
5. **LLM replacement**: The `llm` parameter receives a custom LLM wrapper instead of the default HTTP-based `LLM` class
