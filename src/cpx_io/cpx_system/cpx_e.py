'''TODO: Add module docstring
'''

import logging
import ctypes

from .cpx_base import CpxBase


class InitError(Exception):
    '''Error should be raised if a cpx-e-... module is instanciated without connecting it to a base module.
    Connect it to the cpx-e by adding it with add_module(<object instance>)
    '''
    def __init__(self, message="Module must be part of a cpx_e class. Use add_module() to add it"):
        super().__init__(message)


class _ModbusCommands:
    '''Modbus start adresses used to read and write registers
    '''
    # (RegAdress, Length)
    # input registers

    # holding registers
    process_data_outputs=(40001,1)
    data_system_table_write=(40002,1)

    process_data_inputs=(45392,1)
    data_system_table_read=(45393,1)

    module_configuration=(45367,3)
    fault_detection=(45383,3)
    status_register=(45391,1)


class CpxE(CpxBase):
    '''CPX-E base class
    '''
    def __init__(self, modules=None, **kwargs):
        super().__init__(**kwargs)
        self._control_bit_value = 1 << 15
        self._write_bit_value = 1 << 13

        self._next_output_register = 0
        self._next_input_register = 0

        self.output_register = None
        self.input_register = None

        self.modules = {}

        if modules:
            for m in modules:
                self.add_module(m)
        else:
            self.add_module(CpxEEp())

    def write_function_number(self, function_number: int, value: int):
        '''Write parameters via function number
        '''
        self.write_reg_data(value, *_ModbusCommands.data_system_table_write)
        #self.write_reg_data(0, *_ModbusCommands.process_data_outputs) # TODO: needed?
        self.write_reg_data(self._control_bit_value | self._write_bit_value | function_number,
                            *_ModbusCommands.process_data_outputs)

        data = 0
        its = 0
        while (data & self._control_bit_value) == 0 and its < 1000:
            data = self.read_reg_data(*_ModbusCommands.process_data_inputs)[0]
            its += 1

        if its >= 1000:
            raise ConnectionError()

        data &= ~self._control_bit_value
        data2 = self.read_reg_data(*_ModbusCommands.data_system_table_read)[0]
        logging.info(f"Write Data({value}) to {function_number}: {data} and {data2}")

    def read_function_number(self, function_number: int):
        '''Read parameters via function number
        '''
        #self.write_reg_data(0, *_ModbusCommands.process_data_outputs) # TODO: needed?
        self.write_reg_data(self._control_bit_value | function_number,
                          *_ModbusCommands.process_data_outputs)

        data = 0
        its = 0
        while (data & self._control_bit_value) == 0 and its < 1000:
            data = self.read_reg_data(*_ModbusCommands.process_data_inputs)[0]
            its += 1

        if its >= 1000:
            raise ConnectionError()

        data &= ~self._control_bit_value
        data2 = self.read_reg_data(*_ModbusCommands.data_system_table_read)
        logging.info(f"Read Data from {function_number}: {data} and {data2}")
        return data2

    def module_count(self) -> int:
        ''' returns the total count of attached modules
        '''
        data = self.read_reg_data(*_ModbusCommands.module_configuration)
        return sum(d.bit_count() for d in data)

    def fault_detection(self) -> list[bool]:
        ''' returns list of bools with Errors (True = Error)
        '''
        data = self.read_reg_data(*_ModbusCommands.fault_detection)
        data = data[2] << 16 + data[1] << 8 + data[0]
        return [d == "1" for d in bin(data)[2:].zfill(24)[::-1]]

    def status_register(self) -> tuple:
        ''' returns (Write-protected, Force active)
        '''
        write_protect_bit = 1 << 11
        force_active_bit = 1 << 15
        data = self.read_reg_data(*_ModbusCommands.status_register)
        return (bool(data[0] & write_protect_bit), bool(data[0] & force_active_bit))

    def read_device_identification(self) -> int:
        ''' returns Objects IDO 1,2,3,4,5
        '''
        data = self.read_function_number(43)
        return data[0]

    def add_module(self, module):
        '''Adds one module to the base. This is required to use the module.
        '''
        module._initialize(self, len(self.modules))
        return module


