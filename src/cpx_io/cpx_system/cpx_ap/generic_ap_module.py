"""Generic AP module implementation from APDD"""

import struct
import inspect
from typing import Any
from dataclasses import dataclass
from cpx_io.cpx_system.cpx_base import CpxBase, CpxRequestError
from cpx_io.cpx_system.cpx_ap.cpx_ap_module import CpxApModule
from cpx_io.cpx_system.cpx_ap.ap_parameter import ParameterEnum
from cpx_io.cpx_system.cpx_ap.ap_product_categories import ProductCategory
from cpx_io.cpx_system.cpx_ap import ap_registers
from cpx_io.utils.boollist import bytes_to_boollist, boollist_to_bytes
from cpx_io.utils.helpers import (
    div_ceil,
    channel_range_check,
    value_range_check,
    convert_uint32_to_octett,
    convert_to_mac_string,
)
from cpx_io.utils.logging import Logging


@dataclass
class Channel:
    """Channel dataclass"""

    bits: int
    channel_id: int
    data_type: str
    description: str
    direction: str
    name: str
    profile_list: list


@dataclass
class ChannelGroup:
    """ChannelGroup dataclass"""

    channel_group_id: int
    channels: dict
    name: str
    parameter_group_ids: list


class ChannelGroupBuilder:
    """ChannelGroupBuilder"""

    def build_channel_group(self, channel_group_dict):
        return ChannelGroup(
            channel_group_dict.get("ChannelGroupId"),
            channel_group_dict.get("Channels"),
            channel_group_dict.get("Name"),
            channel_group_dict.get("ParameterGroupIds"),
        )


class ChannelBuilder:
    """ChannelBuilder"""

    def build_channel(self, channel_dict):
        return Channel(
            channel_dict.get("Bits"),
            channel_dict.get("ChannelId"),
            channel_dict.get("DataType"),
            channel_dict.get("Description"),
            channel_dict.get("Direction"),
            channel_dict.get("Name"),
            channel_dict.get("ProfileList"),
        )


@dataclass
class SystemParameters:
    """SystemParameters"""

    # pylint: disable=too-many-instance-attributes
    dhcp_enable: bool = None
    ip_address: str = None
    subnet_mask: str = None
    gateway_address: str = None
    active_ip_address: str = None
    active_subnet_mask: str = None
    active_gateway_address: str = None
    mac_address: str = None
    setup_monitoring_load_supply: int = None


