"""Documentation generator for AP systems"""

import inspect
import json
from datetime import datetime


def _generate_module_data(modules: list) -> dict:
    """Makes a dict of relevant information from the modules list"""

    module_data = []
    for m in modules:
        parameter_data = []
        for p in m.parameter_dict.values():
            parameter_data.append(
                {
                    "Id": p.parameter_id,
                    "Name": p.name,
                    "Description": p.description,
                    "R/W": "R/W" if p.is_writable else "R",
                    "Type": p.data_type,
                    "Size": (
                        p.array_size
                        if p.array_size and p.data_type != "ENUM_ID"
                        else ""
                    ),
                    "Instances": p.parameter_instances["NumberOfInstances"],
                }
            )
            # if enum data is available, add it to the last entry
            enum_data = p.enums.enum_values if p.enums else None
            if enum_data:
                parameter_data[-1]["Enums"] = enum_data

        module_functions = {}
        for function_name in m.PRODUCT_CATEGORY_MAPPING.keys():
            if m.is_function_supported(function_name):
                func = getattr(m, function_name)
                # suppress the configure function
                if function_name != "configure":
                    module_functions[function_name] = {
                        "Description": inspect.getdoc(func),
                        "Signature": str(inspect.signature(func)),
                    }

        module_data.append(
            {
                "Index": m.position,
                "Type": m.apdd_information.module_type,
                "Description": m.apdd_information.description,
                "Code": m.apdd_information.module_code,
                "AP Slot": m.position + 1,
                "FWVersion": m.information.fw_version,
                "Default Name": m.name,
                "Module Functions": module_functions,
                "Parameters": parameter_data,
            }
        )

    return module_data


def generate_system_information_file(ap_system) -> None:
    """Saves a readable document that includes the system information in the apdd path"""

    system_data = {
        "Information": "AP System description",
        "IP-Address": ap_system.ip_address,
        "Number of modules": len(ap_system.modules),
        "Creation Date": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "Docu Path": ap_system.docu_path,
        "APDD Path": ap_system.apdd_path,
        "Modules": _generate_module_data(ap_system.modules),
    }

    # json
    with open(
        ap_system.docu_path
        + f"/system_information_{ap_system.ip_address.replace('.','-')}.json",
        "w",
        encoding="ascii",
    ) as f:
        f.write(json.dumps(system_data, indent=4))

    # markup
    with open(
        ap_system.docu_path
        + f"/system_information_{ap_system.ip_address.replace('.','-')}.md",
        "w",
        encoding="ascii",
    ) as f:
        f.write(f"# {system_data['Information']}\n")
        f.write(
            "Documentation of your AP system that is autogenerated by reading "
            "in all the information from all connected modules. This file will be "
            "updated everytime you make an instance of the CpxAp Object and is "
            "saved in the festo-cpx-io folder in your user directory depending on "
            f"your operating system *{ap_system.docu_path}*\n"
        )
        f.write(f"* IP-Address: {system_data['IP-Address']}\n")
        f.write(f"* Number of modules: {system_data['Number of modules']}\n")
        f.write(f"* Date of creation: {system_data['Creation Date']}\n")
        f.write(f"* Docu Path: {system_data['Docu Path']}\n")
        f.write(f"* APDD Path: {system_data['APDD Path']}\n")
        f.write("\n# Modules\n")
        for m in system_data["Modules"]:
            f.write(f"\n## Index {m['Index']}: {m['Type']}\n")
            # it can happen that there is no description which leads to a "-" in the md file
            if len(m["Description"]) > 1:
                f.write(f"{m['Description']}\n")
            f.write(f"* Type: {m['Type']}\n")
            f.write(f"* Modul Code: {m['Code']}\n")
            f.write(f"* AP Slot: {m['AP Slot']}\n")
            f.write(f"* FWVersion: {m['FWVersion']}\n")
            f.write(f"* Default Name: {m['Default Name']}\n")

            if m["Module Functions"]:
                f.write("### Module Functions\n")
                for name, doc in m["Module Functions"].items():
                    func_header = name + doc["Signature"]
                    docstring = doc["Description"].replace("\n:", "<br>:")
                    f.write(f"### {func_header} \n{docstring}\n")

            if m["Parameters"]:
                f.write("### Parameter Table\n")
                f.write(
                    "| Id | Name | Description | R/W | Type | Size | Instances | Enums |\n"
                    "| -- | ---- | ----------- | --- | ---- | ---- | --------- | ----- |\n"
                )
                for p in m["Parameters"]:
                    enums_str = "<ul>"
                    if p.get("Enums"):
                        for k, v in p["Enums"].items():
                            enums_str += f"<li>{v}: {k}</li>"
                    enums_str += "</ul>"
                    description_corrected_newline = p["Description"].replace(
                        "\n", "<br>"
                    )
                    f.write(
                        f"|{p['Id']}|{p['Name']}|{description_corrected_newline}|{p['R/W']}|"
                        f"{p['Type']}|{p['Size']}|{p['Instances']}|{enums_str}|\n"
                    )
