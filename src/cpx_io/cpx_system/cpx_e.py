"""TODO: Add module docstring"""

from cpx_io.cpx_system.cpx_base import CpxBase, CpxInitError


def module_list_from_typecode(typecode: str) -> list:
    module_id_dict = {
        "EP": CpxEEp,
        "M": CpxE16Di,
        "L": CpxE8Do,
        "NI": CpxE4AiUI,
        "NO": CpxE4AoUI,
    }

    module_list = []
    for i in range(len(typecode)):
        substring = typecode[i:]
        for key, value in module_id_dict.items():
            if substring.startswith(key):
                module_list.append(value())

    return module_list


class _ModbusCommands:
    """Modbus start adresses used to read and write registers"""

    # (RegAdress, Length)
    # input registers

    # holding registers
    process_data_outputs = (40001, 1)
    data_system_table_write = (40002, 1)

    process_data_inputs = (45392, 1)
    data_system_table_read = (45393, 1)

    module_configuration = (45367, 3)
    fault_detection = (45383, 3)
    status_register = (45391, 1)


class CpxE(CpxBase):
    """CPX-E base class"""

    def __init__(self, modules=None, **kwargs):
        super().__init__(**kwargs)
        self._control_bit_value = 1 << 15
        self._write_bit_value = 1 << 13

        self._next_output_register = None
        self._next_input_register = None
        self._modules = []

        self.modules = modules

    @property
    def modules(self):
        return self._modules

    @modules.setter
    def modules(self, modules_value):
        for m in self._modules:
            self.__delattr__(m.name)
        self._modules = []

        if modules_value == None:
            module_list = [CpxEEp()]
        elif isinstance(modules_value, list):
            module_list = modules_value
        elif isinstance(modules_value, str):
            module_list = module_list_from_typecode(modules_value)
        else:
            raise CpxInitError

        for m in module_list:
            self.add_module(m)

    def write_function_number(self, function_number: int, value: int):
        """Write parameters via function number"""
        self.write_reg_data(value, *_ModbusCommands.data_system_table_write)
        # need to write 0 first because there might be an
        # old unknown configuration in the register
        self.write_reg_data(0, *_ModbusCommands.process_data_outputs)
        self.write_reg_data(
            self._control_bit_value | self._write_bit_value | function_number,
            *_ModbusCommands.process_data_outputs,
        )

        data = 0
        its = 0
        while (data & self._control_bit_value) == 0 and its < 1000:
            data = self.read_reg_data(*_ModbusCommands.process_data_inputs)[0]
            its += 1

        if its >= 1000:
            raise ConnectionError()

        data &= ~self._control_bit_value
        data2 = self.read_reg_data(*_ModbusCommands.data_system_table_read)[0]

    def read_function_number(self, function_number: int):
        """Read parameters via function number"""
        # need to write 0 first because there might be an
        # old unknown configuration in the register
        self.write_reg_data(0, *_ModbusCommands.process_data_outputs)
        self.write_reg_data(
            self._control_bit_value | function_number,
            *_ModbusCommands.process_data_outputs,
        )

        data = 0
        its = 0
        while (data & self._control_bit_value) == 0 and its < 1000:
            data = self.read_reg_data(*_ModbusCommands.process_data_inputs)[0]
            its += 1

        if its >= 1000:
            raise ConnectionError()

        data &= ~self._control_bit_value
        data2 = self.read_reg_data(*_ModbusCommands.data_system_table_read)
        return data2

    def module_count(self) -> int:
        """returns the total count of attached modules"""
        data = self.read_reg_data(*_ModbusCommands.module_configuration)
        return sum(d.bit_count() for d in data)

    def fault_detection(self) -> list[bool]:
        """returns list of bools with Errors (True = Error)"""
        data = self.read_reg_data(*_ModbusCommands.fault_detection)
        data = data[2] << 16 + data[1] << 8 + data[0]
        return [d == "1" for d in bin(data)[2:].zfill(24)[::-1]]

    def status_register(self) -> tuple:
        """returns (Write-protected, Force active)"""
        write_protect_bit = 1 << 11
        force_active_bit = 1 << 15
        data = self.read_reg_data(*_ModbusCommands.status_register)
        return (bool(data[0] & write_protect_bit), bool(data[0] & force_active_bit))

    def read_device_identification(self) -> int:
        """returns Objects IDO 1,2,3,4,5"""
        data = self.read_function_number(43)
        return data[0]

    def read_module_count(self) -> int:
        """Reads and returns IO module count as integer"""
        return len(self._modules)

    def add_module(self, module):
        """Adds one module to the base. This is required to use the module."""
        module._initialize(self, len(self._modules))
        self._modules.append(module)
        self.__setattr__(module.name, module)
        return module


