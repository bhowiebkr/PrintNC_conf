# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains LinuxCNC configuration files for Howard's PrintNC CNC machine. The machine uses:
- Mesa 7i76e Ethernet I/O card
- QtDragon HD GUI interface
- 3-axis gantry configuration (X, Y with dual motors Y/Y2, Z)
- Manual tool changes (no ATC - requires manual endmill/collet changes)
- Tool height sensor at machine coordinates X354.5, Y368.9
- 2.2kW spindle with VFD control

## Key Configuration Files

### Main Configuration
- `PrintNC/PrintNC.ini` - Primary INI configuration defining machine parameters, axis limits, velocities, and UI settings
- `PrintNC/PrintNC.hal` - HAL (Hardware Abstraction Layer) configuration connecting physical I/O to LinuxCNC internals
- `PrintNC/custom.hal` - Custom HAL components and connections
- `PrintNC/custom_postgui.hal` - HAL connections made after GUI loads

### Tool Management
- `PrintNC/tool.tbl` - Tool table defining tool offsets and parameters
- `PrintNC/subroutines/tool-change.ngc` - Automatic tool height measurement subroutine (M6 remap)
- `PrintNC/subroutines/tool-job-begin.ngc` - Job initialization subroutine (M600 remap)
- Tool height sensor is configured in the HAL files
- Manual tool changes with automatic Z offset compensation via tool sensor probing

### UI Configuration
- `PrintNC/qtdragon_hd/` - QtDragon HD interface customizations
- `PrintNC/qtdragon_hd/qtdragon_hd_handler.py` - Python handler for custom UI behavior
- `PrintNC/qtdragon.pref` - UI preferences (excluded from git)

## Calculation Scripts

Located in `PrintNC/Misc/`:
- `step_calc.py` - Calculates step scale for stepper motor configuration based on pulleys and ball screw pitch
- `servo_settings_calc.py` - Calculates electronic gear ratio for servo motor configuration

Run these scripts directly with Python:
```bash
python3 PrintNC/Misc/step_calc.py
python3 PrintNC/Misc/servo_settings_calc.py
```

## Machine Specifications

From the configuration files:
- Board IP: 10.10.10.10 (Mesa 7i76e)
- Axes: X, Y (with gantry Y2), Z
- Spindle: 1000-24000 RPM range
- Home/limit switches connected to Mesa 7i76 inputs
- 5 stepgens configured (X, Y, Y2, Z, and formerly W axis)

## Working with HAL Files

When editing HAL files:
1. Comments start with `#`
2. Signal names use hyphens (e.g., `min-home-x`)
3. Pin names use dots (e.g., `hm2_7i76e.0.7i76.0.0.input-04`)
4. Always verify connections match physical wiring

## Working with INI Files

INI file sections:
- `[EMC]` - General machine info
- `[DISPLAY]` - UI configuration
- `[AXIS_*]` and `[JOINT_*]` - Axis/joint specific parameters
- `[SPINDLE_*]` - Spindle configuration
- `[HAL]` - HAL file loading order

## CRITICAL RULES

### DO NOT touch code when the user is asking a question
- If the user is asking a question, ONLY answer the question. Do not edit files. Do not commit.
- "Tell me what's wrong", "what happened", "check this", "is this right" — these are questions. ONLY respond with text.
- Only edit code when given explicit action instructions like "fix it", "change it", "do it", "commit".
- This is a CNC machine. Bad code wastes expensive material and can damage the machine.
- When in doubt whether the user wants an answer or an action, ASK. Do not assume.

### Verify G-code math before committing
- Always verify Z depths, offsets, and tool compensation math with actual numbers before committing.
- Walk through the calculations with real values (e.g., board_z=16.6, surface_depth=0.5, tool_dia=6).
- A finishing pass must cut to the TARGET depth, not deeper. Roughing leaves material, finishing removes it to target.
- Never go negative on X or Y unless explicitly intended — G54 origin is at the workpiece corner.

### G-code safety
- Always use G1 (not G0) for plunge moves into material.
- Use G53 Z-5 for safe machine-absolute travel between operations.
- No nested parentheses in G-code comments — LinuxCNC parser will error.
- Always include G90 (absolute positioning) at program start.
- Add G4 P2 dwell after M3 spindle start.
- Climb cutting only (with M3 CW spindle). Never alternate between climb and conventional.

### LinuxCNC G-code format
- Programs must start and end with `%` markers.
- No nested parentheses in comments: use `(--- MILL +X END - end grain ---)` not `(--- MILL +X END (end grain) ---)`.

## Git Workflow

- Main branch: `main`
- Feature branches should be created for configuration changes
- Use descriptive commit messages explaining configuration changes
- The `.gitignore` excludes temporary files, backups, and UI preferences

## Testing Changes

After making configuration changes:
1. LinuxCNC will validate HAL and INI syntax on startup
2. Test homing sequences for all axes
3. Verify spindle control and speed ranges
4. Check tool change procedures if modified
5. Test any custom UI functionality changes

## Common Tasks

### Modifying axis parameters
Edit the appropriate `[JOINT_*]` and `[AXIS_*]` sections in `PrintNC.ini`

### Adding/removing HAL components
Edit `PrintNC.hal` and ensure proper loading order in the INI file's `[HAL]` section

### Adjusting step scales
Use the calculation scripts in `PrintNC/Misc/` to determine correct values, then update in INI file

### UI customizations
Modify `PrintNC/qtdragon_hd/qtdragon_hd_handler.py` for behavior changes

### Manual Tool Change Workflow
1. Touch off workpiece X, Y, Z with reference tool to set G54
2. Run `M600` in MDI to reset tool measurement system
3. Run `M6 Tx` with reference tool to establish baseline height
4. During program execution, each `M6` command will:
   - Move to tool change position (X300, Y30)
   - Pause for manual tool/collet change
   - Automatically probe new tool at sensor location (X354.5, Y368.9)
   - Calculate and apply Z offset relative to reference tool
   - Return to work with correct Z compensation