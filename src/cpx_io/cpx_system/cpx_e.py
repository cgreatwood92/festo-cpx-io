__author__ = "Wiesner, Martin"
__copyright__ = "Copyright 2022, Festo"
__credits__ = [""]
__license__ = "Apache"
__version__ = "0.0.1"
__maintainer__ = "Wiesner, Martin"
__email__ = "martin.wiesner@festo.com"
__status__ = "Development"


import logging

# TODO: Fix imports
if __name__ == "__main__":
    from cpx_base import CPX_BASE
else:
    from .cpx_base import CPX_BASE


class InitError(Exception):
    def __init__(self, message="Module must be part of a cpx_e class. Use add_module() to add it"):
        super().__init__(message)


class _ModbusCommands:    
    # (RegAdress, Length)
    # input registers

    # holding registers
    RequestDiagnosis=(40001,1)
    DataSystemTableWrite=(4002,1)

    ResponseDiagnosis=(45392,1)
    DataSystemTableRead=(45393,1)
    #ModuleDiagnosisData=(45394,1)

    ModuleConfiguration=(45367,3)
    FaultDetection=(45383,3)
    StatusRegister=(45391,1)


class CPX_E(CPX_BASE):

    def __init__(self, modules=None, **kwargs):
        super().__init__(**kwargs)
        self._control_bit_value = 1 << 15
        self._write_bit_value = 1 << 13
        
        self._next_output_register = 0
        self._next_input_register = 0

        self.modules = {}
        
        if modules:
            for m in modules:
                self.add_module(m)
        else:
            self.add_module(CPX_E_EP())

    def writeFunctionNumber(self, FunctionNumber: int, value: int):
        self.writeRegData(value, *_ModbusCommands.DataSystemTableWrite)
        self.writeRegData(0, *_ModbusCommands.RequestDiagnosis)
        self.writeRegData(self._control_bit_value | self._write_bit_value | FunctionNumber, 
                            *_ModbusCommands.RequestDiagnosis)

        data = 0
        its = 0
        while (data & self._control_bit_value) == 0 and its < 1000:
            data = self.readRegData(*_ModbusCommands.ResponseDiagnosis)[0]
            its += 1

        if its >= 1000:
            raise ConnectionError()

        data &= ~self._control_bit_value
        data2 = self.readRegData(*_ModbusCommands.DataSystemTableRead)[0]
        logging.info(f"Write Data({value}) to {FunctionNumber}: {data} and {data2} (after {its} iterations)")

    def readFunctionNumber(self, FunctionNumber: int):
        self.writeRegData(0, *_ModbusCommands.RequestDiagnosis)
        self.writeRegData(self._control_bit_value | FunctionNumber, *_ModbusCommands.RequestDiagnosis)

        data = 0
        its = 0
        while (data & self._control_bit_value) == 0 and its < 1000:
            data = self.readRegData(*_ModbusCommands.ResponseDiagnosis)[0]
            its += 1

        if its >= 1000:
            raise ConnectionError()

        data &= ~self._control_bit_value
        data2 = self.readRegData(*_ModbusCommands.DataSystemTableRead)
        logging.info(f"Read Data from {FunctionNumber}: {data} and {data2} (after {its} iterations)")
        return data2

    def module_count(self) -> int:
        ''' returns the total count of attached modules
        '''
        data = self.readRegData(*_ModbusCommands.ModuleConfiguration)
        return sum([bin(d).count("1") for d in data])

    def fault_detection(self) -> list[bool]:
        ''' returns list of bools with Errors (True)
        '''
        data = self.readRegData(*_ModbusCommands.FaultDetection)
        data = data[2] << 16 + data[1] << 8 + data[0] 
        return [d == "1" for d in bin(data)[2:].zfill(24)[::-1]] 

    def status_register(self) -> tuple:
        ''' returns (Write-protected, Force active)
        '''
        writeProtectBit = 11
        forceActiveBit = 15
        data = self.readRegData(*_ModbusCommands.StatusRegister)
        return (bool(data[0] & 1 << writeProtectBit), bool(data[0] & 1 << forceActiveBit))

    def read_device_identification(self) -> int:
        ''' returns Objects IDO 1,2,3,4,5
        '''
        data = self.readFunctionNumber(43)
        return data[0] 

    def add_module(self, module):
        module._initialize(self, len(self.modules), self._next_output_register, self._next_input_register)
        return module

