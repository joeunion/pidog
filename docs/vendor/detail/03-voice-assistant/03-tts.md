# voice-assistant: TTS (Text-to-Speech)

<!-- Status: COMPLETE | Iteration: 1 -->

> **Source files:** `tts/piper.py`, `tts/espeak.py`, `tts/pico2wave.py`, `tts/openai_tts.py`, `tts/piper_models.py`, `tts/__init__.py`

## Purpose

Four pluggable TTS engines with a common `say(text)` interface. Piper (neural, local, default) is used by VoiceAssistant. eSpeak and pico2wave are lightweight local alternatives. OpenAI TTS is a cloud-based option. All engines output audio via `AudioPlayer` (PyAudio) or system `aplay`.

## Exports (`tts/__init__.py`)

```python
from .espeak import Espeak
from .pico2wave import Pico2Wave
from .piper import Piper
from .openai_tts import OpenAI_TTS
__all__ = ["Espeak", "Pico2Wave", "Piper", "OpenAI_TTS"]
```

---

## TTS Engine Comparison

| Engine | Type | Quality | Latency | Offline | Streaming | Dependencies | Notes |
|--------|------|---------|---------|---------|-----------|--------------|-------|
| **Piper** | Neural ONNX | High | ~200-500ms first chunk | Yes | Yes | `piper`, `onnxruntime`, PyAudio | Default for VoiceAssistant |
| **eSpeak** | Formant synthesis | Low | <50ms | Yes | No | `espeak` system binary | Very fast, robotic voice |
| **pico2wave** | Concatenative | Medium | ~100ms | Yes | No | `pico2wave` system binary, `aplay` | Limited to 6 languages |
| **OpenAI TTS** | Cloud neural | Very High | ~500-1000ms (network) | No | Yes | `requests`, PyAudio, API key | Requires internet + API key |

---

## API Reference

### Piper (`tts/piper.py`)

Neural TTS engine using ONNX models. Default engine for VoiceAssistant.

**Inherits from:** `_Base`

#### Constructor

```python
Piper(*args, model: str = None, **kwargs) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | `None` | Piper model name (e.g., `"en_US-ryan-low"`). If provided, model is loaded immediately. |

**Side effects:**
- Creates `/opt/piper_models` directory if missing (with `chmod 0o777`, `chown 1000:1000`)
- If model specified: may download model files (~15-100MB)

**Instance attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.model` | `str` or `None` | Current model name |
| `self.piper` | `PiperVoice` or `None` | Loaded Piper voice (ONNX) |

#### Methods

##### `say(text: str, stream: bool = True) -> None`

Speaks text through the system audio output.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | (required) | Text to speak |
| `stream` | `bool` | `True` | If True, streams audio chunks to speaker in real-time. If False, synthesizes to temp file then plays. |

- **Raises:** `ValueError` if model not set
- **Side effects:** When `stream=False`, writes `/tmp/tts_piper.wav`
- **Thread safety:** Not thread-safe (uses shared PiperVoice instance)

##### `tts(text: str, file: str) -> None`

Synthesizes text to a WAV file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to synthesize |
| `file` | `str` | Output WAV file path |

- **Raises:** `ValueError` if model not set
- **Side effects:** Writes WAV file

##### `stream(text: str) -> None`

Streams synthesized audio directly to speaker using `AudioPlayer`.

- Opens `AudioPlayer(sample_rate=self.piper.config.sample_rate)` as context manager
- Iterates `self.piper.synthesize(text)` yielding `RawAudio` chunks
- Plays `chunk.audio_int16_bytes` for each chunk

##### `set_model(model: str) -> None`

Loads a Piper model by name. Downloads if not present. Re-downloads if ONNX protobuf is invalid.

- **Raises:** `ValueError` if model name not in `MODELS` list
- **Side effects:** May download model files from GitHub

##### `download_model(model: str, force: bool = False, progress_callback: Callable[[int, int], None] = None) -> None`

Downloads model `.onnx` and `.onnx.json` files.

- **Storage:** `/opt/piper_models/{model}.onnx` and `/opt/piper_models/{model}.onnx.json`
- **Download source:** Piper GitHub releases (via `piper.download_voices` URL format)

##### `is_model_downloaded(model: str) -> bool`

Checks if both `.onnx` and `.onnx.json` files exist.

