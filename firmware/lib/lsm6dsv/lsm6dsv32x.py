from . import LSM6DSV_CORE, LSM6DSV_DEFAULT_ADDRESS, AccelRange

try:
    import typing  # pylint: disable=unused-import
    from busio import I2C
except ImportError:
    pass

class LSM6DSV32X(LSM6DSV_CORE):
    CHIP_ID = 0x70

    def __init__(self, i2c_bus: I2C, address: int = LSM6DSV_DEFAULT_ADDRESS) -> None:
        super().__init__(i2c_bus, address)
        self.accelerometer_range = AccelRange.RANGE_8G  # pylint:disable=no-member

    @staticmethod
    def _add_accel_ranges() -> None:
        AccelRange.add_values(
            (
                ("RANGE_4G", 0, 2, 0.122),
                ("RANGE_8G", 1, 4, 0.244),
                ("RANGE_16G", 2, 8, 0.488),
                ("RANGE_32G", 3, 16, 0.976),
            )
        )
