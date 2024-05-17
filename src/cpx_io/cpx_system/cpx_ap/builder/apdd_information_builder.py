"""ApddInformation builder function from APDD"""

from dataclasses import dataclass
from typing import List
from cpx_io.cpx_system.cpx_ap.ap_module import ApModule
from cpx_io.utils.logging import Logging


@dataclass
class Variant:
    """Variant dataclass"""

    description: str
    name: str
    parameter_group_ids: List[int]
    variant_identification: dict


def build_variant(variant_dict):
    """Builds one Variant"""
    return Variant(
        variant_dict.get("Description"),
        variant_dict.get("Name"),
        variant_dict.get("ParameterGroupIds"),
        variant_dict.get("VariantIdentification"),
    )


def build_apdd_information(apdd, module_code):
    """Builds one ApddInformation"""
    variant_list = [build_variant(d) for d in apdd["Variants"]["VariantList"]]
    Logging.logger.debug(f"Variants: {variant_list}")
    variant = next(
        (
            v
            for v in variant_list
            if v.variant_identification["ModuleCode"] == module_code
        ),
        None,
    )
    if variant is None:
        raise IndexError(f"Could not find variant for ModuleCode {module_code}")
    Logging.logger.debug(f"Module Variant: {variant}")

    product_category = apdd["Variants"]["DeviceIdentification"]["ProductCategory"]
    product_family = apdd["Variants"]["DeviceIdentification"]["ProductFamily"]

    return ApModule.ApddInformation(
        variant.description,
        variant.name.lower().replace("-", "_").replace(" ", "_"),
        variant.name,
        variant.variant_identification["ConfiguratorCode"],
        variant.variant_identification["FestoPartNumberDevice"],
        variant.variant_identification["ModuleClass"],
        variant.variant_identification["ModuleCode"],
        variant.variant_identification["OrderText"],
        product_category,
        product_family,
    )
