# voice-assistant: Audio Internals

<!-- Status: COMPLETE | Iteration: 1 -->

> **Source files:** `_audio_player.py`, `_keyboard_input.py`, `_utils.py`, `_logger.py`

## Purpose

Internal utility modules providing audio playback (PyAudio), keyboard input threading, shell command execution, stderr suppression, and colored logging. These are shared infrastructure used by STT, TTS, and the main VoiceAssistant.

---

## API Reference

### AudioPlayer (`_audio_player.py`)

PyAudio-based audio player supporting real-time streaming with buffering, volume gain control, and file playback. Used by Piper TTS (streaming), eSpeak TTS (file playback), and OpenAI TTS (streaming).

#### Constructor

```python
AudioPlayer(
    sample_rate: int = 22050,
    channels: int = 1,
    gain: float = 1.0,
    format: int = pyaudio.paInt16,
    timeout: float = None,
    enable_buffering: bool = True,
    buffer_size: int = 8192,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | `int` | `22050` | Audio sample rate in Hz |
| `channels` | `int` | `1` | Number of channels (1=mono, 2=stereo) |
| `gain` | `float` | `1.0` | Volume multiplier (1.0 = unchanged) |
| `format` | `int` | `pyaudio.paInt16` | PyAudio format constant |
| `timeout` | `float` | `None` | Timeout for playback thread join |
| `enable_buffering` | `bool` | `True` | Enable internal audio buffering |
| `buffer_size` | `int` | `8192` | Minimum buffer size in bytes (for constructor; actual play threshold is different) |

**Raises:** `ImportError` if PyAudio is not installed.

**Side effects:** Creates a `pyaudio.PyAudio()` instance immediately (initializes PortAudio).

#### Context Manager Usage

```python
with AudioPlayer(sample_rate=22050) as player:
    player.play(audio_bytes)
    player.play(more_bytes)
# Stream and PyAudio automatically cleaned up
```

- `__enter__`: Redirects stderr to null (ALSA noise), opens output stream
- `__exit__`: Stops playback, closes stream, terminates PyAudio, restores stderr

#### Methods

##### `play(audio_bytes: bytes) -> None`

Plays raw audio bytes with optional buffering.

**With buffering (`enable_buffering=True`, default):**
1. Appends bytes to internal `_audio_buffer`
2. When buffer reaches threshold (`max(512, 8)` = 512 bytes min), plays in 2KB chunks
3. Each chunk is frame-aligned (2-byte boundary for int16 mono)
4. Gain is applied to the incoming `audio_bytes` before buffering

**Without buffering:**
1. Gain applied
2. Frame-aligned
3. Written directly to PyAudio stream

- **Thread safety:** Not thread-safe (shared buffer and stream)
- **Note:** The `buffer_size` constructor parameter (8192) is NOT used by `play()`. The play threshold is hardcoded as `max(512, frame_size * 4)`.

##### `flush_buffer() -> None`

Plays all remaining data in the internal buffer. Call after the last `play()` to ensure all audio is output.

**Note:** `flush_buffer()` applies gain AGAIN to remaining buffer data, but `play()` already applied gain before buffering. This is a double-gain bug for buffered data that was not played during `play()` calls.

##### `play_file(file_path: str, chunk_size: int = 4096) -> None`

Plays a WAV file with proper format detection.

1. Opens WAV file, reads format metadata (channels, sample rate, sample width)
2. Opens a temporary PyAudio stream with file's parameters (not the constructor's)
3. Reads in chunks, buffers to 8KB, applies gain, writes to stream
4. Closes temporary stream on completion

- **Format support:** WAV only; sample widths 1-4 bytes (int8, int16, int24, int32)
- **Raises:** `FileNotFoundError`, `ValueError` for unsupported format
- **Side effects:** Redirects/restores stderr independently of context manager

##### `play_async(audio_bytes: bytes) -> None`

Plays audio in a daemon background thread. Stops any previous async playback first.

##### `play_file_async(file_path: str, chunk_size: int = 1024) -> None`

Plays a file in a daemon background thread. Stops any previous async playback first.

##### `stop() -> None`

Signals stop event, waits for playback thread to finish (with optional timeout), clears buffer.

##### `set_gain(gain: float) -> None`

Sets gain. Clamps to minimum 0.0.

##### `get_gain() -> float`

Returns current gain value.

##### `gain_file(input_file: str, output_file: str, gain: float) -> bool`

Reads WAV file, applies gain with numpy, writes to new WAV file.

- **Return:** `True` on success, `False` on error
- **Note:** Does not use clipping protection (unlike `_apply_gain()`). Integer overflow wraps silently.

##### `is_available() -> bool` (static)

Returns whether PyAudio was successfully imported.

#### Internal Methods

##### `_open_stream() -> None`

Opens PyAudio output stream if not already open or if stopped.

##### `_apply_gain(audio_bytes: bytes) -> bytes`

Applies gain to audio bytes using numpy:
1. Converts bytes to numpy array of appropriate dtype
2. Multiplies by gain factor
3. Clips to dtype min/max to prevent distortion
4. Returns adjusted bytes

Handles byte alignment (truncates to dtype boundary). Returns original bytes on error.

---

### KeyboardInput (`_keyboard_input.py`)

Threaded keyboard input reader for non-blocking stdin polling.

#### Constructor

```python
KeyboardInput() -> None
```

No parameters. Initializes `thread=None, running=False, result=None`.

#### Methods

##### `start() -> None`

Starts a background thread that reads one line from stdin.

- **Thread name:** `"Keyboard Input Thread"`
- **Side effects:** Prints `">>> "` prompt to stdout
- **Guard:** Returns immediately if already running

##### `main() -> None`

Thread target. Uses `select.select([sys.stdin], [], [], 0.1)` to poll stdin every 100ms. When input available, reads one line, strips whitespace, stores in `self.result`.

- Exits after one line is read
- Sets `self.running = False` on exit

##### `is_result_ready() -> bool`

Returns `True` if `self.result is not None`.

##### `stop() -> None`

Sets `self.running = False`, clears result, joins thread.

- **Guard:** Returns immediately if not running
- **Warning:** If the thread is blocked on stdin (no select timeout hit), `join()` may block

---

### Utils (`_utils.py`)

Shell utilities and stderr management.

#### Functions

##### `run_command(cmd: str, user: str = None, group: str = None) -> tuple[int, str]`

Runs a shell command via `subprocess.Popen`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cmd` | `str` | (required) | Shell command string |
| `user` | `str` | `None` | Run as this user |
| `group` | `str` | `None` | Run as this group |

