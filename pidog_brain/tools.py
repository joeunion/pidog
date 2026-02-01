"""Tool System - Parse and execute commands from Claude responses

Parses Claude responses (guaranteed valid JSON via Anthropic Structured Outputs)
and executes tools for:
- Memory operations (remember, recall)
- Trick learning and execution (learn_trick, do_trick)
- Goal management (set_goal, complete_goal)
- Personality updates (update_personality)
- Vision tools (learn_face, learn_room, follow_person, etc.)
- Navigation (explore, go_to_room, find_person)

JSON response format:
    {
        "speech": "What the dog says",
        "actions": ["wag tail", "nod"],
        "tools": [
            {"name": "remember", "params": {"category": "person", "subject": "Joe", "content": "Likes belly rubs"}}
        ]
    }
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass
from .memory_manager import MemoryManager
from .personality import PersonalityManager

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of a tool execution"""
    success: bool
    message: str
    data: Any = None


class ToolExecutor:
    """Executes tool commands from Claude JSON responses

    Usage:
        executor = ToolExecutor(memory_manager, personality_manager)

        # Parse response and execute tools
        speech, actions, tool_results = executor.parse_and_execute(response_json)

        # Or just parse tools from response
        tools = executor.parse_tools(response_json)
    """

    def __init__(self,
                 memory_manager: MemoryManager,
                 personality_manager: PersonalityManager,
                 action_callback: Optional[Callable[[List[str]], None]] = None,
                 vision_callbacks: Optional[Dict[str, Callable]] = None):
        """Initialize tool executor

        Args:
            memory_manager: Memory manager instance
            personality_manager: Personality manager instance
            action_callback: Callback to execute actions (e.g., action_flow.add_action)
            vision_callbacks: Dict of vision tool callbacks (learn_face, follow_person, etc.)
        """
        self.memory = memory_manager
        self.personality = personality_manager
        self.action_callback = action_callback
        self.vision_callbacks = vision_callbacks or {}

        # Register tool handlers
        self._tools: Dict[str, Callable[[Dict], ToolResult]] = {
            # Memory tools
            'remember': self._tool_remember,
            'recall': self._tool_recall,

            # Trick tools
            'learn_trick': self._tool_learn_trick,
            'do_trick': self._tool_do_trick,
            'list_tricks': self._tool_list_tricks,

            # Goal tools
            'set_goal': self._tool_set_goal,
            'complete_goal': self._tool_complete_goal,
            'list_goals': self._tool_list_goals,

            # Personality tools
            'update_personality': self._tool_update_personality,

            # Vision tools (delegated to callbacks)
            'learn_face': self._tool_learn_face,
            'learn_room': self._tool_learn_room,
            'follow_person': self._tool_follow_person,
            'find_person': self._tool_find_person,

            # Navigation tools
            'go_to_room': self._tool_go_to_room,
            'explore': self._tool_explore,
        }

    def parse_response(self, text: str) -> Tuple[str, List[str], List[Tuple[str, Dict]]]:
        """Parse Claude response into speech, actions, and tools

        Supports two formats:
        1. JSON format (when using structured outputs or model returns JSON):
           {"speech": "...", "actions": [...], "tools": [{"name": "...", "params": {...}}]}
        2. Legacy text format (fallback for non-JSON responses):
           Speech text
           ACTIONS: action1, action2
           TOOL: tool_name {"params": "..."}

        Args:
            text: Response text from Claude

        Returns:
            Tuple of (speech_text, actions_list, tools_list)
            where tools_list is [(tool_name, params_dict), ...]
        """
        # Try JSON parsing first
        text_stripped = text.strip()

        # Strip markdown code fences if present (e.g., ```json ... ```)
        if text_stripped.startswith('```'):
            logger.debug("Stripping markdown code fences from response")
            lines = text_stripped.split('\n')
            # Remove opening fence (```json or ```)
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text_stripped = '\n'.join(lines).strip()
            logger.debug(f"After stripping fences, text starts with: {text_stripped[:50]}...")

        if text_stripped.startswith('{'):
            try:
                data = json.loads(text_stripped)
                speech = data.get('speech', '')
                actions = data.get('actions', [])
                tools_data = data.get('tools', [])

                # Convert tools to expected format: [(name, params), ...]
                tools = []
                for tool in tools_data:
                    if isinstance(tool, dict) and 'name' in tool:
                        name = tool['name']
                        params = tool.get('params', {})
                        # Handle params as JSON string (from structured outputs)
                        if isinstance(params, str):
                            try:
                                params = json.loads(params) if params else {}
                            except json.JSONDecodeError:
                                params = {}
                        tools.append((name, params))

                logger.debug(f"Parsed JSON response - speech: '{speech[:50]}...' actions: {actions}")
                return speech, actions, tools
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e}")
                pass  # Fall through to legacy parsing

        # Legacy text format parsing
        return self._parse_legacy_format(text)

    def _parse_legacy_format(self, text: str) -> Tuple[str, List[str], List[Tuple[str, Dict]]]:
        """Parse legacy text format with ACTIONS: and TOOL: lines"""
        import re

        lines = text.strip().split('\n')
        speech_lines = []
        actions = []
        tools = []

        for line in lines:
            line_stripped = line.strip()

            # Parse ACTIONS: line
            if line_stripped.upper().startswith('ACTIONS:'):
                action_str = line_stripped[8:].strip()
                if action_str:
                    actions = [a.strip() for a in action_str.split(',')]

            # Parse TOOL: line
            elif line_stripped.upper().startswith('TOOL:'):
                tool_str = line_stripped[5:].strip()
                # Match tool_name followed by optional JSON object
                match = re.match(r'(\w+)\s*({.*})?', tool_str)
                if match:
                    tool_name = match.group(1).lower()
                    params_str = match.group(2)
                    params = {}
                    if params_str:
                        try:
                            params = json.loads(params_str)
                        except json.JSONDecodeError:
                            pass
                    tools.append((tool_name, params))

            # Everything else is speech
            elif line_stripped and not line_stripped.upper().startswith(('ACTIONS:', 'TOOL:')):
                speech_lines.append(line_stripped)

        speech = '\n'.join(speech_lines).strip()
        return speech, actions, tools

    def parse_tools(self, text: str) -> List[Tuple[str, Dict]]:
        """Parse just the tools from a response

        Args:
            text: Full response text

        Returns:
            List of (tool_name, params_dict) tuples
        """
        _, _, tools = self.parse_response(text)
        return tools

    def execute_tool(self, tool_name: str, params: Dict) -> ToolResult:
        """Execute a single tool

        Args:
            tool_name: Name of the tool
            params: Parameters dictionary

        Returns:
            ToolResult with success status and message
        """
        handler = self._tools.get(tool_name.lower())
        if not handler:
            return ToolResult(False, f"Unknown tool: {tool_name}")

        try:
            return handler(params)
        except Exception as e:
            return ToolResult(False, f"Tool error: {e}")

    def parse_and_execute(self, text: str) -> Tuple[str, List[str], List[ToolResult]]:
        """Parse response and execute all tools

        Args:
            text: Full response text from Claude

        Returns:
            Tuple of (speech_text, actions_list, tool_results_list)
        """
        speech, actions, tools = self.parse_response(text)

        # Execute all tools
        results = []
        for tool_name, params in tools:
            result = self.execute_tool(tool_name, params)
            results.append(result)

        return speech, actions, results

    # ==================== MEMORY TOOLS ====================

    def _tool_remember(self, params: Dict) -> ToolResult:
        """Store a memory

        Params:
            category: person|fact|preference|experience|location
            subject: What/who this is about
            content: The memory content
            importance: Optional importance 0-1
        """
        category = params.get('category', 'fact')
        subject = params.get('subject', '')
        content = params.get('content', '')
        importance = params.get('importance', 0.5)

        if not subject or not content:
            return ToolResult(False, "Missing subject or content")

        valid_categories = ['person', 'fact', 'preference', 'experience', 'location']
        if category not in valid_categories:
            category = 'fact'

        memory_id = self.memory.remember(category, subject, content, importance)
        return ToolResult(True, f"Remembered: {subject}", {'id': memory_id})

    def _tool_recall(self, params: Dict) -> ToolResult:
        """Search memories

        Params:
            query: Search query
            category: Optional category filter
            limit: Optional max results
        """
        query = params.get('query', '')
        if not query:
            return ToolResult(False, "Missing query")

        category = params.get('category')
        limit = params.get('limit', 5)

        memories = self.memory.recall(query, limit=limit, category=category)

        if not memories:
            return ToolResult(True, "No memories found", [])

        # Format results
        results = []
        for m in memories:
            results.append({
                'category': m.category,
                'subject': m.subject,
                'content': m.content,
                'importance': m.importance
            })

        summary = f"Found {len(memories)} memories"
        return ToolResult(True, summary, results)

    # ==================== TRICK TOOLS ====================

    def _tool_learn_trick(self, params: Dict) -> ToolResult:
        """Learn a new trick

        Params:
            name: Trick name
            trigger: Trigger phrase
            actions: List of actions
        """
        name = params.get('name', '')
        trigger = params.get('trigger', params.get('trigger_phrase', ''))
        actions = params.get('actions', [])

        if not name or not trigger or not actions:
            return ToolResult(False, "Missing name, trigger, or actions")

        success, message = self.memory.learn_trick(name, trigger, actions)
        return ToolResult(success, message)

    def _tool_do_trick(self, params: Dict) -> ToolResult:
        """Execute a learned trick

        Params:
            name: Trick name (or trigger phrase)
        """
        name = params.get('name', '')
        if not name:
            return ToolResult(False, "Missing trick name")

        # Try to find trick by name or trigger
        trick = self.memory.get_trick(name)
        if not trick:
            trick = self.memory.find_trick_by_trigger(name)

        if not trick:
            return ToolResult(False, f"Unknown trick: {name}")

        # Execute actions via callback
        if self.action_callback:
            self.action_callback(trick.actions)
            self.memory.record_trick_performed(trick.name)
            return ToolResult(True, f"Performing {trick.name}!", {'actions': trick.actions})
        else:
            return ToolResult(True, f"Would perform {trick.name}: {trick.actions}",
                            {'actions': trick.actions})

    def _tool_list_tricks(self, params: Dict) -> ToolResult:
        """List all learned tricks"""
        tricks = self.memory.get_all_tricks()

        if not tricks:
            return ToolResult(True, "No tricks learned yet", [])

        results = []
        for t in tricks:
            results.append({
                'name': t.name,
                'trigger': t.trigger_phrase,
                'times_performed': t.times_performed
            })

        return ToolResult(True, f"Know {len(tricks)} tricks", results)

    # ==================== GOAL TOOLS ====================

    def _tool_set_goal(self, params: Dict) -> ToolResult:
        """Set a new goal

        Params:
            description: Goal description
            priority: 1-5 (5 is highest)
        """
        description = params.get('description', '')
        priority = params.get('priority', 3)

        if not description:
            return ToolResult(False, "Missing goal description")

        goal_id = self.memory.set_goal(description, priority)
        return ToolResult(True, f"Goal set: {description}", {'id': goal_id})

    def _tool_complete_goal(self, params: Dict) -> ToolResult:
        """Complete a goal

        Params:
            id: Goal ID
        """
        goal_id = params.get('id')
        if goal_id is None:
            return ToolResult(False, "Missing goal ID")

        self.memory.complete_goal(goal_id)
        return ToolResult(True, f"Goal {goal_id} completed!")

    def _tool_list_goals(self, params: Dict) -> ToolResult:
        """List active goals"""
        goals = self.memory.get_active_goals()

        if not goals:
            return ToolResult(True, "No active goals", [])

        results = []
        for g in goals:
            results.append({
                'id': g.id,
                'description': g.description,
                'priority': g.priority
            })

        return ToolResult(True, f"{len(goals)} active goals", results)

    # ==================== PERSONALITY TOOLS ====================

    def _tool_update_personality(self, params: Dict) -> ToolResult:
        """Update a personality trait

        Params:
            trait: Trait name
            value: New value (0-1)
        """
        trait = params.get('trait', '')
        value = params.get('value')

        if not trait or value is None:
            return ToolResult(False, "Missing trait or value")

        success, message = self.personality.update(trait, float(value))
        return ToolResult(success, message)

    # ==================== VISION TOOLS ====================

    def _tool_learn_face(self, params: Dict) -> ToolResult:
        """Learn a face from current camera view

        Params:
            name: Person's name
        """
        name = params.get('name', '')
        if not name:
            return ToolResult(False, "Missing name")

        callback = self.vision_callbacks.get('learn_face')
        if callback:
            try:
                result = callback(name)
                return ToolResult(True, f"Learned {name}'s face", result)
            except Exception as e:
                return ToolResult(False, f"Failed to learn face: {e}")
        else:
            return ToolResult(False, "Vision not available")

    def _tool_learn_room(self, params: Dict) -> ToolResult:
        """Learn current location as a room

        Params:
            name: Room name
        """
        name = params.get('name', '')
        if not name:
            return ToolResult(False, "Missing room name")

        callback = self.vision_callbacks.get('learn_room')
        if callback:
            try:
                result = callback(name)
                return ToolResult(True, f"Learned room: {name}", result)
            except Exception as e:
                return ToolResult(False, f"Failed to learn room: {e}")
        else:
            return ToolResult(False, "Vision not available")

    def _tool_follow_person(self, params: Dict) -> ToolResult:
        """Start following the person in view"""
        callback = self.vision_callbacks.get('follow_person')
        if callback:
            try:
                callback()
                return ToolResult(True, "Following person")
            except Exception as e:
                return ToolResult(False, f"Failed to follow: {e}")
        else:
            return ToolResult(False, "Vision not available")

    def _tool_find_person(self, params: Dict) -> ToolResult:
        """Search for a known person

        Params:
            name: Person's name
        """
        name = params.get('name', '')
        if not name:
            return ToolResult(False, "Missing name")

        callback = self.vision_callbacks.get('find_person')
        if callback:
            try:
                callback(name)
                return ToolResult(True, f"Searching for {name}")
            except Exception as e:
                return ToolResult(False, f"Failed to search: {e}")
        else:
            return ToolResult(False, "Vision not available")

    # ==================== NAVIGATION TOOLS ====================

    def _tool_go_to_room(self, params: Dict) -> ToolResult:
        """Navigate to a learned room

        Params:
            name: Room name
        """
        name = params.get('name', '')
        if not name:
            return ToolResult(False, "Missing room name")

        # Check if room exists
        room = self.memory.get_room(name)
        if not room:
            return ToolResult(False, f"Unknown room: {name}")

        callback = self.vision_callbacks.get('go_to_room')
        if callback:
            try:
                callback(name)
                return ToolResult(True, f"Navigating to {name}")
            except Exception as e:
                return ToolResult(False, f"Navigation failed: {e}")
        else:
            return ToolResult(False, "Navigation not available")

    def _tool_explore(self, params: Dict) -> ToolResult:
        """Start exploring the environment"""
        callback = self.vision_callbacks.get('explore')
        if callback:
            try:
                callback()
                return ToolResult(True, "Exploring...")
            except Exception as e:
                return ToolResult(False, f"Exploration failed: {e}")
        else:
            return ToolResult(False, "Navigation not available")


def extend_parse_response(original_parse_response: Callable, executor: ToolExecutor):
    """Create an extended parse_response that handles JSON tool responses

    Usage:
        # In VoiceActiveDog subclass
        self._original_parse = self.parse_response
        self.parse_response = extend_parse_response(self._original_parse, executor)
    """
    def extended_parse(text: str) -> str:
        # Parse JSON response to extract speech, actions, and tools
        speech, actions, tools = executor.parse_response(text)

        # Execute tools
        for tool_name, params in tools:
            result = executor.execute_tool(tool_name, params)
            if not result.success:
                print(f"Tool {tool_name} failed: {result.message}")

        # Return speech text for TTS (original behavior)
        return speech

    return extended_parse
