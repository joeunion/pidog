"""Personality Manager - Self-modifiable personality traits

Provides bounded personality traits that affect behavior:
- playfulness: How playful and fun-loving (0-1)
- curiosity: How interested in exploring and learning (0-1)
- affection: How loving and attached to people (0-1)
- energy: How active and energetic (0-1)
- talkativeness: How much PiDog talks (0-1)

All traits are bounded 0.0-1.0 and persist across restarts.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class Personality:
    """PiDog's personality traits"""
    playfulness: float = 0.7
    curiosity: float = 0.8
    affection: float = 0.6
    energy: float = 0.5
    talkativeness: float = 0.6

    def __post_init__(self):
        """Ensure all traits are bounded"""
        self.playfulness = self._bound(self.playfulness)
        self.curiosity = self._bound(self.curiosity)
        self.affection = self._bound(self.affection)
        self.energy = self._bound(self.energy)
        self.talkativeness = self._bound(self.talkativeness)

    @staticmethod
    def _bound(value: float) -> float:
        """Bound a value between 0 and 1"""
        return max(0.0, min(1.0, value))

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Personality':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PersonalityManager:
    """Manages PiDog's personality traits

    Usage:
        pm = PersonalityManager()

        # Get current personality
        p = pm.get()
        print(p.curiosity)

        # Update a trait
        pm.update("curiosity", 0.9)

        # Get context for Claude
        context = pm.get_context()
    """

    VALID_TRAITS = ['playfulness', 'curiosity', 'affection', 'energy', 'talkativeness']

    def __init__(self, config_path: Optional[str] = None):
        """Initialize personality manager

        Args:
            config_path: Path to personality JSON file. Defaults to pidog_brain/personality.json
        """
        if config_path is None:
            config_path = Path(__file__).parent / "personality.json"

        self.config_path = Path(config_path)
        self._personality = self._load()

    def _load(self) -> Personality:
        """Load personality from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                return Personality.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass

        # Create default personality
        return Personality()

    def _save(self):
        """Save personality to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self._personality.to_dict(), f, indent=2)

    def get(self) -> Personality:
        """Get current personality"""
        return self._personality

    def update(self, trait: str, value: float) -> tuple[bool, str]:
        """Update a personality trait

        Args:
            trait: Name of the trait to update
            value: New value (will be bounded 0-1)

        Returns:
            Tuple of (success, message)
        """
        if trait not in self.VALID_TRAITS:
            return False, f"Invalid trait '{trait}'. Valid: {', '.join(self.VALID_TRAITS)}"

        # Bound value
        value = max(0.0, min(1.0, value))

        # Update
        setattr(self._personality, trait, value)
        self._save()

        return True, f"Updated {trait} to {value:.2f}"

    def adjust(self, trait: str, delta: float) -> tuple[bool, str]:
        """Adjust a personality trait by a delta

        Args:
            trait: Name of the trait to adjust
            delta: Amount to change (positive or negative)

        Returns:
            Tuple of (success, message)
        """
        if trait not in self.VALID_TRAITS:
            return False, f"Invalid trait '{trait}'"

        current = getattr(self._personality, trait)
        new_value = max(0.0, min(1.0, current + delta))
        setattr(self._personality, trait, new_value)
        self._save()

        direction = "increased" if delta > 0 else "decreased"
        return True, f"{trait.capitalize()} {direction} to {new_value:.2f}"

    def get_context(self) -> str:
        """Generate personality context for Claude prompt injection

        Returns:
            Formatted string describing current personality
        """
        p = self._personality
        lines = ["Current personality:"]

        # Describe each trait
        traits_desc = {
            'playfulness': ('playful', 'serious'),
            'curiosity': ('curious', 'indifferent'),
            'affection': ('affectionate', 'aloof'),
            'energy': ('energetic', 'calm'),
            'talkativeness': ('talkative', 'quiet')
        }

        for trait, (high_word, low_word) in traits_desc.items():
            value = getattr(p, trait)

            if value >= 0.8:
                desc = f"very {high_word}"
            elif value >= 0.6:
                desc = high_word
            elif value >= 0.4:
                desc = f"somewhat {high_word}"
            elif value >= 0.2:
                desc = low_word
            else:
                desc = f"very {low_word}"

            lines.append(f"- {trait}: {value:.1f} ({desc})")

        return "\n".join(lines)

    def get_behavior_modifiers(self) -> Dict[str, float]:
        """Get behavior modifiers based on personality

        Returns:
            Dictionary of behavior modifiers
        """
        p = self._personality

        return {
            # How likely to initiate play
            'play_chance': p.playfulness * p.energy,

            # How likely to investigate new things
            'investigate_chance': p.curiosity,

            # How likely to approach people
            'approach_chance': p.affection,

            # How often to do idle animations
            'idle_animation_frequency': p.energy * 0.5 + 0.25,

            # Response length modifier
            'response_length': p.talkativeness,

            # How often to think autonomously
            'think_frequency': p.curiosity * 0.5 + 0.25,
        }

    def reset(self):
        """Reset personality to defaults"""
        self._personality = Personality()
        self._save()