class CPX_E_MODULE(CPX_E):
    def __init__(self):
        pass

    def _initialize(self, base, position, output_reg_start, input_reg_start):
        self.base = base
        self.position = position

    def _require_base(self, func):
        def wrapper(*args, **kwargs):
            if self.base is None:
                raise InitError()
            return func(*args, **kwargs)
        return wrapper

class CPX_E_EP(CPX_E_MODULE):
    
    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-EP"] = self.position
        
        self.output_register = _ModbusCommands.RequestDiagnosis[0]
        self.input_register = _ModbusCommands.ResponseDiagnosis[0]

        self.base._next_output_register = self.output_register + 2
        self.base._next_input_register = self.input_register + 3

class CPX_E_8DO(CPX_E_MODULE):
    
    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-8DO"] = self.position

        self.output_register = self.base._next_output_register
        self.input_register = self.base._next_input_register

        self.base._next_output_register = self.output_register + 1
        self.base._next_input_register = self.input_register + 2
    
    @_require_base
    def read_channels(self) -> list[bool]:
        # TODO: This register reads back 0
        data = self.base.readRegData(self.input_register)[0] & 0x0F
        return [d == "1" for d in bin(data)[2:].zfill(8)[::-1]]

    @_require_base
    def write_channels(self, data: list[bool]) -> None:
        # Make binary from list of bools
        binary_string = ''.join('1' if value else '0' for value in reversed(data))
        # Convert the binary string to an integer
        integer_data = int(binary_string, 2)
        self.base.writeRegData(integer_data, self.output_register)

    @_require_base
    def read_status(self) -> list[bool]:
        data = self.base.readRegData(self.input_register + 1)[0]
        return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]
        
    def read_channel(self, channel: int) -> bool:
        if self.base:
            return self.read_channels()[channel]
        else:
            raise InitError()

    def set_channel(self, channel: int) -> None:
        if self.base:            
            data = self.base.readRegData(self.input_register)[0] 
            self.base.writeRegData(data | 1 << channel , self.output_register)
        else:
            raise InitError()
            
    def clear_channel(self, channel: int) -> None:
        if self.base: 
            data = self.base.readRegData(self.input_register)[0]
            self.base.writeRegData(data & ~(1 << channel), self.output_register)
        else:
            raise InitError()
    
    def toggle_channel(self, channel: int) -> None:
        if self.base: 
            data = (self.base.readRegData(self.input_register)[0] & 1 << channel) >> channel
            if data == 1:
                self.clear_channel(channel)
            elif data == 0:
                self.set_channel(channel)
            else:
                raise ValueError
        else:
            raise InitError()

class CPX_E_16DI(CPX_E_MODULE):
    
    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-16DI"] = self.position

        self.output_register = None
        self.input_register = self.base._next_input_register

        #self.base._next_output_register = self.base._next_output_register + 0
        self.base._next_input_register = self.input_register + 2

    def read_channels(self) -> list[bool]:
        if self.base:
            data = self.base.readRegData(self.input_register)[0]
            return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]
        else:
            raise InitError()

    def read_status(self) -> list[bool]:
        if self.base:            
            data = self.base.readRegData(self.input_register + 1)[0]
            return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]
        else:
            raise InitError()

    def read_channel(self, channel: int) -> bool:
        if self.base:
            return self.read_channels()[channel]
        else:
            raise InitError()

