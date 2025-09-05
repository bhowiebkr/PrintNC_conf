# Complete Guide to Manual Tool Changes with Automatic Height Compensation

## Overview

This PrintNC CNC machine uses a **manual tool change system** with **automatic tool height measurement**. This means:
- You physically change tools by hand (no automatic tool changer)
- The machine automatically measures each tool's length using a tool sensor
- Z-axis offsets are calculated and applied automatically
- You never need to manually measure or enter tool lengths

## How It Works

The system uses a fixed tool sensor located at:
- **X: 354.5mm** (machine coordinates)
- **Y: 368.9mm** (machine coordinates)

When you change tools, the machine:
1. Moves to a convenient tool change position
2. Waits for you to manually change the tool
3. Automatically probes the new tool on the sensor
4. Calculates the height difference from your reference tool
5. Applies the correct Z offset
6. Returns to work with perfect Z height

## Prerequisites

### 1. Physical Setup
- Tool sensor must be installed and connected
- Sensor position must match configuration (X354.5, Y368.9)
- Probe input must be wired to your Mesa card

### 2. Configuration Verification
Check that your `PrintNC.ini` has these remapped commands:
```ini
[RS274NGC]
SUBROUTINE_PATH = subroutines
REMAP=M6    modalgroup=6 ngc=tool-change
REMAP=M600  modalgroup=6 ngc=tool-job-begin
```

And in the [EMCIO] section:
```ini
[EMCIO]
TOOL_CHANGE_AT_G30 = 0
# Note: TOOL_CHANGE_POSITION and TOOL_CHANGE_QUILL_UP should NOT be set
# (The subroutine handles all positioning)
```

### 3. HAL Configuration Requirements
Your HAL file must have the manual tool change component loaded:
```hal
loadusr -W hal_manualtoolchange
net tool-change iocontrol.0.tool-change => hal_manualtoolchange.change
net tool-changed iocontrol.0.tool-changed <= hal_manualtoolchange.changed
net tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number
net tool-prepare-loopback iocontrol.0.tool-prepare => iocontrol.0.tool-prepared
```

### 4. Tool Table Setup (Optional)
While tool lengths are measured automatically, you can still define tool diameters in the tool table for reference:
- Open tool table in LinuxCNC
- Enter tool numbers and diameters
- Lengths will be handled automatically by the probe

## Step-by-Step Workflow

### Starting a New Job

#### Step 1: Load Your Reference Tool
Choose any tool as your reference - this could be:
- Your first cutting tool (e.g., Tool 1)
- A dedicated touch-off tool
- An edge finder
- A piece of dowel rod

**Example:** Let's say you're using a 6mm endmill as Tool 1.

#### Step 2: Set Your Work Coordinates (G54)
With your reference tool loaded:
1. Jog to your workpiece
2. Touch off X zero (left edge, center, etc.)
3. Touch off Y zero (front edge, center, etc.)
4. Touch off Z zero (top of stock)
5. Set G54 for each axis in LinuxCNC

**Important:** Set your work coordinates BEFORE running M600!

#### Step 3: Initialize the Tool System
In the MDI tab, type and execute:
```gcode
M600
```
This command:
- Clears any previous tool offset data
- Resets the measurement system
- Prepares for a new job

#### Step 4: Measure Your Reference Tool
Still in MDI, type and execute:
```gcode
M6 T1
```
(Replace T1 with your actual tool number)