class _CpxEModule(CpxE):
    """Base class for cpx-e modules"""

    def __init__(self, name=None):
        if name:
            self.name = name
        else:
            # Use class name (lower cased) as default value
            self.name = type(self).__name__.lower()
        self.base = None
        self.position = None

        self.output_register = None
        self.input_register = None

    def _initialize(self, base, position):
        self.base = base
        self.position = position


class CpxEEp(_CpxEModule):
    """Class for CPX-E-EP module"""

    def _initialize(self, *args):
        super()._initialize(*args)

        self.output_register = _ModbusCommands.process_data_outputs[0]
        self.input_register = _ModbusCommands.process_data_inputs[0]

        self.base._next_output_register = self.output_register + 2
        self.base._next_input_register = self.input_register + 3


class CpxE8Do(_CpxEModule):
    """Class for CPX-E-8DO module"""

    def _initialize(self, *args):
        super()._initialize(*args)

        self.output_register = self.base._next_output_register
        self.input_register = self.base._next_input_register

        self.base._next_output_register = self.output_register + 1
        self.base._next_input_register = self.input_register + 2

    @CpxBase._require_base
    def read_channels(self) -> list[bool]:
        """read all channels as a list of bool values"""
        data = self.base.read_reg_data(self.input_register)[0]
        return [d == "1" for d in bin(data)[2:].zfill(8)[::-1]]

    @CpxBase._require_base
    def write_channels(self, data: list[bool]) -> None:
        """write all channels with a list of bool values"""
        if len(data) != 8:
            raise ValueError("Data must be list of eight elements")
        # Make binary from list of bools
        binary_string = "".join("1" if value else "0" for value in reversed(data))
        # Convert the binary string to an integer
        integer_data = int(binary_string, 2)
        self.base.write_reg_data(integer_data, self.output_register)

    @CpxBase._require_base
    def read_status(self) -> list[bool]:
        """read module status register. Further information see module datasheet"""
        data = self.base.read_reg_data(self.input_register + 1)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @CpxBase._require_base
    def read_channel(self, channel: int) -> bool:
        """read back the value of one channel"""
        return self.read_channels()[channel]

    @CpxBase._require_base
    def set_channel(self, channel: int) -> None:
        """set one channel to logic high level"""
        data = self.base.read_reg_data(self.input_register)[0]
        self.base.write_reg_data(data | 1 << channel, self.output_register)

    @CpxBase._require_base
    def clear_channel(self, channel: int) -> None:
        """set one channel to logic low level"""
        data = self.base.read_reg_data(self.input_register)[0]
        self.base.write_reg_data(data & ~(1 << channel), self.output_register)

    @CpxBase._require_base
    def toggle_channel(self, channel: int) -> None:
        """set one channel the inverted of current logic level"""
        data = (
            self.base.read_reg_data(self.input_register)[0] & 1 << channel
        ) >> channel
        if data == 1:
            self.clear_channel(channel)
        elif data == 0:
            self.set_channel(channel)
        else:
            raise ValueError

    @CpxBase._require_base
    def configure_diagnostics(self, short_circuit=None, undervoltage=None):
        """The "Diagnostics of short circuit at output" parameter defines whether the diagnostics of the outputs
        in regard to short circuit or overload should be activated or deactivated.
        The "Diagnostics of undervoltage at load supply" parameter defines if the diagnostics for the load
        supply must be activated or deactivated with regard to undervoltage.
        When the diagnostics are activated, the error will be sent to the bus module and displayed on the
        module by the error LED.
        """
        function_number = 4828 + 64 * self.position + 0
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if short_circuit == None:
            short_circuit = bool((reg & 0x02) >> 2)
        if undervoltage == None:
            undervoltage = bool((reg & 0x04) >> 4)

        value_to_write = (int(short_circuit) << 1) | (int(undervoltage) << 2)

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_power_reset(self, value: bool):
        """The "Behaviour after SCO" parameter defines whether the voltage remains switched off ("False", default) or
        automatically switches on ("True") again after a short circuit or overload at the outputs.
        In the case of the "Leave power switched off" setting, the CPX-E automation system must be switched
        off and on or the corresponding output must be reset and to restore the power.
        """
        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x02
        else:
            value_to_write = reg & 0xFD

        self.base.write_function_number(function_number, value_to_write)