class _CpxEModule(CpxE):
    '''Base class for cpx-e modules
    '''
    def __init__(self):
        self.base = None
        self.position = None

    def _initialize(self, base, position):
        self.base = base
        self.position = position

    @staticmethod
    def _require_base(func):
        def wrapper(self, *args):
            if not self.base:
                raise InitError()
            return func(self, *args)
        return wrapper
    
    @staticmethod
    def int_to_signed16(value: int, bits=16):
        '''Converts a int to 16 bit register where msb is the sign
        '''
        if (value <= -32768) or (value > 32768):
            raise ValueError(f"Integer value {value} must be in range -32768...32767 (15 bit)")
        
        if value >=0:
            return value
        else:
            return (1 << (bits - 1)) | ((value - (1 << bits)) & (((1 << bits) -1) // 2))
    
    @staticmethod
    def signed16_to_int(value: int, bits=16):
        '''Converts a 16 bit register where msb is the sign to python signed int
        by computing the two's complement 
        '''
        if (value & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            value = value - (1 << bits)        # compute negative value
        return value

class CpxEEp(_CpxEModule):
    '''Class for CPX-E-EP module
    '''
    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-EP"] = self.position

        self.output_register = _ModbusCommands.process_data_outputs[0]
        self.input_register = _ModbusCommands.process_data_inputs[0]

        self.base._next_output_register = self.output_register + 2
        self.base._next_input_register = self.input_register + 3


class CpxE8Do(_CpxEModule):
    '''Class for CPX-E-8DO module
    '''

    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-8DO"] = self.position

        self.output_register = self.base._next_output_register
        self.input_register = self.base._next_input_register

        self.base._next_output_register = self.output_register + 1
        self.base._next_input_register = self.input_register + 2

    @_CpxEModule._require_base
    def read_channels(self) -> list[bool]:
        '''read all channels as a list of bool values
        '''
        # TODO: This register reads back 0
        data = self.base.read_reg_data(self.input_register)[0] & 0x0F
        return [d == "1" for d in bin(data)[2:].zfill(8)[::-1]]

    @_CpxEModule._require_base
    def write_channels(self, data: list[bool]) -> None:
        '''write all channels with a list of bool values
        '''
        # Make binary from list of bools
        binary_string = ''.join('1' if value else '0' for value in reversed(data))
        # Convert the binary string to an integer
        integer_data = int(binary_string, 2)
        self.base.write_reg_data(integer_data, self.output_register)

    @_CpxEModule._require_base
    def read_status(self) -> list[bool]:
        '''read module status register. Further information see module datasheet
        '''
        data = self.base.read_reg_data(self.input_register + 1)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @_CpxEModule._require_base
    def read_channel(self, channel: int) -> bool:
        '''read back the value of one channel
        '''
        return self.read_channels()[channel]

    @_CpxEModule._require_base
    def set_channel(self, channel: int) -> None:
        '''set one channel to logic high level
        '''
        data = self.base.read_reg_data(self.input_register)[0]
        self.base.write_reg_data(data | 1 << channel , self.output_register)

    @_CpxEModule._require_base
    def clear_channel(self, channel: int) -> None:
        '''set one channel to logic low level
        '''
        data = self.base.read_reg_data(self.input_register)[0]
        self.base.write_reg_data(data & ~(1 << channel), self.output_register)

    @_CpxEModule._require_base
    def toggle_channel(self, channel: int) -> None:
        '''set one channel the inverted of current logic level
        '''
        data = (self.base.read_reg_data(self.input_register)[0] & 1 << channel) >> channel
        if data == 1:
            self.clear_channel(channel)
        elif data == 0:
            self.set_channel(channel)
        else:
            raise ValueError
        
    @_CpxEModule._require_base
    def set_diagnostics(self, **kwargs):
        '''Sets diagnostics. Allowed keywords are "short_circuit" and "undervoltage"
        '''
        if "short_circuit" in kwargs:
            self.write_function_number(4828 + 64 * self.position + 0)
        elif "undervoltage" in kwargs:
            self.write_function_number(4828 + 64 * self.position + 0)
        else:
            raise KeyError("Key not known. Allowed keys are 'short_circuit' and 'undervoltage'.")
    
    @_CpxEModule._require_base
    def set_behaviour_after_SCO(self, value: bool):
        pass


class CpxE16Di(_CpxEModule):
    '''Class for CPX-E-16DI module
    '''

    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-16DI"] = self.position

        self.output_register = None
        self.input_register = self.base._next_input_register

        #self.base._next_output_register = self.base._next_output_register + 0
        self.base._next_input_register = self.input_register + 2

    @_CpxEModule._require_base
    def read_channels(self) -> list[bool]:
        '''read all channels as a list of bool values
        '''
        data = self.base.read_reg_data(self.input_register)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @_CpxEModule._require_base
    def read_status(self) -> list[bool]:
        '''read module status register. Further information see module datasheet
        '''
        data = self.base.read_reg_data(self.input_register + 1)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @_CpxEModule._require_base
    def read_channel(self, channel: int) -> bool:
        '''read back the value of one channel
        '''
        return self.read_channels()[channel]


class CpxE4AiUI(_CpxEModule):
    '''Class for CPX-E-4AI-UI module
    '''

    def __init__(self, *args):
        super().__init__(*args)

        self._signalrange_01 = 0
        self._signalrange_23 = 0
        self._signalsmothing_01 = 0
        self._signalsmothing_23 = 0

    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-4AI_U_I"] = self.position

        self.output_register = None
        self.input_register = self.base._next_input_register

        #self.base._next_output_register = self.base._next_output_register + 0
        self.base._next_input_register = self.input_register + 5

    @_CpxEModule._require_base
    def read_channels(self) -> list[int]:
        '''read all channels as a list of (signed) integers
        '''
        # TODO: add signal conversion according to signalrange of the channel
        raw_data = self.base.read_reg_data(self.input_register, length=4)
        signed_integers = [self.signed16_to_int(x) for x in raw_data]
        return signed_integers

    @_CpxEModule._require_base
    def read_status(self) -> list[bool]:
        '''read module status register. Further information see module datasheet
        '''
        data = self.base.read_reg_data(self.input_register + 4)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @_CpxEModule._require_base
    def read_channel(self, channel: int) -> bool:
        '''read back the value of one channel
        '''
        return self.read_channels()[channel]

    @_CpxEModule._require_base
    def set_channel_range(self, channel: int, signalrange: str) -> None:
        '''set the signal range and type of one channel
        '''
        signal_dict = {
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
            "4-20mAoU": 0b1010
        }
        if signalrange not in signal_dict:
            raise ValueError(f"'{signalrange}' is not an option")

        keepbits = 0x0F
        bitmask = signal_dict[signalrange]

        if channel in [1,3]:
            bitmask <<= 4
        else:
            keepbits <<= 4

        if channel < 2:
            function_number = 4828 + 64 * self.position + 13
            self._signalrange_01 &= keepbits
            self._signalrange_01 |= bitmask
            self.base.write_function_number(function_number, self._signalrange_01)
        elif 2 <= channel < 4:
            function_number = 4828 + 64 * self.position + 14
            self._signalrange_23 &= keepbits
            self._signalrange_23 |= bitmask
            self.base.write_function_number(function_number, self._signalrange_23)
        else:
            raise ValueError(f"'{channel}' is not in range 0...3")

    @_CpxEModule._require_base
    def set_channel_smothing(self, channel: int, smothing_power: int) -> None:
        '''set the signal smoothing of one channel
        '''
        if smothing_power > 15:
            raise ValueError(f"'{smothing_power}' is not an option")

        keepbits = 0x0F
        bitmask = smothing_power

        if channel in [1, 3]:
            bitmask <<= 4
        else:
            keepbits <<= 4

        if channel < 2:
            function_number = 4828 + 64 * self.position + 15
            self._signalsmothing_01 &= keepbits
            self._signalsmothing_01 |=  bitmask
            self.base.write_function_number(function_number, self._signalsmothing_01)
        elif 2 <= channel < 4:
            function_number = 4828 + 64 * self.position + 16
            self._signalsmothing_23 &= keepbits
            self._signalsmothing_23 |= bitmask
            self.base.write_function_number(function_number, self._signalsmothing_23)
        else:
            raise ValueError(f"'{channel}' is not in range 0...3")


class CpxE4AoUI(_CpxEModule):
    '''Class for CPX-E-4AO-UI module
    '''
    def __init__(self, *args):
        super().__init__(*args)

        self._signalrange_01 = 0b00010001
        self._signalrange_23 = 0b00010001

    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-4AO_U_I"] = self.position

        self.output_register = self.base._next_output_register
        self.input_register = self.base._next_input_register

        self.base._next_output_register = self.output_register  + 4
        self.base._next_input_register = self.input_register + 5

    @_CpxEModule._require_base
    def read_channels(self) -> list[int]:
        '''read all channels as a list of integer values
        '''
        # TODO: add signal conversion according to signalrange of the channel
        raw_data = self.base.read_reg_data(self.input_register, length=4)
        signed_integers = [self.signed16_to_int(x) for x in raw_data]
        return signed_integers

    @_CpxEModule._require_base
    def read_status(self) -> list[bool]:
        '''read module status register. Further information see module datasheet
        '''
        data = self.base.read_reg_data(self.input_register + 4)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]

    @_CpxEModule._require_base
    def read_channel(self, channel: int) -> bool:
        '''read back the value of one channel
        '''
        return self.read_channels()[channel]

    @_CpxEModule._require_base
    def write_channels(self, data: list[int]) -> None:
        '''write data to module channels in ascending order
        '''
        # TODO: scaling to given signalrange
        reg_data = [self.int_to_signed16(x) for x in data]
        self.base.write_reg_data(reg_data, self.output_register, length=4)

    @_CpxEModule._require_base
    def write_channel(self, channel: int, data: int) -> None:
        '''write data to module channel number
        '''
        # TODO: scaling to given signalrange
        reg_data = self.int_to_signed16(data)
        self.base.write_reg_data(reg_data, self.output_register + channel)

    @_CpxEModule._require_base
    def set_channel_range(self, channel: int, signalrange: str):
        '''set the signal range and type of one channel
        '''
        signal_dict = {
            "0-10V": 0b0001,
            "-10-+10V": 0b0010,
            "-5-+5V": 0b0011,
            "1-5V": 0b0100,
            "0-20mA": 0b0101,
            "4-20mA": 0b0110,
            "-20-+20mA": 0b0111
        }
        if signalrange not in signal_dict:
            raise ValueError(f"'{signalrange}' is not an option")

        keepbits = 0b1111
        bitmask = signal_dict[signalrange]

        if channel in [1, 3]:
            bitmask <<= 4
        else:
            keepbits <<= 4

        if channel < 2:
            function_number = 4828 + 64 * self.position + 11
            self._signalrange_01 &= keepbits
            self._signalrange_01 |= bitmask
            self.base.write_function_number(function_number, self._signalrange_01)
        elif 2 <= channel < 4:
            function_number = 4828 + 64 * self.position + 12
            self._signalrange_23 &= keepbits
            self._signalrange_23 |= bitmask
            self.base.write_function_number(function_number, self._signalrange_23)
        else:
            raise ValueError(f"'{channel}' is not in range 0...3")


# TODO: Add IO-Link module