What happens:
1. Machine moves to tool change position (X300, Y30)
2. Since this is the first tool after M600, no pause occurs
3. Machine goes directly to tool sensor
4. Probes the tool twice (rough then fine)
5. Stores this as the reference height (#<_ToolZRef> = #5063)
6. Sets #<_ToolDidFirst> = 1 to mark reference established
7. Returns to previous position

Your reference tool is now established!

### During Your Program

#### Running G-Code with Tool Changes
Your G-code will contain tool changes like:
```gcode
T3 M6  ; Change to Tool 3
```
or
```gcode
M6 T3  ; Alternative format
```

When the machine encounters an M6:

1. **Machine Moves to Tool Change Position**
   - Rises to safe Z height (-1mm in machine coordinates)
   - Moves to X300, Y30
   - Spindle stops automatically (M5)
   - Coolant stops automatically (M9)

2. **Tool Change Behavior**
   - For **first tool after M600**: Machine goes directly to probe (no pause needed - tool already loaded)
   - For **subsequent tools**: Machine pauses here for manual tool change

3. **You Manually Change the Tool** (only for subsequent tools)
   - Open the collet
   - Remove the old tool
   - Insert the new tool
   - Tighten the collet
   - Make sure the tool is secure!

4. **Continue After Tool Change**
   - The pause is handled by the hal_manualtoolchange component
   - Click the tool change acknowledgment in LinuxCNC's UI

5. **Machine Measures the New Tool**
   - Moves to sensor location
   - Probes the tool (rough pass)
   - Retracts slightly
   - Probes again (fine pass for accuracy)
   - Calculates height difference from reference

6. **Returns to Work**
   - Moves back to where it left off
   - Applies the calculated Z offset
   - Continues cutting with correct Z height

### Starting a Second Operation (Same Setup)

If you're running multiple programs with the same Z zero:
1. Keep the same G54 settings
2. Run `M600` before starting the new program
3. Measure your reference tool again with `M6 T#`
4. Run your program

### Starting a Completely New Setup

For a new workpiece or different Z zero:
1. Load your reference tool
2. Touch off new X, Y, Z coordinates
3. Set new G54
4. Run `M600`
5. Run `M6 T#` with your reference tool
6. Start your program

## CAM Software Setup

### Fusion 360 Configuration

#### Post Processor Settings
Configure your post processor with these critical settings:

1. **Disable G43 Commands**
   - The subroutine handles tool length compensation
   - G43 commands will interfere with the automatic system
   - In post processor properties, disable "Use Tool Length Compensation" or similar

2. **Use G53 Instead of G28**
   - Check "Use G53 for safe retracts" or similar option
   - G28 can cause unexpected movements

3. **Machine Configuration**
   - Set Z home position to -0.250" (if your machine homes at top of travel)
   - This ensures safe clearance moves

#### Tool Library
- Define your tools with correct diameters
- Tool lengths don't matter - they're measured automatically
- Use consistent tool numbers across projects

#### Example Tool Change in G-Code
Your post processor should output:
```gcode
; Operation 1 - Face Mill
T1 M6                    ; Tool change to Tool 1
S10000 M3               ; Spindle on
G0 X50 Y50              ; Move to start
G0 Z5                   ; Move to clearance
G1 Z-0.5 F500           ; Start cutting
...

; Operation 2 - Drill
T5 M6                    ; Tool change to Tool 5
S8000 M3                ; Spindle on
...
```

**NOT this (wrong - includes G43):**
```gcode
T1 M6
G43 H1                  ; NO! Don't include this
```

### Other CAM Software

#### General Requirements
1. Tool changes must use M6 command
2. No G43 (tool length compensation) commands
3. Use machine coordinates (G53) for safe moves, not G28
4. Tool numbers should be consistent

## Common Scenarios

### Scenario 1: Simple Job with Multiple Tools
```gcode
; In MDI before starting:
M600                    ; Reset system
M6 T1                   ; Measure reference tool (already loaded)

; Your program:
T1 M6                   ; Uses Tool 1 (already measured)
G0 X0 Y0 Z5
; ... cutting with Tool 1 ...

T3 M6                   ; Change to Tool 3
; ... cutting with Tool 3 ...

T1 M6                   ; Back to Tool 1
; ... more cutting ...

T5 M6                   ; Change to Tool 5
; ... drilling operations ...
```

### Scenario 2: Breaking an Endmill Mid-Job
If you break Tool 3 during cutting:
1. Stop the program
2. Replace the broken tool with a new Tool 3
3. In MDI, run: `M6 T3` (to remeasure the new tool)
4. Restart your program from the appropriate line
5. The new tool will be measured and correct offset applied

### Scenario 3: Using an Edge Finder First
```gcode
; Load edge finder (let's call it Tool 99)
; Manually find edges and set G54 X and Y

; Use a gauge block or the edge finder to set Z
; Set G54 Z

M600                    ; Initialize system
M6 T99                  ; Measure edge finder as reference

; Load your first cutting tool manually
M6 T1                   ; Machine measures Tool 1
; Run your program
```

### Scenario 4: Tool Breaks and You Use a Different One
If Tool 3 breaks and you want to use Tool 8 instead:
1. Edit your G-code to replace T3 with T8
2. When prompted for tool change, insert Tool 8
3. The system will measure it automatically
4. Continue cutting with correct offset

## Troubleshooting

### Problem: Z Height Is Wrong After Tool Change
**Causes:**
- Didn't run M600 at job start
- Touched off Z after running M600 (should be before)
- Tool slipped in collet during measurement

**Solution:**
1. Stop the program
2. Re-touch off your Z zero
3. Run M600
4. Run M6 with your reference tool
5. Restart program

### Problem: Machine Doesn't Pause for Tool Change
**Note:** The M0 pause command at line 149 is commented out with parentheses: `(M0)`
The actual pause is handled by the hal_manualtoolchange component, which creates a tool change dialog.
If you're not getting a pause dialog, check that hal_manualtoolchange is properly configured in your HAL file.

### Problem: First Tool After M600 Behavior
**Important:** The first tool after M600 DOES get probed! It establishes the reference height. 
- The tool goes directly to the probe (no pause since tool is already loaded)
- It measures and stores the reference height in #<_ToolZRef>
- All subsequent tools are measured and compared to this reference

### Problem: Probe Errors During Tool Measurement
**Causes:**
- Tool too long (would hit probe at safe height)
- Tool too short (can't reach probe)
- Probe not working

**Solutions:**
- Adjust `_ProbeFastZ` in tool-change.ngc if needed
- Check probe with manual testing
- Ensure tool is properly secured in collet

### Problem: Wrong Tool Change Position
**Current position:** X300, Y30

If you need to change it:
1. Edit `/home/howard/PrintNC_conf/PrintNC/subroutines/tool-change.ngc`
2. Find lines 80-81:
   ```
   #<_ToolChangeX> = 300
   #<_ToolChangeY> = 30
   ```
3. Change to your preferred position
4. Save and restart LinuxCNC

## Important Notes

### What You DON'T Need to Do
- ❌ Never manually enter tool lengths
- ❌ Never use G43 H# commands
- ❌ Never touch off Z for each tool
- ❌ Never calculate tool offsets yourself

### What You MUST Do
- ✅ Always run M600 when starting a new job
- ✅ Always set G54 BEFORE running M600
- ✅ Always secure tools properly in the collet
- ✅ Always wait for the machine to stop before changing tools

### Safety Reminders
1. **Spindle stops automatically** during M6, but always verify
2. **Don't touch the probe** while it's measuring
3. **Secure tools tightly** - loose tools can slip during measurement
4. **Check clearances** - ensure no clamps or fixtures block the path to the sensor

## Quick Reference Card

### New Job Checklist
```
□ Load reference tool
□ Touch off X, Y, Z → Set G54
□ MDI: M600
□ MDI: M6 T[reference_tool_number]
□ Load and run program
```

### Tool Change Process (Automatic)
```
1. M6 encountered → Machine moves to change position
2. You: Change tool manually
3. You: Click Resume
4. Machine: Measures tool automatically
5. Machine: Returns with correct offset
```

### Key Positions
- **Tool Change:** X300, Y30
- **Tool Sensor:** X354.5, Y368.9
- **Safe Z Travel:** Z-1 (near top)

### Commands
- `M600` - Reset tool measurement system (new job)
- `M6 T#` - Change to tool # with automatic measurement
- No G43 needed - offsets are automatic!

## Summary

This system makes tool changes simple and reliable:
1. You handle the physical tool change
2. The machine handles all measurements and math
3. Your Z zero stays perfect across all tools

The key is understanding that the first tool after M600 becomes your reference - all other tools are measured relative to it. As long as you follow the workflow (Set G54 → M600 → M6 T# with reference → Run program), your tools will always have the correct height compensation.

Remember: The machine does the hard work of measuring and calculating. You just need to change the tools when asked!