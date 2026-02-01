"""Memory Manager - SQLite-based persistent memory with FTS5 full-text search

Provides CRUD operations for:
- Memories (people, facts, preferences, experiences)
- Conversations (compressed summaries)
- Tricks (learned action sequences)
- Goals (autonomous objectives)
- Faces (face encodings for recognition)
- Rooms (learned locations)
"""

import sqlite3
import json
import os
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """A single memory entry"""
    id: Optional[int] = None
    category: str = "fact"
    subject: str = ""
    content: str = ""
    importance: float = 0.5
    created_at: Optional[str] = None
    last_accessed: Optional[str] = None
    access_count: int = 0


@dataclass
class Trick:
    """A learned trick (action sequence)"""
    id: Optional[int] = None
    name: str = ""
    trigger_phrase: str = ""
    actions: List[str] = None
    times_performed: int = 0
    created_at: Optional[str] = None
    last_performed: Optional[str] = None

    def __post_init__(self):
        if self.actions is None:
            self.actions = []


@dataclass
class Goal:
    """An autonomous objective"""
    id: Optional[int] = None
    description: str = ""
    priority: int = 3
    status: str = "active"
    progress: Optional[Dict] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Face:
    """A stored face encoding"""
    id: Optional[int] = None
    name: str = ""
    encoding: bytes = None
    image_hash: Optional[str] = None
    created_at: Optional[str] = None
    last_seen: Optional[str] = None
    times_seen: int = 1


