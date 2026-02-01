---
description: Control PiDog robot - start brain, stop, check status
argument-hint: start | stop | status
allowed-tools: Bash(sshpass:*)
---

# PiDog Control Command

Control the PiDog robot brain remotely from your Mac.

## Commands

- `start` - Start Claude brain on PiDog (requires ANTHROPIC_API_KEY env var)
- `stop` - Stop PiDog and cleanup GPIO
- `status` - Check if PiDog processes are running

## Connection Details

- Host: `pidog.local`
- User: `zadie`
- Password: `12345`

## Implementation

Based on the argument provided ($ARGUMENTS), execute the appropriate action:

### For `start`:
```bash
sshpass -p '12345' ssh -o StrictHostKeyChecking=no zadie@pidog.local \
  "cd /home/zadie/pidog/examples && ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY sudo -E python3 claude_pidog.py"
```

Note: This will run in the foreground. The user should use Ctrl+C to stop or run in background.

### For `stop`:
```bash
sshpass -p '12345' ssh -o StrictHostKeyChecking=no zadie@pidog.local \
  "sudo python3 /home/zadie/pidog/brain/cleanup.py"
```

### For `status`:
```bash
sshpass -p '12345' ssh -o StrictHostKeyChecking=no zadie@pidog.local \
  "sudo python3 /home/zadie/pidog/brain/cleanup.py status"
```

## Prerequisites

1. `sshpass` must be installed on Mac: `brew install sshpass` or `brew install hudochenkov/sshpass/sshpass`
2. `ANTHROPIC_API_KEY` environment variable must be set for the `start` command
3. PiDog must be powered on and connected to the same network

## Example Usage

```
/pidog status    # Check if running
/pidog start     # Start Claude brain (requires API key)
/pidog stop      # Stop and cleanup
```
