# voice-assistant: LLM

<!-- Status: COMPLETE | Iteration: 1 -->

> **Source files:** `llm/llm.py`, `llm/__init__.py`

## Purpose

Generic OpenAI-compatible HTTP chat completion client with streaming support, message history management, image attachment (base64), and preset provider classes for DeepSeek, Grok, Doubao, Qwen, OpenAI, Ollama, and Gemini. Uses raw `requests` library -- no vendor SDKs.

## Exports (`llm/__init__.py`)

```python
from .llm import LLM

__all__ = ["LLM", "Deepseek", "Grok", "Doubao", "Gemini", "Qwen", "OpenAI", "Ollama"]
```

---

## API Reference

### LLM Base Class (`llm/llm.py`)

#### Constructor

```python
LLM(
    api_key: str = None,
    model: str = None,
    url: str = None,
    base_url: str = None,
    max_messages: int = 20,
    authorization: Authorization = Authorization.BEARER,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `None` | API key for authentication |
| `model` | `str` | `None` | Model name (e.g., `"gpt-4o-mini"`, `"deepseek-r1:1.5b"`) |
| `url` | `str` | `None` | Full endpoint URL. If None, constructed from `base_url + "/chat/completions"` |
| `base_url` | `str` | `None` | Base URL (e.g., `"https://api.openai.com/v1"`). Appends `/chat/completions` |
| `max_messages` | `int` | `20` | Maximum messages retained in history (FIFO eviction) |
| `authorization` | `Authorization` | `BEARER` | Auth header format: `"Bearer {key}"` or `"Api-Key {key}"` |

**If both `url` and `base_url` are provided**, `url` takes precedence (base_url is stored but url is not overwritten).

**Instance attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.messages` | `list[dict]` | Conversation history (`[{"role": "...", "content": "..."}]`) |
| `self.params` | `dict` | Additional parameters sent with every request (set via `set()`) |
| `self.model` | `str` | Model name |
| `self.url` | `str` | Full chat completions URL |
| `self.api_key` | `str` | API key |
| `self.authorization` | `Authorization` | Auth type |

#### Authorization Enum

```python
class Authorization(StrEnum):
    BEARER = "Bearer"   # Header: "Authorization: Bearer {key}"
    API_KEY = "Api-Key"  # Header: "Authorization: Api-Key {key}"
```

**Note:** When `authorization == Authorization.BEARER`, the header is set as `Authorization: Bearer {key}`. The `API_KEY` variant is defined but the code always uses `Authorization.BEARER` format in the `if` check. There is no `else` branch, so `API_KEY` authorization produces **no Authorization header at all**.

---

#### Configuration Methods

##### `set_api_key(api_key: str) -> None`

Sets `self.api_key`.

##### `set_base_url(base_url: str) -> None`

Sets `self.base_url` and recalculates `self.url = base_url + "/chat/completions"`.

##### `set_model(model: str) -> None`

Sets `self.model`.

##### `set_max_messages(max_messages: int) -> None`

Sets `self.max_messages`. Does not retroactively trim existing history.

##### `set(name: str, value) -> None`

Adds a key-value pair to `self.params`, which is merged into every HTTP request body. Useful for `temperature`, `top_p`, `max_tokens`, etc.

```python
llm.set("temperature", 0.7)
llm.set("max_tokens", 500)
```

##### `set_instructions(instructions: str) -> None`

Adds a system message to the beginning of the conversation:
```python
self.add_message("system", instructions)
```

**Note:** This is additive -- calling it multiple times adds multiple system messages. There is no deduplication.

##### `set_welcome(welcome: str) -> None`

Adds an assistant message to the conversation history:
```python
self.add_message("assistant", welcome)
```

---

#### Message Management

##### `add_message(role: str, content: str, image_path: str = None) -> None`

Appends a message to `self.messages`. If `image_path` is provided, content becomes a multipart array:

```python
# Without image:
{"role": "user", "content": "Hello"}

# With image:
{"role": "user", "content": [
    {"type": "text", "text": "Hello"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
]}
```

**FIFO eviction:** If `len(self.messages) > self.max_messages`, the oldest message (`messages[0]`) is removed. This means system instructions can be evicted after enough conversation turns.

##### `get_base64_from_image(image_path: str) -> str`

Reads image file and returns base64-encoded string.

