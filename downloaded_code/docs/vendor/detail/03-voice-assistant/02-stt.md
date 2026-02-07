# voice-assistant: STT (Speech-to-Text)

<!-- Status: COMPLETE | Iteration: 1 -->

> **Source files:** `stt/vosk.py`, `stt/__init__.py`

## Purpose

Vosk-based speech-to-text with wake word detection, streaming partial results, and VAD-like silence detection. Wraps the Vosk `KaldiRecognizer` with microphone input via `sounddevice`, background wake word listening threads, and automatic model downloading from `alphacephei.com`.

## Exports (`stt/__init__.py`)

```python
from .vosk import Vosk
STT = Vosk  # Alias used by VoiceAssistant
__all__ = ["Vosk", "STT"]
```

---

## Audio Format Requirements

| Property | Value |
|----------|-------|
| Sample Rate | Device default (queried via `sounddevice`), typically 16000 or 44100 Hz |
| Bit Depth | 16-bit signed integer (`int16`) |
| Channels | 1 (mono) |
| Block Size | 1024 frames per callback |
| Format | Raw PCM via `sounddevice.RawInputStream` |
| File Format (for `stt()`) | WAV, mono, PCM, 16-bit |

---

## API Reference

### Vosk Class

#### Constructor

```python
Vosk(
    language: str = None,
    samplerate: int = None,
    device: int = None,
    log: logging.Logger = None,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `language` | `str` | `None` | Vosk language code (e.g., `"en-us"`). If provided, model is downloaded and recognizer is initialized immediately. |
| `samplerate` | `int` | `None` | Audio sample rate. If None, queries device default via `sounddevice`. |
| `device` | `int` | `None` | Audio input device index. If None, uses `sounddevice.default.device`. |
| `log` | `logging.Logger` | `None` | Logger instance. Falls back to `logging.getLogger(__name__)`. |

**Side effects on construction:**
1. Creates `/opt/vosk_models` directory if it does not exist
2. **Fetches model list from network**: `requests.get("https://alphacephei.com/vosk/models/model-list.json")` -- blocks, 10s timeout
3. Suppresses Vosk logging: `SetLogLevel(-1)`
4. Creates threading events: `stop_downloading_event`, `stop_listening_event`
5. If `language` is provided: downloads model (if needed), creates `KaldiRecognizer`

**Instance attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.recognizer` | `KaldiRecognizer` or `None` | Vosk recognizer (None until `init()` called) |
| `self._language` | `str` or `None` | Current language code |
| `self._samplerate` | `int` | Audio sample rate |
| `self._device` | device spec | sounddevice device identifier |
| `self.wake_words` | `list[str]` or `None` | Wake word phrases |
| `self.waked` | `bool` | True after wake word detected |
| `self.wake_word_thread` | `Thread` or `None` | Background wake word thread |
| `self.wake_word_thread_started` | `bool` | Wake word thread running flag |
| `self.downloading` | `bool` | Model download in progress |
| `self.available_models` | `list[dict]` | Vosk model list (type=small, not obsolete) |
| `self.available_languages` | `list[str]` | Available language codes |
| `self.available_model_names` | `list[str]` | Available model names |

---

#### Core Methods

##### `init() -> None`

Loads/downloads the Vosk model for `self._language` and creates a `KaldiRecognizer`.

- **Side effects:** Downloads model ZIP to `/opt/vosk_models` if not present, extracts it
- **Prerequisite:** `self._language` must be set (via constructor or `set_language()`)

##### `is_ready() -> bool`

Returns `True` if `self.recognizer` is not None (model loaded and ready).

##### `set_language(language: str, init: bool = True) -> None`

Sets the language and optionally re-initializes the recognizer.

- **Raises:** `ValueError` if language not in `self.available_languages`

##### `set_wake_words(wake_words: list[str]) -> None`

Sets the list of wake word phrases. Compared case-insensitively against STT results.

##### `close() -> None`

Stops all background threads by setting both stop events and the thread flag.

---

#### Listening Methods

##### `listen(stream: bool = False, device: int = None, samplerate: int = None, timeout: float = None) -> str | Generator`

