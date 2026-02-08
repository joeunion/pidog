"""Moonshine ONNX STT - Drop-in replacement for Vosk with better accuracy

Moonshine is purpose-built for edge devices. On Pi 5 it runs at ~9.3x realtime
with the tiny model, has ~48% lower error rates than Whisper Tiny, and needs
only 27M parameters (~190MB).

This module implements the same interface as sunfounder_voice_assistant.stt.Vosk
so it can be used as a transparent replacement in VoiceAssistant and
ConversationManager.

Dependencies:
    pip install useful-moonshine-onnx silero-vad
"""

import time
import queue
import logging
import threading
import numpy as np

logger = logging.getLogger(__name__)

# Audio parameters matching Moonshine requirements
SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # ~32ms per chunk at 16kHz
MAX_SPEECH_SECS = 15  # Safety cap to prevent hallucination on long audio

# Hardware capture parameters — Google VoiceHAT is locked to 48kHz stereo.
# We capture at the native rate and downsample in Python.
CAPTURE_RATE = 48000
DOWNSAMPLE_FACTOR = CAPTURE_RATE // SAMPLE_RATE  # 3
CAPTURE_CHUNK = CHUNK_SIZE * DOWNSAMPLE_FACTOR   # 1536 samples at 48kHz → 512 at 16kHz


