# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PiDog is an autonomous robot dog built on Raspberry Pi 5 with the SunFounder PiDog kit. This repository contains a custom "brain" that extends the base PiDog library with Claude-powered autonomous behavior, persistent memory, computer vision, and navigation capabilities.

## Architecture

### Two Codebases

1. **Vendor libraries** (installed on Pi via `pip install`):
   - `robot-hat` - Hardware abstraction (servos, GPIO, sensors)
   - `vilib` - Camera/vision (picamera2)
   - `pidog` - PiDog control (actions, voice assistant)

2. **Custom brain** (this repo, synced to Pi):
   - `pidog_brain/` - Autonomous brain modules
   - `examples/autonomous_pidog.py` - Main entry point

### Brain Architecture

```
pidog_brain/
├── autonomous_dog.py       # Main class - extends VoiceActiveDog
├── autonomous_brain.py     # State machine (IDLE/CURIOUS/THINKING/ACTING/INTERACTING)
├── conversation_manager.py # Wake-word-free conversation modes (timeout/VAD)
├── memory_manager.py       # SQLite + FTS5 for persistent memory
├── personality.py          # Personality traits (0-1 bounded) + mood
├── tools.py                # TOOL: parser and executor
├── robust_llm.py           # Retry/timeout wrapper for Claude API
└── vision/
    ├── face_memory.py    # Face learning/recognition (dlib)
    ├── person_tracker.py # Person detection (TFLite MobileNet-SSD)
    ├── room_memory.py    # Room learning via Claude descriptions
    ├── navigator.py      # Exploration and navigation
    └── obstacle_detector.py
```

### Data Flow

1. Sensors (ultrasonic, touch, IMU, camera) feed observations to `AutonomousBrain`
2. Brain accumulates novelty/boredom locally (no API calls)
3. When thresholds trigger, brain calls Claude with memory context
4. Claude responds with speech + `ACTIONS:` + `TOOL:` lines
5. `ToolExecutor` parses and executes tools, updates memory
6. Actions execute via `Pidog.do_action()`

### Key Design Principle

**Minimize API calls.** Everything possible runs locally:
- Memory retrieval: SQLite FTS5 (~5ms)
- Face detection/recognition: Local dlib (~200ms)
- Person detection: TFLite (~100ms)
- Only complex reasoning goes to Claude (rate-limited: max 5 calls/min, 30s minimum interval)

## Commands

### Running on Raspberry Pi

```bash
# SSH to Pi
ssh zadie@pidog.local  # password: 12345

# Full autonomous mode
sudo -E python3 ~/examples/autonomous_pidog.py

# Without vision (saves CPU)
sudo -E python3 ~/examples/autonomous_pidog.py --no-vision

# Test mode (no hardware)
python3 ~/examples/autonomous_pidog.py --test

# Interactive text mode
python3 ~/examples/autonomous_pidog.py --interactive
```

### Conversation Modes

PiDog supports two modes for more natural conversations without repeating the wake word:

**Timeout Mode** - Stay listening for X seconds after each response:
```bash
sudo -E python3 ~/examples/autonomous_pidog.py --conversation-mode timeout --conversation-timeout 20
```

**VAD Mode** - Keep listening until silence is detected:
```bash
sudo -E python3 ~/examples/autonomous_pidog.py --conversation-mode vad --vad-silence 3
```

Both modes end when:
- Timeout/silence threshold reached
- User says "bye", "thanks", "goodbye", etc.

### Calibration (on Pi, requires interactive terminal)

```bash
cd ~/pidog/examples && python3 0_calibration.py
```

### Deploying Code to Pi

```bash
sshpass -p '12345' scp -r pidog_brain zadie@pidog.local:~/
sshpass -p '12345' scp -r examples zadie@pidog.local:~/
```

## Raspberry Pi Process Management

**Never use `kill -9` directly on stuck PiDog/GPIO processes.**

Using SIGKILL on processes holding GPIO locks can corrupt the SD card:
- SIGKILL terminates without cleanup
- Open file handles don't flush
- Raspberry Pi SD cards are especially vulnerable

**Recovery procedure:**
1. Try `Ctrl+C` to exit cleanly (preferred)
2. If stuck, use the cleanup script:
   ```bash
   sudo python3 ~/pidog/brain/cleanup.py
   ```
   This kills processes AND releases GPIO pins properly.
3. Check status: `sudo python3 ~/pidog/brain/cleanup.py status`
4. If cleanup.py doesn't work, **power cycle the Pi** as last resort

**Signs of SD card corruption:**
- Solid green activity LED (not blinking) after boot
- Pi not appearing on network after reboot

## SSH Connection Details

- Hostname: `pidog.local` or `pidog.lan` (depends on network)
- User: `zadie`
- Password: `12345`
- Fallback: `arp -a | grep pidog` to find IP

## Environment Variables

- `ANTHROPIC_API_KEY` - Required for Claude brain (stored in `~/.config/pidog/.env`)

## Fresh Install Setup (Autonomous Mode)

After a fresh Raspberry Pi OS install, run these steps:

