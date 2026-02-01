"""Memory Maintenance - Background consolidation and cleanup using Claude

Provides automatic memory maintenance:
- Importance decay for old, unused memories
- Claude-powered consolidation of duplicate/similar memories
- Automatic pruning when database exceeds size limits
- Face deduplication for duplicate entries

Safety: Won't run during active interactions to avoid interference.
"""

import time
import threading
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceConfig:
    """Configuration for memory maintenance"""
    interval_hours: float = 6.0              # Hours between maintenance runs
    initial_delay_minutes: float = 5.0       # Delay before first maintenance run
    busy_retry_minutes: float = 5.0          # Retry interval when system is busy
    max_memories: int = 500                  # Prune when memory count exceeds this
    min_importance: float = 0.2              # Memories below this are eligible for pruning
    decay_rate_per_day: float = 0.01         # Daily importance decay rate
    decay_tolerance: float = 0.001           # Min decay to trigger an update
    access_protection_days: int = 7          # Days of protection after last access
    consolidation_batch_size: int = 20       # Max memories per Claude consolidation call
    consolidation_delay_seconds: float = 1.0 # Delay between consolidation API calls
    face_distance_threshold: float = 0.4     # Threshold for face deduplication


@dataclass
class MaintenanceStats:
    """Statistics from a maintenance run"""
    decayed_count: int = 0
    consolidated_count: int = 0
    pruned_count: int = 0
    merged_faces_count: int = 0
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# Claude prompt for memory consolidation
CONSOLIDATION_PROMPT = """Review these memories about "{subject}" and identify:
1. Duplicates (same information, different wording)
2. Memories that should be merged into one
3. Outdated information contradicted by newer memories

Memories (id: content [importance]):
{memories}

Respond with JSON only, no other text:
{{
  "delete_ids": [1, 2],
  "updates": [{{"id": 3, "content": "...", "importance": 0.7}}],
  "merged": {{"content": "...", "importance": 0.8, "source_ids": [4, 5]}}
}}

Rules:
- delete_ids: IDs to delete (duplicates, outdated)
- updates: Memories to update (content/importance changes)
- merged: Single merged memory from multiple sources (optional, omit if not needed)
- Keep important information, remove redundancy
- Preserve the most recent/accurate information
- If no changes needed, return: {{"delete_ids": [], "updates": [], "merged": null}}
"""