Primary listening method. Opens a `sounddevice.RawInputStream`, feeds audio to the recognizer.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stream` | `bool` | `False` | If True, returns a generator yielding partial/final results. If False, blocks until final result. |
| `device` | `int` | `None` | Override device (falls back to constructor value) |
| `samplerate` | `int` | `None` | Override sample rate (falls back to constructor value) |
| `timeout` | `float` | `None` | Seconds to wait for speech start. None = no timeout. Timeout only applies before speech starts. |

**Streaming mode return (generator):**

Yields dicts:
```python
{
    "done": False,      # True when final result ready
    "partial": "hello", # Partial transcription (when done=False)
    "final": ""         # Final transcription (when done=True)
}
```

Generator ends after first final result.

**Non-streaming mode return:** `str` -- final transcription text, or empty string on timeout/stop.

- **Thread safety:** Not thread-safe. Uses shared `self.recognizer`.
- **Side effects:** Redirects stderr to `/dev/null` during listening (ALSA noise suppression)

##### `_listen_streaming(q, device, samplerate, callback, timeout) -> Generator`

Internal streaming implementation. Opens `RawInputStream(dtype="int16", channels=1, blocksize=1024)`. Reads from queue, feeds to recognizer. Tracks `speech_started` flag -- timeout only applies before first partial result.

##### `_listen_non_streaming(q, device, samplerate, callback, timeout) -> str`

Internal non-streaming implementation. Same microphone setup. Blocks until `AcceptWaveform` returns True with non-empty text.

##### `listen_until_silence(silence_threshold: float = 2.0) -> str`

Continuous listening mode for VAD-like behavior. Accumulates all recognized utterances until silence is detected.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `silence_threshold` | `float` | `2.0` | Seconds of silence to end listening |

**Behavior:**
- Accumulates finalized text segments into a list
- Tracks `last_speech_time` updated on both partial and final results
- Ends when: silence exceeds `silence_threshold` after speech detected, OR `silence_threshold * 2` if no speech at all
- Returns all accumulated text joined by spaces

- **Return:** `str` -- concatenated recognized text, or empty string
- **Thread safety:** Not thread-safe

##### `stop_listening() -> None`

Sets `stop_listening_event` to signal all listening methods to exit.

---

#### Wake Word Methods

##### `start_listening_wake_words() -> None`

Starts a background thread that continuously listens for wake words.

- **Side effects:** Creates and starts `wake_word_thread` (name: `"wake_word_thread"`)
- Sets `self.waked = False` before starting

##### `wait_for_wake_word() -> None`

Thread target. Loops calling `heard_wake_word()` with 100ms sleep between checks. Sets `self.waked = True` when wake word detected. Exits when `stop_listening_event` is set or wake word found.

##### `heard_wake_word(print_callback=...) -> bool`

Single-shot check. Calls `listen(stream=False)` and compares result (lowercased) against `self.wake_words`.

- **Return:** `bool` -- True if wake word detected
- **Note:** The `listen(stream=False)` call blocks until speech is detected and finalized. The 100ms sleep in `wait_for_wake_word` is between listen attempts, not polling.

##### `wait_until_heard(wake_words=None, print_callback=...) -> str`

Blocking method. Loops calling `listen(stream=False)` until result matches a wake word. Returns the matched word.

##### `is_waked() -> bool`

Returns `self.waked` flag. Checked by `VoiceAssistant.trigger_wake_word()`.

---

#### Model Management

##### `update_model_list() -> None`

Fetches model list from `https://alphacephei.com/vosk/models/model-list.json`. Filters to `type="small"` and `obsolete="false"`.

- **Side effects:** Populates `available_models`, `available_languages`, `available_model_names`
- **Network:** Blocks with 10s timeout

##### `get_model_name(lang: str) -> str`

Returns model name for a language code by index lookup.

##### `get_model_path(lang: str) -> Path`

Returns `Path("/opt/vosk_models", model_name)`.

##### `is_model_downloaded(lang: str) -> bool`

Checks if model directory exists at the expected path.

##### `download_model(lang: str, progress_callback=None, max_retries: int = 5) -> None`

Downloads model ZIP with resume support and progress display.

- **URL pattern:** `https://alphacephei.com/vosk/models/{model_name}.zip`
- **Storage:** `/opt/vosk_models/{model_name}.zip` -> extracted to `/opt/vosk_models/{model_name}/`
- **Resume:** Supports HTTP Range headers for partial downloads
- **Retry:** Exponential backoff (2^n seconds), up to `max_retries`
- **Cancel:** Set `stop_downloading_event` to cancel mid-download; partial file is preserved for resume

##### `cancel_download() -> None`

Public method to cancel an in-progress download.

---

#### File-Based STT

##### `stt(filename: str, stream: bool = False) -> str | Generator`

Performs STT on a WAV file.

- **Raises:** `ValueError` if file is not mono PCM WAV
- **Stream mode:** Returns generator yielding partial/final JSON strings from recognizer
- **Non-stream mode:** Returns single result string

---

## Implementation Notes

### How Wake Word Detection Works

1. `start_listening_wake_words()` spawns `wake_word_thread`
2. Thread calls `heard_wake_word()` in a loop
3. `heard_wake_word()` calls `listen(stream=False)` which blocks until utterance completes
4. Completed utterance is compared (lowercased) to each string in `self.wake_words`
5. Match means exact equality -- no fuzzy matching, no substring matching
6. On match: `self.waked = True`, thread exits
7. Main loop polls `is_waked()` → fires `trigger_wake_word()` → stops listening → records full utterance