class MoonshineStt:
    """Speech-to-text engine using Moonshine ONNX + Silero VAD.

    Drop-in replacement for sunfounder_voice_assistant.stt.Vosk.
    """

    def __init__(self, language=None, samplerate=None, device=None, log=None):
        """Initialize Moonshine STT.

        Args:
            language: Ignored (Moonshine is English-optimized).
            samplerate: Ignored (always uses 16kHz internally).
            device: Audio input device index or name. None = default.
            log: Optional logger instance.
        """
        self._log = log or logger
        self._device = device
        self._ready = False
        self._model = None
        self._tokenizer = None
        self._vad_model = None
        self._vad_iterator = None

        # Wake word state
        self._wake_words = []
        self._waked = False
        self._wake_thread = None
        self._wake_listening = False

        # Audio stream
        self._stream = None

        # Capture settings (probed in _probe_capture_settings)
        self._capture_rate = CAPTURE_RATE
        self._capture_channels = 1
        self._needs_downsample = True

        self._init_model()
        self._probe_capture_settings()

    @staticmethod
    def _find_mic_device():
        """Find the best microphone device by name.

        On PiDog the ALSA config creates a 'mic' device that points to the
        real hardware mic. The default device is often 'robothat' which is
        the I2C bus — not a real microphone.

        Returns:
            Device name string, or None to use sounddevice default.
        """
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            # Prefer 'mic' (ALSA alias with resampling support) over
            # 'mic_hw' (raw hardware — may not support 16kHz).
            for target in ('mic', 'mic_hw'):
                for i, dev in enumerate(devices):
                    dev_name = dev['name'].split(',')[0].strip()
                    if dev_name == target and dev['max_input_channels'] > 0:
                        logger.info(f"Audio input device: {dev['name']} (index {i})")
                        return i
        except Exception as e:
            logger.debug(f"Device discovery failed: {e}")
        return None

    def _probe_capture_settings(self):
        """Probe audio device to determine capture rate and channels.

        The Google VoiceHAT hardware only supports 48kHz stereo S32_LE.
        ALSA 'plug' wrapper (used by 'robothat'/'default' devices) handles
        rate/channel conversion transparently. Raw devices like 'mic' and
        'mic_hw' do NOT convert — they reject non-native rates.

        Strategy:
        1. Try default device (None) at 16kHz — works when ALSA default is
           'robothat' (plug-wrapped), which is the case when running as root.
        2. Try explicit 'mic' device at 48kHz with Python downsampling.
        3. Try 48kHz stereo as last resort.
        """
        try:
            import sounddevice as sd

            # First: try default device at 16kHz (vendor approach).
            # As root, ALSA default = 'robothat' which has plug wrapper
            # and handles 16kHz conversion transparently.
            try:
                sd.check_input_settings(
                    device=None, channels=1,
                    dtype='float32', samplerate=SAMPLE_RATE)
                self._device = None
                self._capture_rate = SAMPLE_RATE
                self._capture_channels = 1
                self._needs_downsample = False
                self._log.info(
                    "Audio: default device supports 16kHz mono directly")
                return
            except Exception:
                pass

            # Default didn't work at 16kHz — find mic device and use 48kHz
            if self._device is None:
                self._device = self._find_mic_device()

            device = self._device

            # Try 48kHz mono
            try:
                sd.check_input_settings(
                    device=device, channels=1,
                    dtype='float32', samplerate=CAPTURE_RATE)
                self._capture_rate = CAPTURE_RATE
                self._capture_channels = 1
                self._needs_downsample = True
                self._log.info(
                    f"Audio: device {device} at 48kHz mono, will downsample")
                return
            except Exception:
                pass

            # Try 48kHz stereo (matches raw hardware exactly)
            try:
                sd.check_input_settings(
                    device=device, channels=2,
                    dtype='float32', samplerate=CAPTURE_RATE)
                self._capture_rate = CAPTURE_RATE
                self._capture_channels = 2
                self._needs_downsample = True
                self._log.info(
                    f"Audio: device {device} at 48kHz stereo, will downsample")
                return
            except Exception:
                pass

            # Nothing worked — fall back to default at 16kHz and hope
            self._log.warning(
                f"Audio: device {device} rejected all formats, "
                f"falling back to default device")
            self._device = None
            self._capture_rate = SAMPLE_RATE
            self._capture_channels = 1
            self._needs_downsample = False

        except Exception as e:
            self._log.error(f"Audio probe failed: {e}")
            self._capture_rate = SAMPLE_RATE
            self._capture_channels = 1
            self._needs_downsample = False

    @staticmethod
    def _downsample_48k_to_16k(audio_48k):
        """Downsample audio from 48kHz to 16kHz (factor of 3).

        Uses simple averaging (box filter) as anti-alias before decimation.
        Quality is sufficient for speech recognition.

        Args:
            audio_48k: Float32 mono audio at 48kHz.

        Returns:
            Float32 mono audio at 16kHz.
        """
        n = len(audio_48k) - len(audio_48k) % DOWNSAMPLE_FACTOR
        if n == 0:
            return np.array([], dtype=np.float32)
        return audio_48k[:n].reshape(-1, DOWNSAMPLE_FACTOR).mean(
            axis=1).astype(np.float32)

    def _init_model(self):
        """Load Moonshine model and Silero VAD."""
        try:
            from moonshine_onnx import MoonshineOnnxModel, load_tokenizer
            import silero_vad

            self._log.info("Loading Moonshine ONNX model (tiny)...")
            self._model = MoonshineOnnxModel(model_name="moonshine/tiny")
            self._tokenizer = load_tokenizer()

            # Warmup inference to avoid cold-start latency on first real call
            self._model.generate(np.zeros(SAMPLE_RATE, dtype=np.float32)[np.newaxis, :])
            self._log.info("Moonshine model loaded and warmed up")

            self._log.info("Loading Silero VAD...")
            self._vad_model = silero_vad.load_silero_vad(onnx=True)
            self._log.info("Silero VAD loaded")

            self._ready = True

        except Exception as e:
            self._log.error(f"Failed to initialize Moonshine STT: {e}")
            self._ready = False

    def _create_vad_iterator(self):
        """Create a fresh VAD iterator for a new listening session."""
        import silero_vad
        return silero_vad.VADIterator(
            model=self._vad_model,
            threshold=0.5,
            sampling_rate=SAMPLE_RATE,
            min_silence_duration_ms=300,
            speech_pad_ms=30,
        )

    def _transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio array with Moonshine.

        Args:
            audio: Float32 mono audio at 16kHz, shape (N,).

        Returns:
            Transcribed text string.
        """
        if len(audio) < SAMPLE_RATE * 0.1:  # Less than 100ms
            return ""

        # Model expects shape (1, N) float32
        tokens = self._model.generate(audio[np.newaxis, :].astype(np.float32))
        text = self._tokenizer.decode_batch(tokens)[0].strip()
        return text

    def is_ready(self) -> bool:
        """Check if the STT engine is ready.

        Returns:
            True if model and VAD are loaded.
        """
        return self._ready

    def listen(self, stream=False, device=None, samplerate=None, timeout=None) -> object:
        """Listen for speech and transcribe.

        Args:
            stream: If True, yield partial results as a generator.
            device: Audio device (overrides default). Ignored if set — we use
                    the device configured at init or the system default.
            samplerate: Ignored (always 16kHz).
            timeout: Max seconds to wait for speech start. None = wait forever.

        Returns:
            str: Transcribed text (non-streaming).
            generator: Yields dicts with partial/final results (streaming).
        """
        if not self._ready:
            return "" if not stream else iter([])

        if stream:
            return self._listen_streaming(timeout=timeout)
        else:
            return self._listen_blocking(timeout=timeout)

    def _audio_chunk_to_16k(self, indata):
        """Convert a raw capture chunk to 16kHz mono float32.

        Handles stereo→mono and 48kHz→16kHz conversion as needed
        based on probed device settings.

        Args:
            indata: Raw audio from sounddevice callback, shape (frames, channels).

        Returns:
            Float32 mono audio at 16kHz.
        """
        # Extract mono
        mono = indata[:, 0].copy()
        # Downsample if capturing at 48kHz
        if self._needs_downsample:
            return self._downsample_48k_to_16k(mono)
        return mono

    def _listen_blocking(self, timeout=None) -> str:
        """Listen for a single utterance and return transcription.

        Uses VAD to detect speech start/end, then transcribes the
        captured audio with Moonshine.

        Args:
            timeout: Max seconds to wait for speech to start.

        Returns:
            Transcribed text, or "" if timeout/no speech.
        """
        import sounddevice as sd

        audio_queue = queue.Queue()
        vad = self._create_vad_iterator()
        speech_audio = []
        speech_started = False
        start_time = time.time()
        capture_blocksize = (CAPTURE_CHUNK if self._needs_downsample
                             else CHUNK_SIZE)

        chunk_count = 0
        peak_max = 0.0

        def audio_callback(indata, frames, time_info, status):
            if status:
                self._log.debug(f"Audio status: {status}")
            audio_queue.put(self._audio_chunk_to_16k(indata))

        try:
            self._log.info(
                f"Opening audio stream (device={self._device}, "
                f"rate={self._capture_rate}, ch={self._capture_channels}, "
                f"blocksize={capture_blocksize})...")
            with sd.InputStream(
                samplerate=self._capture_rate,
                channels=self._capture_channels,
                dtype='float32',
                blocksize=capture_blocksize,
                device=self._device,
                callback=audio_callback,
            ):
                self._log.info(
                    f"Listening (device={self._device}, "
                    f"rate={self._capture_rate}, ch={self._capture_channels})")
                while True:
                    # Check timeout (only before speech starts)
                    if not speech_started and timeout is not None:
                        if time.time() - start_time > timeout:
                            self._log.info(
                                f"Listen timeout ({timeout}s), "
                                f"chunks={chunk_count}, peak={peak_max:.4f}")
                            return ""

                    # Check max speech duration
                    if speech_started:
                        speech_duration = sum(len(c) for c in speech_audio) / SAMPLE_RATE
                        if speech_duration >= MAX_SPEECH_SECS:
                            self._log.debug(f"Max speech duration reached ({MAX_SPEECH_SECS}s)")
                            break

                    try:
                        chunk = audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    chunk_count += 1
                    chunk_peak = float(np.max(np.abs(chunk)))
                    if chunk_peak > peak_max:
                        peak_max = chunk_peak

                    # Feed chunk to VAD (accepts numpy float32 directly)
                    vad_result = vad(chunk)

                    if vad_result is not None:
                        if 'start' in vad_result:
                            speech_started = True
                            self._log.info("VAD: speech started")
                        if 'end' in vad_result:
                            if speech_started:
                                self._log.info("VAD: speech ended")
                                break

                    if speech_started:
                        speech_audio.append(chunk)

        except Exception as e:
            self._log.error(f"Audio capture error: {e}")
            return ""

        if not speech_audio:
            return ""

        audio = np.concatenate(speech_audio)
        text = self._transcribe(audio)
        self._log.debug(f"Transcribed: '{text}'")
        return text

    def _listen_streaming(self, timeout=None):
        """Listen and yield partial transcriptions during speech.

        Yields:
            dict with keys:
                - done (bool): True when speech is finished
                - partial (str): Partial transcription during speech
                - final (str): Final transcription when done
        """
        import sounddevice as sd

        audio_queue = queue.Queue()
        vad = self._create_vad_iterator()
        speech_audio = []
        speech_started = False
        start_time = time.time()
        last_partial_time = 0
        capture_blocksize = (CAPTURE_CHUNK if self._needs_downsample
                             else CHUNK_SIZE)

        def audio_callback(indata, frames, time_info, status):
            if status:
                self._log.debug(f"Audio status: {status}")
            audio_queue.put(self._audio_chunk_to_16k(indata))

        try:
            with sd.InputStream(
                samplerate=self._capture_rate,
                channels=self._capture_channels,
                dtype='float32',
                blocksize=capture_blocksize,
                device=self._device,
                callback=audio_callback,
            ):
                while True:
                    if not speech_started and timeout is not None:
                        if time.time() - start_time > timeout:
                            yield {"done": True, "partial": "", "final": ""}
                            return

                    if speech_started:
                        speech_duration = sum(len(c) for c in speech_audio) / SAMPLE_RATE
                        if speech_duration >= MAX_SPEECH_SECS:
                            break

                    try:
                        chunk = audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    vad_result = vad(chunk)

                    if vad_result is not None:
                        if 'start' in vad_result:
                            speech_started = True
                        if 'end' in vad_result:
                            if speech_started:
                                break

                    if speech_started:
                        speech_audio.append(chunk)

                        # Yield partial transcription every ~0.5s
                        now = time.time()
                        if now - last_partial_time >= 0.5 and len(speech_audio) > 0:
                            last_partial_time = now
                            partial_audio = np.concatenate(speech_audio)
                            partial_text = self._transcribe(partial_audio)
                            yield {"done": False, "partial": partial_text, "final": ""}

        except Exception as e:
            self._log.error(f"Streaming audio error: {e}")
            yield {"done": True, "partial": "", "final": ""}
            return

        if not speech_audio:
            yield {"done": True, "partial": "", "final": ""}
            return

        audio = np.concatenate(speech_audio)
        final_text = self._transcribe(audio)
        self._log.debug(f"Final transcription: '{final_text}'")
        yield {"done": True, "partial": "", "final": final_text}

    def listen_until_silence(self, silence_threshold=2.0) -> str:
        """Listen and accumulate speech until sustained silence.

        Captures multiple utterances (VAD start→end cycles) and stops
        when silence exceeds the threshold. Returns all accumulated text.

        Args:
            silence_threshold: Seconds of silence to stop listening.

        Returns:
            All accumulated transcribed text.
        """
        if not self._ready:
            return ""

        import sounddevice as sd

        audio_queue = queue.Queue()
        vad = self._create_vad_iterator()
        all_text = []
        speech_audio = []
        speech_started = False
        last_speech_end = time.time()
        capture_blocksize = (CAPTURE_CHUNK if self._needs_downsample
                             else CHUNK_SIZE)

        def audio_callback(indata, frames, time_info, status):
            if status:
                self._log.debug(f"Audio status: {status}")
            audio_queue.put(self._audio_chunk_to_16k(indata))

        try:
            with sd.InputStream(
                samplerate=self._capture_rate,
                channels=self._capture_channels,
                dtype='float32',
                blocksize=capture_blocksize,
                device=self._device,
                callback=audio_callback,
            ):
                while True:
                    # Check silence threshold (only after at least one utterance)
                    if not speech_started and all_text:
                        if time.time() - last_speech_end > silence_threshold:
                            self._log.debug("Silence threshold reached")
                            break

                    # Safety cap per utterance
                    if speech_started:
                        speech_duration = sum(len(c) for c in speech_audio) / SAMPLE_RATE
                        if speech_duration >= MAX_SPEECH_SECS:
                            # Transcribe what we have and reset
                            audio = np.concatenate(speech_audio)
                            text = self._transcribe(audio)
                            if text:
                                all_text.append(text)
                            speech_audio = []
                            speech_started = False
                            last_speech_end = time.time()
                            vad = self._create_vad_iterator()
                            continue

                    try:
                        chunk = audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        # Still check silence during empty chunks
                        if not speech_started and all_text:
                            if time.time() - last_speech_end > silence_threshold:
                                break
                        continue

                    vad_result = vad(chunk)

                    if vad_result is not None:
                        if 'start' in vad_result:
                            speech_started = True
                        if 'end' in vad_result:
                            if speech_started:
                                # Transcribe this utterance
                                if speech_audio:
                                    audio = np.concatenate(speech_audio)
                                    text = self._transcribe(audio)
                                    if text:
                                        all_text.append(text)
                                speech_audio = []
                                speech_started = False
                                last_speech_end = time.time()
                                # Reset VAD for next utterance
                                vad = self._create_vad_iterator()

                    if speech_started:
                        speech_audio.append(chunk)

        except Exception as e:
            self._log.error(f"listen_until_silence error: {e}")

        # Transcribe any remaining audio
        if speech_audio:
            audio = np.concatenate(speech_audio)
            text = self._transcribe(audio)
            if text:
                all_text.append(text)

        result = " ".join(all_text)
        self._log.debug(f"listen_until_silence result: '{result}'")
        return result

    def set_language(self, language, init=True):
        """Set language (no-op — Moonshine is English-optimized).

        Args:
            language: Ignored.
            init: Ignored.
        """
        pass

    def set_wake_words(self, wake_words):
        """Set wake words for detection.

        Args:
            wake_words: List of wake word strings, or a single string.
        """
        if isinstance(wake_words, str):
            self._wake_words = [wake_words.lower()]
        else:
            self._wake_words = [w.lower() for w in wake_words]
        self._log.debug(f"Wake words set: {self._wake_words}")

    def start_listening_wake_words(self):
        """Start background thread that listens for wake words.

        Sets self._waked = True when a wake word is detected.
        """
        if self._wake_listening:
            return

        self._wake_listening = True
        self._waked = False

        self._wake_thread = threading.Thread(
            target=self._wake_word_loop, daemon=True
        )
        self._wake_thread.start()
        self._log.debug("Wake word listener started")

    def _wake_word_loop(self):
        """Background loop that listens for wake words."""
        while self._wake_listening:
            try:
                text = self.listen(timeout=5.0)
                if text:
                    text_lower = text.lower()
                    for wake in self._wake_words:
                        if wake in text_lower:
                            self._waked = True
                            self._log.info(f"Wake word detected: '{wake}' in '{text}'")
                            # Stay waked until consumed — don't keep listening
                            while self._waked and self._wake_listening:
                                time.sleep(0.1)
                            break
            except Exception as e:
                self._log.error(f"Wake word loop error: {e}")
                time.sleep(1.0)

    def is_waked(self) -> bool:
        """Check if wake word was detected.

        Returns:
            True if wake word detected (resets after read).
        """
        if self._waked:
            self._waked = False
            return True
        return False

    def stop_listening(self):
        """Stop wake word listening."""
        self._wake_listening = False
        if self._wake_thread and self._wake_thread.is_alive():
            self._wake_thread.join(timeout=3.0)
        self._wake_thread = None
        self._log.debug("Wake word listener stopped")

    def close(self):
        """Clean up resources."""
        self.stop_listening()
        self._model = None
        self._tokenizer = None
        self._vad_model = None
        self._ready = False
        self._log.info("Moonshine STT closed")