# Mood system - transient emotional state (not persisted)
@dataclass
class Mood:
    """PiDog's current mood (transient, not persisted)"""
    happiness: float = 0.5
    excitement: float = 0.3
    tiredness: float = 0.0
    boredom: float = 0.0
    curiosity_level: float = 0.3  # Current curiosity (spikes with novel input)

    def __post_init__(self):
        self._bound_all()

    def _bound_all(self):
        """Bound all values"""
        self.happiness = max(0.0, min(1.0, self.happiness))
        self.excitement = max(0.0, min(1.0, self.excitement))
        self.tiredness = max(0.0, min(1.0, self.tiredness))
        self.boredom = max(0.0, min(1.0, self.boredom))
        self.curiosity_level = max(0.0, min(1.0, self.curiosity_level))

    def update(self, **kwargs):
        """Update mood values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, max(0.0, min(1.0, value)))

    def decay(self, dt: float = 1.0):
        """Decay mood values over time

        Args:
            dt: Time delta in seconds
        """
        decay_rate = 0.01 * dt

        # Excitement and curiosity decay toward baseline
        self.excitement = max(0.3, self.excitement - decay_rate)
        self.curiosity_level = max(0.3, self.curiosity_level - decay_rate)

        # Boredom increases when idle
        self.boredom = min(1.0, self.boredom + decay_rate * 0.5)

        # Tiredness slowly increases
        self.tiredness = min(1.0, self.tiredness + decay_rate * 0.1)

    def on_interaction(self):
        """Reset mood on user interaction"""
        self.boredom = max(0.0, self.boredom - 0.3)
        self.happiness = min(1.0, self.happiness + 0.1)
        self.excitement = min(1.0, self.excitement + 0.2)

    def on_novel_stimulus(self, novelty: float):
        """React to novel stimulus

        Args:
            novelty: How novel the stimulus is (0-1)
        """
        self.curiosity_level = min(1.0, self.curiosity_level + novelty * 0.3)
        self.boredom = max(0.0, self.boredom - novelty * 0.2)
        self.excitement = min(1.0, self.excitement + novelty * 0.1)

    def should_think(self, personality: Personality) -> bool:
        """Determine if PiDog should think autonomously

        Args:
            personality: Current personality traits

        Returns:
            True if should think
        """
        # Think if curious enough or bored enough
        curiosity_threshold = 0.6 - (personality.curiosity * 0.2)
        boredom_threshold = 0.8 - (personality.curiosity * 0.2)

        return (self.curiosity_level > curiosity_threshold or
                self.boredom > boredom_threshold)

    def get_context(self) -> str:
        """Generate mood context for Claude"""
        parts = []

        if self.happiness > 0.7:
            parts.append("feeling happy")
        elif self.happiness < 0.3:
            parts.append("feeling a bit down")

        if self.excitement > 0.7:
            parts.append("excited")
        elif self.tiredness > 0.7:
            parts.append("tired")

        if self.boredom > 0.7:
            parts.append("bored")
        elif self.curiosity_level > 0.7:
            parts.append("very curious")

        if parts:
            return f"Current mood: {', '.join(parts)}"
        return "Current mood: neutral"
