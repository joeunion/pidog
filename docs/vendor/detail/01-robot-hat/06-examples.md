# robot-hat: Examples

<!-- Status: complete | Iteration: 1 -->

> All 23 example files annotated with walkthroughs

## Example Index

| File | Purpose | Hardware Used | Key Patterns |
|------|---------|---------------|--------------|
| `led_test.py` | LED blink patterns | LED (GPIO26) | on/off, blink with timing |
| `pin_input.py` | Read GPIO input | Pin D3 | Polling digital input |
| `ultrasonic.py` | Distance measurement | Ultrasonic (D2/D3) | Sensor polling, formatting |
| `llm_deepseek.py` | Deepseek AI chat | None (API) | LLM setup, streaming |
| `llm_doubao.py` | Doubao AI chat | None (API) | LLM setup, streaming |
| `llm_doubao_with_image.py` | Doubao vision | Picamera2 | Image capture, multimodal LLM |
| `llm_gemini.py` | Google Gemini chat | None (API) | LLM setup, streaming |
| `llm_grok.py` | xAI Grok chat | None (API) | LLM setup, streaming |
| `llm_ollama.py` | Local Ollama chat | None (local) | Local LLM, streaming |
| `llm_ollama_with_image.py` | Ollama vision | Picamera2 | Local multimodal LLM |
| `llm_openai.py` | OpenAI GPT chat | None (API) | LLM setup, streaming, max messages |
| `llm_openai_with_image.py` | OpenAI vision | Picamera2 | Image capture, GPT-4 vision |
| `llm_others.py` | Generic LLM setup | None (API) | Custom API endpoints |
| `llm_qwen.py` | Alibaba Qwen chat | None (API) | LLM setup, streaming |
| `stt_vosk_stream.py` | Streaming speech recognition | Microphone | sounddevice, partial results |
| `stt_vosk_wake_word.py` | Wake word detection | Microphone | wait_until_heard() |
| `stt_vosk_wake_word_thread.py` | Threaded wake word | Microphone | Threading, callbacks |
| `stt_vosk_without_stream.py` | Non-streaming STT | Microphone | Record then transcribe |
| `tts_espeak.py` | Espeak text-to-speech | Speaker | Fast, robotic TTS |
| `tts_openai.py` | OpenAI TTS | Speaker, API | Natural voice, API key |
| `tts_pico2wave.py` | Pico2Wave TTS | Speaker | Lightweight TTS |
| `tts_piper.py` | Piper neural TTS | Speaker | Fast local neural TTS |
| `voice_assistant.py` | Full voice assistant | All | LLM+STT+TTS+Camera integration |

## Detailed Walkthroughs

### led_test.py

**Purpose**: Demonstrate LED control patterns (on/off/blink).

**Code Flow**:
1. Create LED object (default pin "LED" = GPIO26)
2. Turn on for 2 seconds
3. Turn off for 2 seconds
4. Slow blink (1s delay) for 5 seconds
5. Fast triple blink (0.1s delay, 0.5s pause) repeating for 5 seconds
6. Double blink pattern for 5 seconds
7. Close LED (stops blink thread)

**Key Concepts**:
- `led.on()` / `led.off()` for manual control
- `led.blink(times, delay, pause)` for background blinking
- `times`: Blinks per pattern cycle
- `delay`: Time per on/off cycle
- `pause`: Time between pattern repeats
- Always call `led.close()` to clean up blink thread

**Usage**: Basic status indicator for robot states.

---

### pin_input.py

**Purpose**: Read digital input from GPIO pin.

**Code Flow**:
1. Create Pin object on D3 with mode IN, pull-up enabled
2. Infinite loop: read pin value every 100ms, print to console

**Key Concepts**:
- `Pin(name, mode=Pin.IN, pull=Pin.PULL_UP)` for input configuration
- Pull-up: pin reads HIGH when floating, LOW when grounded
- `pin.value()` returns 0 or 1
- No interrupt-based reading (polling only)

**Usage**: Read button, switch, or sensor digital states.

---

### ultrasonic.py

**Purpose**: Measure distance using HC-SR04 ultrasonic sensor.

**Hardware Setup**:
- Trigger pin: D2 (GPIO27)
- Echo pin: D3 (GPIO22)

**Code Flow**:
1. Create Ultrasonic object with trig/echo pins
2. Infinite loop: read distance, print with ANSI clear (`\r\x1b[K`), sleep 200ms

