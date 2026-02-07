# voice-assistant: Core

<!-- Status: COMPLETE | Iteration: 1 -->

> **Source files:** `voice_assistant.py`, `_base.py`

## Purpose

`VoiceAssistant` is the top-level orchestrator class that wires together STT, TTS, and LLM components into a trigger-driven main loop with hook points at every lifecycle stage. `_Base` is a minimal mixin providing a logger instance to all internal classes.

---

## API Reference

### VoiceAssistant Class (`voice_assistant.py`)

#### Constructor

```python
VoiceAssistant(
    llm: LLM,
    name: str = "Buddy",
    with_image: bool = True,
    tts_model: str = "en_US-ryan-low",
    stt_language: str = "en-us",
    keyboard_enable: bool = True,
    wake_enable: bool = True,
    wake_word: list = ["hey buddy"],
    answer_on_wake: str = "Hi there",
    welcome: str = "Hi, I'm Buddy...",
    instructions: str = "You are a helpful assistant, named {name}.",
    disable_think: bool = False,
    round_cooldown: float = 1.0,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm` | `LLM` | (required) | Language model instance for the think step |
| `name` | `str` | `"Buddy"` | Assistant name, substituted into `instructions` via `{name}` |
| `with_image` | `bool` | `True` | If True, initializes picamera2 and captures frames before LLM calls |
| `tts_model` | `str` | `"en_US-ryan-low"` | Piper TTS model name (auto-downloads if missing) |
| `stt_language` | `str` | `"en-us"` | Vosk language code (auto-downloads model if missing) |
| `keyboard_enable` | `bool` | `True` | Register keyboard input trigger |
| `wake_enable` | `bool` | `True` | Register wake word trigger |
| `wake_word` | `list[str]` | `["hey buddy"]` | Wake phrases (case-insensitive matching) |
| `answer_on_wake` | `str` | `"Hi there"` | Spoken via TTS when wake word detected; empty string to disable |
| `welcome` | `str` | `"Hi, I'm Buddy..."` | Spoken via TTS on startup |
| `instructions` | `str` | `"You are a helpful assistant, named {name}."` | LLM system prompt; `{name}` is replaced at init time |
| `disable_think` | `bool` | `False` | If True, passes `think=False` to `llm.prompt()` (disables chain-of-thought) |
| `round_cooldown` | `float` | `1.0` | Seconds to sleep between conversation rounds |

**Side effects on construction:**
1. Creates `TTS(model=tts_model)` -- Piper instance, may download model
2. Creates `STT(language=stt_language)` -- Vosk instance, fetches model list from network, may download model
3. Calls `llm.set_instructions(instructions)` -- adds system message to LLM history
4. Calls `stt.set_wake_words(wake_word)`
5. If `wake_enable`: registers `trigger_wake_word` trigger
6. If `keyboard_enable`: creates `KeyboardInput()` instance, registers `trigger_keyboard_input`
7. If `with_image`: calls `init_camera()` -- starts picamera2

**Instance attributes set:**

| Attribute | Type | Initial Value | Description |
|-----------|------|---------------|-------------|
| `self.llm` | `LLM` | (passed) | LLM backend |
| `self.tts` | `Piper` | (created) | TTS engine |
| `self.stt` | `Vosk` | (created) | STT engine (monkey-patchable) |
| `self.waked` | `bool` | `False` | Whether wake word was detected |
| `self.running` | `bool` | `False` | Main loop control flag |
| `self.wake_waiting` | `bool` | `False` | Unused in current code |
| `self.triggers` | `list[Callable]` | `[]` | Registered trigger functions |
| `self.picam2` | `Picamera2` | (if with_image) | Camera instance |
| `self.keyboard_input` | `KeyboardInput` | (if keyboard_enable) | Keyboard thread |

---

#### Lifecycle Methods

##### `run() -> None`

Entry point. Calls `main()` wrapped in try/except. On exit (KeyboardInterrupt or exception), sets `self.running = False`, closes STT, keyboard, camera, and calls `on_stop()`.

- **Thread safety:** Must be called from the main thread
- **Side effects:** Blocks until `self.running` is set to False
- **Error handling:** Prints exceptions in red ANSI to stdout, does not re-raise

##### `main() -> None`

The core event loop. Sequence per iteration:

```
1. self.running = True
2. self.on_start()
3. self.tts.say(self.welcome)
4. LOOP:
   a. Check for exclusive triggers (is_active() protocol)
   b. If wake_enable and no exclusive: stt.start_listening_wake_words()
   c. If keyboard_enable: keyboard_input.start()
   d. Poll triggers every 10ms until one fires
   e. Stop wake word / keyboard listeners
   f. result = self.think(message, disable_image)
   g. response_text = self.parse_response(result)
   h. If response_text != '': before_say() → tts.say() → after_say()
   i. on_finish_a_round()
   j. sleep(round_cooldown)
```

