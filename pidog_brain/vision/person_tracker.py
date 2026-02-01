"""Person Tracker - Detect and follow people using TFLite MobileNet-SSD

Uses TensorFlow Lite with MobileNet-SSD for real-time person detection.
Runs entirely locally on Pi 5 (~100ms per frame).

The model detects multiple object classes, but we filter for 'person' only.
"""

import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import urllib.request
import os

# Lazy imports
tflite_runtime = None
cv2 = None


def _ensure_tflite():
    """Lazy load TFLite runtime"""
    global tflite_runtime
    if tflite_runtime is None:
        try:
            import tflite_runtime.interpreter as tflite
            tflite_runtime = tflite
        except ImportError:
            try:
                import tensorflow.lite as tflite
                tflite_runtime = tflite
            except ImportError:
                raise ImportError(
                    "TFLite runtime not installed. Install with: "
                    "pip install tflite-runtime"
                )


def _ensure_cv2():
    """Lazy load OpenCV"""
    global cv2
    if cv2 is None:
        import cv2 as opencv
        cv2 = opencv


@dataclass
class BoundingBox:
    """A bounding box for a detected object"""
    left: float  # 0-1 normalized
    top: float
    right: float
    bottom: float
    confidence: float
    label: str = "person"

    @property
    def center_x(self) -> float:
        """Get normalized center X (0-1)"""
        return (self.left + self.right) / 2

    @property
    def center_y(self) -> float:
        """Get normalized center Y (0-1)"""
        return (self.top + self.bottom) / 2

    @property
    def width(self) -> float:
        """Get normalized width (0-1)"""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Get normalized height (0-1)"""
        return self.bottom - self.top

    @property
    def area(self) -> float:
        """Get normalized area (0-1)"""
        return self.width * self.height

    def to_pixels(self, image_width: int, image_height: int) -> Tuple[int, int, int, int]:
        """Convert to pixel coordinates

        Returns:
            (left, top, right, bottom) in pixels
        """
        return (
            int(self.left * image_width),
            int(self.top * image_height),
            int(self.right * image_width),
            int(self.bottom * image_height)
        )


class PersonTracker:
    """Detect and track people for following

    Usage:
        tracker = PersonTracker()

        # Detect people in frame
        people = tracker.detect_people(image)

        # Get follow command for first person
        if people:
            cmd = tracker.get_follow_command(people[0])
            print(cmd)  # "turn left", "forward", etc.
    """

    # Model download URL (COCO-trained MobileNet-SSD)
    MODEL_URL = "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip"
    MODEL_FILENAME = "detect.tflite"
    LABELS_FILENAME = "labelmap.txt"

    # Detection settings
    MIN_CONFIDENCE = 0.5
    PERSON_CLASS_ID = 0  # COCO person class

    # Following thresholds (normalized 0-1)
    CENTER_TOLERANCE = 0.15  # How centered person needs to be
    CLOSE_DISTANCE = 0.25  # Area threshold for "too close"
    FAR_DISTANCE = 0.05  # Area threshold for "too far"

    def __init__(self, model_dir: Optional[str] = None):
        """Initialize person tracker

        Args:
            model_dir: Directory containing TFLite model. Downloads if missing.
        """
        if model_dir is None:
            model_dir = Path(__file__).parent / "models"

        self.model_dir = Path(model_dir)
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self._input_size = (300, 300)  # MobileNet-SSD input size

    def _ensure_model(self):
        """Download model if not present"""
        model_path = self.model_dir / self.MODEL_FILENAME

        if model_path.exists():
            return

        print("Downloading person detection model...")
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Download and extract
        import zipfile
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            urllib.request.urlretrieve(self.MODEL_URL, tmp.name)

            with zipfile.ZipFile(tmp.name) as zf:
                zf.extractall(self.model_dir)

            os.unlink(tmp.name)

        print("Model downloaded successfully")

    def _load_model(self):
        """Load TFLite model"""
        if self._interpreter is not None:
            return

        _ensure_tflite()
        self._ensure_model()

        model_path = self.model_dir / self.MODEL_FILENAME

        self._interpreter = tflite_runtime.Interpreter(model_path=str(model_path))
        self._interpreter.allocate_tensors()

        self._input_details = self._interpreter.get_input_details()
        self._output_details = self._interpreter.get_output_details()

        # Get input size from model
        input_shape = self._input_details[0]['shape']
        self._input_size = (input_shape[1], input_shape[2])

    def detect_people(self, image: np.ndarray) -> List[BoundingBox]:
        """Detect people in an image

        Args:
            image: BGR image (OpenCV format)

        Returns:
            List of bounding boxes for detected people
        """
        _ensure_cv2()
        self._load_model()

        # Preprocess image
        input_image = cv2.resize(image, self._input_size)
        input_image = np.expand_dims(input_image, axis=0)

        # Run inference
        self._interpreter.set_tensor(self._input_details[0]['index'], input_image)
        self._interpreter.invoke()

        # Get results
        boxes = self._interpreter.get_tensor(self._output_details[0]['index'])[0]
        classes = self._interpreter.get_tensor(self._output_details[1]['index'])[0]
        scores = self._interpreter.get_tensor(self._output_details[2]['index'])[0]

        # Filter for people with sufficient confidence
        people = []
        for i in range(len(scores)):
            if scores[i] >= self.MIN_CONFIDENCE and int(classes[i]) == self.PERSON_CLASS_ID:
                # Boxes are [ymin, xmin, ymax, xmax] normalized
                people.append(BoundingBox(
                    left=float(boxes[i][1]),
                    top=float(boxes[i][0]),
                    right=float(boxes[i][3]),
                    bottom=float(boxes[i][2]),
                    confidence=float(scores[i])
                ))

        # Sort by confidence
        people.sort(key=lambda p: p.confidence, reverse=True)
        return people

    def get_follow_command(self, bbox: BoundingBox) -> str:
        """Get movement command to follow a person

        Args:
            bbox: Bounding box of person to follow

        Returns:
            One of: "turn left", "turn right", "forward", "backward", "stop"
        """
        center_x = bbox.center_x

        # Check horizontal position
        if center_x < 0.5 - self.CENTER_TOLERANCE:
            return "turn left"
        elif center_x > 0.5 + self.CENTER_TOLERANCE:
            return "turn right"

        # Check distance (using area as proxy)
        area = bbox.area

        if area > self.CLOSE_DISTANCE:
            return "backward"  # Too close
        elif area < self.FAR_DISTANCE:
            return "forward"  # Too far
        else:
            return "stop"  # Good distance

    def get_detailed_command(self, bbox: BoundingBox) -> dict:
        """Get detailed follow command with magnitude

        Args:
            bbox: Bounding box of person to follow

        Returns:
            Dict with command details
        """
        center_x = bbox.center_x
        area = bbox.area

        # Calculate turn amount (0-1)
        turn_amount = abs(center_x - 0.5) * 2

        # Calculate distance adjustment (negative = too close)
        if area > self.CLOSE_DISTANCE:
            distance_adjust = -((area - self.CLOSE_DISTANCE) / self.CLOSE_DISTANCE)
        elif area < self.FAR_DISTANCE:
            distance_adjust = (self.FAR_DISTANCE - area) / self.FAR_DISTANCE
        else:
            distance_adjust = 0

        return {
            'turn_direction': 'left' if center_x < 0.5 else 'right',
            'turn_amount': turn_amount,
            'distance_adjust': distance_adjust,
            'centered': turn_amount < self.CENTER_TOLERANCE * 2,
            'good_distance': abs(distance_adjust) < 0.1,
            'command': self.get_follow_command(bbox)
        }


class PersonFollower:
    """State machine for following a person

    Manages the following behavior across multiple frames,
    including losing and re-acquiring the target.
    """

    def __init__(self, tracker: PersonTracker):
        self.tracker = tracker
        self.is_following = False
        self.frames_since_seen = 0
        self.max_frames_lost = 15
        self.last_command = "stop"

    def start(self):
        """Start following"""
        self.is_following = True
        self.frames_since_seen = 0

    def stop(self):
        """Stop following"""
        self.is_following = False
        self.last_command = "stop"

    def update(self, image: np.ndarray) -> Tuple[str, Optional[BoundingBox]]:
        """Update following with new frame

        Args:
            image: Current camera frame

        Returns:
            Tuple of (command, person_bbox or None)
        """
        if not self.is_following:
            return "stop", None

        people = self.tracker.detect_people(image)

        if not people:
            self.frames_since_seen += 1

            if self.frames_since_seen > self.max_frames_lost:
                # Lost person, search by turning
                return "turn left" if self.last_command != "turn left" else "turn right", None

            # Recently lost, continue last movement briefly
            return self.last_command, None

        # Found person(s), follow the most confident detection
        person = people[0]
        self.frames_since_seen = 0

        command = self.tracker.get_follow_command(person)
        self.last_command = command

        return command, person
