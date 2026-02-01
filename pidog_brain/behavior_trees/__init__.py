"""Behavior Trees - Modular behavior definitions for local autonomy

This package contains specialized behavior modules:
- social.py: Person interaction behaviors (greetings, farewells, affection)
- exploration.py: Curiosity and investigation behaviors
- play.py: Play and entertainment behaviors
- idle.py: Boredom and rest behaviors
- goals.py: Goal-directed behaviors

Each module provides behavior functions that return (speech, actions, tools) tuples.
"""

from .social import SocialBehaviors
from .exploration import ExplorationBehaviors
from .play import PlayBehaviors
from .idle import IdleBehaviors
from .goals import GoalBehaviors

__all__ = [
    'SocialBehaviors',
    'ExplorationBehaviors',
    'PlayBehaviors',
    'IdleBehaviors',
    'GoalBehaviors',
]
