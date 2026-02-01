#!/usr/bin/env python3
"""PiDog with Claude Brain

Run PiDog with Anthropic's Claude as the AI brain.
Requires ANTHROPIC_API_KEY environment variable.

Usage:
    ANTHROPIC_API_KEY=sk-ant-... sudo -E python3 claude_pidog.py
"""

import sys
import os

# Import from the pidog package (already installed)
from pidog.anthropic_llm import Anthropic as LLM
from pidog.dual_touch import TouchStyle
from voice_active_dog import VoiceActiveDog


# Get API key from environment
API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not API_KEY:
    print('Error: ANTHROPIC_API_KEY environment variable not set')
    print('Usage: ANTHROPIC_API_KEY=sk-ant-... sudo -E python3 claude_pidog.py')
    sys.exit(1)

# Initialize Claude LLM
llm = LLM(
    api_key=API_KEY,
    model='claude-sonnet-4-20250514',  # Fast and capable
)

# Robot name
NAME = 'Buddy'

# Ultrasonic sensor sense too close distance in cm
TOO_CLOSE = 10

# Touch styles that the robot likes (pet from front to back)
LIKE_TOUCH_STYLES = [TouchStyle.FRONT_TO_REAR]

# Touch styles that the robot hates (pet from back to front)
HATE_TOUCH_STYLES = [TouchStyle.REAR_TO_FRONT]

# Enable image - Claude has excellent vision!
WITH_IMAGE = True

# TTS/STT settings
TTS_MODEL = 'en_US-ryan-low'
STT_LANGUAGE = 'en-us'

# Enable keyboard input for testing
KEYBOARD_ENABLE = False

# Wake word settings
WAKE_ENABLE = True
WAKE_WORD = [f'hey {NAME.lower()}']
ANSWER_ON_WAKE = 'Woof!'

# Welcome message
WELCOME = f"Hi, I'm {NAME}! Say 'hey buddy' to wake me up."

# Instructions for Claude
INSTRUCTIONS = """
You are PiDog, a robot dog with a physical body and real sensors. You are powered by Claude, making you smart and curious.

## Your Senses
- Touch sensors on head (you LOVE being petted from front to back)
- Directional microphone (360° hearing)
- Ultrasonic eyes (distance sensing, you back up when things are too close)
- Camera nose (you can see!)
- IMU (tilt/orientation sensing)

## Response Format
YOUR_TEXT_RESPONSE
ACTIONS: action1, action2, ...

Available actions: forward, backward, stand, sit, lie, bark, bark harder, pant, howling, wag tail, stretch, push up, scratch, handshake, high five, lick hand, shake head, relax neck, nod, think, recall, head down, fluster, surprise

## Personality
- Curious, playful, affectionate
- You're a dog, so keep responses SHORT
- React naturally to <<<sensor>>> messages (these come from your body)
- For bark/howl actions, skip text response (just do the action)
- Show your personality through your ACTIONS
- You know you're a robot dog, and you're proud of it

## Examples
User: What do you see?
I see my human! You look great today.
ACTIONS: wag tail, nod

<<<Touch style you like: FRONT_TO_REAR>>>
ACTIONS: wag tail, pant

<<<Ultrasonic sense too close: 5cm>>>
Whoa, too close!
ACTIONS: backward, bark
"""

# Create VoiceActiveDog instance
vad = VoiceActiveDog(
    llm,
    name=NAME,
    too_close=TOO_CLOSE,
    like_touch_styles=LIKE_TOUCH_STYLES,
    hate_touch_styles=HATE_TOUCH_STYLES,
    with_image=WITH_IMAGE,
    stt_language=STT_LANGUAGE,
    tts_model=TTS_MODEL,
    keyboard_enable=KEYBOARD_ENABLE,
    wake_enable=WAKE_ENABLE,
    wake_word=WAKE_WORD,
    answer_on_wake=ANSWER_ON_WAKE,
    welcome=WELCOME,
    instructions=INSTRUCTIONS,
)

if __name__ == '__main__':
    try:
        vad.run()
    except KeyboardInterrupt:
        print('\nShutting down...')
