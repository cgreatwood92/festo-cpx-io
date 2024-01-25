"""Example code for CPX-AP"""
# pylint: disable=no-member

# import the library
from cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp

# for CpxAp, the attached modules are found automatically
with CpxAp(ip_address="172.16.1.42") as myCPX:
    # read system information
    module_count = myCPX.read_module_count()
    module_information = [myCPX.read_module_information(i) for i in range(module_count)]

    sdas_channel = 0
    # set operating mode of channel 0 to "IO-Link communication"
    myCPX.cpxap4iol.configure_port_mode(2, sdas_channel)

    # read back the port status information to check if it's "OPERATE"
    param = myCPX.cpxap4iol.read_fieldbus_parameters()
    assert param[sdas_channel]["Port status information"] == "OPERATE"

    # read the channel 0 process data
    sdas_data = myCPX.cpxap4iol.read_channel(sdas_channel)

    # sdas only requires 2 bytes, so the first 16 bit value from the list is taken
    process_data = sdas_data[0]

    # the process data consists of 4 ssc bits and 12 bit pdv (see datasheet sdas)
    ssc1 = bool(process_data & 0x1)
    ssc2 = bool(process_data & 0x2)
    ssc3 = bool(process_data & 0x4)
    ssc4 = bool(process_data & 0x8)
    pdv = (process_data & 0xFFF0) >> 4