**Key Concepts**:
- `ultrasonic.read()` returns distance in cm
- Returns -1 on timeout (no obstacle or out of range)
- ANSI escape `\r\x1b[K` clears line for live updating display
- `end=""` and `flush=True` for same-line updates

**Usage**: Obstacle avoidance, distance measurement.

---

### LLM Examples (llm_*.py)

All LLM examples follow similar pattern:

**Common Setup**:
1. Import LLM class from `robot_hat.llm`
2. Import API key from `secret.py`
3. Create LLM instance with `api_key` and `model`
4. Set max messages, instructions, welcome message
5. Input loop: prompt LLM, print response (streaming or non-streaming)

**Streaming Pattern**:
```python
response = llm.prompt(input_text, stream=True)
for next_word in response:
    if next_word:
        print(next_word, end="", flush=True)
print("")
```

**Non-Streaming Pattern**:
```python
response = llm.prompt(input_text)
print(f"response: {response}")
```

#### llm_openai.py

**Model**: `gpt-4o` or `gpt-4o-mini`
**API**: openai.com
**Key Settings**:
- `set_max_messages(20)`: Conversation history limit
- `set_instructions()`: System prompt
- `set_welcome()`: Initial greeting

#### llm_deepseek.py

**Model**: `deepseek-chat`
**API**: deepseek.com
**Notes**: Chinese AI company, cost-effective alternative to OpenAI

#### llm_doubao.py

