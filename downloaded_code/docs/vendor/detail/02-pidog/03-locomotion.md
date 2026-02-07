# pidog: Locomotion

<!-- Status: COMPLETE | Iteration: 1 -->

> Covers: `walk.py` (123 lines), `trot.py` (171 lines)

## Purpose

The locomotion system generates smooth quadruped gait patterns. `Walk` implements a slow 8-section alternating gait (one leg at a time). `Trot` implements a fast 2-section diagonal gait (two legs simultaneously). Both generate cartesian foot positions that feed into inverse kinematics.

## API Reference

### Walk Class (walk.py:22)

Implements walk gait with 8 sections, 6 steps per section (48 total frames per cycle).

#### Class Constants

```python
FORWARD = 1
BACKWARD = -1
LEFT = -1
STRAIGHT = 0
RIGHT = 1

SECTION_COUNT = 8
STEP_COUNT = 6
LEG_ORDER = [1, 0, 4, 0, 2, 0, 3, 0]  # 0 = break, 1-4 = leg index+1
LEG_STEP_HEIGHT = 20  # mm, lift height
LEG_STEP_WIDTH = 80   # mm, stride length
CENTER_OF_GRAVIRTY = -15  # mm, body COM offset
LEG_POSITION_OFFSETS = [-10, -10, 20, 20]  # mm, per-leg forward/back bias
Z_ORIGIN = 80  # mm, standing height

TURNING_RATE = 0.3  # 0.0-1.0, turning stride scale
LEG_STEP_SCALES_LEFT = [TURNING_RATE, 1, TURNING_RATE, 1]    # LH, LF, RH, RF
LEG_STEP_SCALES_MIDDLE = [1, 1, 1, 1]
LEG_STEP_SCALES_RIGHT = [1, TURNING_RATE, 1, TURNING_RATE]
LEG_STEP_SCALES = [LEG_STEP_SCALES_LEFT, LEG_STEP_SCALES_MIDDLE, LEG_STEP_SCALES_RIGHT]
LEG_ORIGINAL_Y_TABLE = [0, 2, 3, 1]  # Initial leg Y offset multipliers
```

#### `__init__(fb, lr)` (walk.py:47)

Initialize walk gait generator.

**Parameters**:
- `fb` (int): Forward/backward direction. `FORWARD` (1) or `BACKWARD` (-1)
- `lr` (int): Left/right turning. `LEFT` (-1), `STRAIGHT` (0), or `RIGHT` (1)

**Side effects**:
- Computes per-leg stride widths, section lengths, step lengths based on direction and turning rate
- Sets `y_offset` based on direction and turning (COM shift)

**Thread-safe**: Yes (no shared state)

---

#### `get_coords()` (walk.py:94)

Generate complete walk cycle coordinates.

**Returns**: List of 193 coordinate lists. Each coordinate list contains 4 leg positions `[[y1,z1], [y2,z2], [y3,z3], [y4,z4]]` in mm.

**Thread-safe**: Yes

**Notes**:
- Leg order: [LH, LF, RH, RF] (left-hind, left-front, right-hind, right-front)
- Y-axis: forward(+) / backward(-)
- Z-axis: up(-) / down(+) relative to body (inverted from standard)
- 8 sections × 6 steps/section = 48 frames
- Plus 4 sections × 6 steps × 4 breaks (leg=0) = 144 frames
- Plus 1 final frame returning to origin = 193 total frames

**Example**:
```python
walk = Walk(fb=Walk.FORWARD, lr=Walk.STRAIGHT)
coords = walk.get_coords()  # 193 frames
# Convert to angles
angles_list = [Pidog.legs_angle_calculation(coord) for coord in coords]
```

---

#### `step_y_func(leg, step)` (walk.py:78)

Compute Y position of stepping leg using cosine function.

**Parameters**:
- `leg` (int): Leg index 0-3 (LH, LF, RH, RF)
- `step` (int): Step index 0-5

**Returns**: float, Y position in mm

**Thread-safe**: Yes (pure function)

