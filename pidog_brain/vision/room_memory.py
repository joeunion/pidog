"""Room Memory - Learn and identify rooms via Claude descriptions

Rooms are learned by having Claude describe visual features,
then storing those descriptions for later matching.

This is one of the few vision operations that uses Claude API,
but only during learning and identification - not every frame.
"""

import hashlib
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class RoomMatch:
    """A potential room match"""
    name: str
    confidence: float  # 0-1
    description: str


class RoomMemory:
    """Learn and identify rooms using visual descriptions

    Usage:
        from pidog_brain.memory_manager import MemoryManager

        memory = MemoryManager()
        rooms = RoomMemory(memory, claude_client)

        # Learn current room
        rooms.learn_room(image, "kitchen")

        # Identify where we are
        match = rooms.identify_room(image)
        if match:
            print(f"This looks like the {match.name}")
    """

    def __init__(self, memory_manager, claude_client=None):
        """Initialize room memory

        Args:
            memory_manager: MemoryManager instance
            claude_client: Claude API client for descriptions (optional)
        """
        self.memory = memory_manager
        self.claude = claude_client

    def set_claude_client(self, client):
        """Set Claude client after initialization"""
        self.claude = client

    def learn_room(self, image, name: str, description: Optional[str] = None) -> Tuple[bool, str]:
        """Learn a room from an image

        Args:
            image: BGR image of the room
            name: Name for this room
            description: Optional pre-generated description

        Returns:
            Tuple of (success, message)
        """
        # Get or generate description
        if description is None:
            if self.claude is None:
                return False, "No Claude client available for room description"

            description = self._describe_room(image)
            if not description:
                return False, "Failed to describe room"

        # Extract landmarks from description
        landmarks = self._extract_landmarks(description)

        # Create image hash
        image_hash = hashlib.md5(image.tobytes()[:10000]).hexdigest()

        # Store room
        self.memory.store_room(name, description, landmarks, image_hash)

        return True, f"Learned room: {name}"

    def _describe_room(self, image) -> Optional[str]:
        """Use Claude to describe room features

        Args:
            image: BGR image

        Returns:
            Description string or None
        """
        if self.claude is None:
            return None

        try:
            # This would use the Claude vision API
            # For now, return a placeholder
            prompt = """Describe this room's key visual features for later identification.
Focus on:
- Type of room (kitchen, living room, bedroom, etc.)
- Distinctive features (furniture, appliances, decorations)
- Colors and lighting
- Any unique landmarks

Keep the description concise but distinctive."""

            # The actual implementation would send the image to Claude
            # response = self.claude.prompt(prompt, image=image)
            # return response

            return None  # Placeholder - implement with actual Claude call

        except Exception as e:
            print(f"Error describing room: {e}")
            return None

    def _extract_landmarks(self, description: str) -> List[str]:
        """Extract key landmarks from a room description

        Args:
            description: Room description text

        Returns:
            List of landmark strings
        """
        # Simple keyword extraction
        # Could be enhanced with NLP
        landmarks = []

        # Common room features to look for
        keywords = [
            'window', 'door', 'sofa', 'couch', 'table', 'chair', 'bed',
            'desk', 'lamp', 'tv', 'television', 'refrigerator', 'stove',
            'sink', 'counter', 'cabinet', 'shelf', 'bookshelf', 'plant',
            'rug', 'carpet', 'painting', 'picture', 'mirror', 'fireplace'
        ]

        description_lower = description.lower()
        for keyword in keywords:
            if keyword in description_lower:
                landmarks.append(keyword)

        return landmarks

    def identify_room(self, image) -> Optional[RoomMatch]:
        """Identify which room we're in

        Args:
            image: Current camera view

        Returns:
            RoomMatch with name and confidence, or None
        """
        if self.claude is None:
            return None

        # Get all known rooms
        rooms = self.memory.get_all_rooms()
        if not rooms:
            return None

        # Have Claude compare current view to known rooms
        try:
            # Build context of known rooms
            room_list = "\n".join([
                f"- {r.name}: {r.description[:100]}..."
                for r in rooms
            ])

            prompt = f"""Look at this image and determine which of these known rooms it most likely is:

{room_list}

If it matches one of these rooms, respond with just the room name.
If it doesn't match any known room, respond with "unknown".
"""

            # The actual implementation would send the image to Claude
            # response = self.claude.prompt(prompt, image=image)

            # For now, return None
            return None

        except Exception as e:
            print(f"Error identifying room: {e}")
            return None

    def get_room_context(self) -> str:
        """Get context string of known rooms for Claude prompt"""
        return self.memory.get_rooms_context()

    def get_all_rooms(self) -> List[str]:
        """Get list of all known room names"""
        rooms = self.memory.get_all_rooms()
        return [r.name for r in rooms]


class SimpleRoomMatcher:
    """Simple room matching without Claude API

    Uses visual feature comparison for basic room matching.
    Less accurate than Claude-based matching but works offline.
    """

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self._color_histograms = {}  # room_name -> histogram

    def learn_room(self, image, name: str) -> Tuple[bool, str]:
        """Learn room using color histogram

        Args:
            image: BGR image
            name: Room name

        Returns:
            Tuple of (success, message)
        """
        try:
            import cv2

            # Calculate color histogram
            hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8],
                               [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            # Store histogram
            self._color_histograms[name.lower()] = hist

            # Store basic info in memory
            self.memory.store_room(
                name,
                f"Room learned via color histogram matching",
                None,
                hashlib.md5(image.tobytes()[:10000]).hexdigest()
            )

            return True, f"Learned room: {name}"

        except Exception as e:
            return False, f"Error learning room: {e}"

    def identify_room(self, image) -> Optional[RoomMatch]:
        """Identify room using histogram comparison

        Args:
            image: Current camera view

        Returns:
            Best matching room or None
        """
        if not self._color_histograms:
            return None

        try:
            import cv2

            # Calculate current histogram
            current_hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8],
                                        [0, 256, 0, 256, 0, 256])
            current_hist = cv2.normalize(current_hist, current_hist).flatten()

            # Compare to known rooms
            best_match = None
            best_score = 0

            for name, hist in self._color_histograms.items():
                score = cv2.compareHist(current_hist, hist, cv2.HISTCMP_CORREL)

                if score > best_score and score > 0.5:  # Minimum threshold
                    best_score = score
                    best_match = name

            if best_match:
                room = self.memory.get_room(best_match)
                return RoomMatch(
                    name=best_match,
                    confidence=best_score,
                    description=room.description if room else ""
                )

            return None

        except Exception as e:
            print(f"Error identifying room: {e}")
            return None
