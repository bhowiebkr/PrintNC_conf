

ENCODER_RES = 131072.0  # encoder resolution per turn
STEPS_REV = 1000  # steps per revolution
LEAD_SCREW = 4.0  # mm


def main():

    instruction_unit = LEAD_SCREW / STEPS_REV

    result = ENCODER_RES / instruction_unit
    print(f'Value calculated: {result}')

    # In the config I have for Z:
    # P03-10 = 8192
    # P03-11 = 625


if __name__ == '__main__':
    main()
