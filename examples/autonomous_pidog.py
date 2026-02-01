#!/usr/bin/env python3
"""Autonomous PiDog - Main Entry Point

This is the main entry point for running PiDog in autonomous mode.
It combines voice interaction with autonomous behavior, memory, and vision.

Usage:
    # Basic usage (on Raspberry Pi)
    sudo -E python3 autonomous_pidog.py

    # With options
    sudo -E python3 autonomous_pidog.py --name Buddy --no-vision

    # Test mode (no hardware)
    python3 autonomous_pidog.py --test

Requirements:
    - ANTHROPIC_API_KEY environment variable set
    - PiDog hardware (or --test mode)
    - Optional: face_recognition, tflite-runtime for vision

Features:
    - Voice interaction with wake word detection
    - Persistent memory (remembers people, facts, preferences)
    - Face recognition and learning
    - Autonomous exploration and navigation
    - Goal-directed behavior
    - Personality that evolves over time
"""

import os
import sys
import time
import signal
import argparse
import logging

# Suppress PulseAudio warnings when running as root
# XDG_RUNTIME_DIR is owned by the normal user, but sudo runs as root
if os.geteuid() == 0:
    os.environ['XDG_RUNTIME_DIR'] = '/run/user/0'
    # Create it if it doesn't exist
    os.makedirs('/run/user/0', mode=0o700, exist_ok=True)

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup logging for pidog_brain package
from pidog_brain.logging_config import setup_logging


def check_environment(local_only: bool = False):
    """Check that required environment variables are set

    Args:
        local_only: If True, API key is optional
    """
    if not local_only and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("Or use --local-only flag to run without Claude API")
        sys.exit(1)


def run_test_mode():
    """Run in test mode without hardware"""
    print("=== Test Mode (No Hardware) ===\n")

    from pidog_brain.memory_manager import MemoryManager
    from pidog_brain.personality import PersonalityManager
    from pidog_brain.tools import ToolExecutor

    # Initialize components
    print("Initializing memory manager...")
    memory = MemoryManager()

    print("Initializing personality manager...")
    personality = PersonalityManager()

    print("Initializing tool executor...")
    tools = ToolExecutor(memory, personality)

    # Test memory
    print("\n--- Testing Memory ---")
    memory.remember("person", "TestUser", "Created during test run", importance=0.8)
    results = memory.recall("test")
    print(f"Stored and recalled memory: {results}")

    # Test personality
    print("\n--- Testing Personality ---")
    p = personality.get()
    print(f"Personality: {p}")
    print(f"Context: {personality.get_context()}")

    # Test tool parsing
    print("\n--- Testing Tool Parsing ---")
    test_response = """Hello! I'm so happy to meet you!
ACTIONS: wag tail, nod
TOOL: remember {"category": "person", "subject": "TestUser", "content": "Met during test"}
TOOL: set_goal {"description": "Learn more tricks", "priority": 3}"""

    speech, actions, tool_results = tools.parse_and_execute(test_response)
    print(f"Speech: {speech}")
    print(f"Actions: {actions}")
    print(f"Tool results: {tool_results}")

    # Show stats
    print("\n--- Database Stats ---")
    print(memory.get_stats())

    print("\n=== Test Complete ===")


def run_interactive_mode(args):
    """Run in interactive mode for testing without full hardware"""
    print("=== Interactive Mode ===\n")

    from pidog_brain.memory_manager import MemoryManager
    from pidog_brain.personality import PersonalityManager
    from pidog_brain.tools import ToolExecutor
    from pidog_brain.robust_llm import RobustLLM
    from pidog.anthropic_llm import Anthropic

    # Initialize
    memory = MemoryManager()
    personality = PersonalityManager()

    # Initialize LLM
    llm = Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        model=args.model
    )
    robust_llm = RobustLLM(llm, timeout=30.0)

    # Set instructions
    instructions = f"""You are PiDog, an autonomous robot dog with memory and learning abilities.
You can use tools to remember things, learn tricks, and set goals.

## Your Memories
{memory.get_memory_context()}

## Your Goals
{memory.get_goals_context()}

## Your Personality
{personality.get_context()}

Respond naturally and use ACTIONS: and TOOL: lines when appropriate.
"""
    llm.set_instructions(instructions)

    # Tool executor (no hardware callbacks)
    tools = ToolExecutor(memory, personality)

    print("PiDog ready! Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if not user_input:
                continue

            # Get response
            response = robust_llm.prompt(user_input)

            # Parse and execute tools
            speech, actions, tool_results = tools.parse_and_execute(response)

            # Show results
            if speech:
                print(f"\nPiDog: {speech}")
            if actions:
                print(f"  [Would do: {', '.join(actions)}]")
            for result in tool_results:
                if result.success:
                    print(f"  [Tool: {result.message}]")
                else:
                    print(f"  [Tool failed: {result.message}]")
            print()

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}\n")

    print("Goodbye!")