##### `get_model_path(model: str) -> str`

Returns `/opt/piper_models/{model}.onnx`.

##### `available_models(country: str = None) -> List[str]`

Returns available model names. If `country` is specified (e.g., `"en_US"`), returns models for that locale only.

##### `available_countrys() -> List[str]`

Returns list of supported locale codes (e.g., `["ar_JO", "ca_ES", ..., "zh_CN"]`).

##### `get_language() -> str`

Extracts language prefix from model name (e.g., `"en_US-ryan-low"` -> `"en_US"`). Splits on `-` and takes first part. **Note:** This only gets the first segment before the first dash, so `"en_US"` becomes `"en_US"` correctly because the split is on `-` and the underscore is preserved.

Wait -- actually examining the code: `self.model.split("-")[0]` on `"en_US-ryan-low"` returns `"en_US"`. Correct.

##### `fix_chinese_punctuation(text: str) -> str`

Replaces Chinese punctuation with English equivalents. Only applies when language starts with `"zh_CN"`. Also converts decimal points like `1.2` to `1点2` for Chinese speech.

---

### Espeak (`tts/espeak.py`)

Lightweight formant synthesizer. Shells out to `espeak` command-line tool.

**Inherits from:** `_Base`

#### Constructor

```python
Espeak(*args, **kwargs) -> None
```

- **Raises:** `Exception` if `espeak` binary not found on PATH
- **Defaults:** amp=100, speed=175, gap=5, pitch=50, lang='en-US'

#### Methods

##### `say(words: str) -> None`

Synthesizes to `/tmp/espeak.wav` then plays via `AudioPlayer.play_file()`.

##### `tts(words: str, file_path: str) -> None`

Runs `espeak -a{amp} -s{speed} -g{gap} -p{pitch} "{words}" -w {file_path}`.

- **Raises:** `Exception` if espeak command fails

##### Parameter Setters

| Method | Range | Default | Description |
|--------|-------|---------|-------------|
| `set_amp(amp: int)` | 0-200 | 100 | Amplitude (volume) |
| `set_speed(speed: int)` | 80-260 | 175 | Words per minute |
| `set_gap(gap: int)` | 0-200 | 5 | Word gap (10ms units) |
| `set_pitch(pitch: int)` | 0-99 | 50 | Voice pitch |

All setters validate type (`int`) and range, raising `ValueError` on invalid input.

---

### Pico2Wave (`tts/pico2wave.py`)

SVOX Pico TTS engine. Shells out to `pico2wave` and `aplay`.

**Inherits from:** `_Base`

#### Constructor

```python
Pico2Wave(*args, lang: str = None, **kwargs) -> None
```

- **Raises:** `Exception` if `pico2wave` binary not found on PATH
- **Default language:** `'en-US'`

#### Supported Languages

```python
SUPPORTED_LANGUAUE = ['en-US', 'en-GB', 'de-DE', 'es-ES', 'fr-FR', 'it-IT']
```

(Note: the attribute name has a typo -- `LANGUAUE` instead of `LANGUAGE`)

#### Methods

##### `say(words: str) -> None`

Runs: `pico2wave -l {lang} -w /tmp/pico2wave.wav "{words}" && aplay /tmp/pico2wave.wav 2>/dev/null &`

**IMPORTANT:** The `&` at the end means `aplay` runs in the background. The `say()` method returns before playback completes. This is different from all other TTS engines.

##### `set_lang(lang: str) -> None`

Sets language. Raises `ValueError` if not in `SUPPORTED_LANGUAUE`.

---

### OpenAI_TTS (`tts/openai_tts.py`)

Cloud-based TTS using OpenAI's audio/speech API.

**Inherits from:** `_Base`

#### Constructor

```python
OpenAI_TTS(
    *args,
    voice: Voice = Voice.ALLOY,
    model: Model = Model.GPT_4O_MINI_TTS,
    api_key: str = None,
    gain: float = 1.5,
    **kwargs,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `voice` | `Voice` enum | `Voice.ALLOY` | Voice selection |
| `model` | `Model` enum | `Model.GPT_4O_MINI_TTS` | TTS model |
| `api_key` | `str` | `None` | OpenAI API key (required for operation) |
| `gain` | `float` | `1.5` | Volume gain factor |

#### Voice Enum

```python
class Voice(StrEnum):
    ALLOY = "alloy"
    ASH = "ash"
    BALLAD = "ballad"
    CORAL = "coral"
    ECHO = "echo"
    FABLE = "fable"
    NOVA = "nova"
    ONYX = "onyx"
    SAGE = "sage"
    SHIMMER = "shimmer"