class CpxE16Di(_CpxEModule):
    """Class for CPX-E-16DI module"""

    def _initialize(self, *args):
        super()._initialize(*args)

        self.output_register = None
        self.input_register = self.base._next_input_register

        self.base._next_input_register = self.input_register + 2

    @CpxBase._require_base
    def read_channels(self) -> list[bool]:
        """read all channels as a list of bool values"""
        data = self.base.read_reg_data(self.input_register)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @CpxBase._require_base
    def read_status(self) -> list[bool]:
        """read module status register. Further information see module datasheet"""
        data = self.base.read_reg_data(self.input_register + 1)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @CpxBase._require_base
    def read_channel(self, channel: int) -> bool:
        """read back the value of one channel"""
        return self.read_channels()[channel]

    @CpxBase._require_base
    def configure_diagnostics(self, value: bool) -> None:
        """The "Diagnostics of sensor supply short circuit" defines whether the diagnostics of the sensor supply
        in regard to short circuit or overload should be activated ("True", default) or deactivated (False).
        When the diagnostics are activated, the error will be sent to the bus module and displayed on the
        module by the error LED.
        """
        function_number = 4828 + 64 * self.position + 0
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x01
        else:
            value_to_write = reg & 0xFE

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_power_reset(self, value: bool) -> None:
        """ "Behaviour after SCO" parameter defines whether the voltage remains switched off ("False") or
        automatically switches on again ("True", default) after a short circuit or overload of the sensor supply.
        In the case of the "Leave power switched off" setting, the CPX-E automation system must be switched
        off and on to restore the power.
        """
        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x01
        else:
            value_to_write = reg & 0xFE

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_debounce_time(self, value: int) -> None:
        """The "Input debounce time" parameter defines when an edge change of the sensor signal shall be
        assumed as a logical input signal.
        In this way, unwanted signal edge changes can be suppressed during switching operations (bouncing
        of the input signal).
        Accepted values are 0: 0.1 ms; 1: 3 ms (default); 2: 10 ms; 3: 20 ms;
        """
        if value < 0 or value > 3:
            raise ValueError("Value {value} must be between 0 and 3")

        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register, delete bit 4+5 from it and refill it with value
        value_to_write = (reg & 0xCF) | (value << 4)

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_signal_extension_time(self, value: int) -> None:
        """The "Signal extension time" parameter defines the minimum valid duration of the assumed signal
        status of the input signal. Edge changes within the signal extension time are ignored.
        Short input signals can also be recorded by defining a signal extension time.
        Accepted values are 0: 0.5 ms; 1: 15 ms (default); 2: 50 ms; 3: 100 ms;
        """
        if value < 0 or value > 3:
            raise ValueError("Value {value} must be between 0 and 3")

        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register, delete bit 6+7 from it and refill it with value
        value_to_write = (reg & 0x3F) | (value << 6)

        self.base.write_function_number(function_number, value_to_write)


