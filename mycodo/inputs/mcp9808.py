# coding=utf-8
from mycodo.inputs.base_input import AbstractInput

# Measurements
measurements_dict = {
    0: {
        'measurement': 'temperature',
        'unit': 'C'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'MCP9808',
    'input_manufacturer': 'Microchip',
    'input_name': 'MCP9808',
    'input_library': 'pypi Adafruit_MCP9808',
    'measurements_name': 'Temperature',
    'measurements_dict': measurements_dict,
    'url_manufacturer': 'https://www.microchip.com/wwwproducts/en/en556182',
    'url_datasheet': 'http://ww1.microchip.com/downloads/en/DeviceDoc/MCP9808-0.5C-Maximum-Accuracy-Digital-Temperature-Sensor-Data-Sheet-DS20005095B.pdf',
    'url_product_purchase': 'https://www.adafruit.com/product/1782',

    'options_enabled': [
        'i2c_location',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        (
            'pip-pypi',
            'Adafruit_GPIO',
            'Adafruit_GPIO'
         ),
        (
            'pip-git',
            'Adafruit_MCP9808',
            'git://github.com/adafruit/Adafruit_Python_MCP9808.git#egg=adafruit-mcp9808'
        ),
    ],

    'interfaces': ['I2C'],
    'i2c_location': [
        '0x18',
        '0x19',
        '0x1a',
        '0x1b',
        '0x1c',
        '0x1d',
        '0x1e',
        '0x1f'
    ],
    'i2c_address_editable': False
}


class InputModule(AbstractInput):
    """ A sensor support class that monitors the MCP9808's temperature """

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        if not testing:
            from Adafruit_MCP9808 import MCP9808

            self.i2c_address = int(str(input_dev.i2c_location), 16)
            self.i2c_bus = input_dev.i2c_bus

            self.sensor = MCP9808.MCP9808(
                address=self.i2c_address,
                busnum=self.i2c_bus)
            self.sensor.begin()

    def get_measurement(self):
        """ Gets the MCP9808's temperature in Celsius """
        self.return_dict = measurements_dict.copy()

        try:
            self.value_set(0, self.sensor.readTempC())
            return self.return_dict
        except Exception as msg:
            self.logger.exception("Inout read failure: {}".format(msg))