```

#### Model Enum

```python
class Model(StrEnum):
    GPT_4O_MINI_TTS = "gpt-4o-mini-tts"
```

#### Methods

##### `say(words: str, instructions: str = None, stream: bool = True) -> None`

Speaks text. In stream mode, audio chunks are played directly via `AudioPlayer`. In non-stream mode, saves to `/tmp/openai_tts.wav` then plays.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `words` | `str` | (required) | Text to speak |
| `instructions` | `str` | `None` | Emotional/style instructions (e.g., "say it sadly") |
| `stream` | `bool` | `True` | Stream audio chunks vs download whole file first |

##### `tts(words: str, output_file: str = "/tmp/openai_tts.wav", instructions: str = None, stream: bool = False) -> bool`

Makes HTTP POST to `https://api.openai.com/v1/audio/speech`.

Request body:
```json
{
    "model": "gpt-4o-mini-tts",
    "input": "text",
    "voice": "alloy",
    "response_format": "wav",
    "instructions": "optional style instructions"
}
```

Returns `True` on success, `False` on error.

##### `set_voice(voice: Voice | str) -> None`

Sets voice. Accepts enum value or string name.

##### `set_model(model: Model | str) -> None`

Sets model. Accepts enum value or string name.

##### `set_api_key(api_key: str) -> None`

Sets API key. **Raises `ValueError` if not a string** -- this means passing `None` raises an error.

##### `set_gain(gain: float) -> None`

Sets volume gain. **Raises `ValueError` if not a float** -- passing an `int` raises an error.

---

### Piper Models (`tts/piper_models.py`)

Static data file defining available Piper voice models.

#### Data Structures

```python
PIPER_MODELS: dict[str, dict[str, list[str]]]
# Structure: {locale: {voice_name: [model_ids]}}
# Example: {"en_US": {"ryan": ["en_US-ryan-low", "en_US-ryan-medium", "en_US-ryan-high"]}}

COUNTRYS: list[str]  # All locale keys from PIPER_MODELS
MODELS: list[str]    # Flat list of all model IDs
```

#### Supported Locales (40 total)

`ar_JO`, `ca_ES`, `cs_CZ`, `cy_GB`, `da_DK`, `de_DE`, `el_GR`, `en_GB`, `en_US`, `es_ES`, `es_MX`, `fa_IR`, `fi_FI`, `fr_FR`, `hu_HU`, `is_IS`, `it_IT`, `ka_GE`, `kk_KZ`, `lb_LU`, `lv_LV`, `ml_IN`, `ne_NP`, `nl_BE`, `nl_NL`, `no_NO`, `pl_PL`, `pt_BR`, `pt_PT`, `ro_RO`, `ru_RU`, `sk_SK`, `sl_SI`, `sr_RS`, `sv_SE`, `sw_CD`, `tr_TR`, `uk_UA`, `vi_VN`, `zh_CN`

#### English Models (en_US)

| Voice | Qualities |
|-------|-----------|
| amy | low, medium |
| arctic | medium |
| bryce | medium |
| danny | low |
| hfc_female | medium |
| hfc_male | medium |
| joe | medium |
| john | medium |
| kathleen | low |
| kristin | medium |
| kusal | medium |
| l2arctic | medium |
| lessac | low, medium, high |
| libritts | high |
| libritts_r | medium |
| ljspeech | medium, high |
| norman | medium |
| reza_ibrahim | medium |
| **ryan** | **low**, medium, high |
| sam | medium |

**Default model for PiDog:** `en_US-ryan-low` (smallest en_US model)

#### Quality Tiers

| Quality | Typical Size | Description |
|---------|-------------|-------------|
| `x_low` | ~15MB | Lowest quality, smallest file |
| `low` | ~20-30MB | Fast, acceptable quality |
| `medium` | ~60-80MB | Good balance |
| `high` | ~100-150MB | Best quality, slower |

---

## Implementation Notes

### Piper Streaming Architecture