**Formula**:
```
y = leg_origin + (leg_step_width × (cos(θ) - fb) / 2 × fb)
where θ = step × π / (STEP_COUNT - 1)
```

**Notes**: Cosine creates smooth acceleration/deceleration (ease-in/out)

---

#### `step_z_func(step)` (walk.py:91)

Compute Z position of stepping leg using linear interpolation.

**Parameters**:
- `step` (int): Step index 0-5

**Returns**: float, Z position in mm

**Thread-safe**: Yes (pure function)

**Formula**:
```
z = Z_ORIGIN - (LEG_STEP_HEIGHT × step / (STEP_COUNT - 1))
```

**Notes**: Linear function creates constant vertical velocity

---

### Trot Class (trot.py:24)

Implements trot gait with 2 sections, 3 steps per section (6 total frames per cycle). Faster than walk, uses diagonal leg pairs.

#### Class Constants

```python
FORWARD = 1
BACKWARD = -1
LEFT = -1
STRAIGHT = 0
RIGHT = 1

SECTION_COUNT = 2
STEP_COUNT = 3
LEG_RAISE_ORDER = [[1, 4], [2, 3]]  # Section 0: legs 1+4, Section 1: legs 2+3 (diagonal pairs)
LEG_STEP_HEIGHT = 20  # mm
LEG_STEP_WIDTH = 100  # mm, larger stride than walk
CENTER_OF_GRAVITY = -17  # mm, shifted back vs walk
LEG_STAND_OFFSET = 5  # mm, leg stance width
Z_ORIGIN = 80  # mm

TURNING_RATE = 0.5  # Higher than walk (0.5 vs 0.3)
LEG_STAND_OFFSET_DIRS = [-1, -1, 1, 1]  # LH, LF, RH, RF (front legs forward, hind back)
LEG_STEP_SCALES_LEFT = [TURNING_RATE, 1, TURNING_RATE, 1]
LEG_STEP_SCALES_MIDDLE = [1, 1, 1, 1]
LEG_STEP_SCALES_RIGHT = [1, TURNING_RATE, 1, TURNING_RATE]
LEG_ORIGINAL_Y_TABLE = [0, 1, 1, 0]  # Initial Y offsets (front legs forward 1 section)
LEG_STEP_SCALES = [LEG_STEP_SCALES_LEFT, LEG_STEP_SCALES_MIDDLE, LEG_STEP_SCALES_RIGHT]
```

#### `__init__(fb, lr)` (trot.py:50)

Initialize trot gait generator.

**Parameters**:
- `fb` (int): Forward/backward direction. `FORWARD` (1) or `BACKWARD` (-1)
- `lr` (int): Left/right turning. `LEFT` (-1), `STRAIGHT` (0), or `RIGHT` (1)

**Side effects**:
- Computes per-leg stride widths, section lengths, step lengths
- Applies `LEG_STAND_OFFSET` (front legs forward, hind back)
- Sets `y_offset` with different values vs walk (tuned for trot stability)

**Thread-safe**: Yes

---

#### `get_coords()` (trot.py:99)

Generate complete trot cycle coordinates.

**Returns**: List of 6 coordinate lists. Each contains 4 leg positions `[[y1,z1], [y2,z2], [y3,z3], [y4,z4]]` in mm.

**Thread-safe**: Yes

