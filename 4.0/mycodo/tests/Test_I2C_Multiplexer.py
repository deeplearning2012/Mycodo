#!/usr/bin/python
# coding=utf-8

# Select address and channel of TCA9548A I2C multiplexer
# I2C Address: 0xYY, where YY can be 70 through 77
# Multiplexer Channel: 1 - 8
# sudo ./multiplexer_channel.py ADDRESS CHANNEL
# Example: sudo ./multiplexer_channel.py 70 1

import time
import argparse

import RPi.GPIO as GPIO
import smbus

def I2C_setup(multiplexer_i2c_address, i2c_channel_setup):
    I2C_address = 0x70 + multiplexer_i2c_address % 10
    if GPIO.RPI_REVISION in [2, 3]:
        I2C_bus_number = 1
    else:
        I2C_bus_number = 0

    bus = smbus.SMBus(I2C_bus_number)
    bus.write_byte(I2C_address, i2c_channel_setup)
    time.sleep(0.1)
    print("TCA9548A I2C channel status:{}".format(bin(bus.read_byte(I2C_address))))

def menu():
    parser = argparse.ArgumentParser(description='Select channel of TCA9548A I2C multiplexer')
    parser.add_argument('address', type=int)
    parser.add_argument('channel', type=int)

    args = parser.parse_args()

    I2C_setup(args.address, args.channel)

if __name__ == "__main__":
    menu()