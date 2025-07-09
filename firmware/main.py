import time
# import board
# import busio
# import digitalio
# import microcontroller

from lib.hx711.hx711_gpio import HX711_GPIO
from lib.lsm6dsv.lsm6dsv16x import LSM6DSV16X


# Init the LSM6 sensor
i2c = busio.I2C(scl=board.GP27, sda=board.GP26)
sensor = LSM6DSV16X(i2c, address=0x6b)

# Pins for the hx711
gpio_data = digitalio.DigitalInOut(board.GP2)
gpio_clk = digitalio.DigitalInOut(board.GP3)

while True:
    print("Leave unloaded.... [y]")
    c = input()
    if c[0].lower() == "y":
        break

# HX init and tare (zeroing)
hx = HX711_GPIO(gpio_data, gpio_clk, tare=True)
#hx = HX711_GPIO(gpio_data, gpio_clk, tare=True, scalar=1234567)

while True:
    print("Apply Test Mass.... [y]")
    c = input()
    if c[0].lower() == "y":
        break

# Test mass calibration, assuming a mass of 100g for gram readings
hx.determine_scalar(100)
print(hx.scalar)

print("Calibrated")

while True:
    print("Acceleration: X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (sensor.acceleration))
    print("Gyro X:%.2f, Y: %.2f, Z: %.2f radians/s" % (sensor.gyro))
    print("Load Cell: %f" % hx.read())
    print("")
    time.sleep(0.5)