class GenericApModule(CpxApModule):

    def __init__(
        self,
        name,
        module_type,
        product_category,
        input_channels,
        output_channels,
        parameters,
        enums,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.name = name
        self.module_type = module_type
        self.product_category = product_category
        self.input_channels = input_channels
        self.output_channels = output_channels
        self.parameters = parameters
        self.enums = enums
        self.fieldbus_parameters = None

    def configure(self, *args, **kwargs):
        super().configure(*args, **kwargs)
        if self.product_category == ProductCategory.IO_LINK:
            self.fieldbus_parameters = self.read_fieldbus_parameters()

    def __repr__(self):
        return f"{self.name} (idx: {self.position}, type: {self.module_type})"

    def __getitem__(self, key):
        return self.read_channel(key)

    def __setitem__(self, key, value):
        self.write_channel(key, value)

    @CpxBase.require_base
    def read_ap_parameter(self) -> dict:
        """Read AP parameters

        :return: All AP parameters
        :rtype: dict
        """
        params = super().read_ap_parameter()

        if self.product_category == ProductCategory.IO_LINK:
            io_link_variant = self.base.read_parameter(
                self.position, self.parameters.get(20090)
            )

            activation_operating_voltage = self.base.read_parameter(
                self.position, self.parameters.get(20097)
            )

            params.io_link_variant = io_link_variant
            params.operating_supply = activation_operating_voltage
        return params

    @CpxBase.require_base
    def read_channels(self) -> Any:
        """Read all channels from module and interpret them as the module intends"""
        # check if supported
        supported_product_categories = [
            ProductCategory.ANALOG.value,
            ProductCategory.DIGITAL.value,
            ProductCategory.IO_LINK.value,
            ProductCategory.MPA_L.value,
            ProductCategory.MPA_S.value,
            ProductCategory.VTSA.value,
            ProductCategory.VTUG.value,
            ProductCategory.VTUX.value,
            ProductCategory.VTOM.value,
        ]
        if self.product_category not in supported_product_categories:
            raise NotImplementedError(
                f"{self} has no function <{inspect.currentframe().f_code.co_name}>"
            )

        # IO-Link special read
        if self.product_category == ProductCategory.IO_LINK.value:
            module_input_size = div_ceil(self.information.input_size, 2) - 2

            reg = self.base.read_reg_data(self.input_register, length=module_input_size)

            # 4 channels per module but channel_size should be in bytes while module_input_size
            # is in 16bit registers
            channel_size = (module_input_size) // 4 * 2

            channels = [
                reg[: channel_size * 1],
                reg[channel_size * 1 : channel_size * 2],
                reg[channel_size * 2 : channel_size * 3],
                reg[channel_size * 3 :],
            ]
            Logging.logger.info(f"{self.name}: Reading channels: {channels}")
            return channels

        # All other modules
        # if available, read inputs
        values = []
        if self.input_channels:
            data = self.base.read_reg_data(
                self.input_register, length=div_ceil(self.information.input_size, 2)
            )
            if all(c.data_type == "BOOL" for c in self.input_channels):
                values.extend(bytes_to_boollist(data)[: len(self.input_channels)])
            elif all(c.data_type == "INT16" for c in self.input_channels):
                values.extend(struct.unpack("<" + "h" * (len(data) // 2), data))
            else:
                raise NotImplementedError(
                    f"Input data type {self.input_channels[0].data_type} are not supported or "
                    "types are not the same for each channel"
                )

        # if available, read outputs
        if self.output_channels:
            data = self.base.read_reg_data(
                self.output_register, length=div_ceil(self.information.output_size, 2)
            )
            if all(c.data_type == "BOOL" for c in self.output_channels):
                values.extend(bytes_to_boollist(data)[: len(self.output_channels)])
            else:
                raise NotImplementedError(
                    f"Output data type {self.output_channels[0].data_type} are not supported or "
                    "types are not the same for each channel"
                )

        Logging.logger.info(f"{self.name}: Reading channels: {values}")
        return values

    @CpxBase.require_base
    def read_channel(
        self, channel: int, outputs_only: bool = False, full_size: bool = False
    ) -> Any:
        """read back the value of one channel
        For mixed IN/OUTput modules the optional parameter 'outputs_only' defines
        if the outputs are numbered WITH (after) the inputs ("False", default), so the range
        of output channels is <number of input channels>..<number of input and output channels>
        If "True", the outputs are numbered from 0..<number of output channels>, the inputs
        cannot be accessed this way.

        :param channel: Channel number, starting with 0
        :type channel: int
        :param outputs_only: Outputs should be numbered independend from inputs, optional
        :type outputs_only: bool
        :param full_size: IO-Link channes should be returned in full datalength and not
        limited to the slave information datalength
        :type full_size: bool
        :return: Value of the channel
        :rtype: bool
        """

        # IO-Link special read
        if self.product_category == ProductCategory.IO_LINK.value:

            if full_size:
                return self.read_channels()[channel]

            return self.read_channels()[channel][
                : self.fieldbus_parameters[channel]["Input data length"]
            ]

        # Other modules:
        if self.input_channels and outputs_only:
            channel += len(self.input_channels)

        return self.read_channels()[channel]

    @CpxBase.require_base
    def write_channels(self, data: list) -> None:
        """write all channels with a list of values

        :param data: list of values for each output channel. The type of the list elements must
        fit to the module type
        :type data: list
        """
        # check if supported
        supported_product_categories = [
            ProductCategory.ANALOG.value,
            ProductCategory.DIGITAL.value,
            ProductCategory.MPA_L.value,
            ProductCategory.MPA_S.value,
            ProductCategory.VTSA.value,
            ProductCategory.VTUG.value,
            ProductCategory.VTUX.value,
            ProductCategory.VTOM.value,
        ]
        if self.product_category not in supported_product_categories:
            raise NotImplementedError(
                f"{self} has no function " f"<{inspect.currentframe().f_code.co_name}>"
            )

        # IO-Link special (comment)
        # IO-Link does not support multiple channel writes as it seems to be unnessesary

        # Other modules
        if self.output_channels:
            if len(data) != len(self.output_channels):
                raise ValueError(
                    f"Data must be list of {len(self.output_channels)} elements"
                )

            if all(c.data_type == "BOOL" for c in self.output_channels) and all(
                isinstance(d, bool) for d in data
            ):
                reg = boollist_to_bytes(data)
            else:
                raise NotImplementedError(
                    f"Output data type {self.output_channels[0].data_type} are not supported or "
                    "types are not the same for each channel"
                )

            self.base.write_reg_data(reg, self.output_register)
            Logging.logger.info(f"{self.name}: Setting channels to {data}")

        else:
            raise NotImplementedError(
                f"Module {self.information.order_text} at index {self.position} "
                "has no outputs to write to"
            )

    @CpxBase.require_base
    def write_channel(self, channel: int, value: Any) -> None:
        """set one channel value

        :param channel: Channel number, starting with 0
        :type channel: int
        :value: Value that should be written to the channel
        :type value: Any
        """
        # check if supported
        supported_product_categories = [
            ProductCategory.ANALOG.value,
            ProductCategory.DIGITAL.value,
            ProductCategory.IO_LINK.value,
            ProductCategory.MPA_L.value,
            ProductCategory.MPA_S.value,
            ProductCategory.VTSA.value,
            ProductCategory.VTUG.value,
            ProductCategory.VTUX.value,
            ProductCategory.VTOM.value,
        ]
        if self.product_category not in supported_product_categories:
            raise NotImplementedError(
                f"{self} has no function " f"<{inspect.currentframe().f_code.co_name}>"
            )

        # IO-Link special
        if self.product_category == ProductCategory.IO_LINK.value:
            module_output_size = div_ceil(self.information.output_size, 2)
            channel_size = (module_output_size) // 4

            self.base.write_reg_data(
                value, self.output_register + channel_size * channel
            )
            Logging.logger.info(f"{self.name}: Setting channel {channel} to {value}")
            return

        if self.output_channels:
            channel_range_check(channel, len(self.output_channels))

            if all(c.data_type == "BOOL" for c in self.output_channels) and isinstance(
                value, bool
            ):
                data = bytes_to_boollist(self.base.read_reg_data(self.output_register))
                data[channel] = value
                reg = boollist_to_bytes(data)
                self.base.write_reg_data(reg, self.output_register)

            else:
                raise NotImplementedError(
                    f"{self.output_channels.data_type} is not supported or type(value) "
                    f"is not compatible"
                )
            Logging.logger.info(f"{self.name}: Setting channel {channel} to {value}")

        else:
            raise NotImplementedError(
                f"Module {self.information.ordercode} has no outputs to write to"
            )

    @CpxBase.require_base
    def set_channel(self, channel: int) -> None:
        """set one channel to logic high level

        :param channel: Channel number, starting with 0
        :type channel: int
        """
        # check if supported
        supported_product_categories = [
            ProductCategory.DIGITAL.value,
            ProductCategory.MPA_L.value,
            ProductCategory.MPA_S.value,
            ProductCategory.VTSA.value,
            ProductCategory.VTUG.value,
            ProductCategory.VTUX.value,
            ProductCategory.VTOM.value,
        ]
        if self.product_category not in supported_product_categories:
            raise NotImplementedError(
                f"{self} has no function " f"<{inspect.currentframe().f_code.co_name}>"
            )

        if self.output_channels:
            if self.output_channels[channel].data_type == "BOOL":
                self.write_channel(channel, True)
            else:
                raise TypeError(
                    f"{self} has has incompatible datatype "
                    f"{self.output_channels[channel].data_type} (should be 'BOOL')"
                )

    @CpxBase.require_base
    def clear_channel(self, channel: int) -> None:
        """set one channel to logic low level

        :param channel: Channel number, starting with 0
        :type channel: int
        """
        # check if supported
        supported_product_categories = [
            ProductCategory.DIGITAL.value,
            ProductCategory.MPA_L.value,
            ProductCategory.MPA_S.value,
            ProductCategory.VTSA.value,
            ProductCategory.VTUG.value,
            ProductCategory.VTUX.value,
            ProductCategory.VTOM.value,
        ]
        if self.product_category not in supported_product_categories:
            raise NotImplementedError(
                f"{self} has no function " f"<{inspect.currentframe().f_code.co_name}>"
            )

        if self.output_channels:
            if self.output_channels[channel].data_type == "BOOL":
                self.write_channel(channel, False)
            else:
                raise TypeError(
                    f"{self} has has incompatible datatype "
                    f"{self.output_channels[channel].data_type} (should be 'BOOL')"
                )

    @CpxBase.require_base
    def toggle_channel(self, channel: int) -> None:
        """set one channel the inverted of current logic level

        :param channel: Channel number, starting with 0
        :type channel: int
        """
        # check if supported
        supported_product_categories = [
            ProductCategory.DIGITAL.value,
            ProductCategory.MPA_L.value,
            ProductCategory.MPA_S.value,
            ProductCategory.VTSA.value,
            ProductCategory.VTUG.value,
            ProductCategory.VTUX.value,
            ProductCategory.VTOM.value,
        ]
        if self.product_category not in supported_product_categories:
            raise NotImplementedError(
                f"{self} has no function " f"<{inspect.currentframe().f_code.co_name}>"
            )
        if self.output_channels:
            if self.output_channels[channel].data_type == "BOOL":
                # get the relevant value from the register and write the inverse
                value = self.read_channel(channel)
                self.write_channel(channel, not value)
            else:
                raise TypeError(
                    f"{self} has has incompatible datatype "
                    f"{self.output_channels[channel].data_type} (should be 'BOOL')"
                )

    @CpxBase.require_base
    def read_system_parameters(self) -> SystemParameters:
        """Read parameters from EP module

        :return: Parameters object containing all r/w parameters
        :rtype: Parameters
        """
        params = SystemParameters(
            dhcp_enable=self.base.read_parameter(
                self.position, self.parameters.get(12000)
            ),
            ip_address=convert_uint32_to_octett(
                self.base.read_parameter(self.position, self.parameters.get(12001))
            ),
            subnet_mask=convert_uint32_to_octett(
                self.base.read_parameter(self.position, self.parameters.get(12002)),
            ),
            gateway_address=convert_uint32_to_octett(
                self.base.read_parameter(self.position, self.parameters.get(12003))
            ),
            active_ip_address=convert_uint32_to_octett(
                self.base.read_parameter(self.position, self.parameters.get(12004))
            ),
            active_subnet_mask=convert_uint32_to_octett(
                self.base.read_parameter(self.position, self.parameters.get(12005))
            ),
            active_gateway_address=convert_uint32_to_octett(
                self.base.read_parameter(self.position, self.parameters.get(12006))
            ),
            mac_address=convert_to_mac_string(
                self.base.read_parameter(self.position, self.parameters.get(12007))
            ),
            setup_monitoring_load_supply=self.base.read_parameter(
                self.position, self.parameters.get(20022)
            )
            & 0xFF,
        )
        Logging.logger.info(f"{self.name}: Reading parameters: {params}")
        return params

    @CpxBase.require_base
    def configure_diagnosis_for_defect_valve(self, value: bool) -> None:
        """Enable (True, default) or disable (False) diagnosis for defect valve.

        :param value: Value to write to the module (True to enable diagnosis)
        :type value: bool
        """
        parameter = self.parameters.get(20021)

        if parameter is None:
            raise NotImplementedError(
                f"{self} has no function <{inspect.currentframe().f_code.co_name}>"
            )

        self.base.write_parameter(
            self.position,
            parameter,
            value,
        )

        Logging.logger.info(
            f"{self.name}: Setting diagnosis for defect valve to {value}"
        )

    @CpxBase.require_base
    def read_pqi(self, channel: int = None) -> dict | list[dict]:
        """Returns Port Qualifier Information for each channel. If no channel is given,
        returns a list of PQI dict for all channels

        :param channel: Channel number, starting with 0, optional
        :type channel: int
        :return: PQI information as dict for one channel or as list of dicts for more channels
        :rtype: dict | list[dict] depending on param channel
        """
        if self.product_category is not ProductCategory.IO_LINK.value:
            raise NotImplementedError(
                f"{self} has no function <{inspect.currentframe().f_code.co_name}>"
            )

        data45 = self.base.read_reg_data(self.input_register + 16)[0]
        data67 = self.base.read_reg_data(self.input_register + 17)[0]
        data = [
            data45 & 0xFF,
            (data45 & 0xFF00) >> 8,
            data67 & 0xFF,
            (data67 & 0xFF00) >> 8,
        ]

        channels_pqi = []

        for data_item in data:
            port_qualifier = (
                "input data is valid"
                if (data_item & 0b10000000) >> 7
                else "input data is invalid"
            )
            device_error = (
                "there is at least one error or warning on the device or port"
                if (data_item & 0b01000000) >> 6
                else "there are no errors or warnings on the device or port"
            )
            dev_com = (
                "device is in status PREOPERATE or OPERATE"
                if (data_item & 0b00100000) >> 5
                else "device is not connected or not yet in operation"
            )

            channels_pqi.append(
                {
                    "Port Qualifier": port_qualifier,
                    "Device Error": device_error,
                    "DevCOM": dev_com,
                }
            )
        if channel is None:
            return channels_pqi

        Logging.logger.info(f"{self.name}: Reading PQI of channel(s) {channel}")
        return channels_pqi[channel]

    @CpxBase.require_base
    def read_fieldbus_parameters(self) -> list[dict]:
        """Read all fieldbus parameters (status/information) for all channels.

        :return: a dict of parameters for every channel.
        :rtype: list[dict]
        """
        if self.product_category is not ProductCategory.IO_LINK.value:
            raise NotImplementedError(
                f"{self} has no function <{inspect.currentframe().f_code.co_name}>"
            )

        param_port_status_info = self.parameters.get(20074)
        param_revision_id = self.parameters.get(20075)
        param_transmission_rate = self.parameters.get(20076)
        param_actual_cycle_time = self.parameters.get(20077)
        param_actual_vendor_id = self.parameters.get(20078)
        param_actual_device_id = self.parameters.get(20079)
        param_iolink_input_data_length = self.parameters.get(20108)
        param_iolink_output_data_length = self.parameters.get(20109)

        channel_params = []

        port_status_dict = {
            0: "NO_DEVICE",
            1: "DEACTIVATED",
            2: "PORT_DIAG",
            3: "PREOPERATE",
            4: "OPERATE",
            5: "DI_CQ",
            6: "DO_CQ",
            254: "PORT_POWER_OFF",
            255: "NOT_AVAILABLE",
        }
        transmission_rate_dict = {0: "not detected", 1: "COM1", 2: "COM2", 3: "COM3"}

        for channel_item in range(4):
            port_status_information = port_status_dict.get(
                self.base.read_parameter(
                    self.position, param_port_status_info, channel_item
                ),
            )

            revision_id = self.base.read_parameter(
                self.position, param_revision_id, channel_item
            )

            transmission_rate = transmission_rate_dict.get(
                self.base.read_parameter(
                    self.position, param_transmission_rate, channel_item
                ),
            )

            actual_cycle_time = self.base.read_parameter(
                self.position, param_actual_cycle_time, channel_item
            )

            actual_vendor_id = self.base.read_parameter(
                self.position, param_actual_vendor_id, channel_item
            )

            actual_device_id = self.base.read_parameter(
                self.position, param_actual_device_id, channel_item
            )

            input_data_length = self.base.read_parameter(
                self.position, param_iolink_input_data_length, channel_item
            )

            output_data_length = self.base.read_parameter(
                self.position,
                param_iolink_output_data_length,
                channel_item,
            )

            channel_params.append(
                {
                    "Port status information": port_status_information,
                    "Revision ID": revision_id,
                    "Transmission rate": transmission_rate,
                    "Actual cycle time [in 100 us]": actual_cycle_time,
                    "Actual vendor ID": actual_vendor_id,
                    "Actual device ID": actual_device_id,
                    "Input data length": input_data_length,
                    "Output data length": output_data_length,
                }
            )

        Logging.logger.info(
            f"{self.name}: Reading fieldbus parameters for all channels: {channel_params}"
        )
        # update the instance
        self.fieldbus_parameters = channel_params
        return channel_params

    @CpxBase.require_base
    def read_isdu(self, channel: int, index: int, subindex: int) -> bytes:
        """Read isdu (device parameter) from defined channel
        Raises CpxRequestError when read failed

        :param channel: Channel number, starting with 0
        :type channel: int
        :param index: io-link parameter index
        :type index: int
        :param subindex: io-link parameter subindex
        :type subindex: int
        :return: device parameter (index/subindex) for given channel
        :rtype: bytes
        """
        module_index = (self.position + 1).to_bytes(2, "little")
        channel = (channel + 1).to_bytes(2, "little")
        index = index.to_bytes(2, "little")
        subindex = subindex.to_bytes(2, "little")
        length = (0).to_bytes(2, "little")  # always zero when reading
        # command: 50 Read(with byte swap), 51 write(with byte swap), 100 read, 101 write
        command = (100).to_bytes(2, "little")

        # select module, starts with 1
        self.base.write_reg_data(
            module_index, ap_registers.ISDU_MODULE_NO.register_address
        )
        # select channel, starts with 1
        self.base.write_reg_data(channel, ap_registers.ISDU_CHANNEL.register_address)
        # select index
        self.base.write_reg_data(index, ap_registers.ISDU_INDEX.register_address)
        # select subindex
        self.base.write_reg_data(subindex, ap_registers.ISDU_SUBINDEX.register_address)
        # select length of data in bytes
        self.base.write_reg_data(length, ap_registers.ISDU_LENGTH.register_address)
        # command
        self.base.write_reg_data(command, ap_registers.ISDU_COMMAND.register_address)

        stat = 1
        cnt = 0
        while stat > 0 and cnt < 5000:
            stat = int.from_bytes(
                self.base.read_reg_data(*ap_registers.ISDU_STATUS),
                byteorder="little",
            )

            cnt += 1
        if cnt >= 5000:
            raise CpxRequestError("ISDU data read failed")

        ret = self.base.read_reg_data(*ap_registers.ISDU_DATA)
        Logging.logger.info(f"{self.name}: Reading ISDU for channel {channel}: {ret}")

        return ret

    @CpxBase.require_base
    def write_isdu(self, data: bytes, channel: int, index: int, subindex: int) -> None:
        """Write isdu (device parameter) to defined channel.
        Raises CpxRequestError when write failed

        :param data: Data as 16bit register values in list
        :type data: list[int]
        :param channel: Channel number, starting with 0
        :type channel: int
        :param index: io-link parameter index
        :type index: int
        :param subindex: io-link parameter subindex
        :type subindex: int
        """
        module_index = (self.position + 1).to_bytes(2, "little")
        channel = (channel + 1).to_bytes(2, "little")
        index = (index).to_bytes(2, "little")
        subindex = (subindex).to_bytes(2, "little")
        length = (len(data) * 2).to_bytes(2, "little")
        # command: 50 Read(with byte swap), 51 write(with byte swap), 100 read, 101 write
        command = (101).to_bytes(2, "little")

        # select module, starts with 1
        self.base.write_reg_data(
            module_index, ap_registers.ISDU_MODULE_NO.register_address
        )
        # select channel, starts with 1
        self.base.write_reg_data(channel, ap_registers.ISDU_CHANNEL.register_address)
        # select index
        self.base.write_reg_data(index, ap_registers.ISDU_INDEX.register_address)
        # select subindex
        self.base.write_reg_data(subindex, ap_registers.ISDU_SUBINDEX.register_address)
        # select length of data in bytes
        self.base.write_reg_data(length, ap_registers.ISDU_LENGTH.register_address)
        # write data to data register
        self.base.write_reg_data(data, ap_registers.ISDU_DATA.register_address)
        # command
        self.base.write_reg_data(command, ap_registers.ISDU_COMMAND.register_address)

        stat = 1
        cnt = 0
        while stat > 0 and cnt < 1000:
            stat = int.from_bytes(
                self.base.read_reg_data(*ap_registers.ISDU_STATUS),
                byteorder="little",
            )
            cnt += 1
        if cnt >= 1000:
            raise CpxRequestError("ISDU data write failed")

        Logging.logger.info(
            f"{self.name}: Write ISDU {data} to channel {channel} ({index},{subindex})"
        )

    @CpxBase.require_base
    def get_available_parameters(self) -> dict:
        """returns all available parameters from the module
        :return: All available parameters
        :rtype: dict
        """
        return {v.name: k for k, v in self.parameters.items()}

    @CpxBase.require_base
    def get_available_enums(self) -> dict:
        """returns all enums for the module"""
        return

    @CpxBase.require_base
    def write_module_parameter(  # TODO: correct enum
        self,
        value: int | bool | ParameterEnum,
        parameter: str | int,
        channel: int | list = 0,
    ) -> None:
        """Write module parameter if available"""
        # TODO: fill in docstring

        if isinstance(parameter, int):
            parameter = self.parameters.get(parameter)
        elif isinstance(parameter, str):
            # iterate over available parameters and extract the one with the correct name
            parameter_list = [
                p for p in self.parameters.values() if p.name == parameter
            ]
            parameter = parameter_list[0] if len(parameter_list) == 1 else None

        if parameter is None:
            raise NotImplementedError(f"{self} has no parameter {parameter}")

        # TODO: here, get the correct types or enums and check them

        if isinstance(value, ParameterEnum):
            # TODO: make work
            value = value.value

        # TODO: here, do the correct range check
        value_range_check(value, 2)

        self.base.write_parameter(
            self.position,
            parameter,
            value,
            channel,
        )
        # TODO: add log output for channels if set
        Logging.logger.info(f"{self.name}: Setting {parameter.name} to {value}")

    @CpxBase.require_base
    def read_module_parameter(
        self,
        parameter: str | int,
        channel: int | list = 0,
    ) -> Any:
        """Read module parameter if available"""
        # TODO: fill in docstring

        if isinstance(parameter, int):
            parameter = self.parameters.get(parameter)
        elif isinstance(parameter, str):
            # iterate over available parameters and extract the one with the correct name
            # TODO: docu that this takes longer than parameter id
            parameter_list = [
                p for p in self.parameters.values() if p.name == parameter
            ]
            parameter = parameter_list[0] if len(parameter_list) == 1 else None

        if parameter is None:
            raise NotImplementedError(f"{self} has no parameter {parameter}")

        if parameter.enums:
            # overwrite the parameter datatype
            parameter.data_type = parameter.enums.data_type

        # TODO: should do channel range check for parameter instances

        value = self.base.read_parameter(
            self.position,
            parameter,
            channel,
        )
        # TODO: add log output for channels if set
        Logging.logger.info(
            f"{self.name}: Read {value} from parameter {parameter.name}"
        )

        if parameter.enums:
            return parameter.enums.enum_values.get(value)

        return value