##### `listen() -> str`

Records speech after wake word detection. Calls `before_listen()`, then iterates `stt.listen(stream=True)` printing partial results. Returns final text or `None` if empty/False. Calls `after_listen(result)`.

- **Return:** `str` or `None` (if no speech detected)
- **Thread safety:** Not thread-safe (uses shared STT recognizer)

##### `think(text: str, disable_image: bool = False) -> str`

Processes user input through LLM. Calls `before_think(text)`, optionally captures camera image to `./img_input.jpeg`, then calls `llm.prompt()` with streaming. Accumulates streamed tokens, prints them to stdout. Calls `after_think(result)`.

- **Return:** `str` -- stripped LLM response
- **Side effects:** Writes `./img_input.jpeg` if `with_image` and not `disable_image`

##### `capture_image(path: str) -> None`

Captures a single frame from picamera2 to the given file path.

- **Guard:** Only captures if `self.with_image` and `self.picam2` are truthy

##### `init_camera() -> None`

Initializes picamera2 with preview configuration at 640x480. Starts the camera.

- **Side effects:** Imports `picamera2`, creates and starts camera instance
- **Camera format:** XBGR8888 (picamera2 default preview format)

##### `close_camera() -> None`

Closes the picamera2 instance.

---

#### Trigger System

##### `add_trigger(trigger_function: Callable[[], tuple[bool, bool, str]]) -> None`

Registers a trigger function. Triggers are polled in order during the main loop.

**Trigger function signature:**
```python
def my_trigger() -> tuple[bool, bool, str]:
    """
    Returns:
        triggered (bool): True if this trigger fired
        disable_image (bool): True to skip camera capture this round
        message (str): User input text to send to LLM
    """
```

##### `trigger_wake_word() -> tuple[bool, bool, str]`

Built-in trigger. Checks `stt.is_waked()`. If wake word detected:
1. Stops STT listening
2. Calls `on_wake()` hook
3. Speaks `answer_on_wake` via TTS (if non-empty)
4. Calls `listen()` to record user speech
5. Calls `on_heard(message)` hook
6. Returns `(True, False, message)`

##### `trigger_keyboard_input() -> tuple[bool, bool, str]`

Built-in trigger. Checks `keyboard_input.is_result_ready()`. Returns the typed line as message.

##### Exclusive Trigger Protocol

In the main loop, before starting wake word listening, the code checks each trigger:
```python
if hasattr(trigger, '__self__') and hasattr(trigger.__self__, 'is_active'):
    if trigger.__self__.is_active():
        exclusive_trigger_active = True
```

If any trigger is "active", wake word listening is skipped for that round. This allows conversation-mode triggers to own the microphone.

---

#### Hooks / Callbacks

All hooks are no-op by default. Override in subclasses.

| Hook | Signature | When Called | Typical Use |
|------|-----------|------------|-------------|
| `on_start()` | `() -> None` | Once, at start of `main()` | Initialize hardware |
| `on_wake()` | `() -> None` | After wake word detected, before listening | Play sound, animate |
| `on_heard(text: str)` | `(str) -> None` | After speech transcribed | Log, process commands |
| `before_listen()` | `() -> None` | Before STT starts recording | Pause other audio |
| `after_listen(stt_result: str)` | `(str) -> None` | After STT completes | Resume other audio |
| `before_think(text: str)` | `(str) -> None` | Before LLM call | Show thinking animation |
| `after_think(text: str)` | `(str) -> None` | After LLM response received | Process actions |
| `parse_response(text: str)` | `(str) -> str` | After `think()`, before TTS | Strip action lines, return speech-only text |
| `before_say(text: str)` | `(str) -> None` | Before TTS speaks | Mouth animation start |
| `after_say(text: str)` | `(str) -> None` | After TTS finishes | Mouth animation stop |
| `on_finish_a_round()` | `() -> None` | After speak completes | Update state, log |
| `on_stop()` | `() -> None` | During cleanup in `run()` finally block | Release resources |

---

### _Base Class (`_base.py`)

```python
class _Base:
    def __init__(self, *args, log: logging.Logger = Logger(__name__),
                 log_level: [int, str] = logging.INFO, **kwargs):
```