### 1. Base System
```bash
sudo apt update && sudo apt install -y git python3-pip python3-setuptools python3-smbus
```

### 2. Vendor Libraries
```bash
# robot-hat
cd ~/ && git clone -b v2.0 https://github.com/sunfounder/robot-hat.git
cd robot-hat && sudo python3 setup.py install

# vilib (camera)
cd ~/ && git clone -b picamera2 https://github.com/sunfounder/vilib.git
cd vilib && sudo python3 install.py

# pidog
cd ~/ && git clone https://github.com/sunfounder/pidog.git
cd pidog && pip3 install --break-system-packages .
```

### 3. I2S Audio
```bash
cd ~/pidog && sudo bash i2samp.sh
# Reboot after
```

### 4. Voice Assistant Dependencies
```bash
# sunfounder_voice_assistant (copy from local project or download)
sudo cp -r ~/sunfounder_voice_assistant /usr/local/lib/python3.13/dist-packages/

# robot_hat voice_assistant module
sudo cp ~/voice_assistant.py /usr/local/lib/python3.13/dist-packages/robot_hat/

# Python packages
sudo pip3 install --break-system-packages sounddevice vosk piper-tts anthropic
```

### 5. API Key Setup
```bash
mkdir -p ~/.config/pidog
echo 'ANTHROPIC_API_KEY=sk-ant-...' > ~/.config/pidog/.env
chmod 600 ~/.config/pidog/.env
```

### 6. Deploy Brain Code (from Mac)
```bash
sshpass -p '12345' scp -r pidog_brain zadie@pidog.local:~/
sshpass -p '12345' scp -r examples zadie@pidog.local:~/
sshpass -p '12345' scp downloaded_code/pidog/brain/cleanup.py zadie@pidog.local:~/pidog/brain/
```

### 7. Calibrate Servos
```bash
cd ~/pidog/examples && python3 0_calibration.py
```

### 8. Vision Dependencies
```bash
# Face recognition (dlib takes ~40 minutes to build)
sudo apt install -y cmake
sudo pip3 install --break-system-packages face_recognition
```

### 9. Set Up Overlay Filesystem (SD Card Protection)

**Before enabling overlay**, ensure all software is installed.

```bash
# Create data partition (if not already done during imaging)
# Use fdisk to shrink root to 16GB and create partition 3 with remaining space
# Format: sudo mkfs.ext4 -L pidog_data /dev/mmcblk0p3

# Create mount point and systemd mount unit
sudo mkdir -p /mnt/data
cat << 'EOF' | sudo tee /etc/systemd/system/mnt-data.mount
[Unit]
Description=PiDog Data Partition
DefaultDependencies=no
After=systemd-fsck@dev-mmcblk0p3.service
Before=local-fs.target

[Mount]
What=/dev/mmcblk0p3
Where=/mnt/data
Type=ext4
Options=defaults,noatime

[Install]
WantedBy=local-fs.target
EOF

sudo systemctl enable mnt-data.mount
sudo systemctl start mnt-data.mount

# Create pidog data directory
sudo mkdir -p /mnt/data/pidog
sudo chown zadie:zadie /mnt/data/pidog

# Move memory and personality to data partition
mv ~/pidog_brain/memory.db /mnt/data/pidog/ 2>/dev/null || true
mv ~/pidog_brain/personality.json /mnt/data/pidog/ 2>/dev/null || true

# Create symlinks
ln -sf /mnt/data/pidog/memory.db ~/pidog_brain/memory.db
ln -sf /mnt/data/pidog/personality.json ~/pidog_brain/personality.json

# Enable overlay filesystem
sudo sed -i 's/overlayroot=""/overlayroot="tmpfs:recurse=0"/' /etc/overlayroot.conf
sudo reboot
```

### 10. Run
```bash
sudo -E python3 ~/examples/autonomous_pidog.py

# With conversation timeout
sudo -E python3 ~/examples/autonomous_pidog.py --conversation-mode timeout --conversation-timeout 20
```

## Known Limitations

### Person Tracking Disabled (Python 3.13)

The `person_tracker.py` module requires `tflite-runtime` for MobileNet-SSD inference, but tflite-runtime only has pre-built wheels for Python 3.8-3.11. Raspberry Pi OS (Bookworm) ships with Python 3.13.

**Current status:** Person tracking logs errors but doesn't crash. Face recognition works.

**Workarounds (not yet implemented):**
- Build tflite-runtime from source
- Use a Python 3.11 virtual environment (complex with sudo/hardware access)
- Wait for official Python 3.13 support

**Impact:** The dog cannot track people by body detection, only by face recognition.

### Camera Architecture