- **Returns:** `(status_code, stdout_output_string)` -- stderr is merged into stdout
- **Note:** Uses `shell=True`, `stdout=PIPE`, `stderr=STDOUT`

##### `check_executable(executable: str) -> bool`

Checks if an executable exists on PATH using `distutils.spawn.find_executable`.

- **Deprecation warning:** `distutils` is deprecated in Python 3.12+

##### `is_installed(cmd: str) -> bool`

Checks if a command is installed by running `which {cmd}`.

- **Returns:** `True` if exit status is 0

##### `redirect_error_2_null() -> int`

Redirects file descriptor 2 (stderr) to `/dev/null`. Returns the saved old stderr fd.

**Purpose:** Suppress ALSA/PortAudio noise during audio operations.

```python
old_stderr = redirect_error_2_null()
# ... noisy operations ...
cancel_redirect_error(old_stderr)
```

##### `cancel_redirect_error(old_stderr: int) -> None`

Restores stderr from saved file descriptor.

#### Context Manager

##### `ignore_stderr`

Context manager that redirects stderr to null for its block:

```python
with ignore_stderr():
    # ALSA warnings suppressed here
    sd.RawInputStream(...)
```

- Redirects stderr in `__init__` (not `__enter__`)
- Restores in `__exit__`
- **Bug:** stderr is redirected at object creation time, not when entering the context. If the object is created early and used later, stderr is suppressed longer than intended.

---

### Logger (`_logger.py`)

Colored console logging with optional file rotation.

#### ColoredFormatter

Formats log level names with ANSI colors:

| Level | Color |
|-------|-------|
| DEBUG | Blue (`\033[94m`) |
| INFO | Green (`\033[92m`) |
| WARNING | Yellow (`\033[93m`) |
| ERROR | Red (`\033[91m`) |
| CRITICAL | Purple (`\033[95m`) |

Format: `[{colored_level}] {message}`

#### Logger Class

```python
Logger(
    name: str = 'logger',
    level: int = logging.INFO,
    file: str = None,
    maxBytes: int = 10*1024*1024,  # 10MB
    backupCount: int = 10,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `'logger'` | Logger name |
| `level` | `int` | `logging.INFO` | Log level |
| `file` | `str` | `None` | Log file path (None = console only) |
| `maxBytes` | `int` | `10485760` (10MB) | Max log file size before rotation |
| `backupCount` | `int` | `10` | Number of backup log files to keep |

**Inherits from:** `logging.Logger`

**Console format:** `[{level}] {message}` (colored)
**File format:** `{YY/MM/DD HH:MM:SS.mmm} [{level}] {message}`

##### `setLevel(level: int | str) -> None`

Sets level on logger and ALL handlers. Accepts string levels (`"DEBUG"`, etc.).

#### Module-Level Constants

```python
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
```

---

## Implementation Notes

### AudioPlayer Buffering Strategy

The buffering system is designed to reduce audio crackling/popping from tiny writes:

```
play() called with audio_bytes:
  1. Apply gain to incoming bytes
  2. Append to _audio_buffer (bytearray)
  3. While buffer >= 512 bytes:
     a. Extract min(len(buffer), 2048) bytes (frame-aligned)
     b. Write to PyAudio stream
     c. Remove written bytes from buffer
