# pidog: LLM Integration

<!-- Status: COMPLETE | Iteration: 1 -->

> Covers: `anthropic_llm.py` (205 lines), `llm.py` (1 line), `stt.py` (1 line), `tts.py` (1 line), `voice_assistant.py` (1 line)

## Purpose

Provides Claude/Anthropic API integration for PiDog voice assistant. `anthropic_llm.py` implements the Claude API adapter. The remaining files (`llm.py`, `stt.py`, `tts.py`, `voice_assistant.py`) are thin re-export shims that bridge to the `sunfounder_voice_assistant` and `robot_hat` packages.

## Architecture

```
pidog/
├── anthropic_llm.py     # Claude API adapter (implements LLM interface)
├── llm.py               # Re-exports: from robot_hat.llm import *
├── stt.py               # Re-exports: from robot_hat.stt import *
├── tts.py               # Re-exports: from robot_hat.tts import *
└── voice_assistant.py   # Re-exports: from robot_hat.voice_assistant import VoiceAssistant
```

**External Dependencies**:
- `sunfounder_voice_assistant`: Base LLM/STT/TTS framework
- `robot_hat`: Hardware abstraction (re-exports voice assistant modules)
- `anthropic` (via `requests`): Claude API client

---

## API Reference

### Anthropic Class (anthropic_llm.py:24)

Adapter for Claude API compatible with SunFounder voice assistant LLM interface.

**Inheritance**: `sunfounder_voice_assistant.llm.llm.LLM` (base class)

#### `__init__(api_key=None, model="claude-sonnet-4-20250514", max_tokens=1024, **kwargs)` (anthropic_llm.py:34)

Initialize Claude API client.

**Parameters**:
- `api_key` (str): Anthropic API key. Default: None (must provide)
- `model` (str): Claude model name. Default: "claude-sonnet-4-20250514"
- `max_tokens` (int): Max response tokens. Default: 1024
- `**kwargs`: Additional args passed to base class (ignored for Anthropic)

**Side effects**:
- Sets API endpoint: `https://api.anthropic.com/v1/messages`
- Initializes empty message history
- Sets `system_prompt = None`

**Thread-safe**: Yes (init only)

**Notes**: Does NOT pass `url`/`base_url` to parent class (Anthropic uses different message format than OpenAI).

---

#### `add_message(role, content, image_path=None)` (anthropic_llm.py:41)

Add message to conversation history.

**Parameters**:
- `role` (str): 'system', 'user', or 'assistant'
- `content` (str): Message text
- `image_path` (str): Optional path to image file. Default: None

**Side effects**:
- If `role='system'`: Stores in `self.system_prompt` (separate from message array per Claude API)
- If `role='user'` or `'assistant'`: Appends to `self.messages` list
- If `image_path` provided: Converts image to base64, creates multi-part content with image+text
- Trims message history if exceeds `max_messages` limit

**Thread-safe**: No (mutates `messages` list)

**Content Format**:
- Text only: `{"role": "user", "content": "Hello"}`
- With image: `{"role": "user", "content": [{"type": "image", "source": {...}}, {"type": "text", "text": "..."}]}`

**Empty Content Handling**: Empty strings replaced with "Hello" (Claude API requirement)

---

#### `chat(stream=False, **kwargs)` (anthropic_llm.py:97)

Send chat request to Claude API.

**Parameters**:
- `stream` (bool): Enable streaming response. Default: False
- `**kwargs`: Additional API parameters (e.g., `temperature`, `top_p`)

**Returns**: `requests.Response` object

**Thread-safe**: No (reads `self.messages`, `self.system_prompt`)

**Raises**:
- `ValueError`: If `model` or `api_key` not set

**Side effects**: Makes HTTP POST to `https://api.anthropic.com/v1/messages`

**Headers**:
```python
{
    "Content-Type": "application/json",
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01"
}
```

**Payload**:
```python
{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [...],
    "system": "system prompt text",  # Optional
    "stream": false
}
```

---

#### `decode_stream_response(line)` (anthropic_llm.py:142)

Decode Server-Sent Events (SSE) line from streaming response.

**Parameters**:
- `line` (str): SSE line (format: `"data: {...}"`)

**Returns**: str (decoded text) or None

**Thread-safe**: Yes (pure function)

**SSE Format**:
```
data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}
data: {"type":"message_stop"}
```

**Handled Events**:
- `content_block_delta` with `text_delta`: Returns text content
- `error`: Raises Exception with error message
- Other events: Returns None (ignored)