##### `get_base_64_url_from_image(image_path: str) -> str`

Returns `data:image/{ext};base64,{data}` string. Extension extracted from file path.

---

#### Chat Methods

##### `prompt(msg: str | list, image_path: str = None, stream: bool = False, **kwargs) -> str | Generator`

Primary interface for sending a message and getting a response.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `msg` | `str` or `list` | (required) | User message string, or a complete message list to replace history |
| `image_path` | `str` | `None` | Path to image file to include |
| `stream` | `bool` | `False` | Stream response tokens |
| `**kwargs` | | | Additional params passed to HTTP request (e.g., `think=False`) |

**If `msg` is a string:** Adds as user message (with optional image) to history, then calls `chat()`.
**If `msg` is a list:** Replaces `self.messages` entirely with the provided list.

**Returns:**
- `stream=False`: `str` -- full response text
- `stream=True`: Generator yielding `str` tokens

**Raises:** `ValueError` if model, api_key, or url not set; or if msg is neither str nor list.

##### `chat(stream: bool = False, **kwargs) -> requests.Response`

Low-level HTTP call. Sends POST to `self.url` with:

```python
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {self.api_key}"  # if BEARER auth
}

body = {
    "messages": self.messages,
    "model": self.model,
    "stream": stream,
    **kwargs,
    **self.params
}
```

Returns raw `requests.Response`.

**Raises:** `ValueError` if model, api_key, or url not set.

---

#### Response Parsing

##### `_stream_response(response: requests.Response) -> Generator[str]`

Parses Server-Sent Events (SSE) stream. For each line:
1. Decodes UTF-8
2. Calls `decode_stream_response(line)`
3. Yields non-None content strings
4. After stream ends: joins all tokens and adds as assistant message to history
5. If no content received: tries to parse accumulated text as JSON error

##### `decode_stream_response(line: str) -> str | None`

Parses a single SSE line in OpenAI format:
```
data: {"choices": [{"delta": {"content": "Hello"}}]}
data: [DONE]
```

Returns content string or None.

##### `_non_stream_response(response: requests.Response) -> str`

Parses JSON response: `response.json()["choices"][0]["message"]["content"]`.

**Note:** Does NOT add assistant message to history (unlike streaming mode). This is likely a bug.

##### `print_stream(stream: Generator) -> None`

Helper to print streaming tokens to stdout.

---

### Provider Presets (`llm/__init__.py`)

All presets subclass `LLM` and set `base_url`:

| Class | Base URL | Notes |
|-------|----------|-------|
| `Deepseek` | `https://api.deepseek.com` | DeepSeek API |
| `Grok` | `https://api.x.ai/v1` | xAI Grok API |
| `Doubao` | `https://ark.cn-beijing.volces.com/api/v3` | ByteDance Doubao |
| `Qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Alibaba Qwen |
| `OpenAI` | `https://api.openai.com/v1` | OpenAI API |
| `Gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` | Google Gemini (OpenAI-compat) |
| `Ollama` | `http://{ip}:11434/api/chat` | Local Ollama (uses `url`, not `base_url`) |

#### Ollama Specifics

```python
class Ollama(LLM):
    def __init__(self, ip="localhost", *args, api_key="ollama", **kwargs):
        super().__init__(*args, url=f"http://{ip}:11434/api/chat", api_key=api_key, **kwargs)
```

Ollama overrides two methods:

##### `add_message(role, content, image_path=None)`

Uses Ollama's image format instead of OpenAI's:
```python
# Ollama format:
{"role": "user", "content": "...", "images": ["base64data"]}
# vs OpenAI format:
{"role": "user", "content": [{"type": "text", "text": "..."}, {"type": "image_url", ...}]}
```

##### `decode_stream_response(line)`

Parses Ollama's streaming format:
```json
{"message": {"content": "token"}}
```
vs OpenAI's SSE `data: {...}` format.

---

## Implementation Notes

### HTTP Client

Uses `requests.post()` directly -- no retries, no timeouts on the request itself, no connection pooling. For streaming, uses `response.iter_lines()`.

### Message History

- Messages are stored as a flat list in `self.messages`
- System messages are just regular messages with `role: "system"` at index 0
- FIFO eviction removes `messages[0]` when limit exceeded -- this can evict system instructions
- In streaming mode, the full response is accumulated and added as `role: "assistant"`
- In non-streaming mode, the response is NOT added to history