Minimal base class providing a `self.log` logger attribute. Used by `Piper`, `Espeak`, `Pico2Wave`, `OpenAI_TTS`, and `AudioPlayer`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log` | `logging.Logger` | `Logger(__name__)` | Logger instance |
| `log_level` | `int` or `str` | `logging.INFO` | Log level, applied via `setLevel()` |

**Note:** Uses the custom `Logger` class from `_logger.py` which provides colored console output.

---

## Implementation Notes

### State Machine

VoiceAssistant does not have an explicit state enum. State is implicit in the main loop position:

```
IDLE        -- polling triggers (lines 349-357 in main loop)
LISTENING   -- inside listen() → stt.listen(stream=True)
THINKING    -- inside think() → llm.prompt(stream=True)
SPEAKING    -- inside tts.say()
COOLDOWN    -- time.sleep(round_cooldown)
```

The `self.running` flag is the only control mechanism. Setting it to `False` from any thread/hook will cause the main loop and listen/think generators to exit.

### Camera Integration

- Camera is initialized in constructor if `with_image=True`
- Uses `picamera2.create_preview_configuration(main={"size": (640, 480)})`
- Default format is XBGR8888 (not configurable without subclassing)
- Image is captured to `./img_input.jpeg` before each LLM call
- For PiDog: `CameraPool` accesses `self.picam2` directly and converts XBGR to BGR for OpenCV

### Round Cooldown

After each think-speak cycle, `time.sleep(self.round_cooldown)` prevents rapid-fire LLM calls. Default 1.0 second.

---

## Code Patterns

### Basic Usage

```python
from sunfounder_voice_assistant import VoiceAssistant
from sunfounder_voice_assistant.llm import OpenAI

llm = OpenAI(api_key="sk-...", model="gpt-4o-mini")
va = VoiceAssistant(llm=llm, name="Buddy")
va.run()
```

### Subclassing with Hooks

```python
class MyAssistant(VoiceAssistant):
    def on_wake(self):
        print("Wake word detected!")
        # play a sound, flash LED, etc.

    def parse_response(self, text):
        # Extract actions before TTS
        lines = text.split('\n')
        speech_lines = [l for l in lines if not l.startswith('ACTIONS:')]
        return '\n'.join(speech_lines)

    def on_finish_a_round(self):
        print("Round complete")
```

### Monkey-Patching STT

```python
va = VoiceAssistant(llm=llm)
# Replace Vosk with custom STT after construction
va.stt = MoonshineStt()
va.stt.set_wake_words(["hey pidog"])
va.run()
```

### Adding a Custom Trigger

```python
class ConversationTrigger:
    def is_active(self):
        return self._in_conversation

    def __call__(self):
        if self._has_follow_up:
            return (True, False, self._follow_up_text)
        return (False, False, '')

trigger = ConversationTrigger()
va.add_trigger(trigger)  # bound method with __self__.is_active()
```

### Disabling Features

```python
# No camera
va = VoiceAssistant(llm=llm, with_image=False)

# No wake word (keyboard only)
va = VoiceAssistant(llm=llm, wake_enable=False, keyboard_enable=True)

# No keyboard (wake word only, headless)
va = VoiceAssistant(llm=llm, keyboard_enable=False)
```

---

## Gotchas

1. **STT network call at construction**: `Vosk.__init__()` calls `update_model_list()` which fetches JSON from `https://alphacephei.com/vosk/models/model-list.json`. If the network is down, construction raises an exception. There is no retry or offline fallback.

2. **`instructions` uses `.format(name=name)`**: If your instructions string contains literal `{` or `}` braces (e.g., JSON examples), they will cause a `KeyError`. Escape them as `{{` and `}}`.

3. **Image path is hardcoded**: `think()` always writes to `./img_input.jpeg` (relative to CWD). Multiple VoiceAssistant instances would overwrite each other's images.

4. **`parse_response` return value matters**: If it returns empty string `''`, TTS is skipped entirely (the `if response_text != ''` check). Return a space `' '` if you want TTS to attempt speaking.

5. **`self.waked` vs `stt.waked`**: `VoiceAssistant.waked` is set in `trigger_wake_word` but is different from `stt.waked`. The `stt.waked` flag is the authoritative one checked by `stt.is_waked()`.

6. **`wake_waiting` attribute**: Set to `False` in `__init__` but never used anywhere in the codebase. Likely vestigial.

7. **No graceful LLM error handling in `think()`**: If the LLM streaming fails mid-response, the generator just stops. The `after_think` hook receives whatever partial text was accumulated. No retry logic.

8. **`round_cooldown` blocks the main thread**: The sleep at the end of each round blocks everything, including trigger polling. A long cooldown makes the assistant unresponsive.

9. **Camera close order**: In `run()`, `close_camera()` is called in the finally block after `stt.close()`. If STT close blocks, camera remains open.

10. **Thread safety of `self.running`**: Read from multiple threads (listen loop, think loop, trigger polling) without locks. Works in CPython due to the GIL but is not formally thread-safe.