def run_full_mode(args):
    """Run in full mode with hardware"""
    mode_str = "Local-Only Mode" if args.local_only else "Full Mode"
    print(f"=== Starting {args.name} in {mode_str} ===\n")

    from pidog_brain.autonomous_dog import AutonomousDog

    dog = AutonomousDog(
        name=args.name,
        llm_model=args.model,
        enable_vision=not args.no_vision,
        enable_autonomous=not args.no_autonomous,
        conversation_mode=args.conversation_mode,
        conversation_timeout=args.conversation_timeout,
        vad_silence_threshold=args.vad_silence,
        maintenance_enabled=not args.no_maintenance,
        maintenance_interval_hours=args.maintenance_interval,
        maintenance_model=args.maintenance_model,
        local_only=args.local_only
    )

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        print("\nShutting down...")
        dog.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        dog.start()

        print(f"\n{args.name} is running!")
        if args.local_only:
            print("Mode: LOCAL-ONLY (no Claude API calls for autonomous behavior)")
        else:
            print(f"Mode: Full (Claude API for autonomous behavior)")
        print(f"Wake word: 'hey {args.name.lower()}'")
        if args.conversation_mode == 'timeout':
            print(f"Conversation mode: timeout ({args.conversation_timeout}s window)")
        elif args.conversation_mode == 'vad':
            print(f"Conversation mode: VAD ({args.vad_silence}s silence threshold)")
        if not args.no_maintenance and not args.local_only:
            print(f"Memory maintenance: every {args.maintenance_interval}h (model: {args.maintenance_model})")
        else:
            print("Memory maintenance: disabled")
        print("Press Ctrl+C to stop\n")

        # Main loop
        while True:
            time.sleep(1)

            # Optionally print status periodically
            if args.verbose:
                status = dog.get_status()
                if status.get('brain'):
                    brain_state = status['brain']
                    print(f"State: {brain_state['state']}, "
                          f"Boredom: {brain_state['mood']['boredom']:.2f}, "
                          f"Curiosity: {brain_state['mood']['curiosity_level']:.2f}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        dog.stop()


def main():
    parser = argparse.ArgumentParser(
        description='Autonomous PiDog',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run on Raspberry Pi with full features
    sudo -E python3 autonomous_pidog.py

    # Run without vision (saves CPU/memory)
    sudo -E python3 autonomous_pidog.py --no-vision

    # Test mode (no hardware needed)
    python3 autonomous_pidog.py --test

    # Interactive mode (text-only, no hardware)
    python3 autonomous_pidog.py --interactive

    # Timeout conversation mode - 20 second window for follow-ups
    sudo -E python3 autonomous_pidog.py --conversation-mode timeout --conversation-timeout 20

    # VAD conversation mode - listen until 3 seconds of silence
    sudo -E python3 autonomous_pidog.py --conversation-mode vad --vad-silence 3

    # Custom maintenance interval (every 12 hours)
    sudo -E python3 autonomous_pidog.py --maintenance-interval 12

    # Use Opus for smarter memory consolidation
    sudo -E python3 autonomous_pidog.py --maintenance-model claude-opus-4-20250514

    # Disable automatic memory maintenance
    sudo -E python3 autonomous_pidog.py --no-maintenance
"""
    )

    parser.add_argument('--name', default='Buddy',
                       help='Dog name (default: Buddy)')
    parser.add_argument('--model', default='claude-sonnet-4-5-20250929',
                       help='Claude model to use')
    parser.add_argument('--no-vision', action='store_true',
                       help='Disable computer vision')
    parser.add_argument('--no-autonomous', action='store_true',
                       help='Disable autonomous behavior')
    parser.add_argument('--test', action='store_true',
                       help='Run tests without hardware')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive text mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Print status updates')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--conversation-mode', choices=['none', 'timeout', 'vad'],
                       default='none',
                       help='Conversation mode for wake-word-free follow-ups (default: none)')
    parser.add_argument('--conversation-timeout', type=float, default=15.0,
                       help='Timeout in seconds for timeout conversation mode (default: 15)')
    parser.add_argument('--vad-silence', type=float, default=2.0,
                       help='Silence threshold in seconds for VAD conversation mode (default: 2)')
    parser.add_argument('--maintenance-interval', type=float, default=6.0,
                       help='Hours between memory maintenance runs (default: 6)')
    parser.add_argument('--maintenance-model', type=str, default='claude-sonnet-4-20250514',
                       help='Claude model for maintenance consolidation (default: claude-sonnet-4-20250514)')
    parser.add_argument('--no-maintenance', action='store_true',
                       help='Disable automatic memory maintenance')
    parser.add_argument('--local-only', action='store_true',
                       help='Use local behavior engine instead of Claude API (no API costs, faster response, offline capable)')

    args = parser.parse_args()

    # Setup logging (before anything else)
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    # Validate conversation mode parameters
    if args.conversation_timeout <= 0:
        parser.error("--conversation-timeout must be positive")
    if args.vad_silence <= 0:
        parser.error("--vad-silence must be positive")
    if args.maintenance_interval <= 0:
        parser.error("--maintenance-interval must be positive")

    # Check environment
    if not args.test:
        # Interactive mode always needs API key, full mode only if not local_only
        check_environment(local_only=args.local_only and not args.interactive)

    # Run appropriate mode
    if args.test:
        run_test_mode()
    elif args.interactive:
        run_interactive_mode(args)
    else:
        run_full_mode(args)


if __name__ == '__main__':
    main()
