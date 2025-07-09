__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_LSM6DS.git"

import struct

from time import sleep
from math import radians
from micropython import const
from adafruit_bus_device import i2c_device

from adafruit_register.i2c_struct import ROUnaryStruct, Struct
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_bit import RWBit, ROBit

try:
    from typing import Tuple, Optional
    from busio import I2C
except ImportError:
    pass

class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples: Tuple[str, int, float, Optional[float]]) -> None:
        "creates CV entries"
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Returns true if the given value is a member of the CV"""
        return value in cls.string


class AccelRange(CV):
    """Options for ``accelerometer_range``"""

class AccelOpMode(CV):
    """Options for ``accelerometer_op_mode``"""

class GyroRange(CV):
    """Options for ``gyro_data_range``"""

class GyroOpMode(CV):
    """Options for ``gyrp_op_mode``"""

class Rate(CV):
    """Options for ``accelerometer_data_rate`` and ``gyro_data_rate``"""
    
Rate.add_values(
    (
        ("RATE_SHUTDOWN", 0, 0, None),
        ("RATE_1_875_HZ", 1, 1.875, None),
        ("RATE_7_5_HZ", 2, 7.5, None),
        ("RATE_15_HZ", 3, 15.0, None),
        ("RATE_30_HZ", 4, 30.0, None),
        ("RATE_60_HZ", 5, 60.0, None),
        ("RATE_120_HZ", 6, 120.0, None),
        ("RATE_240_HZ", 7, 240.0, None),
        ("RATE_480_HZ", 8, 480.0, None),
        ("RATE_960_HZ", 9, 960.0, None),
        ("RATE_1_92K_HZ", 10, 1920.0, None),
        ("RATE_3_84K_HZ", 11, 3840, None),
        ("RATE_7_68K_HZ", 11, 7680, None),
    )
)

LSM6DSV_DEFAULT_ADDRESS = const(0x6A) # alternate address: 0x6B

LSM6DSV_CHIP_ID = const(0x70) # typically 0x70 or 0x71 for this series

_LSM6DSV_WHOAMI = const(0xF)
_LSM6DSV_CTRL1 = const(0x10) # accelerometer control register
_LSM6DSV_CTRL2 = const(0x11) # gyroscope control register
_LSM6DSV_CTRL3 = const(0x12) # control register
_LSM6DSV_CTRL6 = const(0x15) # control register; includes gyro full scale
_LSM6DSV_CTRL8 = const(0x17) # control register; includes accel full scale
_LSM6DSV_OUT_TEMP_L = const(0x20)
_LSM6DSV_OUTX_L_G = const(0x22)
_LSM6DSV_OUTX_L_A = const(0x28)
_MILLI_G_TO_ACCEL = 0.00980665
_TEMPERATURE_SENSITIVITY = 256
_TEMPERATURE_OFFSET = 25.0


class LSM6DSV_CORE:
    # ROUnaryStructs:
    _chip_id = ROUnaryStruct(_LSM6DSV_WHOAMI, "<b")

    #Structs
    _raw_accel_data = Struct(_LSM6DSV_OUTX_L_A, "<hhh")
    _raw_gyro_data = Struct(_LSM6DSV_OUTX_L_G, "<hhh")
    _raw_temp_data = Struct(_LSM6DSV_OUT_TEMP_L, "<h")

    #RWBits
    _accel_data_rate = RWBits(4, _LSM6DSV_CTRL1, 0)
    _accel_range = RWBits(2, _LSM6DSV_CTRL8, 0)
    _accel_op_mode = RWBits(3, _LSM6DSV_CTRL1, 4)

    _gyro_data_rate = RWBits(4, _LSM6DSV_CTRL2, 0)
    _gyro_range = RWBits(4, _LSM6DSV_CTRL6, 0)
    _gyro_op_mode = RWBits(3, _LSM6DSV_CTRL2, 4)

    _sw_reset = RWBit(_LSM6DSV_CTRL3, 0)
    _bdu = RWBit(_LSM6DSV_CTRL3, 6)

    CHIP_ID = None

    def __init__(self, i2c_bus: I2C, address: int = LSM6DSV_DEFAULT_ADDRESS, ucf = None) -> None:
        self._cached_accel_range = None
        self._cached_gyro_range = None

        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        if self.CHIP_ID is None:
            raise AttributeError("LSM6DSV Parent Class cannot be directly instantiated")
        if self._chip_id != self.CHIP_ID:
            raise RuntimeError(
                "Failed to find %s - check your wiring!" % self.__class__.__name__
            )
        self.reset()

        self._add_gyro_ranges()
        self._add_gyro_op_modes()
        self._add_accel_ranges()
        self._add_accel_op_modes()

        self._bdu = True

        # Default data rates for both accel and gyro is 0 (off); enable both at lowest standard rate (non-low-power)
        self.accelerometer_data_rate = Rate.RATE_120_HZ  # pylint: disable=no-member
        self.gyro_data_rate = Rate.RATE_120_HZ  # pylint: disable=no-member

        self.accelerometer_range = AccelRange.RANGE_2G  # pylint: disable=no-member
        self.gyro_range = GyroRange.RANGE_125_DPS  # pylint: disable=no-member


    def reset(self) -> None:
        "Resets the sensor's configuration into an initial state"
        self._sw_reset = True
        while self._sw_reset:
            sleep(0.001)

    @staticmethod
    def _add_gyro_ranges() -> None:
        GyroRange.add_values(
            (
                ("RANGE_125_DPS", 0, 125, 4.375),
                ("RANGE_250_DPS", 1, 250, 8.75),
                ("RANGE_500_DPS", 2, 500, 17.50),
                ("RANGE_1000_DPS", 3, 1000, 35.0),
                ("RANGE_2000_DPS", 4, 2000, 70.0),
                ("RANGE_4000_DPS", 12, 4000, 140.0),
            )
        )

    @staticmethod
    def _add_gyro_op_modes() -> None:
        GyroOpMode.add_values(
            (
                ("HIGH_PERFORMANCE_MODE", 0, None, None),
                ("HIGH_ACCURACY_ODR_MODE", 1, None, None),
                ("ODR_TRIGGERED_MODE", 3, None, None),
                ("SLEEP_MODE", 4, None, None),
                ("LOW_POWER_MODE", 5, None, None),
            )
        )

    @staticmethod
    def _add_accel_ranges() -> None:
        AccelRange.add_values(
            (
                ("RANGE_2G", 0, 2, 0.061),
                ("RANGE_4G", 1, 4, 0.122),
                ("RANGE_8G", 2, 8, 0.244),
                ("RANGE_16G", 3, 16, 0.488),
            )
        )

    @staticmethod
    def _add_accel_op_modes() -> None:
        AccelOpMode.add_values(
            (
                ("HIGH_PERFORMANCE_MODE", 0, None, None),
                ("HIGH_ACCURACY_ODR_MODE", 1, None, None),
                ("ODR_TRIGGERED_MODE", 3, None, None),
                ("LOW_POWER_MODE_1", 4, None, None),
                ("LOW_POWER_MODE_2", 5, None, None),
                ("LOW_POWER_MODE_3", 6, None, None),
                ("NORMAL_MODE",7, None, None),
            )
        )

    @property
    def acceleration(self) -> Tuple[float, float, float]:
        """The x, y, z acceleration values returned in a 3-tuple and are in m / s ^ 2."""
        raw_accel_data = self._raw_accel_data

        x = self._scale_xl_data(raw_accel_data[0])
        y = self._scale_xl_data(raw_accel_data[1])
        z = self._scale_xl_data(raw_accel_data[2])

        return (x, y, z)

    @property
    def gyro(self) -> Tuple[float, float, float]:
        """The x, y, z angular velocity values returned in a 3-tuple and are in radians / second"""
        raw_gyro_data = self._raw_gyro_data
        x, y, z = [radians(self._scale_gyro_data(i)) for i in raw_gyro_data]
        return (x, y, z)

    def _scale_xl_data(self, raw_measurement: int) -> float:
        return (
            raw_measurement
            * AccelRange.lsb[self._cached_accel_range]
            * _MILLI_G_TO_ACCEL
        )

    def _scale_gyro_data(self, raw_measurement: int) -> float:
        return raw_measurement * GyroRange.lsb[self._cached_gyro_range] / 1000
    
    @property
    def accelerometer_range(self) -> int:
        """Adjusts the range of values that the sensor can measure, from +/- 2G to +/-16G (or +/- 4G to +/- 32G for some chips)
        Note that larger ranges will be less accurate. Must be an ``AccelRange``"""
        return self._cached_accel_range

    # pylint: disable=no-member
    @accelerometer_range.setter
    def accelerometer_range(self, value: int) -> None:
        if not AccelRange.is_valid(value):
            raise AttributeError("range must be an `AccelRange`")
        self._accel_range = value
        self._cached_accel_range = value
        sleep(0.2)  # needed to let new range settle

    @property
    def gyro_range(self) -> int:
        """Adjusts the range of values that the sensor can measure, from 125 Degrees/s to 4000
        degrees/s. Note that larger ranges will be less accurate. Must be a ``GyroRange``.
        """
        return self._cached_gyro_range

    @gyro_range.setter
    def gyro_range(self, value: int) -> None:
        if not GyroRange.is_valid(value):
            raise AttributeError("range must be a `GyroRange`")
        self._gyro_range = value
        self._cached_gyro_range = value
        sleep(0.2) # needed to let new range settle

    @property
    def accelerometer_data_rate(self) -> int:
        """Select the rate at which the accelerometer takes measurements. Must be a ``Rate``"""
        return self._accel_data_rate

    @accelerometer_data_rate.setter
    def accelerometer_data_rate(self, value: int) -> None:
        if not Rate.is_valid(value):
            raise AttributeError("accelerometer_data_rate must be a `Rate`")

        self._accel_data_rate = value

    @property
    def gyro_data_rate(self) -> int:
        """Select the rate at which the gyro takes measurements. Must be a ``Rate``"""
        return self._gyro_data_rate

    @gyro_data_rate.setter
    def gyro_data_rate(self, value: int) -> None:
        if not Rate.is_valid(value):
            raise AttributeError("gyro_data_rate must be a `Rate`")

        if value == Rate.RATE_1_875_HZ:
            raise AttributeError("gyro cannot use the 1.875Hz ODR")
        
        self._gyro_data_rate = value

    @property
    def temperature(self) -> float:
        """Temperature in Celsius"""
        # Data from Datasheet Table 4.3
        # Temp range -40 to 85 Celsius
        # T_ADC_RES = ADC Res 16 bit
        # Stabilization time 500 μs

        temp = self._raw_temp_data[0]

        return temp / _TEMPERATURE_SENSITIVITY + _TEMPERATURE_OFFSET
