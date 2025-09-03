# Assumptions
motor_teeth = 24  # Number of teeth on the motor gear
ball_screw_teeth = 36  # Number of teeth on the ball screw gear

# Deceleration ratio calculation
deceleration_ratio_R = ball_screw_teeth / motor_teeth
print(f"Deceleration Ratio (R): {deceleration_ratio_R}")

# Lead of the lead screw
lead_screw_lead = 10  # mm

# Resolution of each turn of position ring
encoder_resolution = 131072  # 17 bits

# Load displacement corresponding to 1 position instruction
position_instruction_displacement = 0.001  # mm

# Calculating the position instruction (instruction unit) value required for the screw to rotate 1 turn
table_movement_per_turn = 10  # mm
position_instruction_value = table_movement_per_turn / position_instruction_displacement
print(f"Position Instruction Value: {position_instruction_value}")

# Electronic gear ratio calculation (B/A)
B = encoder_resolution
A = position_instruction_value

electronic_gear_ratio = B / A
print(f"Electronic Gear Ratio (B/A): {electronic_gear_ratio}")

# Parameters p03-10 and p03-11
p03_10 = int(electronic_gear_ratio)
p03_11 = 625

print(f"Parameter p03-10: {p03_10}")
print(f"Parameter p03-11: {p03_11}")
