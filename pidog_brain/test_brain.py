#!/usr/bin/env python3
"""Automated test script for PiDog Brain

Tests all major components without requiring interactive input.
Run with: python3 test_brain.py
"""

import os
import sys
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"       {details}")

def test_memory():
    """Test memory system"""
    print_header("Testing Memory System")

    from pidog_brain.memory_manager import MemoryManager

    # Use a test database
    mm = MemoryManager("/tmp/pidog_test.db")

    # Test 1: Store a memory
    mem_id = mm.remember("person", "Joe", "Likes pizza and playing fetch", importance=0.8)
    print_test("Store memory", mem_id > 0, f"ID: {mem_id}")

    # Test 2: Recall by search
    results = mm.recall("pizza")
    print_test("Recall by keyword", len(results) > 0, f"Found: {len(results)} memories")

    # Test 3: Store another memory
    mm.remember("fact", "Weather", "It's sunny today", importance=0.5)

    # Test 4: Get by category
    people = mm.get_memories_by_category("person")
    print_test("Get by category", len(people) > 0, f"People memories: {len(people)}")

    # Test 5: Important memories
    important = mm.get_important_memories(min_importance=0.7)
    print_test("Important memories", len(important) > 0, f"Important: {len(important)}")

    # Test 6: Learn a trick
    success, msg = mm.learn_trick("spin", "do a spin", ["turn left", "turn left"])
    print_test("Learn trick", success, msg)

    # Test 7: Invalid trick (bad action)
    success, msg = mm.learn_trick("fly", "fly away", ["flap wings"])
    print_test("Reject invalid action", not success, msg)

    # Test 8: Get trick
    trick = mm.get_trick("spin")
    print_test("Get trick", trick is not None, f"Actions: {trick.actions if trick else 'N/A'}")

    # Test 9: Set goal
    goal_id = mm.set_goal("Learn 5 new tricks", priority=4)
    print_test("Set goal", goal_id > 0, f"Goal ID: {goal_id}")

    # Test 10: Get active goals
    goals = mm.get_active_goals()
    print_test("Get active goals", len(goals) > 0, f"Active: {len(goals)}")

    # Test 11: Context generation
    context = mm.get_memory_context("pizza")
    print_test("Memory context", len(context) > 0, f"Length: {len(context)} chars")

    # Test 12: Stats
    stats = mm.get_stats()
    print_test("Database stats", stats['memories'] > 0, f"Stats: {stats}")

    # Cleanup
    os.remove("/tmp/pidog_test.db")

    return True

def test_personality():
    """Test personality system"""
    print_header("Testing Personality System")

    from pidog_brain.personality import PersonalityManager, Mood
    import tempfile

    # Use temp file
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        config_path = f.name

    pm = PersonalityManager(config_path)

    # Test 1: Get personality
    p = pm.get()
    print_test("Get personality", p is not None, f"Curiosity: {p.curiosity}")

    # Test 2: Update trait
    success, msg = pm.update("curiosity", 0.95)
    print_test("Update trait", success, msg)

    # Test 3: Verify update
    p = pm.get()
    print_test("Verify update", p.curiosity == 0.95, f"New value: {p.curiosity}")

    # Test 4: Bounded values (should clamp to 1.0)
    success, msg = pm.update("energy", 1.5)
    p = pm.get()
    print_test("Clamp to bounds", p.energy == 1.0, f"Clamped to: {p.energy}")

    # Test 5: Invalid trait
    success, msg = pm.update("flying_ability", 0.9)
    print_test("Reject invalid trait", not success, msg)

    # Test 6: Context generation
    context = pm.get_context()
    print_test("Personality context", "curiosity" in context.lower(), f"Length: {len(context)}")

    # Test 7: Mood system
    mood = Mood()
    mood.on_interaction()
    print_test("Mood on interaction", mood.happiness > 0.5, f"Happiness: {mood.happiness}")

    # Test 8: Mood decay
    initial_excitement = mood.excitement
    mood.decay(10.0)  # 10 seconds
    print_test("Mood decay", mood.excitement < initial_excitement, f"Excitement: {mood.excitement}")

    # Test 9: Novel stimulus
    mood.on_novel_stimulus(0.8)
    print_test("Novel stimulus", mood.curiosity_level > 0.5, f"Curiosity: {mood.curiosity_level}")

    # Cleanup
    os.remove(config_path)

    return True

