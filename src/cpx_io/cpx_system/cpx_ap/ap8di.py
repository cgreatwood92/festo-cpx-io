"""CPX-AP-`*`-8DI-`*` module implementation"""

# pylint: disable=duplicate-code
# intended: modules have similar functions

from cpx_io.cpx_system.cpx_base import CpxBase
from cpx_io.cpx_system.cpx_ap.cpx_ap_module import CpxApModule
from cpx_io.cpx_system.parameter_mapping import ParameterNameMap
from cpx_io.utils.boollist import bytes_to_boollist
from cpx_io.utils.helpers import value_range_check
from cpx_io.utils.logging import Logging
from cpx_io.cpx_system.cpx_ap.cpx_ap_enums import DebounceTime


class CpxAp8Di(CpxApModule):
    """Class for CPX-AP-`*`-8DI-`*` module"""

    module_codes = {
        8199: "CPX-AP-I-8DI-M8-3P",
        8200: "CPX-AP-I-8DI-M12-5P",
        12297: "CPX-AP-A-8DI-M12-5P",
    }

    def __getitem__(self, key):
        return self.read_channel(key)

    @CpxBase.require_base
    def read_channels(self) -> list[bool]:
        """read all channels as a list of bool values

        :return: Values of all channels
        :rtype: list[bool]
        """
        data = self.base.read_reg_data(self.input_register)
        values = bytes_to_boollist(data)[:8]
        Logging.logger.info(f"{self.name}: Reading channels: {values}")
        return values

    @CpxBase.require_base
    def read_channel(self, channel: int) -> bool:
        """read back the value of one channel

        :param channel: Channel number, starting with 0
        :type channel: int
        :return: Value of the channel
        :rtype: bool
        """
        return self.read_channels()[channel]

    @CpxBase.require_base
    def configure_debounce_time(self, value: DebounceTime | int) -> None:
        """
        The "Input debounce time" parameter defines when an edge change of the sensor signal
        shall be assumed as a logical input signal. In this way, unwanted signal edge changes
        can be suppressed during switching operations (bouncing of the input signal).

          * 0: 0.1 ms
          * 1: 3 ms (default)
          * 2: 10 ms
          * 3: 20 ms

        :param value: Debounce time for all channels. Use DebounceTime from cpx_ap_enums or
        see datasheet.
        :type value: DebounceTime | int
        """

        if isinstance(value, DebounceTime):
            value = value.value

        value_range_check(value, 4)

        self.base.write_parameter(
            self.position, ParameterNameMap()["InputDebounceTime"], value
        )

        Logging.logger.info(f"{self.name}: Setting debounce time to {value}")
