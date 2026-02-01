#!/usr/bin/env python3
"""Force GPIO cleanup when PiDog gets stuck

Use this script to recover from crashes or hung processes that leave
GPIO pins in a bad state.

Usage:
    sudo python3 cleanup.py
"""

import subprocess
import time
import sys


def cleanup():
    """Kill PiDog processes and release GPIO pins"""
    print('PiDog GPIO Cleanup')
    print('=' * 40)

    # Kill any running PiDog Python processes
    print('Killing Python processes...')
    processes_to_kill = [
        'python.*pidog',
        'python.*voice_active',
        'python.*claude_pidog',
    ]

    for pattern in processes_to_kill:
        result = subprocess.run(
            ['sudo', 'pkill', '-9', '-f', pattern],
            capture_output=True,
        )
        if result.returncode == 0:
            print(f'  Killed processes matching: {pattern}')

    # Wait for processes to fully terminate
    print('Waiting for processes to terminate...')
    time.sleep(2)

    # Release GPIO pins used by PiDog servos
    # These are common PWM pins used by the servo driver
    print('Releasing GPIO pins...')
    gpio_pins = [5, 6, 12, 13]

    for pin in gpio_pins:
        result = subprocess.run(
            ['sudo', 'pinctrl', 'set', str(pin), 'ip', 'pd'],
            capture_output=True,
        )
        if result.returncode == 0:
            print(f'  Released GPIO pin {pin}')
        else:
            # pinctrl might not be available, try raspi-gpio
            result = subprocess.run(
                ['sudo', 'raspi-gpio', 'set', str(pin), 'ip', 'pd'],
                capture_output=True,
            )
            if result.returncode == 0:
                print(f'  Released GPIO pin {pin} (via raspi-gpio)')

    # Try to release I2C if stuck
    print('Checking I2C bus...')
    subprocess.run(
        ['sudo', 'i2cdetect', '-y', '1'],
        capture_output=True,
    )

    print('')
    print('=' * 40)
    print('Cleanup complete!')
    print('')
    print('You can now restart the PiDog:')
    print('  ANTHROPIC_API_KEY=... sudo -E python3 claude_pidog.py')


def status():
    """Check if PiDog processes are running"""
    print('PiDog Status Check')
    print('=' * 40)

    # Check for running processes
    result = subprocess.run(
        ['pgrep', '-fa', 'python.*pidog|python.*voice_active|python.*claude'],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        print('Running PiDog processes:')
        for line in result.stdout.strip().split('\n'):
            print(f'  {line}')
    else:
        print('No PiDog processes running.')

    print('')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        status()
    else:
        cleanup()
