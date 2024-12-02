#region Documentation   
#############################################################
######         Amazon VTUG Offline Test Code           ######
#############################################################
#
#   Created Date:   Nov 21, 2024
#   Created By:     Colin N. Greatwood, MTE, Festo Corporation
#   Modified Date:  n/a
#   Modified By:    n/a
# -----------------------------------------------------------
### Application Purpose
#
#   Purpose:    The purpose of this application is to connect to and verify the quality of Festo VTUG valve
#               terminals using a Festo CPX-AP-I IO-Link Master.
#
# -----------------------------------------------------------
### Change History
#
#   Rev     Modified By         Modified Date       Details
#   1.0     Colin Greatwood     Nov 21, 2024        Initial release
#
# -----------------------------------------------------------
### Hardware
#
#   Designation             Type Code                               Part Number     Quantity    Vendor
#   Main power Cable        3-Wire Appliance and Power Tool Cord    PS615143        1           Bergen Industries
#   Power supply unit       CACN-3A-1-5-G2                          8149580         1           Festo
#   Connecting cable        NEBL-M8G4-E-5-N-LE4                     8065110         1           Festo
#   Connecting cable        NEBC-D12G4-ES-1-S-R3G4-ET               8040451         1           Festo  
#   EtherNet/IP interface   CPX-AP-I-EP-M12                         8086610         1           Festo
#   H-rail mounting         CAFM-X4-H                               8095158         2           Festo
#   Connecting cable        NEBC-D8G4-ES-0.3-N-S-D8G4-ET            8082902         1           Festo
#   Connecting cable        NEBL-M8G4-E-0.3-N-M8G4                  8082904         1           Festo
#   IO-Link Master          CPX-AP-I-4IOL-M12                       8086604         1           Festo
#   Cover cap               ISK-M12                                 165592          1           Festo
#   Cover cap               ISK-M8                                  177672          1           Festo
#   Distributor             NEDU-L1R2-M12G5-M12LE-1R                8091516         1           Festo
#
# -----------------------------------------------------------
### Firmware
#
#   Designation                 Version
#   EtherNet/IP Interface       v1.6.3-68256f9.20240830
#   IO-Link Master              v1.6.6
#   VTUG Valve Terminal         tbd
#
# -----------------------------------------------------------
### Software
#
#   Designation                 Version
#   Festo Automation Suite      2.8.0.417
#   FAS CPX-AP Plug-In          1.8.0.111
#   FAS IO-Link Device Plug-In  1.1.1.1
#
# -----------------------------------------------------------
#region Header
print("Program Started")
print("--------------------\n")
#
### Import
#
import sys # System Library
import os # OperatingSystem Library
import struct
import time # Time Module
#
### Append System Path
sys.path.append('C:\\Users\\ColinGreatwood\\Documents\\GitHub\\festo-cpx-io')   # Add path to workspace directory
from src.cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp   #CPX-AP Library 
#
### Variable Declaration
iNumModules = 2
iPort = 0   # Value 0 indicates that the VTUG valve terminal is connected to the top port on the IOLM labeled Port 0.
iSleepTime = 0.250 # Delay time for all sleep functions, in seconds
arrModuleTypecodes = ["cpx_ap_i_ep_m12", "cpx_ap_i_4iol_m12_variant_8"] # These must be in the expected order
arrModuleParams = [20022]
arrModuleParamValues = [1]
arrIolmParams = [20049, 20050, 20071, 20072, 20073, 20080]
arrIolmParamValues = [0, True, 2, 3, 333, 800]
#
### Process Data Configuration
# process data as dict
def read_process_data_in(data):
    """Read the process data and return as dict"""
    #vtug procides 0 bytes in and 4 bytes out accroding to the specific VAEM/VTUG datasheet
    # ehps provides 3 x UIntegerT16 "process data`` in" according to datasheet.
    # you can unpack the data easily with stuct
    vtug_data = struct.unpack("<HHHH", data)
    # the last 16 bit value of this list is always 0 since ehps only uses 3*16 bit
    # assert vtug_data[0] == 0

    process_data_dict = {}
    ('''
    process_data_dict["Error"] = bool((vtug_data[0] >> 15) & 1)
    process_data_dict["DirectionCloseFlag"] = bool((vtug_data[0] >> 14) & 1)
    process_data_dict["DirectionOpenFlag"] = bool((vtug_data[0] >> 13) & 1)
    process_data_dict["LatchDataOk"] = bool((vtug_data[0] >> 12) & 1)
    process_data_dict["UndefinedPositionFlag"] = bool((vtug_data[0] >> 11) & 1)
    process_data_dict["ClosedPositionFlag"] = bool((vtug_data[0] >> 10) & 1)
    process_data_dict["GrippedPositionFlag"] = bool((vtug_data[0] >> 9) & 1)
    process_data_dict["OpenedPositionFlag"] = bool((vtug_data[0] >> 8) & 1)

    process_data_dict["Ready"] = bool((vtug_data[0] >> 6) & 1)

    process_data_dict["ErrorNumber"] = vtug_data[1]
    process_data_dict["ActualPosition"] = vtug_data[2]
    ''')
    return process_data_dict