**Key insight:** Wake word detection reuses the full Vosk recognizer. It transcribes complete utterances and compares them as strings. This means:
- The wake word must be the entire utterance, not a prefix
- Background noise that produces any text will not match (good)
- Multi-word wake words like "hey buddy" require Vosk to transcribe exactly that phrase

### Vosk Recognizer Internals

- `AcceptWaveform(data)` returns `True` when a complete utterance is detected (silence after speech)
- `Result()` returns JSON: `{"text": "..."}`
- `PartialResult()` returns JSON: `{"partial": "..."}`
- The recognizer is stateful -- partial results build up until finalized
- Block size of 1024 frames at typical 16kHz = 64ms per block

### Audio Queue Pattern

All listening methods use the same pattern:
```python
q = queue.Queue()
def callback(indata, frames, time_info, status):
    q.put(bytes(indata))
# sounddevice callback runs in PortAudio thread
# main thread reads from queue
```

### Stderr Suppression

ALSA and PortAudio print noisy warnings to stderr. The `ignore_stderr()` context manager redirects fd 2 to `/dev/null` during listening.

---

## Code Patterns

### Basic Streaming Listen

```python
from sunfounder_voice_assistant.stt import STT

stt = STT(language="en-us")
for result in stt.listen(stream=True):
    if result["done"]:
        print(f"Final: {result['final']}")
    else:
        print(f"Partial: {result['partial']}", end="\r")
```

### Wake Word with Background Thread

```python
stt = STT(language="en-us")
stt.set_wake_words(["hey robot"])

stt.start_listening_wake_words()
while not stt.is_waked():
    time.sleep(0.1)

stt.stop_listening()
# Now listen for the actual command
text = stt.listen(stream=False)
```

### Listen with Timeout

```python
# Wait up to 5 seconds for speech to start
result = stt.listen(stream=False, timeout=5.0)
if result == '':
    print("No speech detected within timeout")
```

### Continuous Listening (VAD Mode)

```python
# Listen until 3 seconds of silence
text = stt.listen_until_silence(silence_threshold=3.0)
print(f"You said: {text}")
```

### Monkey-Patching for PiDog

```python
# Replace Vosk with Moonshine ONNX
va.stt = MoonshineStt()
va.stt.set_wake_words(["hey pidog"])
# MoonshineStt must implement: listen(), start_listening_wake_words(),
# is_waked(), stop_listening(), close(), set_wake_words()
```

---

## Gotchas

1. **Network required at construction**: `update_model_list()` is called in `__init__()` and makes an HTTP request. No offline fallback. Will raise on network failure.

2. **Model path requires root**: Default model path is `/opt/vosk_models`. Requires write access (typically needs `sudo`). The directory is created with `mkdir(parents=True)` but no permission handling.

3. **Wake word is exact match**: `"hey buddy"` will not match `"hey buddy please"`. The entire Vosk utterance must exactly equal the wake word string (case-insensitive).

4. **Recognizer is shared state**: The same `KaldiRecognizer` is used for wake word detection and post-wake listening. Calling `listen()` while the wake word thread is running will corrupt recognizer state. The `trigger_wake_word` correctly calls `stop_listening()` first.

5. **`_listen_streaming` uses constructor's samplerate/device if None passed**: The `listen()` method passes `device=None, samplerate=None` to `_listen_streaming`, but `sounddevice.RawInputStream` uses its own defaults (not `self._device`/`self._samplerate`). However, `listen_until_silence()` correctly uses `self._samplerate` and `self._device`.

6. **No VAD in Vosk**: Silence detection relies on Vosk's built-in endpointing (when `AcceptWaveform` returns True). There is no energy-based or neural VAD. The `listen_until_silence()` method's "silence detection" is based on time since last recognizer output, not actual audio energy.

7. **`listen(stream=False)` blocks indefinitely**: Without a timeout, non-streaming listen will block forever if no speech is detected (the recognizer never returns True for silence-only input).

8. **`stt.waked` is not reset by `stop_listening()`**: Only `start_listening_wake_words()` resets `self.waked = False`. If you call `stop_listening()` and then check `is_waked()`, it may still return True from a previous detection.

9. **Download partial files preserved**: If download is cancelled, the partial ZIP remains at `/opt/vosk_models/{name}.zip`. On next attempt, it tries to resume. If the server does not support Range headers, this could cause issues.

10. **`heard_wake_word` blocks**: Despite being called in a polling loop with 100ms sleep, `heard_wake_word()` itself calls `listen(stream=False)` which blocks until an utterance completes. The 100ms sleep only occurs between complete utterance cycles.