```python
# Piper.stream() flow:
with AudioPlayer(sample_rate) as player:      # Opens PyAudio stream
    for chunk in self.piper.synthesize(text):  # ONNX inference, yields chunks
        player.play(chunk.audio_int16_bytes)   # Writes to PyAudio stream
```

Piper's `synthesize()` generates audio in sentence-level chunks. Each chunk is a `RawAudio` object with `.audio_int16_bytes`. The `AudioPlayer` buffers and plays in 2KB chunks for low-latency streaming.

### eSpeak Subprocess Pattern

eSpeak runs as a subprocess: `espeak ... -w file.wav`. The WAV file is then played via `AudioPlayer.play_file()`. Two-step process means no real-time streaming.

### Pico2Wave Background Playback

`pico2wave` + `aplay` runs with `&` (background shell). This means:
- `say()` returns immediately
- Audio plays asynchronously
- No way to detect when playback finishes
- Cannot be interrupted programmatically

### OpenAI TTS Streaming

In streaming mode, `requests.post(..., stream=True)` returns chunks via `response.iter_content(chunk_size=1024)`. Each chunk is raw WAV data played directly through `AudioPlayer.play()`. The gain is applied by `AudioPlayer` (default 1.5x for OpenAI TTS).

### Model Download (Piper)

The `download_voice()` function uses Piper's built-in URL format and `_needs_download()` check. Files are downloaded from Piper's GitHub releases using `urllib.request.urlopen`. Progress is shown via tqdm or a callback.

---

## Code Patterns

### Default Piper Usage (as used by VoiceAssistant)

```python
from sunfounder_voice_assistant.tts import Piper

tts = Piper(model="en_US-ryan-low")
tts.say("Hello world")  # Streams audio to speaker
```

### Piper to File

```python
tts = Piper(model="en_US-lessac-medium")
tts.tts("Save this to a file", "/tmp/output.wav")
```

### Switch TTS Engine

```python
# All engines implement say(text)
from sunfounder_voice_assistant.tts import Espeak, Pico2Wave, OpenAI_TTS

# Local, low quality, very fast
tts = Espeak()
tts.say("Quick response")

# Local, medium quality
tts = Pico2Wave()
tts.say("Slightly better")

# Cloud, highest quality
tts = OpenAI_TTS(api_key="sk-...")
tts.say("Best quality", instructions="speak cheerfully")
```

### Replace VoiceAssistant's TTS

```python
va = VoiceAssistant(llm=llm)
# Replace Piper with eSpeak
va.tts = Espeak()
# Note: say() interface is compatible across all engines
```

---

## Gotchas

1. **Piper model directory permissions**: `/opt/piper_models` is created with `chmod 0o777` and `chown 1000:1000`. The hardcoded UID 1000 assumes the first non-root user. Running as a different user may cause permission errors.

2. **eSpeak command injection**: The `tts()` method uses f-string interpolation into a shell command: `f'espeak ... "{words}" -w {file_path}'`. Words containing `"` or shell metacharacters can break or be exploited.

3. **pico2wave `say()` is fire-and-forget**: The trailing `&` means audio plays in the background. If `VoiceAssistant` starts the next round immediately, audio from the previous round may still be playing.

4. **OpenAI `set_api_key` rejects None**: Passing `api_key=None` to the constructor calls `set_api_key(None)` which raises `ValueError("Invalid api_key: None, must be str")`. Always pass a string.

5. **OpenAI `set_gain` rejects int**: `set_gain(2)` raises `ValueError` because `isinstance(2, float)` is `False` in Python. Must pass `2.0`.

6. **Piper `get_language()` fails if model is None**: Calling `get_language()` before `set_model()` raises `AttributeError` because `self.model.split("-")` operates on `None`.

7. **Chinese punctuation replacement is aggressive**: `fix_chinese_punctuation()` replaces Chinese commas with `. ` (period + space), not commas. This changes sentence structure.

8. **Model auto-download blocks the main thread**: Both Piper and Vosk download models synchronously during `set_model()` / `init()`. For large models (100MB+), this can block for minutes with no async option.

9. **eSpeak `check_executable` return value ignored**: In `tts()`, `check_executable('espeak')` checks if espeak is available but the return value is used for a log message, not to prevent execution. The espeak command will still be attempted.

10. **No common TTS base class**: All four engines implement `say(text)` but with different additional parameters. There is no shared interface/ABC. Swapping engines may break if caller passes engine-specific arguments.