# -----------------------------------------------------------
#region Connect
### Connect
#
with CpxAp(ip_address="192.168.0.1", timeout=1.5) as myCPX:
    
    ### Print System Info to Default Docu_Path File
    print("System Documentation")
    print(f"Printing system documentation to docu_path folder: {myCPX.docu_path}")
    print("--------------------\n")

    #region Verify
    ### Test - Number of Modules
    print("TEST - NUMBER OF MODULES")        
    print(f"Number of modules: {len(myCPX.modules)}")
    if len(myCPX.modules) == iNumModules:
        print("TEST - PASSED")
        print("--------------------\n")
    else:
        print("TEST - FAILED")
        print("Aborting program. Please correct the number of system modules to {iNumModules} total and start program again.")
        print("--------------------\n")
        sys.exit("Aborting script: Condition not satisfied.")

    ### Test - Type of Modules
    # Module index 0 is 'CPX-AP-I-EP-M12' - refer to arrModuleTypecodes under Variable Declaration
    # Module index 1 is 'CPX-AP-I-4IOL-M12' - refer to arrModuleTypecodes under Variable Declaration
    print("TEST - TYPE OF MODULES")        
    for m in range(iNumModules):
        if myCPX.modules[m].name == arrModuleTypecodes[m]:
            print(f"Type of module: {myCPX.modules[m].name}")
            if m == (iNumModules - 1):
                print("TEST - PASSED")
                print("--------------------\n")
        else:
            print("TEST - FAILED")
            print("Aborting program. Please correct the type of module {m} to {arrModuleTypecodes[m]} and start program again.")
            print("--------------------\n")
            sys.exit("Aborting script: Condition not satisfied.")

    ### Name Fieldbus Module and Sub-Modules for Program Use
    cpxApIEp_1 = myCPX.modules[0]
    cpxApI4iol_1 = myCPX.modules[1]

    #region Setup
    ### Read Module Parameters for CPX-AP-I-EP-M12 Module
    print("SETUP - FIELDBUS MODULE - CPX-AP-I-EP-M12") 
    currentModule = cpxApIEp_1
    currentArrModuleParams = arrModuleParams
    currentArrModuleParamValues = arrModuleParamValues
    print(f"Module {currentModule.name}")
    for i, p in currentModule.module_dicts.parameters.items():
        print(
            f"{f'  > Read {p.name} (ID {i}):':<64}"
            f"{f'{currentModule.read_module_parameter(i)} {p.unit}':<32}"
        )

    ### Write Module Parameters for CPX-AP-I-EP-M12 Module
    print("  > Write: Fieldbus module does not have any parameters to be configured by this program.") # No parameters to write/setup for this module
    print("SETUP - FIELDBUS MODULE - COMPLETE")
    print("--------------------\n")

    ### Read Module Parameters for CPX-AP-I-4IOL Module
    print("SETUP - IOLM MODULE - CPX-AP-I-4IOL-M12")
    currentModule = cpxApI4iol_1
    currentArrModuleParams = arrIolmParams
    currentArrModuleParamValues = arrIolmParamValues
    print(f"Module {currentModule.name}")
    for i, p in currentModule.module_dicts.parameters.items():
        print(
            f"{f'  > Read {p.name} (ID {i}):':<64}"
            f"{f'{currentModule.read_module_parameter(i)} {p.unit}':<32}"
        ) 
    
    ### Write Module Parameters for CPX-AP-I-4IOL Module 
    for parameter in range(len(currentArrModuleParams)):
        currentModule.write_module_parameter(currentArrModuleParams[parameter], currentArrModuleParamValues[parameter], iPort)
    print("SETUP - IOLM MODULE - COMPLETE")
    print("--------------------\n")

    #region Pre-Operate
    ### Wait for VTUG to reach OPERATE State
    print("PRE-OPERATE - VTUG IOLD Port Status Check") 
    portOpCheck = cpxApI4iol_1.read_fieldbus_parameters()
    print(f"Port # is: {iPort}")
    while portOpCheck[iPort]["Port status information"] != "OPERATE":
        portOpCheck = cpxApI4iol_1.read_fieldbus_parameters()
        time.sleep(iSleepTime)
        print("........Waiting for OPERATE state")
    print("PRE-OPERATE - OPERATE STATUS ACHIEVED")
    print("--------------------\n")
    
    #region Operate
    ### Valve Test
    #myCPX.set_timeout(0) # Set Modbus Timeout to Allow for Pauses

    # read process data
    #raw_data = b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Initialize Data for Proper Length
    raw_data = cpxApI4iol_1.read_channel(iPort, full_size=True)

    # interpret it according to datasheet
    process_data_in = read_process_data_in(raw_data)
    
    # write valve outputs
    cpxApI4iol_1.write_channel(0,1)

    ('''
    if param[SDAS_CHANNEL]["Port status information"] == "PORT_DIAG":
            print(myIOL.read_diagnosis_information())
            break
''')

("""
Set up IO-Link Master Port 1 parameters
Detect IO-Link device and print info
Enter number of valves - if necessary
Connect and test valves
---Check connection at all times CpxAp.Connected
Fault detection sample code
Module health - whatever is available
---CpxAp.Diagnostics -> ModulePresent

---maybe check the sensor UElSen and load voltage ULoad and current supply for each module
---check temperature of each module
---active device variant (P20090 == 8201 factory setting) IOLM

---future IOLM and IOLM Port parameters to read/write: 20074, 20076, 20077, 20075
-check PQI bytes for useful status info
""")
    # myCPX.connected
print("Program Completed")
myCPX.shutdown()