def test_tools():
    """Test tool parsing and execution"""
    print_header("Testing Tool System")

    from pidog_brain.memory_manager import MemoryManager
    from pidog_brain.personality import PersonalityManager
    from pidog_brain.tools import ToolExecutor
    import tempfile

    mm = MemoryManager("/tmp/pidog_tools_test.db")

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        pm = PersonalityManager(f.name)
        config_path = f.name

    actions_received = []
    def mock_action(actions):
        actions_received.extend(actions)

    tools = ToolExecutor(mm, pm, action_callback=mock_action)

    # Test 1: Parse simple response
    response = """Hello there!
ACTIONS: wag tail, nod"""
    speech, actions, tool_list = tools.parse_response(response)
    print_test("Parse speech", speech == "Hello there!", f"Speech: '{speech}'")
    print_test("Parse actions", actions == ["wag tail", "nod"], f"Actions: {actions}")

    # Test 2: Parse with tools
    response = """I'll remember that!
ACTIONS: nod
TOOL: remember {"category": "fact", "subject": "Test", "content": "This is a test"}"""
    speech, actions, tool_list = tools.parse_response(response)
    print_test("Parse tools", len(tool_list) == 1, f"Tools: {len(tool_list)}")

    # Test 3: Execute remember tool
    result = tools.execute_tool("remember", {
        "category": "person",
        "subject": "TestPerson",
        "content": "Likes testing"
    })
    print_test("Execute remember", result.success, result.message)

    # Test 4: Execute recall tool
    result = tools.execute_tool("recall", {"query": "testing"})
    print_test("Execute recall", result.success, f"Found: {len(result.data) if result.data else 0}")

    # Test 5: Learn trick via tool
    result = tools.execute_tool("learn_trick", {
        "name": "dance",
        "trigger": "do a dance",
        "actions": ["wag tail", "turn left", "turn right"]
    })
    print_test("Learn trick tool", result.success, result.message)

    # Test 6: Do trick via tool
    result = tools.execute_tool("do_trick", {"name": "dance"})
    print_test("Do trick tool", result.success, f"Actions: {result.data}")
    print_test("Actions callback", len(actions_received) > 0, f"Received: {actions_received}")

    # Test 7: Set goal via tool
    result = tools.execute_tool("set_goal", {
        "description": "Be a good dog",
        "priority": 5
    })
    print_test("Set goal tool", result.success, result.message)

    # Test 8: Update personality via tool
    result = tools.execute_tool("update_personality", {
        "trait": "playfulness",
        "value": 0.9
    })
    print_test("Update personality tool", result.success, result.message)

    # Test 9: Full parse and execute
    response = """Great! I learned something new!
ACTIONS: wag tail
TOOL: remember {"category": "fact", "subject": "Learning", "content": "Just learned to parse"}
TOOL: set_goal {"description": "Parse more things", "priority": 2}"""

    speech, actions, results = tools.parse_and_execute(response)
    all_success = all(r.success for r in results)
    print_test("Full parse and execute", all_success and len(results) == 2,
               f"Results: {len(results)}, All success: {all_success}")

    # Cleanup
    os.remove("/tmp/pidog_tools_test.db")
    os.remove(config_path)

    return True

