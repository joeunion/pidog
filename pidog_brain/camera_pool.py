"""Camera Pool - Thread-safe access to shared picamera2 instance

Provides shared access to camera frames from VoiceAssistant's picamera2.
This avoids conflicts by using the same camera instance.

Features:
- Uses picamera2 instance owned by VoiceAssistant
- Frame caching with configurable TTL
- Thread-safe access via RLock
- Graceful fallback when camera not available
"""

import threading
import time
import logging
from typing import Optional, Any
import numpy as np

logger = logging.getLogger(__name__)


class CameraPool:
    """Thread-safe singleton for camera frame access

    Usage:
        # Set the picamera2 instance (from VoiceAssistant)
        CameraPool.get_instance().set_picam2(voice_dog.picam2)

        # Get a frame
        frame = CameraPool.get_instance().get_frame()

        # Release on shutdown
        CameraPool.get_instance().release()
    """

    _instance: Optional['CameraPool'] = None
    _instance_lock = threading.Lock()

    # Configuration
    DEFAULT_FRAME_TTL = 0.1  # 100ms cache

    def __init__(self, frame_ttl: float = DEFAULT_FRAME_TTL):
        """Initialize camera pool (use get_instance() instead)

        Args:
            frame_ttl: How long to cache frames in seconds (default 100ms)
        """
        self._frame_ttl = frame_ttl
        self._lock = threading.RLock()

        # Picamera2 instance (set externally)
        self._picam2 = None

        # Frame cache
        self._cached_frame = None
        self._cache_time = 0.0

        # State
        self._released = False

    @classmethod
    def get_instance(cls, frame_ttl: float = DEFAULT_FRAME_TTL) -> 'CameraPool':
        """Get the singleton camera pool instance

        Args:
            frame_ttl: Frame cache TTL (only used on first call)

        Returns:
            The singleton CameraPool instance
        """
        if cls._instance is None:
            with cls._instance_lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = cls(frame_ttl)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton (for testing)"""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.release()
                cls._instance = None

    def set_picam2(self, picam2: Any):
        """Set the picamera2 instance to use for frame capture

        Args:
            picam2: Picamera2 instance (from VoiceAssistant)
        """
        with self._lock:
            self._picam2 = picam2
            logger.info("CameraPool connected to picamera2 instance")

    def get_frame(self, force_refresh: bool = False):
        """Get a camera frame, using cache if available

        Args:
            force_refresh: If True, bypass cache and get fresh frame

        Returns:
            BGR image as numpy array (OpenCV format), or None if unavailable
        """
        with self._lock:
            if self._released:
                return None

            now = time.time()

            # Check cache validity
            if not force_refresh and self._cached_frame is not None:
                if now - self._cache_time < self._frame_ttl:
                    return self._cached_frame.copy()

            # Check if picam2 is available
            if self._picam2 is None:
                logger.debug("No picamera2 instance available")
                return self._cached_frame.copy() if self._cached_frame is not None else None

            try:
                # Capture frame from picamera2
                # Note: picamera2 returns XBGR8888 (4 channels) by default
                frame = self._picam2.capture_array()
                if frame is not None:
                    # Handle different image formats - output BGR for OpenCV compatibility
                    if len(frame.shape) == 3:
                        if frame.shape[2] == 4:
                            # XBGR8888: numpy channels are [R, G, B, X] (X=padding)
                            # Extract BGR: reorder to [B, G, R] = channels [2, 1, 0]
                            frame = frame[:, :, [2, 1, 0]]
                        # If already 3 channels, assume BGR (no conversion needed)
                    # Ensure C-contiguous for dlib/face_recognition compatibility
                    frame = np.ascontiguousarray(frame)
                    self._cached_frame = frame
                    self._cache_time = now
                    return frame.copy()
                else:
                    logger.debug("picam2.capture_array() returned None")
                    return self._cached_frame.copy() if self._cached_frame is not None else None

            except Exception as e:
                logger.debug(f"Frame capture error: {e}")
                return self._cached_frame.copy() if self._cached_frame is not None else None

    def release(self):
        """Release resources

        Note: We don't own the camera (VoiceAssistant does), so we just clear state.
        """
        with self._lock:
            if self._released:
                return

            self._released = True
            self._picam2 = None
            self._cached_frame = None
            logger.info("CameraPool released")

    def is_available(self) -> bool:
        """Check if camera frames are available

        Returns:
            True if picam2 is set and not released
        """
        with self._lock:
            return self._picam2 is not None and not self._released

    @property
    def frame_ttl(self) -> float:
        """Get the frame cache TTL"""
        return self._frame_ttl
