# G-Code Tool Change Issue - CAM Post-Processor Problem

## Issue Found
The G-code file `test_part_3_ops.ngc` has **incorrect tool change sequences** that cause the program to stop after the first tool operation.

## Problem Pattern
```gcode
N25 T17 M6    ✅ First tool change works fine
N30 T24       ❌ Tool selection WITHOUT M6 command
...
N210 T24 M6   ✅ Finally changes to T24 (much later)
N215 T8       ❌ Tool selection WITHOUT M6 command  
...
N7685 T8 M6   ✅ Finally changes to T8 (much later)
```

## What Should Happen
LinuxCNC expects tool changes in this format:
```gcode
T17 M6        ✅ Select tool 17 AND change it
T24 M6        ✅ Select tool 24 AND change it  
T8 M6         ✅ Select tool 8 AND change it
```

## What's Actually Generated
Your post-processor is creating:
```gcode
T17 M6        ✅ Works
T24           ❌ Selects but doesn't change
(operations with wrong tool)
T24 M6        ✅ Finally changes (too late)
T8            ❌ Selects but doesn't change
(operations with wrong tool)  
T8 M6         ✅ Finally changes (too late)
```

## Root Cause
**Post-processor configuration issue** in your CAM software. The post-processor is separating tool selection (`T##`) from tool change commands (`M6`).

## Solutions to Check in CAM Software

### 1. Post-Processor Settings
Look for these options:
- **"Tool change command format"**
- **"Combine T and M6 commands"**
- **"Tool change sequence"**
- **"Manual tool change format"**

### 2. LinuxCNC Post-Processor
- Make sure you're using a **LinuxCNC-specific post-processor**
- Avoid generic **"Fanuc"** or **"Haas"** post-processors

### 3. Tool Change Output Format
Check if there's an option to set tool change format to:
- `T## M6` (preferred)
- Not `T##` followed by `M6` on separate lines

### 4. Manual Tool Change Settings
If using manual tool change mode:
- Enable **"Manual tool change"** option
- Check **"Tool change at machine coordinates"** 
- Verify **"Tool change position"** settings

## Quick Fix for Current File
If you need to run the current file immediately, manually edit the G-code:

**Change this:**
```gcode
N30 T24
```
**To this:**
```gcode
N30 T24 M6
```

**Change this:**
```gcode
N215 T8
```
**To this:**
```gcode
N215 T8 M6
```

## Test After Changes
1. Re-generate G-code with corrected post-processor settings
2. Check that EVERY tool selection has `M6` immediately after it
3. Search for pattern: `T\d+$` (tool number at end of line without M6)

## File Location
This file is saved at: `/home/howard/PrintNC_conf/GCODE_TOOL_CHANGE_ISSUE.md`