class CpxE4AiUI(_CpxEModule):
    """Class for CPX-E-4AI-UI module"""

    def _initialize(self, *args):
        super()._initialize(*args)

        self.output_register = None
        self.input_register = self.base._next_input_register

        # self.base._next_output_register = self.base._next_output_register + 0
        self.base._next_input_register = self.input_register + 5

    @CpxBase._require_base
    def read_channels(self) -> list[int]:
        '''read all channels as a list of (signed) integers
        '''
        raw_data = self.base.read_reg_data(self.input_register, length=4)
        data = [CpxBase._decode_int([x]) for x in raw_data]
        return data

    @CpxBase._require_base
    def read_status(self) -> list[bool]:
        """read module status register. Further information see module datasheet"""
        data = self.base.read_reg_data(self.input_register + 4)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @CpxBase._require_base
    def read_channel(self, channel: int) -> bool:
        """read back the value of one channel"""
        return self.read_channels()[channel]

    @CpxBase._require_base
    def configure_channel_range(self, channel: int, signalrange: str) -> None:
        """set the signal range and type of one channel"""
        bitmask = {
            "None": 0b0000,
            "0-10V": 0b0001,
            "-10-+10V": 0b0010,
            "-5-+5V": 0b0011,
            "1-5V": 0b0100,
            "0-20mA": 0b0101,
            "4-20mA": 0b0110,
            "-20-+20mA": 0b0111,
            "0-10VoU": 0b1000,
            "0-20mAoU": 0b1001,
            "4-20mAoU": 0b1010,
        }
        if signalrange not in bitmask:
            raise ValueError(
                f"'{signalrange}' is not an option. Choose from {bitmask.keys()}"
            )

        function_number = 4828 + 64 * self.position

        reg_01 = self.base.read_function_number(function_number + 13)[0]
        reg_23 = self.base.read_function_number(function_number + 14)[0]

        if channel == 0:
            function_number += 13
            value_to_write = reg_01 | bitmask[signalrange]
        elif channel == 1:
            function_number += 13
            value_to_write = reg_01 | bitmask[signalrange] << 4
        elif channel == 2:
            function_number += 14
            value_to_write = reg_23 | bitmask[signalrange]
        elif channel == 3:
            function_number += 14
            value_to_write = reg_23 | bitmask[signalrange] << 4
        else:
            raise ValueError(f"'{channel}' is not in range 0...3")

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_channel_smoothing(self, channel: int, smoothing_power: int) -> None:
        """set the signal smoothing of one channel"""
        if smoothing_power > 15:
            raise ValueError(f"'{smoothing_power}' is not an option")

        bitmask = smoothing_power

        function_number = 4828 + 64 * self.position

        reg_01 = self.base.read_function_number(function_number + 15)[0]
        reg_23 = self.base.read_function_number(function_number + 16)[0]

        if channel == 0:
            function_number += 15
            value_to_write = reg_01 | bitmask
        elif channel == 1:
            function_number += 15
            value_to_write = reg_01 | bitmask << 4
        elif channel == 2:
            function_number += 16
            value_to_write = reg_23 | bitmask
        elif channel == 3:
            function_number += 16
            value_to_write = reg_23 | bitmask << 4
        else:
            raise ValueError(f"'{channel}' is not in range 0...3")

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_diagnostics(self, short_circuit=None, param_error=None):
        """The "Diagnostics of sensor supply short circuit" defines whether the diagnostics of the sensor supply
        in regard to short circuit or overload should be activated ("True", default) or deactivated ("False").
        The parameter "Diagnostics of parameterisation error" defines if the diagnostics for the subsequently
        listed parameters must be activated ("True", default) or deactivated ("False) with regard to unapproved settings:
         * Hysteresis < 0
         * Signal range (sensor type)
         * Lower limit > upper limit
        When the diagnostics are activated, the error will be sent to the bus module and displayed on the
        module by the error LED.
        """
        function_number = 4828 + 64 * self.position + 0
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if short_circuit == None:
            short_circuit = bool((reg & 0x01) >> 0)
        if param_error == None:
            param_error = bool((reg & 0x80) >> 7)

        value_to_write = (int(short_circuit) << 0) | (int(param_error) << 7)

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_power_reset(self, value: bool) -> None:
        """The "Behaviour after SCO" parameter defines whether the voltage remains switched off ("False") or automatically
        switches on ("True, default") again after a short circuit or overload of the sensor supply.
        In the case of the "Leave power switched off" setting, the CPX-E automation system must be switched
        off and on to restore the power
        """
        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x01
        else:
            value_to_write = reg & 0xFE

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_data_format(self, value: bool) -> None:
        """The parameter "Data format" defines the “Sign + 15 bit” or “linear scaling”.
        * False (default): Sign + 15 bit
        * True: Linear scaled
        """
        function_number = 4828 + 64 * self.position + 6
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x01
        else:
            value_to_write = reg & 0xFE

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_sensor_supply(self, value: bool) -> None:
        """The parameter "Sensor supply" defines if the sensor supply must be switched off ("False")
        or switched on ("True", default).
        The sensor supply can also be switched off and switched on during operation.
        """
        function_number = 4828 + 64 * self.position + 6
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x20
        else:
            value_to_write = reg & 0xDF

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_diagnostics_overload(self, value: bool) -> None:
        """The parameter "Diagnostics of overload at analogue inputs" defines if the diagnostics for the current
        inputs must be activated ("True", default) or deactivated ("False") with regard to overload.
        When the diagnostics are activated, the error at an input current of >30 mA will be sent to the bus
        module and displayed with the error LED on the module.
        """
        function_number = 4828 + 64 * self.position + 6
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x40
        else:
            value_to_write = reg & 0xBF

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_behaviour_overload(self, value: bool) -> None:
        """The parameter "Behaviour after overload at analogue inputs" defines if the power remains switched
        off ("False") after an overload at the inputs or if it should be switched on again ("True", default) automatically.
        In the case of the "Leave power switched off" setting, the automation system CPX-E must be switched
        off and on to restore the power.
        """
        function_number = 4828 + 64 * self.position + 6
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x80
        else:
            value_to_write = reg & 0x7F

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_hysteresis_limit_monitoring(
        self, lower: int | None = None, upper: int | None = None
    ) -> None:
        """The parameter "Hysteresis of limit monitoring" defines the hysteresis value of the limit monitoring for
        all channels.
        The set hysteresis value must not be larger than the difference between the upper and lower limit values.
        The defined value is not checked for validity and incorrect parameterisations will be applied.
        """
        if lower:
            if lower < 0 or lower > 32767:
                raise ValueError("Values for low {low} must be between 0 and 32767")
        if upper:
            if upper < 0 or upper > 32767:
                raise ValueError("Values for high {high} must be between 0 and 32767")

        function_number_lower = 4828 + 64 * self.position + 7
        function_number_upper = 4828 + 64 * self.position + 8

        if lower == None and isinstance(upper, int):
            self.base.write_function_number(function_number_upper, upper)
        elif upper == None and isinstance(lower, int):
            self.base.write_function_number(function_number_lower, lower)
        elif isinstance(upper, int) and isinstance(lower, int):
            self.base.write_function_number(function_number_upper, upper)
            self.base.write_function_number(function_number_lower, lower)
        else:
            raise ValueError("Value must be given for upper, lower or both")

    # TODO: add more functions CPX-E-_AI-U-I_description_2020-01a_8126669g1.pdf chapter 3.3 ff.