The camera is owned by `VoiceAssistant` (via picamera2). Vision components access frames through `CameraPool`, which shares the same picamera2 instance. This avoids conflicts but means:
- Camera format is XBGR8888 (VoiceAssistant's choice)
- CameraPool converts to BGR for OpenCV/face_recognition compatibility
- Vision cannot run if VoiceAssistant isn't started

## Claude Response Format

When working with Claude's responses in this codebase, the expected format is:

```
Speech text here (what PiDog says)
ACTIONS: wag tail, nod, forward
TOOL: remember {"category": "person", "subject": "Joe", "content": "Likes fetch"}
TOOL: set_goal {"description": "Learn tricks", "priority": 3}
```

## SD Card Protection (Overlay Filesystem)

PiDog uses an overlay filesystem to protect the SD card from corruption. The root filesystem is read-only with a RAM overlay, while persistent data lives on a separate writable partition.

### Partition Layout

| Partition | Size | Mount Point | Purpose |
|-----------|------|-------------|---------|
| mmcblk0p1 | 512MB | /boot/firmware | Boot files (FAT32) |
| mmcblk0p2 | 16GB | / (overlay) | Root OS (read-only + RAM overlay) |
| mmcblk0p3 | ~103GB | /mnt/data | Persistent data (writable) |

### How It Works

- Root filesystem changes go to RAM and disappear on reboot
- Memory database and personality are symlinked to /mnt/data/pidog/
- Crashes or power loss won't corrupt the OS
- Data partition persists all writes

### Persistent Data Locations

```
/mnt/data/pidog/
├── memory.db        # SQLite memory database
└── personality.json # Personality traits

~/pidog_brain/
├── memory.db -> /mnt/data/pidog/memory.db        # Symlink
└── personality.json -> /mnt/data/pidog/personality.json  # Symlink
```

### Updating PiDog Code (Normal Updates)

Code updates don't require disabling the overlay - just deploy and restart:

```bash
# From Mac - deploy updated code
sshpass -p '12345' scp -r pidog_brain/* zadie@pidog.lan:~/pidog_brain/
sshpass -p '12345' scp -r examples/* zadie@pidog.lan:~/examples/

# The code runs from RAM overlay, so changes work immediately
# But they'll be lost on reboot unless you also update the base filesystem
```

### Permanent System Changes (Installing Packages, Config Changes)

To make changes that survive reboot, use `overlayroot-chroot`:

```bash
ssh zadie@pidog.lan

# Enter the real root filesystem
sudo overlayroot-chroot

# Now you're in the actual filesystem - make changes
apt install some-package
pip3 install --break-system-packages some-python-package

# Edit config files, etc.
exit

# Reboot to apply
sudo reboot
```

### Deploying Code Permanently

To update pidog_brain code permanently (survives reboot):

```bash
# Option 1: Use overlayroot-chroot
ssh zadie@pidog.lan
sudo overlayroot-chroot
# Then copy files within the chroot

# Option 2: Deploy from Mac directly to the underlying filesystem
sshpass -p '12345' ssh zadie@pidog.lan "sudo overlayroot-chroot cp -r /home/zadie/pidog_brain/* /home/zadie/pidog_brain/"
```

### Disabling Overlay (Temporarily)

If you need full read-write access for major changes:

```bash
sudo overlayroot-chroot
sed -i 's/overlayroot="tmpfs:recurse=0"/overlayroot=""/' /etc/overlayroot.conf
exit
sudo reboot

# Make your changes...

# Re-enable overlay when done
sudo sed -i 's/overlayroot=""/overlayroot="tmpfs:recurse=0"/' /etc/overlayroot.conf
sudo reboot
```

### Backup Important Data

The data partition contains PiDog's memories. To backup:

```bash
# From Mac
sshpass -p '12345' scp zadie@pidog.lan:/mnt/data/pidog/memory.db ~/pidog_backup/
sshpass -p '12345' scp zadie@pidog.lan:/mnt/data/pidog/personality.json ~/pidog_backup/
sshpass -p '12345' scp zadie@pidog.lan:~/calibration_offsets.txt ~/pidog_backup/
sshpass -p '12345' scp zadie@pidog.lan:~/.config/pidog/.env ~/pidog_backup/
```

### Restoring After Reimage

If you need to reimage the SD card:

1. Use Raspberry Pi Imager with custom partition layout (16GB root, rest for data)
2. After first boot, create data partition and mount unit
3. Restore backups:
   ```bash
   # Config and API key
   sshpass -p '12345' ssh zadie@pidog.lan "mkdir -p ~/.config/pidog"
   sshpass -p '12345' scp ~/pidog_backup/env_backup zadie@pidog.lan:~/.config/pidog/.env
   sshpass -p '12345' scp ~/pidog_backup/pidog.conf zadie@pidog.lan:~/.config/pidog/
   sshpass -p '12345' scp ~/pidog_backup/calibration_offsets.txt zadie@pidog.lan:~/

   # Memory and personality (to data partition)
   sshpass -p '12345' scp ~/pidog_backup/memory.db zadie@pidog.lan:/mnt/data/pidog/
   sshpass -p '12345' scp ~/pidog_backup/personality.json zadie@pidog.lan:/mnt/data/pidog/
   ```
4. Create symlinks and enable overlay (see Fresh Install Setup)

## Available Slash Commands

- `/pidog start` - Start Claude brain on PiDog
- `/pidog stop` - Stop PiDog and cleanup GPIO
- `/pidog status` - Check if PiDog processes are running
- `/code-pidog` - Show PiDog API reference for writing robot control code