**Example**:
```python
response = llm.chat(stream=True)
for line in response.iter_lines():
    line_str = line.decode('utf-8')
    text = llm.decode_stream_response(line_str)
    if text:
        print(text, end='', flush=True)
```

---

#### `_non_stream_response(response)` (anthropic_llm.py:179)

Parse non-streaming Claude API response.

**Parameters**:
- `response` (requests.Response): HTTP response object

**Returns**: str (concatenated text from all content blocks)

**Thread-safe**: Yes (no state mutation)

**Raises**:
- `Exception`: If response contains error

**Response Format**:
```json
{
    "content": [
        {"type": "text", "text": "Hello, how can I help?"}
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "end_turn",
    ...
}
```

---

### Bridge Modules

#### `llm.py` (llm.py:1)

```python
from robot_hat.llm import *
```

**Purpose**: Re-export all LLM base classes and utilities from `robot_hat` package.

**Exports**: `LLM` (base class), potentially other LLM adapters (OpenAI, Ollama, etc.)

---

#### `stt.py` (stt.py:1)

```python
from robot_hat.stt import *
```

**Purpose**: Re-export speech-to-text modules from `robot_hat`.

**Exports**: Likely `Vosk` (offline STT), `Whisper` (OpenAI STT), or other STT classes

---

#### `tts.py` (tts.py:1)

```python
from robot_hat.tts import *
```

**Purpose**: Re-export text-to-speech modules from `robot_hat`.

**Exports**: Likely `PiperTTS` (local TTS), `GoogleTTS`, or other TTS classes

---

#### `voice_assistant.py` (voice_assistant.py:1)

```python
from robot_hat.voice_assistant import VoiceAssistant
```

**Purpose**: Re-export `VoiceAssistant` class from `robot_hat`.

**Exports**: `VoiceAssistant` (main class that orchestrates STT → LLM → TTS pipeline)

---

## Implementation Notes

### Why Bridge Modules?

The `pidog` package re-exports `robot_hat` and `sunfounder_voice_assistant` modules to:
1. Provide a unified import namespace (`from pidog.llm import LLM` vs `from robot_hat.llm import LLM`)
2. Allow custom implementations (like `Anthropic`) alongside vendor implementations
3. Simplify dependencies for users (install `pidog` package, get all voice assistant components)

### Claude API Differences from OpenAI

| Feature | OpenAI | Claude (Anthropic) |
|---------|--------|-------------------|
| System messages | In `messages` array | Separate `system` field |
| Image format | URL or base64 in `image_url` | Base64 in `source.data` with `media_type` |
| Streaming event | `data: {"choices":[{"delta":{"content":"..."}}]}` | `data: {"type":"content_block_delta","delta":{"text":"..."}}` |
| API key header | `Authorization: Bearer <key>` | `x-api-key: <key>` |
| Version header | None | `anthropic-version: 2023-06-01` |

`Anthropic` class handles these differences to conform to `LLM` base class interface.

### Message History Management

**Max Messages**: Inherited from base `LLM` class (default: 10)

**Trimming**: When `len(messages) > max_messages`, oldest message removed via `messages.pop(0)`

**System Prompt**: Stored separately, not counted in message limit

---

## Code Patterns

### Pattern 1: Initialize Anthropic LLM

```python
from pidog.anthropic_llm import Anthropic
import os

llm = Anthropic(
    api_key=os.environ['ANTHROPIC_API_KEY'],
    model='claude-sonnet-4-20250514',
    max_tokens=2048
)

llm.set_instructions("You are a friendly robot dog.")
```

### Pattern 2: Simple Query

```python
llm.add_message('user', 'What should I do?')
response = llm.chat(stream=False)
text = llm._non_stream_response(response)
print(text)
```

### Pattern 3: Streaming Response

```python
llm.add_message('user', 'Tell me a story')
response = llm.chat(stream=True)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        text = llm.decode_stream_response(line_str)
        if text:
            print(text, end='', flush=True)
```

### Pattern 4: Image Input

```python
llm.add_message('user', 'What do you see?', image_path='/tmp/camera.jpg')
response = llm.chat()
text = llm._non_stream_response(response)
print(text)
```

### Pattern 5: Use with VoiceAssistant (via robot_hat)

```python
from pidog.voice_assistant import VoiceAssistant
from pidog.anthropic_llm import Anthropic

llm = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
llm.set_instructions("You are PiDog, a friendly robot dog.")

va = VoiceAssistant(
    llm=llm,
    stt='vosk',  # Speech-to-text
    tts='piper'  # Text-to-speech
)

va.run()  # Start voice loop
```