def test_claude_integration():
    """Test Claude API integration"""
    print_header("Testing Claude API Integration")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set, skipping Claude tests")
        return True

    from pidog_brain.memory_manager import MemoryManager
    from pidog_brain.personality import PersonalityManager
    from pidog_brain.tools import ToolExecutor
    from pidog_brain.robust_llm import RobustLLM
    from pidog_os.anthropic_llm import Anthropic
    import tempfile

    mm = MemoryManager("/tmp/pidog_claude_test.db")

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        pm = PersonalityManager(f.name)
        config_path = f.name

    tools = ToolExecutor(mm, pm)

    # Initialize Claude
    llm = Anthropic(api_key=api_key, model="claude-haiku-4-5-20251001")
    robust = RobustLLM(llm, timeout=30.0)

    instructions = """You are PiDog, a robot dog. Keep responses brief.
When asked to remember something, use: TOOL: remember {"category": "fact", "subject": "...", "content": "..."}
When asked to do an action, use: ACTIONS: action1, action2
Valid actions: wag tail, nod, sit, bark, stand"""

    llm.set_instructions(instructions)

    # Test 1: Basic response
    print("  Sending: 'Say hello in one short sentence'")
    response = robust.prompt("Say hello in one short sentence")
    print_test("Claude responds", len(response) > 0, f"Response: {response[:80]}...")

    # Test 2: Action generation
    print("  Sending: 'Wag your tail and nod'")
    response = robust.prompt("Wag your tail and nod")
    speech, actions, _ = tools.parse_response(response)
    has_actions = len(actions) > 0
    print_test("Generates actions", has_actions, f"Actions: {actions}")

    # Test 3: Tool usage
    print("  Sending: 'Remember that my favorite food is pizza'")
    response = robust.prompt("Remember that my favorite food is pizza")
    speech, actions, tool_list = tools.parse_response(response)
    has_tool = len(tool_list) > 0
    print_test("Uses TOOL:", has_tool, f"Tools: {[t[0] for t in tool_list]}")

    # Execute tools if present
    if tool_list:
        for tool_name, params in tool_list:
            result = tools.execute_tool(tool_name, params)
            print_test(f"  Tool '{tool_name}' executed", result.success, result.message)

    # Test 4: Memory recall
    print("  Sending: 'What is my favorite food?'")

    # Add memory context to instructions
    memory_context = mm.get_memory_context("food")
    llm.set_instructions(instructions + f"\n\nYour memories:\n{memory_context}")

    response = robust.prompt("What is my favorite food?")
    mentions_pizza = "pizza" in response.lower()
    print_test("Recalls memory", mentions_pizza, f"Response: {response[:80]}...")

    # Test 5: Stats
    stats = robust.get_stats()
    print_test("LLM stats tracked", stats['calls'] >= 4, f"Calls: {stats['calls']}")

    # Cleanup
    os.remove("/tmp/pidog_claude_test.db")
    os.remove(config_path)

    return True

def test_autonomous_brain():
    """Test autonomous brain components"""
    print_header("Testing Autonomous Brain")

    from pidog_brain.autonomous_brain import (
        RateLimiter, NoveltyDetector, Observation, AutonomousState
    )

    # Test 1: Rate limiter
    rl = RateLimiter(max_calls_per_minute=5, min_interval=1.0)
    print_test("Rate limiter initial", rl.can_call(), "Can make first call")

    rl.record_call()
    can_call_immediately = rl.can_call()
    print_test("Rate limiter blocks", not can_call_immediately, "Blocked after call")

    time_until = rl.time_until_next()
    print_test("Time until next", time_until > 0, f"Wait: {time_until:.1f}s")

    # Test 2: Novelty detector
    nd = NoveltyDetector()

    obs1 = Observation(sensor_type="ultrasonic", value=50.0)
    novelty1 = nd.add_observation(obs1)
    print_test("First observation novel", novelty1 == 1.0, f"Novelty: {novelty1}")

    # Add similar values
    for i in range(10):
        nd.add_observation(Observation(sensor_type="ultrasonic", value=50.0 + i*0.1))

    # Now a very different value should be novel
    obs_novel = Observation(sensor_type="ultrasonic", value=10.0)
    novelty_high = nd.add_observation(obs_novel)
    print_test("Unusual value novel", novelty_high > 0.5, f"Novelty: {novelty_high:.2f}")

    # Test 3: Categorical novelty
    obs_touch = Observation(sensor_type="touch", value="FRONT")
    novelty_cat = nd.add_observation(obs_touch)
    print_test("Categorical novelty", novelty_cat > 0, f"Touch novelty: {novelty_cat:.2f}")

    # Test 4: States exist
    states = [AutonomousState.IDLE, AutonomousState.CURIOUS,
              AutonomousState.THINKING, AutonomousState.ACTING]
    print_test("States defined", len(states) == 4, f"States: {[s.name for s in states]}")

    return True

def main():
    print("\n" + "="*60)
    print("  PiDog Brain - Automated Test Suite")
    print("="*60)

    all_passed = True

    try:
        all_passed &= test_memory()
    except Exception as e:
        print(f"❌ Memory tests failed: {e}")
        all_passed = False

    try:
        all_passed &= test_personality()
    except Exception as e:
        print(f"❌ Personality tests failed: {e}")
        all_passed = False

    try:
        all_passed &= test_tools()
    except Exception as e:
        print(f"❌ Tool tests failed: {e}")
        all_passed = False

    try:
        all_passed &= test_autonomous_brain()
    except Exception as e:
        print(f"❌ Autonomous brain tests failed: {e}")
        all_passed = False

    try:
        all_passed &= test_claude_integration()
    except Exception as e:
        print(f"❌ Claude integration tests failed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print_header("Test Summary")
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
