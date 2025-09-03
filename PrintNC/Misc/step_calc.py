motor_pulley_teeth = 28
screw_pulley_teeth = 36
motor_steps_per_revolution = 2000  # steps per revolution
screw_pitch = 5.0  # mm


def main():
    # Calculate steps per revolution of the screw
    steps_per_revolution = (
        float(screw_pulley_teeth)
        / float(motor_pulley_teeth)
        * motor_steps_per_revolution
    )

    # Calculate step scale (mm per step)
    step_scale = steps_per_revolution * 1 / screw_pitch

    print(f"Step scale: {step_scale} mm/step")


main()