**Notes**:
- 2 sections × 3 steps/section = 6 frames (much fewer than walk's 193)
- Diagonal pairs lift simultaneously (legs 1+4, then legs 2+3)
- Leg order: [LH, LF, RH, RF]
- Y-axis: forward(+) / backward(-)
- Z-axis: up(-) / down(+) relative to body

**Example**:
```python
trot = Trot(fb=Trot.FORWARD, lr=Trot.STRAIGHT)
coords = trot.get_coords()  # 6 frames
angles_list = [Pidog.legs_angle_calculation(coord) for coord in coords]
```

---

#### `step_y_func(leg, step)` (trot.py:83)

Compute Y position of stepping leg using cosine function.

**Parameters**:
- `leg` (int): Leg index 0-3
- `step` (int): Step index 0-2

**Returns**: float, Y position in mm

**Thread-safe**: Yes (pure function)

**Formula**: Same as Walk (cosine ease-in/out)

---

#### `step_z_func(step)` (trot.py:96)

Compute Z position of stepping leg using linear interpolation.

**Parameters**:
- `step` (int): Step index 0-2

**Returns**: float, Z position in mm

**Thread-safe**: Yes (pure function)

**Formula**: Same as Walk (linear vertical motion)

---

## Gait Parameters

### Walk Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `fb` | - | FORWARD (1), BACKWARD (-1) | Direction |
| `lr` | - | LEFT (-1), STRAIGHT (0), RIGHT (1) | Turning |
| `SECTION_COUNT` | 8 | Fixed | Number of gait sections (4 legs × 2 breaks each) |
| `STEP_COUNT` | 6 | Fixed | Frames per section (smooth motion) |
| `LEG_STEP_HEIGHT` | 20 mm | Configurable | Vertical lift during step |
| `LEG_STEP_WIDTH` | 80 mm | Configurable | Horizontal stride length |
| `CENTER_OF_GRAVIRTY` | -15 mm | Configurable | Body COM forward/back offset |
| `Z_ORIGIN` | 80 mm | Fixed | Standing height |
| `TURNING_RATE` | 0.3 | 0.0-1.0 | Inside leg stride scale during turns |

**Effective speeds**:
- Forward straight: 80mm × 1 stride / 193 frames = 0.41 mm/frame
- Turn left: Outside legs 80mm, inside legs 24mm (30% of 80mm)

### Trot Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `fb` | - | FORWARD (1), BACKWARD (-1) | Direction |
| `lr` | - | LEFT (-1), STRAIGHT (0), RIGHT (1) | Turning |
| `SECTION_COUNT` | 2 | Fixed | Number of gait sections (2 diagonal pairs) |
| `STEP_COUNT` | 3 | Fixed | Frames per section (fast motion) |
| `LEG_STEP_HEIGHT` | 20 mm | Configurable | Vertical lift during step |
| `LEG_STEP_WIDTH` | 100 mm | Configurable | Horizontal stride length (larger than walk) |
| `CENTER_OF_GRAVITY` | -17 mm | Configurable | Body COM offset (more rearward than walk) |
| `Z_ORIGIN` | 80 mm | Fixed | Standing height |
| `TURNING_RATE` | 0.5 | 0.0-1.0 | Inside leg stride scale during turns (higher than walk) |

**Effective speeds**:
- Forward straight: 100mm × 1 stride / 6 frames = 16.67 mm/frame
- **40× faster than walk** (16.67 / 0.41 = 40.7)

---

## IK Constants

Both Walk and Trot use these constants from `Pidog` class:

| Constant | Value | Description |
|----------|-------|-------------|
| `LEG` | 42 mm | Upper leg segment length |
| `FOOT` | 76 mm | Lower leg segment length |
| `BODY_LENGTH` | 117 mm | Body length (front to back) |
| `BODY_WIDTH` | 98 mm | Body width (left to right) |

**Leg reach**:
- Maximum extension: `LEG + FOOT = 118 mm`
- Minimum extension: `abs(LEG - FOOT) = 34 mm`
- Default standing height: `Z_ORIGIN = 80 mm` (well within range)

**Workspace**:
- Y-axis (forward/back): Limited by body length and collision
- Z-axis (height): 34mm (fully retracted) to 118mm (fully extended)

---

## Implementation Notes

### Walk Gait Algorithm

**Cycle Structure**:
```
Section | Leg Moving | Other Legs | Duration
--------|------------|------------|----------
   0    | None       | All ground | 6 frames (break)
   1    | Leg 1 (LH) | 3 ground   | 6 frames
   2    | None       | All ground | 6 frames (break)
   3    | Leg 4 (RF) | 3 ground   | 6 frames
   4    | None       | All ground | 6 frames (break)
   5    | Leg 2 (LF) | 3 ground   | 6 frames
   6    | None       | All ground | 6 frames (break)
   7    | Leg 3 (RH) | 3 ground   | 6 frames
```

**Leg Order**: `LEG_ORDER = [1, 0, 4, 0, 2, 0, 3, 0]` (1-indexed, 0 = break)

**Ground Contact**: Always 3 or 4 legs on ground (stable)

**Y-coordinate Motion**:
- Stepping leg: Cosine wave (ease-in/out), travels `LEG_STEP_WIDTH` mm
- Ground legs: Linear motion, drag back `LEG_STEP_WIDTH / (SECTION_COUNT - 1)` per section
- Net result: Body moves forward while legs "pedal" backward

**Z-coordinate Motion**:
- Stepping leg: Linear rise to `Z_ORIGIN - LEG_STEP_HEIGHT`, then linear return
- Ground legs: Fixed at `Z_ORIGIN`

---

### Trot Gait Algorithm

**Cycle Structure**:
```
Section | Legs Moving   | Other Legs | Duration
--------|---------------|------------|----------
   0    | 1,4 (LH, RF)  | 2,3 ground | 3 frames (diagonal pair)
   1    | 2,3 (LF, RH)  | 1,4 ground | 3 frames (diagonal pair)
```

**Leg Pairs**: `LEG_RAISE_ORDER = [[1, 4], [2, 3]]` (1-indexed)

**Ground Contact**: Always 2 legs on ground (diagonal pair, stable if balanced)

**Y-coordinate Motion**:
- Stepping pair: Cosine wave, travels `LEG_STEP_WIDTH` mm
- Ground pair: Linear drag, travels `LEG_STEP_WIDTH / (SECTION_COUNT - 1)` per section
- Net result: Body moves forward ~2× faster than walk per frame

**Z-coordinate Motion**:
- Same as walk (linear rise/fall)

**Difference from Walk**:
- 2 legs lift simultaneously (diagonal) vs 1 leg (walk)
- Larger stride (100mm vs 80mm)
- Fewer frames (6 vs 193)
- Higher turning rate (0.5 vs 0.3)
- Shifted COM (-17mm vs -15mm)

---

### Leg Sequencing

**Walk Sequencing** (alternating tetrapod):
```
Time: 0--6--12-18-24-30-36-42-48 (frames)
LH:   ^^^---------
LF:   ---------^^^------
RH:   ---------------^^^------
RF:   ---^^^------------
```

**Trot Sequencing** (diagonal):
```
Time: 0-3-6 (frames)
LH:   ^^^---
LF:   ---^^^
RH:   ---^^^
RF:   ^^^---
```

**Leg Index Mapping**:
- Leg 1 = Left Hind (LH) = indices [0, 1] (upper, lower)
- Leg 2 = Left Front (LF) = indices [2, 3]
- Leg 3 = Right Hind (RH) = indices [4, 5]
- Leg 4 = Right Front (RF) = indices [6, 7]

---

### Speed Control

**Frame rate** is controlled by `speed` parameter in `Pidog.do_action()`:
```python
dog.do_action('forward', speed=50)  # Slower
dog.do_action('forward', speed=100) # Faster
```

**Speed affects inter-frame delay**:
- `speed=100`: Minimum delay (~5ms + servo DPS limit)
- `speed=50`: Medium delay (~30ms)
- `speed=0`: Maximum delay (~50ms)

**Stride speed** is fixed by gait parameters:
- Walk: 80mm stride / 193 frames = 0.41 mm/frame (at execution speed)
- Trot: 100mm stride / 6 frames = 16.67 mm/frame (at execution speed)

**Turning speed** is scaled by `TURNING_RATE`:
- Walk turning: Inside legs move 30% of stride (0.3 × 80mm = 24mm)
- Trot turning: Inside legs move 50% of stride (0.5 × 100mm = 50mm)

**Real-world speeds** (at speed=100, assuming ~10ms/frame):
- Walk: 0.41 mm/frame × 100 frames/sec = 41 mm/sec = 4.1 cm/sec
- Trot: 16.67 mm/frame × 100 frames/sec = 1667 mm/sec = 166.7 cm/sec (theoretical, servo-limited)

**Actual speeds are servo-limited** by `LEGS_DPS = 428°/sec`, not by gait algorithm.

---

## Code Patterns

### Pattern 1: Generate Walk Gait

```python
from pidog.walk import Walk
from pidog import Pidog

# Create walk generator
walk = Walk(fb=Walk.FORWARD, lr=Walk.STRAIGHT)
coords = walk.get_coords()  # 193 frames

# Convert to angles
angles_list = [Pidog.legs_angle_calculation(coord) for coord in coords]

# Execute
dog = Pidog()
dog.legs_move(angles_list, immediately=True, speed=90)
dog.wait_legs_done()
```

### Pattern 2: Generate Trot Gait

```python
from pidog.trot import Trot
from pidog import Pidog

# Create trot generator
trot = Trot(fb=Trot.FORWARD, lr=Trot.STRAIGHT)
coords = trot.get_coords()  # 6 frames

# Convert to angles
angles_list = [Pidog.legs_angle_calculation(coord) for coord in coords]

# Execute
dog = Pidog()
dog.legs_move(angles_list, immediately=True, speed=98)
dog.wait_legs_done()
```

### Pattern 3: Turning

```python
# Walk turning left
walk_left = Walk(fb=Walk.FORWARD, lr=Walk.LEFT)
coords = walk_left.get_coords()
angles = [Pidog.legs_angle_calculation(c) for c in coords]

dog.legs_move(angles, speed=80)
```

### Pattern 4: Use ActionDict (Easier)

```python
# ActionDict already wraps Walk/Trot
dog.do_action('forward', step_count=3, speed=90)  # 3 walk cycles
dog.do_action('trot', step_count=2, speed=98)     # 2 trot cycles
```

---

## Gotchas

1. **Walk is NOT 48 Frames**: Walk has 8 sections × 6 steps = 48 moving frames, but `get_coords()` returns 193 frames because it includes breaks (0-movement frames) and interpolation. Use returned list length, not computed SECTION_COUNT × STEP_COUNT.

2. **Trot is Unstable at Low Speed**: Trot requires fast execution (speed >80) to maintain stability. At low speeds, the robot may tip during diagonal stance phases.

3. **Leg Index is 1-Based in Code**: `LEG_ORDER = [1, 0, 4, 0, 2, 0, 3, 0]` uses 1-based indexing (leg 1 = first leg). Must subtract 1 when indexing into coord arrays: `raise_leg = LEG_ORDER[section]; if raise_leg != 0 and i == raise_leg - 1:`.

4. **Y-Axis is Inverted**: In gait code, forward = positive Y. But in standard robotics, forward = negative Y (towards nose). This is intentional — IK handles the conversion.

5. **Z-Axis is Inverted**: In gait code, down = positive Z (larger Z = foot lower). Standard robotics uses up = positive Z. Again, IK handles conversion.

6. **Turning Modifies Stride Width**: Setting `lr != STRAIGHT` scales per-leg stride width via `LEG_STEP_SCALES`. Inside legs move less, outside legs move more (or same). This creates turning motion, not yaw rotation.

7. **Backwards is NOT Reverse Playback**: `fb=BACKWARD` recomputes all coordinates, not just reverses forward sequence. Leg order changes: `LEG_ORDER[SECTION_COUNT - section - 1]`.

8. **Center of Gravity Shifts with Direction**: `y_offset` changes based on `fb` and `lr`. This shifts body weight to maintain balance. Forward/backward/turning each have different offsets.

9. **No Smooth Transitions Between Gaits**: Switching from walk to trot requires stopping (returning to stand), then starting new gait. No built-in transition animations.

10. **Frame Count Differs by Gait**: Walk returns 193 frames, trot returns 6 frames. If looping gaits, ensure you know which gait you're using. Code like `while True: dog.legs_move(coords)` will execute walk ~32× slower than trot per iteration.