class CPX_E_4AI_U_I(CPX_E_MODULE):
    
    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-4AI_U_I"] = self.position

        self.output_register = None
        self.input_register = self.base._next_input_register

        #self.base._next_output_register = self.base._next_output_register + 0
        self.base._next_input_register = self.input_register + 5

        self._signalrange_01 = 0
        self._signalrange_23 = 0
        self._signalsmothing_01 = 0
        self._signalsmothing_23 = 0

    def read_channels(self) -> list[bool]:
        if self.base:
            # TODO: add signal conversion according to signalrange of the channel
            data = self.base.readRegData(self.input_register, length=4)
            return data
        else:
            raise InitError()

    def read_status(self) -> list[bool]:
        if self.base:
            data = self.base.readRegData(self.input_register + 4)[0]
            return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]
        else:
            raise InitError()

    def read_channel(self, channel: int) -> bool:
        if self.base:
            return self.read_channels()[channel]
        else:
            raise InitError()

    def set_channel_range(self, channel: int, signalrange: str) -> None:
        if self.base:
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
                functionNumber = 4828 + 64 * self.position + 13
                self._signalrange_01 &= keepbits
                self._signalrange_01 |= bitmask
                self.base.writeFunctionNumber(functionNumber, self._signalrange_01)
            elif 2 <= channel < 4:
                functionNumber = 4828 + 64 * self.position + 14
                self._signalrange_23 &= keepbits
                self._signalrange_23 |= bitmask
                self.base.writeFunctionNumber(functionNumber, self._signalrange_23)
            else:
                raise ValueError(f"'{channel}' is not in range 0...3")
        else:
            raise InitError()
                
    def set_channel_smothing(self, channel: int, smothing_power: int) -> None:
        if self.base:
            if smothing_power > 15:
                raise ValueError(f"'{smothing_power}' is not an option")

            keepbits = 0x0F
            bitmask = smothing_power

            if channel in [1, 3]:
                bitmask <<= 4
            else:
                keepbits <<= 4

            if channel < 2:
                functionNumber = 4828 + 64 * self.position + 15
                self._signalsmothing_01 &= keepbits
                self._signalsmothing_01 |=  bitmask
                self.base.writeFunctionNumber(functionNumber, self._signalsmothing_01)
            elif 2 <= channel < 4:
                functionNumber = 4828 + 64 * self.position + 16
                self._signalsmothing_23 &= keepbits
                self._signalsmothing_23 |= bitmask
                self.base.writeFunctionNumber(functionNumber, self._signalsmothing_23)
            else:
                raise ValueError(f"'{channel}' is not in range 0...3")
        else:
            raise InitError()

class CPX_E_4AO_U_I(CPX_E_MODULE):
    
    def _initialize(self, *args):
        super()._initialize(*args)

        self.base.modules["CPX-E-4AO_U_I"] = self.position

        self.output_register = self.base._next_output_register
        self.input_register = self.base._next_input_register

        self.base._next_output_register = self.output_register  + 4
        self.base._next_input_register = self.input_register + 5

        self._signalrange_01 = 0b00010001
        self._signalrange_23 = 0b00010001

    def read_channels(self) -> list[bool]:
        if self.base:
            # TODO: add signal conversion according to signalrange of the channel
            data = self.base.readRegData(self.input_register, length=4)
            return data
        else:
            raise InitError()

    def read_status(self) -> list[bool]:
        if self.base:
            data = self.base.readRegData(self.input_register + 4)[0]
            return [d == "1" for d in bin(data)[2:].zfill(16)[::-1]]
        else:
            raise InitError()

    def read_channel(self, channel: int) -> bool:
        if self.base:
            return self.read_channels()[channel]
        else:
            raise InitError()

    def write_channels(self, data: list[int]) -> None:
        if self.base:
            # TODO: scaling to given signalrange
            self.base.writeRegData(data, self.output_register, length=4)
        else:
            raise InitError()

    def write_channel(self, channel: int, data: int) -> None:
        if self.base:
            # TODO: scaling to given signalrange
            self.base.writeRegData(data, self.output_register + channel)
        else:
            raise InitError()

    def set_channel_range(self, channel: int, signalrange: str):
        if self.base:
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
                funcionNumber = 4828 + 64 * self.position + 11
                self._signalrange_01 &= keepbits
                self._signalrange_01 |= bitmask
                self.base.writeFunctionNumber(funcionNumber, self._signalrange_01)
            elif 2 <= channel < 4:
                funcionNumber = 4828 + 64 * self.position + 12
                self._signalrange_23 &= keepbits
                self._signalrange_23 |= bitmask
                self.base.writeFunctionNumber(funcionNumber, self._signalrange_23)
            else:
                raise ValueError(f"'{channel}' is not in range 0...3")
        else:
            raise InitError()


# TODO: Add IO-Link module