---

## Gotchas

1. **API Key Required**: `Anthropic` class requires `api_key` parameter. No default, no auto-load from environment. Must pass explicitly or read from environment before init.

2. **System Messages Handled Differently**: Calling `add_message('system', 'You are a dog')` does NOT add to `messages` array. Stored in `system_prompt` field instead. This means system message doesn't count toward `max_messages` limit.

3. **Empty Content Replaced**: Empty strings in `content` are replaced with "Hello" to satisfy Claude API requirements. If you want to send empty content, this will silently change it.

4. **Image Media Type Auto-Detected**: Media type inferred from file extension (`.jpg` → `image/jpeg`, `.png` → `image/png`, etc.). If extension is non-standard, defaults to `image/<extension>` which may cause API errors.

5. **Streaming Errors May Not Raise**: In `decode_stream_response()`, errors are raised via Exception, but non-error events (like `message_stop`) return None. If you don't check for None, you may print "None" to output.

6. **Parent Class Methods Not Documented**: `Anthropic` inherits from `LLM` base class, which provides methods like `set_instructions()`, `prompt()`, `clear_messages()`. These are not redefined in `anthropic_llm.py` so they use base class implementations.

7. **Bridge Modules Import Everything**: `from pidog.llm import *` imports ALL exports from `robot_hat.llm`, not just `LLM` class. This may include test classes, internal utilities, etc. Use explicit imports (`from pidog.llm import LLM`) if you want clean namespace.

8. **Streaming Response Requires iter_lines()**: The `chat(stream=True)` returns `requests.Response` object, but does NOT automatically iterate lines. Must call `response.iter_lines()` or `response.iter_content()` to consume stream.

9. **No Built-in Retry Logic**: If API call fails (network error, rate limit, etc.), `chat()` raises exception. No automatic retry. Wrap in try/except or use `pidog_brain/robust_llm.py` wrapper for retries.

10. **Max Tokens Hardcoded**: `max_tokens=1024` is default. Long responses may be truncated. Increase via `__init__(max_tokens=4096)` if expecting long responses.

---

## Usage with sunfounder_voice_assistant

The `Anthropic` class is designed to be drop-in compatible with `sunfounder_voice_assistant`'s LLM interface. Example integration:

```python
# Standard way (from examples/claude_pidog.py likely)
from pidog import Pidog
from pidog.anthropic_llm import Anthropic
from pidog.voice_assistant import VoiceAssistant
import os

# Initialize robot
dog = Pidog()

# Initialize LLM
llm = Anthropic(
    api_key=os.environ.get('ANTHROPIC_API_KEY'),
    model='claude-sonnet-4-20250514'
)
llm.set_instructions("""
You are PiDog, a friendly robot dog. You can:
- Move: forward, backward, turn left, turn right
- Express: wag tail, bark, sit, stand, lie down
- Sense: ultrasonic distance, IMU (pitch/roll), touch sensors

Respond naturally and suggest actions in the format:
ACTIONS: sit, wag tail, bark
""")

# Initialize voice assistant
va = VoiceAssistant(
    llm=llm,
    stt='vosk',
    tts='piper',
    # Optional: camera integration
)

# Run voice loop
va.run()

# In main loop, parse actions from LLM response
while True:
    user_input = va.get_last_input()  # From STT
    llm_response = va.get_last_response()  # From LLM

    # Parse ACTIONS: line
    if 'ACTIONS:' in llm_response:
        actions_line = llm_response.split('ACTIONS:')[1].split('\n')[0]
        actions = [a.strip() for a in actions_line.split(',')]
        for action in actions:
            dog.do_action(action)

    sleep(0.1)
```

---

## API Endpoint

**Base URL**: `https://api.anthropic.com/v1/messages`

**Authentication**: `x-api-key` header

**API Version**: `2023-06-01` (required in `anthropic-version` header)

**Rate Limits**: Varies by plan (see Anthropic documentation)

**Timeout**: No timeout set in code (uses `requests` default, ~infinite). Consider setting timeout for production:
```python
response = requests.post(url, headers=headers, data=json.dumps(data), stream=stream, timeout=30)
```

---

## See Also

- `sunfounder_voice_assistant` package documentation (external)
- `robot_hat` package documentation (external)
- Anthropic API documentation: https://docs.anthropic.com/
- PiDog autonomous brain (`pidog_brain/`) for example usage
