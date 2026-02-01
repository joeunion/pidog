"""Conversation Manager - Manages wake-word-free conversation modes

This module provides two modes for continuous conversations without repeating
the wake word:

1. Timeout Mode: Stay listening for X seconds after each response
2. VAD Mode: Use voice activity detection to allow natural follow-ups

Both modes end when:
- The timeout/silence threshold is reached
- The user says a goodbye phrase ("bye", "thanks", etc.)
"""

import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation state for wake-word-free follow-ups

    Modes:
    - "none": Default, always require wake word
    - "timeout": Stay listening for X seconds after response
    - "vad": Listen until silence threshold reached
    """

    VALID_MODES = ("none", "timeout", "vad")

    END_PHRASES = [
        "bye", "goodbye", "thanks", "thank you", "that's all",
        "see you later", "see ya", "later", "bye bye"
    ]

    def __init__(self,
                 mode: str = "none",
                 timeout: float = 15.0,
                 vad_silence: float = 2.0):
        """Initialize conversation manager

        Args:
            mode: Conversation mode - "none", "timeout", or "vad"
            timeout: Seconds to stay listening in timeout mode
            vad_silence: Seconds of silence to end VAD mode

        Raises:
            ValueError: If mode is invalid or timeout/vad_silence are not positive
        """
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid conversation mode: {mode}. Must be one of {self.VALID_MODES}")
        if timeout <= 0:
            raise ValueError(f"timeout must be positive, got {timeout}")
        if vad_silence <= 0:
            raise ValueError(f"vad_silence must be positive, got {vad_silence}")

        self.mode = mode
        self.timeout = timeout
        self.vad_silence = vad_silence
        self._active = False
        self._start_time = 0.0
        self._stt = None  # Set when integrated with voice assistant

    def set_stt(self, stt):
        """Set the STT instance for listening

        Args:
            stt: The Vosk STT instance from VoiceAssistant
        """
        self._stt = stt

    def activate(self):
        """Called after PiDog responds - start conversation window"""
        if self.mode != "none":
            self._active = True
            self._start_time = time.time()
            logger.debug(f"Conversation mode activated ({self.mode})")

    def deactivate(self):
        """End conversation mode"""
        self._active = False
        logger.debug("Conversation mode deactivated")

    def is_active(self) -> bool:
        """Check if still in conversation mode

        Returns:
            True if conversation mode is active
        """
        if not self._active or self.mode == "none":
            return False
        if self.mode == "timeout":
            if time.time() - self._start_time > self.timeout:
                self._active = False
        return self._active

    def should_end(self, text: str) -> bool:
        """Check if user said goodbye

        Args:
            text: The user's transcribed speech

        Returns:
            True if the text contains a goodbye phrase
        """
        if not text:
            return False
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self.END_PHRASES)

    def trigger(self) -> Tuple[bool, bool, str]:
        """Trigger function for VoiceAssistant

        This is registered as a trigger in VoiceAssistant.triggers list.
        It's called in the main loop to check if we should process speech
        without requiring a wake word.

        Returns:
            Tuple of (triggered, disable_image, message):
            - triggered: Whether we got speech to process
            - disable_image: Whether to disable image capture for this round
            - message: The transcribed speech text
        """
        if not self.is_active() or self._stt is None:
            return False, False, ''

        message = ''

        try:
            if self.mode == "timeout":
                # Listen with timeout for remaining conversation window
                remaining = self.timeout - (time.time() - self._start_time)
                if remaining <= 0:
                    self.deactivate()
                    return False, False, ''
                # Listen for up to 3 seconds at a time (or remaining time)
                message = self._stt.listen(timeout=min(remaining, 3.0))

            elif self.mode == "vad":
                # Listen until silence
                message = self._stt.listen_until_silence(self.vad_silence)

        except Exception as e:
            logger.error(f"STT error in conversation trigger: {e}")
            self.deactivate()
            return False, False, ''

        # Handle None return from STT (shouldn't happen after vosk.py fix, but be safe)
        if message is None:
            message = ''

        if message:
            if self.should_end(message):
                logger.info(f"Conversation ended by user: '{message}'")
                self.deactivate()
            else:
                # Reset timeout on successful speech
                self._start_time = time.time()
            return True, False, message

        return False, False, ''