class MemoryMaintainer:
    """Background thread for memory maintenance

    Follows the AutonomousBrain pattern for thread management.

    Usage:
        maintainer = MemoryMaintainer(
            memory_manager=memory,
            llm=robust_llm,
            config=MaintenanceConfig(),
            is_busy_callback=lambda: brain.state == AutonomousState.INTERACTING
        )
        maintainer.start()
        # ... runs in background ...
        maintainer.stop()
    """

    def __init__(self,
                 memory_manager,
                 llm,
                 config: Optional[MaintenanceConfig] = None,
                 is_busy_callback: Optional[Callable[[], bool]] = None):
        """Initialize memory maintainer

        Args:
            memory_manager: MemoryManager instance
            llm: RobustLLM instance for Claude consolidation calls
            config: Maintenance configuration
            is_busy_callback: Callback that returns True if system is busy (skip maintenance)
        """
        self.memory = memory_manager
        self.llm = llm
        self.config = config or MaintenanceConfig()
        self.is_busy = is_busy_callback or (lambda: False)

        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Statistics
        self._last_stats: Optional[MaintenanceStats] = None
        self._stats_lock = threading.Lock()

    def start(self):
        """Start the maintenance background thread"""
        if self._running:
            logger.warning("MemoryMaintainer already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._thread.start()
        logger.info(f"Memory maintenance started (interval: {self.config.interval_hours}h)")

    def stop(self, timeout: float = 10.0):
        """Stop the maintenance thread gracefully

        Args:
            timeout: Maximum seconds to wait for thread to stop
        """
        if not self._running:
            return

        logger.info("Stopping memory maintenance...")
        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("Memory maintenance thread did not stop within timeout")
            self._thread = None

        logger.info("Memory maintenance stopped")

    def run_maintenance(self) -> MaintenanceStats:
        """Manually trigger a maintenance run

        Returns:
            MaintenanceStats with results
        """
        return self._do_maintenance()

    def get_last_stats(self) -> Optional[MaintenanceStats]:
        """Get statistics from the last maintenance run"""
        with self._stats_lock:
            return self._last_stats

    def _maintenance_loop(self):
        """Main maintenance loop - runs every interval_hours"""
        interval_seconds = self.config.interval_hours * 3600
        initial_delay_seconds = self.config.initial_delay_minutes * 60
        busy_retry_seconds = self.config.busy_retry_minutes * 60

        # Initial delay before first run (let system stabilize)
        if self._stop_event.wait(timeout=initial_delay_seconds):
            return  # Stop event was set

        while self._running:
            # Check if system is busy before running
            if self.is_busy():
                logger.debug("Skipping maintenance - system is busy, will retry")
                # Retry sooner when busy instead of waiting full interval
                if self._stop_event.wait(timeout=busy_retry_seconds):
                    break
                continue

            # Run maintenance
            try:
                stats = self._do_maintenance()
                with self._stats_lock:
                    self._last_stats = stats
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

            # Wait for next interval or stop signal
            if self._stop_event.wait(timeout=interval_seconds):
                break

    def _do_maintenance(self) -> MaintenanceStats:
        """Execute a full maintenance cycle"""
        start_time = time.time()
        stats = MaintenanceStats()

        logger.info("Running memory maintenance...")

        try:
            # Step 1: Decay importance of old memories
            stats.decayed_count = self._decay_importance()

            # Step 2: Consolidate similar memories (uses Claude)
            if not self.is_busy():
                stats.consolidated_count = self._consolidate_memories()

            # Step 3: Prune low-importance memories if over limit
            stats.pruned_count = self._prune_low_importance()

            # Step 4: Deduplicate faces
            stats.merged_faces_count = self._deduplicate_faces()

        except Exception as e:
            logger.error(f"Maintenance cycle error: {e}")

        stats.duration_seconds = time.time() - start_time
        logger.info(
            f"Maintenance complete: decayed={stats.decayed_count}, "
            f"consolidated={stats.consolidated_count}, pruned={stats.pruned_count}, "
            f"merged_faces={stats.merged_faces_count}, duration={stats.duration_seconds:.2f}s"
        )

        return stats

    def _decay_importance(self) -> int:
        """Apply time-based decay to old, unaccessed memories

        Returns:
            Number of memories whose importance was decayed
        """
        # Get memories that haven't been accessed recently
        stale_memories = self.memory.get_stale_memories(
            days_since_access=self.config.access_protection_days,
            max_importance=0.9  # Don't decay very important memories as aggressively
        )

        if not stale_memories:
            return 0

        updates = []
        now = datetime.now()

        for mem in stale_memories:
            # Calculate days since last access
            days_stale = self._calculate_days_stale(mem.last_accessed, now)

            # Calculate decay (only for days beyond protection period)
            days_beyond_protection = max(0, days_stale - self.config.access_protection_days)
            decay = self.config.decay_rate_per_day * days_beyond_protection

            # Only update if decay is significant (avoid float precision issues)
            if decay >= self.config.decay_tolerance:
                new_importance = max(0.0, mem.importance - decay)
                updates.append((mem.id, new_importance))

        if updates:
            self.memory.bulk_update_importance(updates)
            logger.debug(f"Decayed importance for {len(updates)} memories")

        return len(updates)

    def _calculate_days_stale(self, last_accessed: Optional[str], now: datetime) -> int:
        """Calculate days since last access, handling various timestamp formats

        Args:
            last_accessed: ISO format timestamp string or None
            now: Current datetime

        Returns:
            Number of days since last access
        """
        if not last_accessed:
            return self.config.access_protection_days + 1

        try:
            # Handle various ISO formats
            timestamp = last_accessed.replace('Z', '+00:00')

            # Try parsing with timezone
            try:
                last_access = datetime.fromisoformat(timestamp)
                # Convert to naive datetime in local time for comparison
                if last_access.tzinfo is not None:
                    last_access = last_access.replace(tzinfo=None)
            except ValueError:
                # Fallback: try without timezone suffix
                last_access = datetime.fromisoformat(last_accessed.split('+')[0].split('Z')[0])

            return (now - last_access).days
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Could not parse timestamp '{last_accessed}': {e}")
            return self.config.access_protection_days + 1

    def _consolidate_memories(self) -> int:
        """Use Claude to consolidate similar memories

        Returns:
            Number of memories affected by consolidation
        """
        # Group memories by subject
        grouped = self.memory.get_memories_by_subject_grouped()

        total_consolidated = 0
        subjects_processed = 0

        for subject, memories in grouped.items():
            # Skip if too few memories to consolidate
            if len(memories) < 2:
                continue

            # Skip if too many (would need multiple batches)
            if len(memories) > self.config.consolidation_batch_size:
                memories = sorted(memories, key=lambda m: m.importance, reverse=True)
                memories = memories[:self.config.consolidation_batch_size]

            # Check if busy before Claude call
            if self.is_busy():
                logger.debug("Stopping consolidation - system became busy")
                break

            # Check for stop signal
            if not self._running:
                break

            # Rate limit between consolidation calls
            if subjects_processed > 0 and self.config.consolidation_delay_seconds > 0:
                time.sleep(self.config.consolidation_delay_seconds)

            try:
                consolidated = self._consolidate_subject_memories(subject, memories)
                total_consolidated += consolidated
                subjects_processed += 1
            except Exception as e:
                logger.error(f"Error consolidating memories for '{subject}': {e}")

        return total_consolidated

    def _consolidate_subject_memories(self, subject: str, memories: list) -> int:
        """Consolidate memories for a single subject using Claude

        Returns:
            Number of memories affected
        """
        # Build set of valid IDs for this subject (prevents hallucinated ID attacks)
        valid_ids: Set[int] = {m.id for m in memories}

        # Format memories for Claude
        memory_lines = []
        for m in memories:
            memory_lines.append(f"{m.id}: {m.content} [{m.importance:.2f}]")

        prompt = CONSOLIDATION_PROMPT.format(
            subject=subject,
            memories="\n".join(memory_lines)
        )

        # Clear any existing conversation and set simple instructions
        self.llm.clear_history()
        self.llm.set_instructions("You are a memory consolidation assistant. Respond only with valid JSON.")

        # Get Claude's analysis
        try:
            response = self.llm.prompt(prompt, use_cache=False)
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Claude returned invalid JSON for consolidation: {e}")
            return 0
        except Exception as e:
            logger.error(f"Claude consolidation call failed: {e}")
            return 0

        affected = 0
        deleted_ids: Set[int] = set()  # Track already-deleted IDs to prevent double-counting

        # Process deletions (validate IDs first)
        delete_ids = result.get("delete_ids", [])
        validated_delete_ids = [id for id in delete_ids if id in valid_ids]
        if len(validated_delete_ids) != len(delete_ids):
            invalid_count = len(delete_ids) - len(validated_delete_ids)
            logger.warning(f"Ignored {invalid_count} invalid memory IDs in delete_ids for '{subject}'")

        if validated_delete_ids:
            self.memory.bulk_delete_memories(validated_delete_ids)
            deleted_ids.update(validated_delete_ids)
            affected += len(validated_delete_ids)
            logger.debug(f"Deleted {len(validated_delete_ids)} duplicate memories for '{subject}'")

        # Process updates (validate IDs, skip deleted ones)
        updates = result.get("updates", [])
        for update in updates:
            try:
                mem_id = update.get("id")
                if mem_id not in valid_ids:
                    logger.warning(f"Ignored invalid memory ID {mem_id} in update for '{subject}'")
                    continue
                if mem_id in deleted_ids:
                    logger.debug(f"Skipped update for already-deleted memory {mem_id}")
                    continue

                if "content" in update:
                    self.memory.update_memory_content(mem_id, update["content"])
                if "importance" in update:
                    self.memory.update_memory_importance(mem_id, update["importance"])
                affected += 1
            except Exception as e:
                logger.warning(f"Failed to update memory {update}: {e}")

        # Process merged memory (validate source_ids)
        merged = result.get("merged")
        if merged and merged.get("content") and merged.get("source_ids"):
            source_ids = merged["source_ids"]

            # Validate source IDs and filter out already-deleted ones
            validated_source_ids = [id for id in source_ids if id in valid_ids and id not in deleted_ids]

            if len(validated_source_ids) != len(source_ids):
                invalid_count = len(source_ids) - len(validated_source_ids)
                logger.warning(f"Ignored {invalid_count} invalid/deleted IDs in merged.source_ids for '{subject}'")

            if validated_source_ids:
                try:
                    # Get category from first valid source memory
                    source_mem = next((m for m in memories if m.id in validated_source_ids), None)
                    if source_mem is None:
                        logger.warning(f"Could not find source memory for merge in '{subject}'")
                    else:
                        # Create merged memory
                        self.memory.remember(
                            category=source_mem.category,
                            subject=subject,
                            content=merged["content"],
                            importance=merged.get("importance", 0.5)
                        )

                        # Delete source memories (only the ones not already deleted)
                        self.memory.bulk_delete_memories(validated_source_ids)
                        affected += len(validated_source_ids)
                        logger.debug(f"Merged {len(validated_source_ids)} memories about '{subject}' into 1")
                except Exception as e:
                    logger.warning(f"Failed to create merged memory: {e}")

        return affected

    def _prune_low_importance(self) -> int:
        """Remove low-importance memories when database exceeds size limit

        Returns:
            Number of memories pruned
        """
        stats = self.memory.get_stats()
        memory_count = stats.get("memories", 0)

        if memory_count <= self.config.max_memories:
            return 0

        # Calculate how many to prune
        excess = memory_count - self.config.max_memories
        # Prune a bit more to avoid frequent pruning
        prune_count = int(excess * 1.2)

        # Get candidates for pruning (low importance, old)
        candidates = self.memory.get_prune_candidates(
            max_importance=self.config.min_importance,
            limit=prune_count
        )

        if not candidates:
            return 0

        ids_to_delete = [m.id for m in candidates]
        self.memory.bulk_delete_memories(ids_to_delete)

        logger.info(f"Pruned {len(ids_to_delete)} low-importance memories")
        return len(ids_to_delete)

    def _deduplicate_faces(self) -> int:
        """Merge duplicate face entries

        Returns:
            Number of face entries merged
        """
        duplicates = self.memory.get_duplicate_faces(
            distance_threshold=self.config.face_distance_threshold
        )

        if not duplicates:
            return 0

        merged_count = 0

        for group in duplicates:
            if len(group) < 2:
                continue

            # Sort by times_seen to keep the most-seen entry
            group.sort(key=lambda f: f.times_seen, reverse=True)
            keep = group[0]
            delete_ids = [f.id for f in group[1:]]

            try:
                self.memory.merge_face_entries(keep.id, delete_ids)
                merged_count += len(delete_ids)
                logger.debug(f"Merged {len(delete_ids)} duplicate face entries for '{keep.name}'")
            except Exception as e:
                logger.warning(f"Failed to merge faces for '{keep.name}': {e}")

        return merged_count
