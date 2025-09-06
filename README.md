# PrintNC LinuxCNC Configuration

Complete LinuxCNC configuration for a PrintNC CNC machine build featuring 3-axis gantry design, Mesa 7i76e control, and QtDragon HD interface.

## Machine Overview

**PrintNC** is an open-source steel tube CNC machine design optimized for rigidity and precision. This configuration supports a 3-axis gantry mill with:

- **Frame**: PrintNC steel tube construction
- **Work envelope**: Configured for medium-format machining
- **Spindle**: 2.2kW VFD-controlled spindle (1000-24000 RPM)
- **Motion**: Ball screw drive on all axes with stepper motors
- **Control**: Mesa 7i76e Ethernet I/O card with LinuxCNC

## Hardware Configuration

### Motion Control
- **X-axis**: Single motor drive
- **Y-axis**: Dual motor gantry (Y/Y2) for square alignment
- **Z-axis**: Single motor with tool height sensor integration
- **Mesa 7i76e**: Ethernet-based I/O card at 10.10.10.10

### Tooling System
- **Manual tool changes** with automatic Z-offset compensation
- **Tool height sensor** at machine coordinates X354.5, Y368.9
- Automatic tool measurement via M6 remap subroutine
- Tool table management for offset tracking

### User Interface
- **QtDragon HD**: Modern LinuxCNC interface with custom handlers
- Touch-screen compatible layout
- Integrated DRO, spindle control, and axis jogging

## Key Features

- **Automatic tool height measurement**: Each tool change probes the new tool and calculates Z-offset
- **Gantry squaring**: Dual Y-axis motors maintain perpendicularity
- **Home/limit integration**: Combined switches for efficient homing cycles
- **VFD spindle control**: Full speed and direction control through HAL
- **Custom subroutines**: M6 tool change and M600 job initialization

## File Structure

```
PrintNC/
├── PrintNC.ini              # Main configuration
├── PrintNC.hal              # Hardware abstraction layer
├── custom.hal               # Custom HAL components
├── custom_postgui.hal       # Post-GUI HAL connections
├── tool.tbl                 # Tool table
├── subroutines/
│   ├── tool-change.ngc      # M6 tool change routine
│   └── tool-job-begin.ngc   # M600 job initialization
├── qtdragon_hd/
│   └── qtdragon_hd_handler.py # UI customizations
└── Misc/
    ├── step_calc.py         # Stepper calculation utilities
    └── servo_settings_calc.py # Servo calculation utilities
```

## Quick Start

1. **Prerequisites**: LinuxCNC 2.8+ with Mesa driver support
2. **Network**: Configure Mesa 7i76e at IP 10.10.10.10
3. **Launch**: `linuxcnc PrintNC/PrintNC.ini`
4. **Home**: Execute homing sequence for all axes
5. **Tool setup**: Run `M600` then `M6 T1` to establish reference tool

## Tool Change Workflow

1. Set work coordinates with reference tool
2. Execute `M600` to initialize tool measurement system
3. During program execution, `M6 Tx` commands automatically:
   - Move to tool change position (X300, Y30)
   - Pause for manual tool/collet change
   - Probe new tool at sensor location
   - Calculate Z-offset compensation
   - Resume machining with correct tool length

## About

This configuration is maintained by Bryan Howard. Build documentation, machining examples, and configuration updates available on [YouTube](https://www.youtube.com/c/BryanHoward/videos).

**PrintNC Project**: Open-source CNC machine design focused on steel construction and precision machining capabilities.