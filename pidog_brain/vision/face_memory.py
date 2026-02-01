"""Face Memory - Learn and recognize faces using dlib/face_recognition

Uses the face_recognition library (dlib-based) for:
- Face detection in images
- Face encoding extraction (128-dimensional vector)
- Face matching against stored encodings

Performance on Pi 5:
- Face detection: ~50ms
- Face encoding: ~150ms
- Face matching: <1ms per face
"""

import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
import hashlib

# Lazy import face_recognition (heavy dependency)
face_recognition = None


def _ensure_face_recognition():
    """Lazy load face_recognition library"""
    global face_recognition
    if face_recognition is None:
        try:
            import face_recognition as fr
            face_recognition = fr
        except ImportError:
            raise ImportError(
                "face_recognition not installed. Install with: "
                "pip install face_recognition"
            )


@dataclass
class DetectedFace:
    """A detected face in an image"""
    name: Optional[str]  # None if unknown
    confidence: float  # 0-1, higher is more confident
    location: Tuple[int, int, int, int]  # (top, right, bottom, left)
    encoding: Optional[np.ndarray] = None

    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of face bounding box"""
        top, right, bottom, left = self.location
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def width(self) -> int:
        """Get width of face bounding box"""
        return self.location[1] - self.location[3]

    @property
    def height(self) -> int:
        """Get height of face bounding box"""
        return self.location[2] - self.location[0]


class FaceMemory:
    """Face learning and recognition system

    Usage:
        from pidog_brain.memory_manager import MemoryManager
        from pidog_brain.vision.face_memory import FaceMemory

        memory = MemoryManager()
        faces = FaceMemory(memory)

        # Learn a face
        image = cv2.imread("photo.jpg")
        success = faces.learn_face(image, "Joe")

        # Recognize faces
        detected = faces.recognize(image)
        for face in detected:
            print(f"Found {face.name} with confidence {face.confidence}")
    """

    # Distance threshold for face matching (lower = stricter)
    MATCH_THRESHOLD = 0.6

    def __init__(self, memory_manager):
        """Initialize face memory

        Args:
            memory_manager: MemoryManager instance for storing encodings
        """
        self.memory = memory_manager
        self._known_encodings: Optional[List[Tuple[str, np.ndarray, int]]] = None

    def _load_known_faces(self):
        """Load all known face encodings from database"""
        if self._known_encodings is not None:
            return

        self._known_encodings = []
        faces = self.memory.get_all_faces()

        for face in faces:
            try:
                encoding = np.frombuffer(face.encoding, dtype=np.float64)
                self._known_encodings.append((face.name, encoding, face.id))
            except Exception:
                continue

    def _invalidate_cache(self):
        """Invalidate the known faces cache"""
        self._known_encodings = None

    def learn_face(self, image: np.ndarray, name: str) -> Tuple[bool, str]:
        """Learn a face from an image

        Args:
            image: BGR image (OpenCV format) or RGB image
            name: Person's name

        Returns:
            Tuple of (success, message)
        """
        _ensure_face_recognition()

        # Convert BGR to RGB if needed (OpenCV uses BGR)
        if len(image.shape) == 3 and image.shape[2] == 3:
            # Assume BGR from OpenCV, convert to RGB
            # Use ascontiguousarray for dlib compatibility
            rgb_image = np.ascontiguousarray(image[:, :, ::-1])
        else:
            rgb_image = image

        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image)

        if not face_locations:
            return False, "No face detected in image"

        if len(face_locations) > 1:
            # Use the largest face
            largest = max(face_locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
            face_locations = [largest]

        # Get face encoding
        encodings = face_recognition.face_encodings(rgb_image, face_locations)

        if not encodings:
            return False, "Could not encode face"

        encoding = encodings[0]

        # Create image hash for deduplication
        image_hash = hashlib.md5(image.tobytes()[:10000]).hexdigest()

        # Store in database
        self.memory.store_face(name, encoding.tobytes(), image_hash)

        # Invalidate cache
        self._invalidate_cache()

        return True, f"Learned {name}'s face"

    def recognize(self, image: np.ndarray) -> List[DetectedFace]:
        """Recognize faces in an image

        Args:
            image: BGR image (OpenCV format) or RGB image

        Returns:
            List of detected faces with names (if known)
        """
        _ensure_face_recognition()
        self._load_known_faces()

        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            # Use ascontiguousarray for dlib compatibility
            rgb_image = np.ascontiguousarray(image[:, :, ::-1])
        else:
            rgb_image = image

        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image)

        if not face_locations:
            return []

        # Get encodings
        encodings = face_recognition.face_encodings(rgb_image, face_locations)

        # Match against known faces
        results = []
        for location, encoding in zip(face_locations, encodings):
            name, confidence, face_id = self._match_face(encoding)

            # Record that we saw this face
            if face_id is not None:
                self.memory.record_face_seen(face_id)

            results.append(DetectedFace(
                name=name,
                confidence=confidence,
                location=location,
                encoding=encoding
            ))

        return results

    def _match_face(self, encoding: np.ndarray) -> Tuple[Optional[str], float, Optional[int]]:
        """Match a face encoding against known faces

        Args:
            encoding: 128-dimensional face encoding

        Returns:
            Tuple of (name, confidence, face_id) or (None, 0, None) if no match
        """
        if not self._known_encodings:
            return None, 0.0, None

        # Calculate distances to all known faces
        known_names = [kf[0] for kf in self._known_encodings]
        known_encodings = [kf[1] for kf in self._known_encodings]
        known_ids = [kf[2] for kf in self._known_encodings]

        distances = face_recognition.face_distance(known_encodings, encoding)

        # Find best match
        if len(distances) == 0:
            return None, 0.0, None

        best_idx = np.argmin(distances)
        best_distance = distances[best_idx]

        if best_distance <= self.MATCH_THRESHOLD:
            # Convert distance to confidence (0-1, higher is better)
            confidence = 1.0 - best_distance
            return known_names[best_idx], confidence, known_ids[best_idx]

        return None, 0.0, None

    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces without recognition (faster)

        Args:
            image: BGR or RGB image

        Returns:
            List of face locations (top, right, bottom, left)
        """
        _ensure_face_recognition()

        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = image[:, :, ::-1]
        else:
            rgb_image = image

        return face_recognition.face_locations(rgb_image)

    def get_known_names(self) -> List[str]:
        """Get list of all known face names"""
        self._load_known_faces()
        if not self._known_encodings:
            return []
        return list(set(kf[0] for kf in self._known_encodings))

    def forget_face(self, name: str):
        """Remove all stored faces for a person

        Args:
            name: Person's name
        """
        faces = self.memory.get_faces_by_name(name)
        for face in faces:
            self.memory.delete_face(face.id)
        self._invalidate_cache()