### Image Handling

Images are base64-encoded inline in the message content. For a 640x480 JPEG, this adds ~50-100KB to the request. No compression or resizing is applied.

### Streaming Protocol

The base class parses OpenAI's SSE format:
```
data: {"id":"...","choices":[{"delta":{"content":"Hello"}}]}
data: {"id":"...","choices":[{"delta":{"content":" world"}}]}
data: [DONE]
```

Ollama uses a different format (JSON per line, no `data:` prefix) and overrides `decode_stream_response()`.

---

## Code Patterns

### Basic Usage

```python
from sunfounder_voice_assistant.llm import OpenAI

llm = OpenAI(api_key="sk-...", model="gpt-4o-mini")
llm.set_instructions("You are a helpful robot dog.")

# Non-streaming
response = llm.prompt("Hello!")
print(response)

# Streaming
for token in llm.prompt("Tell me a joke", stream=True):
    if token:
        print(token, end="", flush=True)
print()
```

### With Image

```python
response = llm.prompt("What do you see?", image_path="./photo.jpg", stream=True)
for token in response:
    if token:
        print(token, end="", flush=True)
```

### Custom Parameters

```python
llm.set("temperature", 0.3)
llm.set("max_tokens", 200)
llm.set("top_p", 0.9)
```

### Ollama Local

```python
from sunfounder_voice_assistant.llm import Ollama

llm = Ollama(ip="192.168.1.100", model="deepseek-r1:1.5b")
response = llm.prompt("Hello", stream=True)
```

### Direct Message List

```python
# Replace entire conversation
messages = [
    {"role": "system", "content": "You are a pirate."},
    {"role": "user", "content": "Hello!"},
]
response = llm.prompt(messages, stream=True)
```

### PiDog Integration Pattern

PiDog does NOT use this LLM class directly. Instead, `autonomous_dog.py` passes a custom LLM wrapper that calls the Anthropic API via the `anthropic` Python SDK. The wrapper implements the same `prompt()` interface:

```python
class CustomLLM:
    def prompt(self, msg, image_path=None, stream=True, **kwargs):
        # Call Anthropic API
        yield token  # Must be a generator for streaming

    def set_instructions(self, instructions):
        self.system_prompt = instructions
```

---

## Gotchas

1. **System instructions can be evicted**: With `max_messages=20`, after 19 user/assistant exchanges, the system message at index 0 gets popped. Long conversations lose their instructions. Workaround: set `max_messages` high or periodically re-add instructions.

2. **Non-streaming does not save to history**: `_non_stream_response()` returns the response text but does not call `add_message("assistant", ...)`. This means non-streaming conversations have no memory of assistant responses. Streaming mode correctly saves responses.

3. **`Authorization.API_KEY` produces no header**: The `chat()` method only has an `if self.authorization == Authorization.BEARER` check. There is no `elif` for `API_KEY`. Using `API_KEY` authorization results in no `Authorization` header being sent.

4. **No request timeout**: `requests.post()` is called without a `timeout` parameter. Network issues can hang the entire main loop indefinitely.

5. **No error handling on HTTP errors**: The `chat()` method does not check `response.status_code`. Errors are only caught if the streaming parser encounters them. A 401 or 500 response in non-streaming mode will crash at `response.json()["choices"]`.

6. **`prompt()` with list replaces all history**: Passing `msg` as a list replaces `self.messages` entirely, losing any system instructions that were set. The VoiceAssistant's `think()` always passes a string, so this does not affect normal usage.

7. **Image type detection is naive**: `get_base_64_url_from_image()` uses `image_path.split(".")[-1]` to determine MIME type. A file named `photo.backup.jpg` correctly returns `"jpg"`, but a file without an extension crashes.

8. **`set_instructions` is additive**: Each call adds another system message. Calling it twice creates two system messages, both counting toward `max_messages`.

9. **Ollama URL uses `url` not `base_url`**: The Ollama preset sets `url` directly to `http://{ip}:11434/api/chat`. This bypasses the `/chat/completions` suffix logic. Calling `set_base_url()` afterward would override the URL incorrectly.

10. **No content-type negotiation**: The streaming parser assumes `text/event-stream` (OpenAI SSE) format. Providers that return `application/json` streaming (like some Ollama versions) may not parse correctly with the base class. Ollama handles this with its override.