class CpxE4AoUI(_CpxEModule):
    """Class for CPX-E-4AO-UI module"""

    def _initialize(self, *args):
        super()._initialize(*args)

        self.output_register = self.base._next_output_register
        self.input_register = self.base._next_input_register

        self.base._next_output_register = self.output_register + 4
        self.base._next_input_register = self.input_register + 5

    @CpxBase._require_base
    def read_channels(self) -> list[int]:
        '''read all channels as a list of integer values
        '''
        raw_data = self.base.read_reg_data(self.input_register, length=4)
        data = [CpxBase._decode_int([x]) for x in raw_data]
        return data

    @CpxBase._require_base
    def read_status(self) -> list[bool]:
        """read module status register. Further information see module datasheet"""
        data = self.base.read_reg_data(self.input_register + 4)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @CpxBase._require_base
    def read_channel(self, channel: int) -> bool:
        """read back the value of one channel"""
        return self.read_channels()[channel]

    @CpxBase._require_base
    def write_channels(self, data: list[int]) -> None:
        '''write data to module channels in ascending order
        '''
        reg_data = [self.base._decode_int([x]) for x in data]
        self.base.write_reg_data(reg_data, self.output_register, length=4)

    @CpxBase._require_base
    def write_channel(self, channel: int, data: int) -> None:
        '''write data to module channel number
        '''
        reg_data = self.base._decode_int([data])
        self.base.write_reg_data(reg_data, self.output_register + channel)

    @CpxBase._require_base
    def configure_channel_range(self, channel: int, signalrange: str):
        """set the signal range and type of one channel"""
        bitmask = {
            "0-10V": 0b0001,
            "-10-+10V": 0b0010,
            "-5-+5V": 0b0011,
            "1-5V": 0b0100,
            "0-20mA": 0b0101,
            "4-20mA": 0b0110,
            "-20-+20mA": 0b0111,
        }
        if signalrange not in bitmask:
            raise ValueError(
                f"'{signalrange}' is not an option. Choose from {bitmask.keys()}"
            )

        function_number = 4828 + 64 * self.position

        reg_01 = self.base.read_function_number(function_number + 11)[0]
        reg_23 = self.base.read_function_number(function_number + 12)[0]

        if channel == 0:
            function_number += 11
            value_to_write = reg_01 | bitmask[signalrange]
        elif channel == 1:
            function_number += 11
            value_to_write = reg_01 | bitmask[signalrange] << 4
        elif channel == 2:
            function_number += 12
            value_to_write = reg_23 | bitmask[signalrange]
        elif channel == 3:
            function_number += 12
            value_to_write = reg_23 | bitmask[signalrange] << 4
        else:
            raise ValueError(f"'{channel}' is not in range 0...3")

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_diagnostics(
        self, short_circuit=None, undervoltage=None, param_error=None
    ):
        """The parameter "Diagnostics of short circuit in actuator supply" defines if the diagnostics for the
        actuator supply with regard to short circuit or overload must be activated ("True", default) or deactivated ("False").
        When the diagnostics are activated, the error will be sent to the bus module and displayed on the module by the
        error LED.
        """
        function_number = 4828 + 64 * self.position + 0
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if short_circuit == None:
            short_circuit = bool((reg & 0x01) >> 1)
        if undervoltage == None:
            undervoltage = bool((reg & 0x04) >> 2)
        if param_error == None:
            param_error = bool((reg & 0x80) >> 7)

        value_to_write = (
            (int(short_circuit) << 1)
            | (int(undervoltage) << 2)
            | (int(param_error) << 7)
        )

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_power_reset(self, value: bool) -> None:
        """he parameter “Behaviour after SCS actuator supply” defines if the power remains switched off ("False) after a
        short circuit or overload of the actuator supply or if it should be switched on again automatically ("True", default).
        In the case of the "Leave power switched off" setting, the automation system CPX-E must be switched
        off and on to restore the power.
        """
        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x02
        else:
            value_to_write = reg & 0xFD

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_behaviour_overload(self, value: bool) -> None:
        """The parameter “Behaviour after SCS analogue output” defines if the power remains switched off ("False") after
        a short circuit or overload at the outputs or if it should be switched on again automatically ("True", default). In the case
        of the "Leave power switched off" setting, the automation system CPX-E must be switched off and on
        to restore the power.
        """
        function_number = 4828 + 64 * self.position + 1
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x08
        else:
            value_to_write = reg & 0xF7

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_data_format(self, value: bool) -> None:
        """The parameter “Data format” defines the data format "Sign + 15 bit” or “linear scaled".
        * False (default): Sign + 15 bit
        * True: Linear scaled
        """
        function_number = 4828 + 64 * self.position + 6
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x01
        else:
            value_to_write = reg & 0xFE

        self.base.write_function_number(function_number, value_to_write)

    @CpxBase._require_base
    def configure_actuator_supply(self, value: bool) -> None:
        """The parameter “Actuator supply” defines if the diagnostics for the actuator supply
        must be activated ("True", default) or deactivated ("False").

        """
        function_number = 4828 + 64 * self.position + 6
        reg = self.base.read_function_number(function_number)[0]

        # Fill in the unchanged values from the register
        if value:
            value_to_write = reg | 0x20
        else:
            value_to_write = reg & 0xDF

        self.base.write_function_number(function_number, value_to_write)

    # TODO: add more functions CPX-E-_AO-U-I_description_2020-01a_8126651g1.pdf chapter 3.3 ff.


class CpxE4Iol(_CpxEModule):
    # TODO: Add IO-Link module
    def __init__(self):
        raise NotImplementedError("The module CPX-E-4IOL has not yet been implemented")


class CpxE1Cl(_CpxEModule):
    # TODO: Add 1Cl module
    def __init__(self):
        raise NotImplementedError("The module CPX-E-1Cl has not yet been implemented")