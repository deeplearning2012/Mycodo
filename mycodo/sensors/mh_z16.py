# coding=utf-8

from lockfile import LockFile
import logging
import serial
import smbus
import struct
import time
from .base_sensor import AbstractSensor

from sensorutils import is_device


class MHZ16Sensor(AbstractSensor):
    """ A sensor support class that monitors the MH-Z16's CO2 concentration """

    def __init__(self, interface, device_loc=None, baud_rate=None,
                 i2c_address=None, i2c_bus=None):
        super(MHZ16Sensor, self).__init__()
        self.interface = interface
        if self.interface == 'UART':
            self.logger = logging.getLogger(
                "mycodo.sensors.mhz16.{dev}".format(dev=device_loc.replace('/', '')))
        elif self.interface == 'I2C':
            self.logger = logging.getLogger(
                "mycodo.sensors.mhz16.{dev}".format(dev=i2c_address))

        self.k30_lock_file = None
        self._co2 = 0

        if self.interface == 'UART':
            # Check if device is valid
            self.serial_device = is_device(device_loc)
            if self.serial_device:
                try:
                    self.ser = serial.Serial(self.serial_device,
                                             baudrate=baud_rate,
                                             timeout=1)
                    self.k30_lock_file = "/var/lock/sen-mhz16-{}".format(device_loc.replace('/', ''))
                except serial.SerialException:
                    self.logger.exception('Opening serial')
            else:
                self.logger.error(
                    'Could not open "{dev}". '
                    'Check the device location is correct.'.format(
                        dev=device_loc))

        elif self.interface == 'I2C':
            self.cmd_measure = [0xFF, 0x01, 0x9C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x63]
            self.IOCONTROL = 0X0E << 3
            self.FCR = 0X02 << 3
            self.LCR = 0X03 << 3
            self.DLL = 0x00 << 3
            self.DLH = 0X01 << 3
            self.THR = 0X00 << 3
            self.RHR = 0x00 << 3
            self.TXLVL = 0X08 << 3
            self.RXLVL = 0X09 << 3
            self.i2c_address = i2c_address
            self.i2c = smbus.SMBus(i2c_bus)
            self.begin()

    def __repr__(self):
        """  Representation of object """
        return "<{cls}(co2={co2})>".format(
            cls=type(self).__name__,
            co2="{0:.2f}".format(self._co2))

    def __str__(self):
        """ Return CO2 information """
        return "CO2: {co2}".format(co2="{0:.2f}".format(self._co2))

    def __iter__(self):  # must return an iterator
        """ MH-Z16 iterates through live CO2 readings """
        return self

    def next(self):
        """ Get next CO2 reading """
        if self.read():  # raised an error
            raise StopIteration  # required
        return dict(co2=float('{0:.2f}'.format(self._co2)))

    def info(self):
        conditions_measured = [
            ("CO2", "co2", "float", "0.00", self._co2, self.co2)
        ]
        return conditions_measured

    @property
    def co2(self):
        """ CO2 concentration in ppmv """
        if not self._co2:  # update if needed
            self.read()
        return self._co2

    def get_measurement(self):
        """ Gets the MH-Z16's CO2 concentration in ppmv via UART"""
        self._co2 = None

        if self.interface == 'UART':
            self.ser.flushInput()
            time.sleep(1)
            self.ser.write("\xff\x01\x86\x00\x00\x00\x00\x00\x79")
            time.sleep(.01)
            resp = self.ser.read(9)
            if len(resp) != 0:
                high_level = struct.unpack('B', resp[2])[0]
                low_level = struct.unpack('B', resp[3])[0]
                co2 = high_level * 256 + low_level
                return co2

        elif self.interface == 'I2C':
            self.write_register(self.FCR, 0x07)
            self.send(self.cmd_measure)
            try:
                co2 = self.parse(self.receive())
            except:
                co2 = None
            return co2

        return None

    def read(self):
        """
        Takes a reading from the MH-Z16 and updates the self._co2 value

        :returns: None on success or 1 on error
        """
        if self.interface == 'UART':
            lock = LockFile(self.k30_lock_file)

        try:
            if self.interface == 'UART':
                if not self.serial_device:  # Don't measure if device isn't validated
                    return None

                # Acquire lock on MHZ16 to ensure more than one read isn't
                # being attempted at once.
                while not lock.i_am_locking():
                    try:  # wait 60 seconds before breaking lock
                        lock.acquire(timeout=60)
                    except Exception as e:
                        self.logger.error(
                            "{cls} 60 second timeout, {lock} lock broken: "
                            "{err}".format(
                                cls=type(self).__name__,
                                lock=self.k30_lock_file,
                                err=e))
                        lock.break_lock()
                        lock.acquire()
                self._co2 = self.get_measurement()
                lock.release()

            elif self.interface == 'I2C':
                for _ in range(2):
                    self._co2 = self.get_measurement()
                    if self._co2:
                        return  # success - no errors
                    time.sleep(1)

            if self._co2 is None:
                return 1
            return  # success - no errors
        except Exception as e:
            self.logger.error(
                "{cls} raised an exception when taking a reading: "
                "{err}".format(cls=type(self).__name__, err=e))
            if self.interface == 'UART':
                lock.release()
            return 1

    def begin(self):
        try:
            self.write_register(self.IOCONTROL, 0x08)
        except IOError:
            pass

        self.write_register(self.FCR, 0x07)
        self.write_register(self.LCR, 0x83)
        self.write_register(self.DLL, 0x60)
        self.write_register(self.DLH, 0x00)
        self.write_register(self.LCR, 0x03)

    @staticmethod
    def parse(response):
        checksum = 0

        if len(response) < 9:
            return None

        for i in range(0, 9):
            checksum += response[i]

        if response[0] == 0xFF:
            if response[1] == 0x9C:
                if checksum % 256 == 0xFF:
                    return (response[2] << 24) + (response[3] << 16) + (response[4] << 8) + response[5]

        return None

    def read_register(self, reg_addr):
        time.sleep(0.001)
        return self.i2c.read_byte_data(self.i2c_address, reg_addr)

    def write_register(self, reg_addr, val):
        time.sleep(0.001)
        self.i2c.write_byte_data(self.i2c_address, reg_addr, val)

    def send(self, command):
        if self.read_register(self.TXLVL) >= len(command):
            self.i2c.write_i2c_block_data(self.i2c_address, self.THR, command)

    def receive(self):
        n = 9
        buf = []
        start = time.clock()

        while n > 0:
            rx_level = self.read_register(self.RXLVL)

            if rx_level > n:
                rx_level = n

            buf.extend(self.i2c.read_i2c_block_data(self.i2c_address, self.RHR, rx_level))
            n = n - rx_level

            if time.clock() - start > 0.2:
                break
        return buf