@dataclass
class Room:
    """A learned room/location"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    landmarks: Optional[List[str]] = None
    image_hash: Optional[str] = None
    created_at: Optional[str] = None
    last_visited: Optional[str] = None
    times_visited: int = 1


class MemoryManager:
    """SQLite-based memory system with FTS5 full-text search

    Usage:
        mm = MemoryManager()

        # Store a memory
        mm.remember("person", "Joe", "Likes belly rubs", importance=0.8)

        # Search memories
        results = mm.recall("belly rubs")

        # Learn a trick
        mm.learn_trick("spin", "do a spin", ["turn left", "turn left"])

        # Get a trick
        trick = mm.get_trick("spin")
    """

    # Valid actions that can be used in tricks
    VALID_ACTIONS = [
        "forward", "backward", "lie", "stand", "sit", "bark", "bark harder",
        "pant", "howling", "wag tail", "stretch", "push up", "scratch",
        "handshake", "high five", "lick hand", "shake head", "relax neck",
        "nod", "think", "recall", "head down", "fluster", "surprise",
        "turn left", "turn right", "stop"
    ]

    MAX_ACTIONS_PER_TRICK = 10

    def __init__(self, db_path: Optional[str] = None):
        """Initialize memory manager

        Args:
            db_path: Path to SQLite database. Defaults to pidog_brain/memory.db
        """
        if db_path is None:
            db_path = Path(__file__).parent / "memory.db"

        self.db_path = Path(db_path)

        # Thread-local storage for connections
        self._local = threading.local()
        self._close_lock = threading.Lock()
        self._closed = False

        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent / "schema.sql"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Read and execute schema
            if schema_path.exists():
                with open(schema_path) as f:
                    conn.executescript(f.read())

            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local database connection

        Returns a connection from thread-local storage, creating one if needed.
        This avoids the overhead of creating new connections for each query
        while remaining thread-safe.
        """
        with self._close_lock:
            if self._closed:
                raise RuntimeError("MemoryManager has been closed")

        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row

        return self._local.conn

    def close(self):
        """Close all database connections

        Should be called during shutdown to properly release resources.
        """
        with self._close_lock:
            if self._closed:
                return
            self._closed = True

        # Close thread-local connection if it exists
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self._local.conn = None

    # ==================== MEMORIES ====================

    def remember(self, category: str, subject: str, content: str,
                 importance: float = 0.5) -> int:
        """Store a new memory

        Args:
            category: One of 'person', 'fact', 'preference', 'experience', 'location'
            subject: What/who this memory is about
            content: The memory content
            importance: How important (0.0-1.0)

        Returns:
            ID of the new memory
        """
        importance = max(0.0, min(1.0, importance))  # Clamp to valid range

        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO memories (category, subject, content, importance)
                   VALUES (?, ?, ?, ?)""",
                (category, subject, content, importance)
            )
            conn.commit()
            return cursor.lastrowid

    def recall(self, query: str, limit: int = 5,
               category: Optional[str] = None) -> List[Memory]:
        """Search memories using FTS5 full-text search

        Args:
            query: Search query (supports FTS5 syntax)
            limit: Maximum results to return
            category: Optional category filter

        Returns:
            List of matching memories, sorted by relevance
        """
        with self._get_conn() as conn:
            # Update access timestamp for matching memories
            if category:
                rows = conn.execute(
                    """SELECT m.* FROM memories m
                       JOIN memories_fts fts ON m.id = fts.rowid
                       WHERE memories_fts MATCH ? AND m.category = ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, category, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT m.* FROM memories m
                       JOIN memories_fts fts ON m.id = fts.rowid
                       WHERE memories_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, limit)
                ).fetchall()

            # Collect IDs for batch update
            ids_to_update = []
            memories = []

            for row in rows:
                ids_to_update.append(row['id'])
                memories.append(Memory(
                    id=row['id'],
                    category=row['category'],
                    subject=row['subject'],
                    content=row['content'],
                    importance=row['importance'],
                    created_at=row['created_at'],
                    last_accessed=row['last_accessed'],
                    access_count=row['access_count']
                ))

            # Batch update access count and timestamp (fixes N+1 query)
            if ids_to_update:
                placeholders = ','.join('?' * len(ids_to_update))
                conn.execute(
                    f"""UPDATE memories
                        SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE id IN ({placeholders})""",
                    ids_to_update
                )

            conn.commit()
            return memories

    def get_memories_by_subject(self, subject: str) -> List[Memory]:
        """Get all memories about a specific subject"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE subject = ? ORDER BY importance DESC",
                (subject,)
            ).fetchall()

            return [Memory(**dict(row)) for row in rows]

    def get_memories_by_category(self, category: str, limit: int = 10) -> List[Memory]:
        """Get memories by category, sorted by importance"""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM memories WHERE category = ?
                   ORDER BY importance DESC LIMIT ?""",
                (category, limit)
            ).fetchall()

            return [Memory(**dict(row)) for row in rows]

    def get_important_memories(self, min_importance: float = 0.7,
                               limit: int = 10) -> List[Memory]:
        """Get the most important memories"""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM memories WHERE importance >= ?
                   ORDER BY importance DESC, access_count DESC LIMIT ?""",
                (min_importance, limit)
            ).fetchall()

            return [Memory(**dict(row)) for row in rows]

    def update_memory_importance(self, memory_id: int, importance: float):
        """Update the importance of a memory"""
        importance = max(0.0, min(1.0, importance))

        with self._get_conn() as conn:
            conn.execute(
                "UPDATE memories SET importance = ? WHERE id = ?",
                (importance, memory_id)
            )
            conn.commit()

    def delete_memory(self, memory_id: int):
        """Delete a memory"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()

    # ==================== TRICKS ====================

    def learn_trick(self, name: str, trigger_phrase: str,
                    actions: List[str]) -> Tuple[bool, str]:
        """Learn a new trick (action sequence)

        Args:
            name: Unique name for the trick
            trigger_phrase: What to say to trigger the trick
            actions: List of actions to perform

        Returns:
            Tuple of (success, message)
        """
        # Validate actions
        if len(actions) > self.MAX_ACTIONS_PER_TRICK:
            return False, f"Too many actions (max {self.MAX_ACTIONS_PER_TRICK})"

        invalid_actions = [a for a in actions if a.lower() not in
                          [v.lower() for v in self.VALID_ACTIONS]]
        if invalid_actions:
            return False, f"Invalid actions: {', '.join(invalid_actions)}"

        # Normalize action names
        actions = [a.lower() for a in actions]

        with self._get_conn() as conn:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO tricks (name, trigger_phrase, actions)
                       VALUES (?, ?, ?)""",
                    (name.lower(), trigger_phrase.lower(), json.dumps(actions))
                )
                conn.commit()
                return True, f"Learned trick '{name}'"
            except sqlite3.Error as e:
                return False, f"Database error: {e}"

    def get_trick(self, name: str) -> Optional[Trick]:
        """Get a trick by name"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tricks WHERE name = ?",
                (name.lower(),)
            ).fetchone()

            if row:
                return Trick(
                    id=row['id'],
                    name=row['name'],
                    trigger_phrase=row['trigger_phrase'],
                    actions=json.loads(row['actions']),
                    times_performed=row['times_performed'],
                    created_at=row['created_at'],
                    last_performed=row['last_performed']
                )
            return None

    def find_trick_by_trigger(self, phrase: str) -> Optional[Trick]:
        """Find a trick that matches a trigger phrase"""
        phrase_lower = phrase.lower()

        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM tricks").fetchall()

            for row in rows:
                if row['trigger_phrase'] in phrase_lower:
                    return Trick(
                        id=row['id'],
                        name=row['name'],
                        trigger_phrase=row['trigger_phrase'],
                        actions=json.loads(row['actions']),
                        times_performed=row['times_performed'],
                        created_at=row['created_at'],
                        last_performed=row['last_performed']
                    )
            return None

    def record_trick_performed(self, name: str):
        """Record that a trick was performed"""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE tricks
                   SET times_performed = times_performed + 1,
                       last_performed = CURRENT_TIMESTAMP
                   WHERE name = ?""",
                (name.lower(),)
            )
            conn.commit()

    def get_all_tricks(self) -> List[Trick]:
        """Get all learned tricks"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tricks ORDER BY times_performed DESC"
            ).fetchall()

            return [Trick(
                id=row['id'],
                name=row['name'],
                trigger_phrase=row['trigger_phrase'],
                actions=json.loads(row['actions']),
                times_performed=row['times_performed'],
                created_at=row['created_at'],
                last_performed=row['last_performed']
            ) for row in rows]

    def delete_trick(self, name: str):
        """Delete a trick"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM tricks WHERE name = ?", (name.lower(),))
            conn.commit()

    # ==================== GOALS ====================

    def set_goal(self, description: str, priority: int = 3) -> int:
        """Create a new goal

        Args:
            description: What the goal is
            priority: 1-5 (5 is highest priority)

        Returns:
            ID of the new goal
        """
        priority = max(1, min(5, priority))

        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO goals (description, priority) VALUES (?, ?)",
                (description, priority)
            )
            conn.commit()
            return cursor.lastrowid

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals, sorted by priority"""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM goals WHERE status = 'active'
                   ORDER BY priority DESC, created_at ASC"""
            ).fetchall()

            return [Goal(
                id=row['id'],
                description=row['description'],
                priority=row['priority'],
                status=row['status'],
                progress=json.loads(row['progress']) if row['progress'] else None,
                created_at=row['created_at'],
                completed_at=row['completed_at']
            ) for row in rows]

    def complete_goal(self, goal_id: int):
        """Mark a goal as completed"""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE goals
                   SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (goal_id,)
            )
            conn.commit()

    def update_goal_progress(self, goal_id: int, progress: Dict):
        """Update goal progress"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE goals SET progress = ? WHERE id = ?",
                (json.dumps(progress), goal_id)
            )
            conn.commit()

    def abandon_goal(self, goal_id: int):
        """Abandon a goal"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE goals SET status = 'abandoned' WHERE id = ?",
                (goal_id,)
            )
            conn.commit()

    # ==================== FACES ====================

    def store_face(self, name: str, encoding: bytes,
                   image_hash: Optional[str] = None) -> int:
        """Store a face encoding

        Args:
            name: Person's name
            encoding: 128-dimensional face encoding as bytes
            image_hash: Optional hash for deduplication

        Returns:
            ID of the stored face
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO faces (name, encoding, image_hash)
                   VALUES (?, ?, ?)""",
                (name, encoding, image_hash)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_faces(self) -> List[Face]:
        """Get all stored faces"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM faces ORDER BY times_seen DESC"
            ).fetchall()

            return [Face(
                id=row['id'],
                name=row['name'],
                encoding=row['encoding'],
                image_hash=row['image_hash'],
                created_at=row['created_at'],
                last_seen=row['last_seen'],
                times_seen=row['times_seen']
            ) for row in rows]

    def get_faces_by_name(self, name: str) -> List[Face]:
        """Get all face encodings for a person"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM faces WHERE name = ?",
                (name,)
            ).fetchall()

            return [Face(**dict(row)) for row in rows]

    def record_face_seen(self, face_id: int):
        """Record that a face was seen"""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE faces
                   SET times_seen = times_seen + 1, last_seen = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (face_id,)
            )
            conn.commit()

    def delete_face(self, face_id: int):
        """Delete a face encoding"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            conn.commit()

    # ==================== ROOMS ====================

    def store_room(self, name: str, description: str,
                   landmarks: Optional[List[str]] = None,
                   image_hash: Optional[str] = None) -> int:
        """Store a room/location

        Args:
            name: Room name
            description: Visual description from Claude
            landmarks: Notable visual features
            image_hash: Optional hash for deduplication

        Returns:
            ID of the stored room
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO rooms (name, description, landmarks, image_hash)
                   VALUES (?, ?, ?, ?)""",
                (name.lower(), description,
                 json.dumps(landmarks) if landmarks else None, image_hash)
            )
            conn.commit()
            return cursor.lastrowid

    def get_room(self, name: str) -> Optional[Room]:
        """Get a room by name"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM rooms WHERE name = ?",
                (name.lower(),)
            ).fetchone()

            if row:
                return Room(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    landmarks=json.loads(row['landmarks']) if row['landmarks'] else None,
                    image_hash=row['image_hash'],
                    created_at=row['created_at'],
                    last_visited=row['last_visited'],
                    times_visited=row['times_visited']
                )
            return None

    def get_all_rooms(self) -> List[Room]:
        """Get all stored rooms"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM rooms ORDER BY times_visited DESC"
            ).fetchall()

            return [Room(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                landmarks=json.loads(row['landmarks']) if row['landmarks'] else None,
                image_hash=row['image_hash'],
                created_at=row['created_at'],
                last_visited=row['last_visited'],
                times_visited=row['times_visited']
            ) for row in rows]

    def record_room_visited(self, name: str):
        """Record that a room was visited"""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE rooms
                   SET times_visited = times_visited + 1, last_visited = CURRENT_TIMESTAMP
                   WHERE name = ?""",
                (name.lower(),)
            )
            conn.commit()

    # ==================== CONVERSATIONS ====================

    def store_conversation(self, summary: str, participant: Optional[str] = None,
                          mood: Optional[str] = None,
                          topics: Optional[List[str]] = None) -> int:
        """Store a conversation summary

        Args:
            summary: Compressed summary of the conversation
            participant: Who was talked to
            mood: Overall mood of the conversation
            topics: Topics discussed

        Returns:
            ID of the stored conversation
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO conversations (summary, participant, mood, topics)
                   VALUES (?, ?, ?, ?)""",
                (summary, participant, mood,
                 json.dumps(topics) if topics else None)
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_conversations(self, limit: int = 5) -> List[Dict]:
        """Get recent conversation summaries"""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM conversations
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            ).fetchall()

            return [{
                'id': row['id'],
                'summary': row['summary'],
                'participant': row['participant'],
                'mood': row['mood'],
                'topics': json.loads(row['topics']) if row['topics'] else None,
                'created_at': row['created_at']
            } for row in rows]

    # ==================== CONTEXT GENERATION ====================

    def get_memory_context(self, query: Optional[str] = None,
                          max_memories: int = 5) -> str:
        """Generate memory context for Claude prompt injection

        Args:
            query: Optional query to find relevant memories
            max_memories: Maximum memories to include

        Returns:
            Formatted string for prompt injection
        """
        lines = []

        # Get relevant memories if query provided
        if query:
            memories = self.recall(query, limit=max_memories)
            if memories:
                lines.append("Relevant memories:")
                for m in memories:
                    lines.append(f"- [{m.category}] {m.subject}: {m.content}")

        # Always include important memories
        important = self.get_important_memories(min_importance=0.7, limit=3)
        if important:
            if lines:
                lines.append("")
            lines.append("Important memories:")
            for m in important:
                lines.append(f"- {m.subject}: {m.content}")

        return "\n".join(lines) if lines else "No memories yet."

    def get_goals_context(self) -> str:
        """Generate goals context for Claude prompt injection"""
        goals = self.get_active_goals()

        if not goals:
            return "No active goals."

        lines = ["Active goals:"]
        for g in goals:
            priority_stars = "*" * g.priority
            lines.append(f"- [{priority_stars}] {g.description}")

        return "\n".join(lines)

    def get_faces_context(self) -> str:
        """Generate faces context for Claude prompt injection"""
        faces = self.get_all_faces()

        if not faces:
            return "No known faces."

        # Get unique names
        names = list(set(f.name for f in faces))
        return f"Known faces: {', '.join(names)}"

    def get_rooms_context(self) -> str:
        """Generate rooms context for Claude prompt injection"""
        rooms = self.get_all_rooms()

        if not rooms:
            return "No known rooms."

        lines = ["Known rooms:"]
        for r in rooms:
            lines.append(f"- {r.name}: {r.description[:50]}...")

        return "\n".join(lines)

    # ==================== MAINTENANCE ====================

    def cleanup_old_observations(self, max_age_hours: int = 24):
        """Delete old observations to save space"""
        with self._get_conn() as conn:
            conn.execute(
                """DELETE FROM observations
                   WHERE created_at < datetime('now', ?)""",
                (f'-{max_age_hours} hours',)
            )
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with self._get_conn() as conn:
            stats = {}
            for table in ['memories', 'tricks', 'goals', 'faces', 'rooms', 'conversations']:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[table] = count
            return stats

    # ==================== BULK OPERATIONS (for maintenance) ====================

    def get_memories_by_subject_grouped(self) -> Dict[str, List[Memory]]:
        """Get all memories grouped by subject

        Returns:
            Dict mapping subject -> list of memories
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY subject, importance DESC"
            ).fetchall()

            grouped: Dict[str, List[Memory]] = {}
            for row in rows:
                mem = Memory(**dict(row))
                if mem.subject not in grouped:
                    grouped[mem.subject] = []
                grouped[mem.subject].append(mem)

            return grouped

    def get_stale_memories(self, days_since_access: int,
                          max_importance: float = 1.0) -> List[Memory]:
        """Get memories that haven't been accessed recently

        Args:
            days_since_access: Minimum days since last access
            max_importance: Maximum importance to consider

        Returns:
            List of stale memories
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM memories
                   WHERE last_accessed < datetime('now', ?)
                   AND importance <= ?
                   ORDER BY importance ASC, last_accessed ASC""",
                (f'-{days_since_access} days', max_importance)
            ).fetchall()

            return [Memory(**dict(row)) for row in rows]

    def get_prune_candidates(self, max_importance: float,
                            limit: int = 100) -> List[Memory]:
        """Get memories eligible for pruning (low importance, old)

        Args:
            max_importance: Maximum importance for pruning
            limit: Maximum number to return

        Returns:
            List of memories eligible for pruning
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM memories
                   WHERE importance <= ?
                   ORDER BY importance ASC, access_count ASC, last_accessed ASC
                   LIMIT ?""",
                (max_importance, limit)
            ).fetchall()

            return [Memory(**dict(row)) for row in rows]

    def bulk_update_importance(self, updates: List[Tuple[int, float]]):
        """Update importance for multiple memories efficiently

        Args:
            updates: List of (memory_id, new_importance) tuples
        """
        if not updates:
            return

        with self._get_conn() as conn:
            # Use executemany for efficiency
            conn.executemany(
                "UPDATE memories SET importance = ? WHERE id = ?",
                [(importance, mem_id) for mem_id, importance in updates]
            )
            conn.commit()

    def bulk_delete_memories(self, ids: List[int]):
        """Delete multiple memories efficiently

        Args:
            ids: List of memory IDs to delete
        """
        if not ids:
            return

        with self._get_conn() as conn:
            placeholders = ','.join('?' * len(ids))
            conn.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})",
                ids
            )
            conn.commit()

    def update_memory_content(self, memory_id: int, content: str):
        """Update the content of a memory

        Args:
            memory_id: ID of memory to update
            content: New content
        """
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE memories SET content = ? WHERE id = ?",
                (content, memory_id)
            )
            conn.commit()

    def get_duplicate_faces(self, distance_threshold: float = 0.4) -> List[List[Face]]:
        """Find groups of duplicate face entries

        Compares face encodings to find duplicates within threshold.

        Args:
            distance_threshold: Maximum distance to consider duplicates

        Returns:
            List of groups, each group contains duplicate Face entries
        """
        faces = self.get_all_faces()

        if len(faces) < 2:
            return []

        try:
            import numpy as np
        except ImportError:
            logger.warning("numpy not available for face deduplication")
            return []

        # Group by name first (only merge faces with same name)
        by_name: Dict[str, List[Face]] = {}
        for face in faces:
            if face.name not in by_name:
                by_name[face.name] = []
            by_name[face.name].append(face)

        duplicate_groups = []

        for name, name_faces in by_name.items():
            if len(name_faces) < 2:
                continue

            # Convert encodings to numpy arrays
            encodings = []
            for f in name_faces:
                try:
                    enc = np.frombuffer(f.encoding, dtype=np.float64)
                    encodings.append(enc)
                except Exception as e:
                    logger.debug(f"Could not decode face encoding for '{f.name}' (id={f.id}): {e}")
                    encodings.append(None)

            # Find duplicates within this name group
            used = set()
            for i in range(len(name_faces)):
                if i in used or encodings[i] is None:
                    continue

                group = [name_faces[i]]
                used.add(i)

                for j in range(i + 1, len(name_faces)):
                    if j in used or encodings[j] is None:
                        continue

                    # Calculate Euclidean distance
                    try:
                        dist = np.linalg.norm(encodings[i] - encodings[j])
                        if dist < distance_threshold:
                            group.append(name_faces[j])
                            used.add(j)
                    except Exception as e:
                        logger.debug(f"Error comparing face encodings: {e}")
                        continue

                if len(group) > 1:
                    duplicate_groups.append(group)

        return duplicate_groups

    def merge_face_entries(self, keep_id: int, delete_ids: List[int]):
        """Merge duplicate face entries into one

        Args:
            keep_id: ID of face entry to keep
            delete_ids: IDs of face entries to merge and delete
        """
        if not delete_ids:
            return

        with self._get_conn() as conn:
            # Sum up times_seen from entries being deleted
            placeholders = ','.join('?' * len(delete_ids))
            result = conn.execute(
                f"SELECT SUM(times_seen) FROM faces WHERE id IN ({placeholders})",
                delete_ids
            ).fetchone()
            additional_seen = result[0] or 0

            # Update kept entry
            conn.execute(
                "UPDATE faces SET times_seen = times_seen + ? WHERE id = ?",
                (additional_seen, keep_id)
            )

            # Delete merged entries
            conn.execute(
                f"DELETE FROM faces WHERE id IN ({placeholders})",
                delete_ids
            )

            conn.commit()