**Model**: Doubao (ByteDance's LLM)
**API**: volcengine.com
**Notes**: Chinese market, requires region-specific API key

#### llm_gemini.py

**Model**: `gemini-2.0-flash-exp`
**API**: Google AI Studio
**Notes**: Google's latest multimodal model, free tier available

#### llm_grok.py

**Model**: Grok (xAI's LLM)
**API**: x.ai
**Notes**: Elon Musk's AI company, conversational style

#### llm_ollama.py

**Model**: `llama3.2` (local)
**API**: Local Ollama server (localhost:11434)
**Notes**: Runs locally, no API key needed, requires Ollama installed

#### llm_qwen.py

**Model**: Qwen (Alibaba Cloud's LLM)
**API**: dashscope.aliyuncs.com
**Notes**: Chinese market, strong Chinese language support

#### llm_others.py

**Purpose**: Template for custom LLM API endpoints
**Pattern**: Use generic `LLM` class with custom `base_url`

---

### Vision LLM Examples (llm_*_with_image.py)

Pattern for multimodal LLMs (text + image):

**Common Setup**:
1. Initialize picamera2
2. Capture image
3. Save to temp file (`/tmp/image.jpg`)
4. Create LLM with `with_image=True`
5. Prompt LLM: "What do you see?" with image file

#### llm_openai_with_image.py

**Model**: `gpt-4o` (vision capable)
**Camera**: Picamera2, 640x480 resolution
**Pattern**:
```python
camera = Picamera2()
camera.start()
camera.capture_file("/tmp/image.jpg")
camera.stop()

llm = OpenAI(api_key=API_KEY, model="gpt-4o")
response = llm.prompt("What do you see?", file_path="/tmp/image.jpg")
```

#### llm_doubao_with_image.py

**Model**: Doubao vision model
**Similar pattern**: Capture, save, prompt with image

#### llm_ollama_with_image.py

**Model**: `llava` (local vision model via Ollama)
**Notes**: Requires Ollama with llava model installed locally

---

### STT Examples (stt_vosk_*.py)

All STT examples use Vosk speech recognition engine (offline).

#### stt_vosk_wake_word.py

**Purpose**: Wait for wake word before returning.

**Pattern**:
```python
stt = STT(language="en-us")
stt.set_wake_words(["hey robot"])
print('Wake me with: "Hey robot"')
result = stt.wait_until_heard()  # Blocks until wake word detected
print("Wake word detected")
```

**Key Concepts**:
- `set_wake_words()`: List of phrases to detect
- `wait_until_heard()`: Blocking call, returns when wake word heard
- Case-insensitive matching
- No partial word matching (full phrase required)

#### stt_vosk_wake_word_thread.py

**Purpose**: Non-blocking wake word detection with callback.

**Pattern**:
```python
def on_wake():
    print("Wake word detected!")

stt = STT(language="en-us")
stt.set_wake_words(["hey robot"])
stt.wait_until_heard_threaded(callback=on_wake)

print("Listening in background...")
# Main thread continues
while True:
    time.sleep(1)
```

**Key Concepts**:
- `wait_until_heard_threaded()`: Returns immediately, calls callback when wake word detected
- Callback runs in separate thread
- Useful for continuous monitoring without blocking

#### stt_vosk_stream.py

**Purpose**: Streaming speech recognition with partial results.

**Pattern**:
```python
stt = STT(language="en-us")
print("Speak now...")

for result in stt.stream():  # Generator yielding partial/final results
    if result['partial']:
        print(f"Partial: {result['text']}")
    elif result['final']:
        print(f"Final: {result['text']}")
```

**Key Concepts**:
- `stream()`: Generator yielding recognition results
- Partial results: Real-time transcription (may change)
- Final results: Confirmed transcription (end of utterance)
- Uses sounddevice for audio input

#### stt_vosk_without_stream.py

**Purpose**: Record audio, then transcribe (non-streaming).

**Pattern**:
```python
stt = STT(language="en-us")
print("Recording for 5 seconds...")

audio = stt.record(duration=5)
text = stt.transcribe(audio)
print(f"Transcription: {text}")
```

**Key Concepts**:
- `record(duration)`: Capture audio for fixed duration
- `transcribe(audio)`: Process recorded audio, return text
- Simpler than streaming, but no real-time feedback
- Good for voice commands (short utterances)

---

### TTS Examples (tts_*.py)

#### tts_piper.py

**Engine**: Piper (fast local neural TTS)
**Model**: `en_US-amy-low` (or other Piper voices)

**Pattern**:
```python
tts = Piper()
tts.set_model('en_US-amy-low')
tts.say("Hello, I'm Piper TTS.")
```

**Characteristics**:
- Fast (~100-200ms latency)
- High quality, natural sounding
- Local (no API calls)
- Multiple voices/languages
- Embeds espeak-ng for phonemization

**Usage**: Best for offline robots, fast response needed.

#### tts_espeak.py

**Engine**: Espeak (formant synthesis TTS)

**Pattern**:
```python
tts = Espeak()
tts.say("Hello, I'm Espeak.")
```

**Characteristics**:
- Very fast (<50ms latency)
- Robotic, synthetic voice
- Lightweight (~5 MB)
- Good for debug messages

**Usage**: Quick feedback, status messages, alarms.

#### tts_pico2wave.py

**Engine**: Pico2Wave (SVOX Pico TTS)

**Pattern**:
```python
tts = Pico2Wave()
tts.say("Hello, I'm Pico2Wave.")
```

**Characteristics**:
- Medium quality
- Lightweight
- No network required
- Limited voices

**Usage**: Offline TTS when quality matters more than speed.

#### tts_openai.py

**Engine**: OpenAI TTS API
**Model**: `tts-1` or `tts-1-hd`
**Voice**: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

**Pattern**:
```python
tts = OpenAI_TTS(api_key=API_KEY, model="tts-1", voice="alloy")
tts.say("Hello from OpenAI TTS.")
```

**Characteristics**:
- Highest quality (human-like)
- Requires API key and internet
- Latency: 500-2000ms
- Cost per character

**Usage**: High-quality voice interactions, demos, customer-facing robots.

---

### voice_assistant.py

**Purpose**: Full-featured voice assistant integrating LLM, STT, TTS, and camera.

**Components**:
- LLM: OpenAI GPT-4o-mini (can use any LLM from examples)
- STT: Vosk (offline speech recognition)
- TTS: Piper (fast local TTS)
- Camera: Picamera2 (optional, for vision)

**Configuration**:
```python
NAME = "Buddy"
WITH_IMAGE = True  # Enable vision
LLM_MODEL = "gpt-4o-mini"
TTS_MODEL = "en_US-ryan-low"  # Piper voice
STT_LANGUAGE = "en-us"
KEYBOARD_ENABLE = True  # Allow text input via keyboard
WAKE_ENABLE = True
WAKE_WORD = ["hey buddy"]
ANSWER_ON_WAKE = "Hi there"  # Response when wake word detected
WELCOME = f"Hi, I'm {NAME}. Wake me up with: hey buddy"
INSTRUCTIONS = "You are a helpful assistant, named Buddy."
```

**Flow**:
1. Initialize VoiceAssistant with all components
2. Display welcome message
3. Wait for wake word (if enabled)
4. Listen for user speech
5. Transcribe speech to text
6. Send text + image (if enabled) to LLM
7. Get LLM response
8. Speak response via TTS
9. Repeat from step 3

**Key Features**:
- **Wake word**: Robot only responds after "hey buddy"
- **Continuous conversation**: No need to repeat wake word during conversation
- **Vision integration**: Can describe what it sees via camera
- **Keyboard fallback**: Type instead of speak (useful for testing)
- **Multimodal**: Combines audio, vision, and language understanding

**Customization Points**:
- Change LLM: Import different LLM class (Ollama for local, Gemini, etc.)
- Change TTS: Use `tts_model` parameter (piper, espeak, openai)
- Change STT: Vosk language models (en-us, de, fr, etc.)
- Instructions: Customize personality, behavior, constraints

**Example Interactions**:
```
User: "Hey Buddy" (wake word)
Robot: "Hi there"
User: "What do you see?"
Robot: [captures image] "I see a table with a laptop and a cup of coffee."
User: "What's the weather like?"
Robot: "I don't have access to weather data, but I can help with other tasks."
```

**Usage**: Template for building custom voice-controlled robots. Replace components as needed for specific use cases (local-only, specific LLM, custom TTS voice).

---

## Common Patterns

### LLM API Key Management

All LLM examples import API key from `secret.py`:
```python
# secret.py
OPENAI_API_KEY = "sk-..."
DEEPSEEK_API_KEY = "..."
GEMINI_API_KEY = "..."
```

Never commit API keys to git. Use `.gitignore` for `secret.py`.

### Streaming vs Non-Streaming

**Streaming** (for interactive responses):
```python
for word in llm.prompt(text, stream=True):
    print(word, end="", flush=True)
```

**Non-Streaming** (for complete responses):
```python
response = llm.prompt(text)
print(response)
```

Streaming provides real-time feedback, non-streaming is simpler for batch processing.

### Camera Image Capture

Standard pattern across vision examples:
```python
camera = Picamera2()
camera.start()
time.sleep(2)  # Warm-up (auto-exposure, focus)
camera.capture_file("/tmp/image.jpg")
camera.stop()
```

Always stop camera when done to release resources.

### STT Vosk Model Location

Vosk models stored in `~/.cache/vosk-models/`. First run downloads model automatically. Models are 50-1000 MB depending on language/quality.

### TTS Speaker Enable

All TTS classes auto-call `enable_speaker()` in `__init__`. No manual speaker enable needed (handled by `robot_hat.tts` wrappers).

## Testing Tips

### Without Hardware

- **LED**: No error if LED pin not connected (just won't light)
- **Ultrasonic**: Returns -1 if sensor missing (safe to test logic)
- **LLM**: All work without hardware (API-based)
- **TTS**: Works without speaker (plays to default audio device)
- **STT**: Works with any USB microphone or laptop mic

### With Hardware

- **LED**: Connect LED to GPIO26 (onboard LED on Robot HAT)
- **Ultrasonic**: Connect HC-SR04 to D2 (trig) and D3 (echo)
- **Camera**: Picamera2 requires Raspberry Pi camera module
- **Speaker**: Connect to audio jack or I2S HAT

### API Key Requirements

Examples requiring API keys:
- OpenAI: `llm_openai*.py`, `tts_openai.py`
- Deepseek: `llm_deepseek.py`
- Doubao: `llm_doubao*.py`
- Gemini: `llm_gemini.py`
- Grok: `llm_grok.py`
- Qwen: `llm_qwen.py`

Examples working without API keys:
- Ollama: `llm_ollama*.py` (requires local Ollama server)
- Piper, Espeak, Pico2Wave: All TTS except OpenAI
- Vosk: All STT examples (offline)
- Hardware examples: `led_test.py`, `pin_input.py`, `ultrasonic.py`

### Quick Start

**Minimal test** (no API key, no hardware):
```bash
python3 examples/led_test.py  # Works without LED (no error)
```

**Speech test** (microphone required):
```bash
python3 examples/stt_vosk_stream.py
```

**TTS test** (speaker required):
```bash
python3 examples/tts_piper.py
```

**LLM test** (API key required):
```bash
# Create secret.py first
echo 'OPENAI_API_KEY="sk-..."' > secret.py
python3 examples/llm_openai.py
```

**Full assistant** (all hardware + API key):
```bash
python3 examples/voice_assistant.py
```