class FaceTracker:
    """Track faces across frames for smoother following

    Maintains state about which face we're currently tracking
    to avoid jumping between faces.
    """

    def __init__(self, face_memory: FaceMemory):
        self.face_memory = face_memory
        self.tracking_name: Optional[str] = None
        self.last_location: Optional[Tuple[int, int, int, int]] = None
        self.frames_since_seen: int = 0
        self.max_frames_lost = 10

    def update(self, image: np.ndarray) -> Optional[DetectedFace]:
        """Update tracking with new frame

        Args:
            image: Current camera frame

        Returns:
            The tracked face, or None if lost
        """
        faces = self.face_memory.recognize(image)

        if not faces:
            self.frames_since_seen += 1
            if self.frames_since_seen > self.max_frames_lost:
                self.tracking_name = None
                self.last_location = None
            return None

        # If we're tracking someone, look for them
        if self.tracking_name:
            for face in faces:
                if face.name == self.tracking_name:
                    self.last_location = face.location
                    self.frames_since_seen = 0
                    return face

            # Tracked person not found, but we see other faces
            self.frames_since_seen += 1
            if self.frames_since_seen > self.max_frames_lost:
                # Lost tracked person, switch to nearest face
                self.tracking_name = faces[0].name
                self.last_location = faces[0].location
                self.frames_since_seen = 0
                return faces[0]

            return None

        # Not tracking anyone, start tracking the first/largest face
        largest = max(faces, key=lambda f: f.width * f.height)
        self.tracking_name = largest.name
        self.last_location = largest.location
        self.frames_since_seen = 0
        return largest

    def start_tracking(self, name: str):
        """Start tracking a specific person

        Args:
            name: Person's name to track
        """
        self.tracking_name = name
        self.frames_since_seen = 0

    def stop_tracking(self):
        """Stop tracking"""
        self.tracking_name = None
        self.last_location = None
        self.frames_since_seen = 0
