"""Obstacle Detector - Camera-based obstacle detection

Simple obstacle detection using edge detection and depth estimation.
Works in conjunction with ultrasonic sensor for redundant safety.

Performance target: <50ms per frame on Pi 5
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass

cv2 = None


def _ensure_cv2():
    """Lazy load OpenCV"""
    global cv2
    if cv2 is None:
        import cv2 as opencv
        cv2 = opencv


@dataclass
class Obstacle:
    """A detected obstacle"""
    position: str  # "left", "center", "right"
    distance_estimate: str  # "close", "medium", "far"
    confidence: float
    x: int  # Pixel x position
    y: int  # Pixel y position
    width: int
    height: int


class ObstacleDetector:
    """Detect obstacles using computer vision

    Uses multiple cues:
    - Edge density (obstacles have many edges)
    - Optical flow (obstacles are stationary)
    - Color discontinuities
    - Ground plane estimation

    Usage:
        detector = ObstacleDetector()

        # Check for obstacles
        obstacles = detector.detect(image)
        if detector.is_path_blocked(obstacles):
            print("Path blocked!")
    """

    # Detection thresholds
    EDGE_THRESHOLD = 50
    MIN_OBSTACLE_AREA = 500  # Minimum pixel area
    CLOSE_Y_THRESHOLD = 0.7  # Bottom 30% of image = close
    MEDIUM_Y_THRESHOLD = 0.5  # Middle = medium distance

    def __init__(self):
        self._prev_frame = None
        self._flow = None

    def detect(self, image: np.ndarray) -> List[Obstacle]:
        """Detect obstacles in image

        Args:
            image: BGR image from camera

        Returns:
            List of detected obstacles
        """
        _ensure_cv2()

        height, width = image.shape[:2]
        obstacles = []

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, self.EDGE_THRESHOLD, self.EDGE_THRESHOLD * 2)

        # Focus on lower half of image (ground level obstacles)
        lower_half = edges[height // 2:, :]

        # Find contours in lower half
        contours, _ = cv2.findContours(
            lower_half, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.MIN_OBSTACLE_AREA:
                continue

            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Adjust y for lower half offset
            y += height // 2

            # Determine position
            center_x = x + w // 2
            if center_x < width // 3:
                position = "left"
            elif center_x > 2 * width // 3:
                position = "right"
            else:
                position = "center"

            # Estimate distance based on y position
            center_y = y + h // 2
            y_ratio = center_y / height
            if y_ratio > self.CLOSE_Y_THRESHOLD:
                distance = "close"
            elif y_ratio > self.MEDIUM_Y_THRESHOLD:
                distance = "medium"
            else:
                distance = "far"

            # Confidence based on edge density in region
            roi = edges[max(0, y - h // 2):min(height, y + h // 2),
                       max(0, x - w // 2):min(width, x + w // 2)]
            edge_density = np.mean(roi > 0) if roi.size > 0 else 0

            obstacles.append(Obstacle(
                position=position,
                distance_estimate=distance,
                confidence=min(1.0, edge_density * 2),
                x=x,
                y=y,
                width=w,
                height=h
            ))

        return obstacles

    def is_path_blocked(self, obstacles: List[Obstacle]) -> bool:
        """Check if forward path is blocked

        Args:
            obstacles: List of detected obstacles

        Returns:
            True if center path has close obstacles
        """
        for obs in obstacles:
            if obs.position == "center" and obs.distance_estimate == "close":
                return True
        return False

    def get_clear_direction(self, obstacles: List[Obstacle]) -> str:
        """Get the clearest direction to move

        Args:
            obstacles: List of detected obstacles

        Returns:
            "left", "right", "forward", or "backward"
        """
        left_blocked = False
        right_blocked = False
        center_blocked = False

        for obs in obstacles:
            if obs.distance_estimate == "close":
                if obs.position == "left":
                    left_blocked = True
                elif obs.position == "right":
                    right_blocked = True
                else:
                    center_blocked = True

        if not center_blocked:
            return "forward"
        elif not left_blocked:
            return "left"
        elif not right_blocked:
            return "right"
        else:
            return "backward"

    def detect_with_flow(self, image: np.ndarray) -> Tuple[List[Obstacle], np.ndarray]:
        """Detect obstacles using optical flow for motion detection

        Moving obstacles (like people walking) can be distinguished from
        static obstacles using optical flow.

        Args:
            image: BGR image

        Returns:
            Tuple of (obstacles, flow_magnitude_image)
        """
        _ensure_cv2()

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if self._prev_frame is None:
            self._prev_frame = gray
            return [], np.zeros_like(gray)

        # Calculate optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self._prev_frame, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        # Calculate flow magnitude
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        self._prev_frame = gray

        # Basic obstacle detection
        obstacles = self.detect(image)

        return obstacles, magnitude


class GroundPlaneDetector:
    """Detect ground plane for better obstacle understanding

    Uses color and texture to identify the ground,
    then anything significantly above it is an obstacle.
    """

    def __init__(self):
        self._ground_color = None
        self._ground_mask = None

    def calibrate_ground(self, image: np.ndarray):
        """Calibrate ground color from bottom of image

        Call this when dog is on clear ground.

        Args:
            image: BGR image
        """
        _ensure_cv2()

        height = image.shape[0]

        # Sample bottom 10% of image as ground
        ground_sample = image[int(height * 0.9):, :]

        # Convert to HSV for color matching
        hsv = cv2.cvtColor(ground_sample, cv2.COLOR_BGR2HSV)

        # Calculate mean and std of ground color
        self._ground_color = {
            'mean': np.mean(hsv, axis=(0, 1)),
            'std': np.std(hsv, axis=(0, 1))
        }

    def detect_non_ground(self, image: np.ndarray) -> np.ndarray:
        """Detect regions that are not ground

        Args:
            image: BGR image

        Returns:
            Binary mask of non-ground regions
        """
        if self._ground_color is None:
            # Not calibrated, return empty mask
            return np.zeros(image.shape[:2], dtype=np.uint8)

        _ensure_cv2()

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create mask based on color distance from ground
        mean = self._ground_color['mean']
        std = self._ground_color['std']

        # Threshold at 2 standard deviations
        lower = mean - 2 * std
        upper = mean + 2 * std

        # Clip to valid range
        lower = np.clip(lower, 0, 255)
        upper = np.clip(upper, 0, 255)

        # Create ground mask
        ground_mask = cv2.inRange(hsv, lower.astype(np.uint8), upper.astype(np.uint8))

        # Non-ground is inverse
        non_ground = cv2.bitwise_not(ground_mask)

        # Clean up with morphology
        kernel = np.ones((5, 5), np.uint8)
        non_ground = cv2.morphologyEx(non_ground, cv2.MORPH_OPEN, kernel)
        non_ground = cv2.morphologyEx(non_ground, cv2.MORPH_CLOSE, kernel)

        return non_ground