```

The 2KB chunk size and 512-byte threshold provide a balance between latency and smoothness. For Piper TTS streaming, each synthesize chunk is typically several KB, so this threshold is usually exceeded immediately.

### Stderr Redirection Mechanism

Uses POSIX file descriptor manipulation:
```python
devnull = os.open(os.devnull, os.O_WRONLY)
old_stderr = os.dup(2)        # Save fd 2
os.dup2(devnull, 2)           # Point fd 2 to /dev/null
os.close(devnull)
# ... later ...
os.dup2(old_stderr, 2)        # Restore fd 2
os.close(old_stderr)
```

This works at the OS level, catching output from C libraries (ALSA, PortAudio) that write directly to fd 2, which Python's `sys.stderr` redirect would miss.

### KeyboardInput Threading

Uses `select.select()` with 100ms timeout for non-blocking stdin reads. This allows the thread to be stopped via the `self.running` flag without blocking on `input()`. However, on some terminals/platforms, `select` on stdin may not work correctly (e.g., Windows).

---

## Code Patterns

### Streaming TTS Playback (Piper)

```python
with AudioPlayer(sample_rate=22050) as player:
    for chunk in piper_voice.synthesize(text):
        player.play(chunk.audio_int16_bytes)
    player.flush_buffer()  # Play remaining buffered audio
```

### File Playback (eSpeak)

```python
with AudioPlayer() as player:
    player.play_file("/tmp/espeak.wav")
```

### Async Playback

```python
player = AudioPlayer()
player.__enter__()
player.play_file_async("/tmp/audio.wav")
# ... do other things ...
player.stop()
player.__exit__(None, None, None)
```

### Suppress ALSA Noise

```python
from sunfounder_voice_assistant._utils import ignore_stderr

with ignore_stderr():
    stream = sd.RawInputStream(samplerate=16000, blocksize=1024,
                                dtype="int16", channels=1, callback=cb)
```

### Custom Logger

```python
from sunfounder_voice_assistant._logger import Logger

log = Logger("my_module", level="DEBUG", file="/tmp/my_log.txt")
log.info("This appears in color on console and in log file")
```

---

## Gotchas

1. **AudioPlayer `flush_buffer()` double-gain bug**: `play()` applies gain before buffering. `flush_buffer()` applies gain again to the buffer contents. Audio played via `flush_buffer()` will have gain applied twice (gain^2 effect).

2. **AudioPlayer constructor `buffer_size` parameter is unused**: The `buffer_size=8192` parameter is stored as `self._buffer_size` but never read by `play()`. The actual play threshold is hardcoded as `max(512, frame_size * 4)` = 512 bytes.

3. **`ignore_stderr` redirects in `__init__`, not `__enter__`**: Creating the context manager object immediately redirects stderr:
   ```python
   ctx = ignore_stderr()  # stderr is NOW redirected to /dev/null
   # ... stderr suppressed here, even before `with` block ...
   with ctx:
       pass
   # stderr restored here
   ```

4. **`check_executable` uses deprecated `distutils`**: `distutils.spawn.find_executable` is deprecated since Python 3.12 and removed in 3.13. On newer Python versions, this will fail with `ImportError`.

5. **`run_command` with `shell=True`**: Shell injection is possible if `cmd` contains unsanitized user input. Used by eSpeak and pico2wave TTS with text that may contain special characters.

6. **KeyboardInput `stop()` may hang**: If the thread is waiting in `select()` (100ms timeout), `stop()` returns quickly. But if for some reason select blocks longer (platform-dependent), `thread.join()` will block.

7. **AudioPlayer `play_file` creates separate PyAudio stream**: Each `play_file()` call opens a new stream with the WAV file's parameters, independent of the constructor's stream. This means `sample_rate`, `channels`, and `format` passed to the constructor are irrelevant for file playback.

8. **AudioPlayer stderr redirection nesting**: Both the context manager (`__enter__`/`__exit__`) and `play_file()` independently redirect stderr. If `play_file()` is called within a context manager, stderr redirection is nested. The inner `cancel_redirect_error` in `play_file` restores the outer redirect's fd, not the original stderr.

9. **Logger `setLevel` updates all handlers**: Unlike standard Python logging where handlers can have independent levels, `Logger.setLevel()` applies the same level to every handler. You cannot have DEBUG to file and INFO to console.

10. **`gain_file()` does not clip**: Unlike `_apply_gain()` which uses `np.clip()`, `gain_file()` does `(array * gain).astype(dtype)` which silently wraps on integer overflow, producing audio artifacts.
