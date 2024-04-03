"""AP module Builder from APDD"""

from dataclasses import dataclass
from itertools import chain
from cpx_io.cpx_system.cpx_ap.parameter import Parameter
from cpx_io.cpx_system.cpx_ap.generic_ap_module import GenericApModule
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


@dataclass
class Variant:
    """Variant dataclass"""

    description: str
    name: str
    parameter_group_ids: list
    variant_identification: dict


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


class VariantBuilder:
    """VariantBuilder"""

    def build_variant(self, variant_dict):
        return Variant(
            variant_dict.get("Description"),
            variant_dict.get("Name"),
            variant_dict.get("ParameterGroupIds"),
            variant_dict.get("VariantIdentification"),
        )


class ParameterBuilder:
    """ParameterBuilder"""

    def build_parameter(self, parameter_id, parameter_dict):
        return Parameter(
            parameter_id,
            parameter_dict.get("ArraySize"),
            parameter_dict.get("DataType"),
            parameter_dict.get("DefaultValue"),
            parameter_dict.get("Description"),
            parameter_dict.get("Name"),
        )


class CpxApModuleBuilder:

    def build(self, apdd, module_code):
        # TODO: Eventuell: Wenn IO-Link Modul, dann lege das nicht-generische an (könnte auch woanders sein, z.B. beim add_module von cpx_ap)

        product_category = apdd["Variants"]["DeviceIdentification"]["ProductCategory"]
        product_family = apdd["Variants"]["DeviceIdentification"]["ProductFamily"]

        variants = []
        for variant_dict in apdd["Variants"]["VariantList"]:
            variants.append(VariantBuilder().build_variant(variant_dict))

        Logging.logger.debug(f"Set up Variants: {variants}")

        # TODO: the build parameter <module_code> is only needed if one apdd includes more than
        # one ModulCode. this is currently only known for IO-Link modules. Due to its complexity
        # it might be generally better to make an expeption for this type of module and use
        # the existing hardcoded file.

        for v in variants:
            if v.variant_identification["ModuleCode"] == module_code:
                actual_variant = v

        if actual_variant:
            Logging.logger.debug(f"Set module variant to: {actual_variant}")
        else:
            raise IndexError(f"Could not find variant for ModuleCode {module_code}")

        description = actual_variant.description
        # TODO: Make better names?? Names seem to be numbered always and not only if duplicate modules
        name = actual_variant.name.lower().replace("-", "_").replace(" ", "_")
        module_type = actual_variant.name
        configurator_code = actual_variant.variant_identification["ConfiguratorCode"]
        part_number = actual_variant.variant_identification["FestoPartNumberDevice"]
        module_class = actual_variant.variant_identification["ModuleClass"]
        module_code = actual_variant.variant_identification["ModuleCode"]
        order_text = actual_variant.variant_identification["OrderText"]

        # setup all channel types
        channel_types = []
        if apdd.get("Channels"):
            for channel_dict in apdd.get("Channels"):
                channel_types.append(ChannelBuilder().build_channel(channel_dict))
            Logging.logger.debug(f"Set up Channel Types: {channel_types}")

        # setup all channel groups
        channel_groups = []
        if apdd.get("ChannelGroups"):
            for channel_group_dict in apdd.get("ChannelGroups"):
                channel_groups.append(
                    ChannelGroupBuilder().build_channel_group(channel_group_dict)
                )
            Logging.logger.debug(f"Set up Channel Groups: {channel_groups}")

        # setup all channels for the module
        channels = []
        for channel_group in channel_groups:
            for channel in channel_group.channels:
                for channel_type in channel_types:
                    if channel_type.channel_id == channel.get("ChannelId"):
                        break

                for _ in range(channel["Count"]):
                    channels.append(channel_type)

        Logging.logger.debug(f"Set up Channels: {channels}")

        # TODO: Maybe it would be better to just provide amount of i/o channels and type to module
        # split in in/out channels and set instance variables
        input_channels = [c for c in channels if c.direction == "in"]
        output_channels = [c for c in channels if c.direction == "out"]

        # setup enums used in the module
        metadata = apdd.get("Metadata")
        if metadata:
            enum_data_types = metadata.get("EnumDataTypes")

        # setup parameter groups, including list of all used parameters
        parameter_ids = {}
        parameter_groups = apdd.get("ParameterGroups")
        for pg in parameter_groups:
            parameter_ids[pg.get("Name")] = pg.get("ParameterIds")

        # setup parameters
        apdd_parameters = apdd.get("Parameters")
        if apdd_parameters:
            parameter_list = apdd_parameters.get("ParameterList")

        parameters = {
            p["ParameterId"]: ParameterBuilder().build_parameter(
                p["ParameterId"], p["DataDefinition"]
            )
            for p in parameter_list
        }

        # TODO: Not needed, can be extracted from parameters
        supported_parameter_ids = list(
            chain.from_iterable(group.get("ParameterIds") for group in parameter_groups)
        )

        return GenericApModule(
            name,
            module_type,
            product_category,
            input_channels,
            output_channels,
            supported_parameter_ids,
            parameters,
        )
