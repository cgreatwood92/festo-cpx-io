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
#   Designation                 Type Code                               Part Number     Quantity    Vendor
#   Main power Cable            3-Wire Appliance and Power Tool Cord    PS615143        1           Bergen Industries
#   Power supply unit           CACN-3A-1-5-G2                          8149580         1           Festo
#   Connecting cable            NEBL-M8G4-E-5-N-LE4                     8065110         1           Festo
#   Connecting cable            NEBC-D12G4-ES-1-S-R3G4-ET               8040451         1           Festo  
#   EtherNet/IP interface       CPX-AP-I-EP-M12                         8086610         1           Festo
#   H-rail mounting             CAFM-X4-H                               8095158         2           Festo
#   Connecting cable            NEBC-D8G4-ES-0.3-N-S-D8G4-ET            8082902         1           Festo
#   Connecting cable            NEBL-M8G4-E-0.3-N-M8G4                  8082904         1           Festo
#   IO-Link Master              CPX-AP-I-4IOL-M12                       8086604         1           Festo
#   Cover cap                   ISK-M12                                 165592          1           Festo
#   Cover cap                   ISK-M8                                  177672          1           Festo
#   Distributor                 NEDU-L1R2-M12G5-M12LE-1R                8091516         1           Festo
#
# -----------------------------------------------------------
### Firmware
#
#   Designation                 Version
#   EtherNet/IP Interface       v1.6.3-68256f9.20240830
#   IO-Link Master              v1.6.6
#   VTUG Valve Terminal         10
#
# -----------------------------------------------------------
### Software
#
#   Designation                 Version
#   Festo Automation Suite      2.9.0.719
#   FAS CPX-AP Plug-In          1.8.0.111
#   FAS IO-Link Device Plug-In  2.9.0.37
#
# -----------------------------------------------------------
#region Header
print("Program Started")
print("--------------------\n")
#
### Import - Basic System Modules
#
import sys      # System Library
import os       # OperatingSystem Library
import struct
import time     # Time Module
#
### Append System Path
#sys.path.append('C:\\Users\\lab4-local\\Documents\\GitHub\\festo-cpx-io-1')   # Add path to workspace directory
sys.path.append('C:\\Users\\ColinGreatwood\\Documents\\GitHub\\festo-cpx-io')   # Add path to workspace directory
#
### Import - Additional Module and Math Libraries
from src.cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp           # CPX-AP Modules Library 
from src.cpx_io.utils.boollist import boollist_to_bytes         # Boolean conversion utility for managing the raw data going to the I-Port VTUG
#
### Variable Declaration
xAllCoilInitState = False
sIpAddress = '192.168.0.1'              # IP Address of the CPX-AP-I-EP-M12 module. Can be verified in Festo Automation Suite P0.12001 Default IP Address: 192.168.1.1
fModbusTimeout = 10.0                   # Modbus timeout in seconds, as float. This value must be greater than fSleepTime.
fSleepTime = 0.100                      # Delay time for all sleep functions, in seconds
iNumModules = 2                         # Number of AP-I Modules in the entire system, including the fieldbus module
iPort = 0                               # Value 0 indicates that the VTUG valve terminal is connected to the top port on the IOLM labeled Port 0.
iTestCycles = 10                        # Number of test cycles through the entire valve terminal and all available coils
arrModuleTypecodes = ["cpx_ap_i_ep_m12", "cpx_ap_i_4iol_m12_variant_8"] # These must be in the expected order
arrModuleParams = []                    # Parameters to be configured for the Ethernet/IP/ModbusTCP fieldbus module. Refer to CPX-AP-I-EP-M12 manual for parameter index numbers.
arrModuleParamValues = [1]              # Parameter values for the Ethernet/IP/ModbusTCP fieldbus module
arrIolmParams = ["Nominal Cycle Time", "Enable diagnosis of IO-Link device lost", "Validation & Backup", "Nominal Vendor ID", "DeviceID", "Port Mode"] # Parameters to be configured for the IO-Link Master module. Refer to CPX-AP-I-4IOL-M12 manual for parameter index numbers.
arrIolmParamValues = [0, True, "Type compatible Device V1.1", 333, 800, "IOL_AUTOSTART"]  # Parameter values for the IO-Link Master module. Port Mode must be set after Nominal Vendor ID and DeviceID
arrVAEMParams = ["OutputDataLength"]    # Parameters to be configured for the VAEM I-Port interface on the valve terminal     
arrVAEMParamValues = [4]                # Parameter values for the VAEM I-Port interface on the valve terminal
liTestSequence = [11,15,4,7,0,23,19]    # Sequence of COILS to be tested in sequence. These coils will be turned ON starting from the 1st list value to the last, one at a time. Index starts with 0.
#
# -----------------------------------------------------------
#region Functions
#
# Function - Initialize Valves
def initialize_all_coils(iModule: int, iChannel: int, iOutputDataLength: int, xStartCondition: bool):
    """
    Function to initialize a list of valve coil states, convert it to a byte list, and then execute the desired initialized state.
    No confirmation of valve positions is included. 
    
    Parameters:
    iModule (int): Integer indicating the position of the IO-Link Master in the AP System.
    iChannel (int): Integer indicating the position of the valve terminal on the IO-Link Master. Port 0 (top) of the module is value 0.
    iOutputDataLength (int): Integer indicating the number of control bytes (i.e PLC to Valve Terminal) for the valve terminal. Can be found in FAS or the Webserver.
    xStartCondition (bool): If True, initialize all valves to ON; if False, initialize all valves to OFF.
    
    Returns:
    None
    """
    # Calculate the number of coils
    iNumCoils = 8 * iOutputDataLength
    
    # Initialize the list of valve coil states (all OFF initially)
    xCoilInitStateList = [xStartCondition] * iNumCoils
    
    # Convert the boolean list to a byte list
    bCoilInitStateList = boollist_to_bytes(xCoilInitStateList)

    # Write the initialization values from the byte list to the valve terminal
    iModule.write_channel(iChannel, bCoilInitStateList)

    # Wait for 1 second for valve coils to achieve their desired initialized state                    
    time.sleep(1.000)
    
    #Return nothing
    return
#
# Function - Cycle All Coils
def cycle_all_coils(iModule: int, iChannel: int = 0, iOutputDataLength: int = 4, fCycleSleep: float = 0.100, iNumCycles: int = 10):
    """
    Function to cycle all valve coils in order. 

    Parameters:
    iModule (int): Integer indicating the position of the IO-Link Master in the AP System.
    iChannel (int): Integer indicating the position of the valve terminal on the IO-Link Master. Port 0 (top) of the module is value 0.
    iOutputDataLength (int): Integer indicating the number of control bytes (i.e PLC to Valve Terminal) for the valve terminal. Can be found in FAS or the Webserver.
    fCycleSleep (float): Float indicating the time for the coil states to be maintained before the next step in the cycle, in seconds. 
    iNumCycles (int): Integer indicating the number of cycles to repeat the entire process. Not to exceed the maximum. 

    Returns:
    None
    """
    ### Import
    #
    from datetime import datetime, timedelta

    ### Variable Declaration
    fMinCycleSleep = 0.100              # Define minimum allowed sleep time between coil state changes, in milliseconds
    iMaxCycles = 1000                   # Define the maximum allowed cycles  
    iNumCoils = 8 * iOutputDataLength   # Calculate the number of coils

    # Input Check - Check if fCycleSleep is below the minimum allowed sleep time
    if fCycleSleep < fMinCycleSleep:
        print(f"Warning: fCycleSleep is below the minimum allowed value of {fMinCycleSleep} seconds. Modifying to {fMinCycleSleep} seconds.")
        fCycleSleep = fMinCycleSleep
    
    # Input Check - Check if iNumCycles exceeds the maximum allowed cycles
    if iNumCycles > iMaxCycles:
        print(f"Error: iNumCycles exceeds the maximum allowed value of {iMaxCycles}. Aborting function.")
        sys.exit()
    else: 
        # Calculate test total execution time in seconds
        total_execution_time = iNumCycles * iNumCoils * 2 * fCycleSleep

        # Calculate the estimated completion time in real-world computer system time format
        start_time = datetime.now()
        estimated_completion_time = start_time + timedelta(seconds=total_execution_time)
        print(f"  > Estimated completion time: \t\t{estimated_completion_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Perform Test for iNumCycles of All Coils
    for i in range(iNumCycles):
        # Initialize the list of valve states to OFF
        xCoilStateList = [False] * iNumCoils

        for j in range(iNumCoils):
            # Set the coil to ON
            xCoilStateList[j] = True
            bCoilStateList = boollist_to_bytes(xCoilStateList)
            iModule.write_channel(iChannel, bCoilStateList)

            # Wait for fCycleSleep seconds for valve to achieve their desired initialized state and hold                   
            time.sleep(fCycleSleep)

            # Reset the coil to OFF
            xCoilStateList[j] = False
            bCoilStateList = boollist_to_bytes(xCoilStateList)
            iModule.write_channel(iChannel, bCoilStateList)

            # Wait for fCycleSleep seconds for valve to achieve their desired initialized state and hold                   
            time.sleep(fCycleSleep)

        # Print current total cycle count
        print(f"  > Cycle {i + 1} Complete.")
    
    # Print current system time at the end of all cycles
    end_time = datetime.now()
    print(f"  > System Time at Test Completion: \t{end_time.strftime('%Y-%m-%d %H:%M:%S')}")  

    #Return nothing
    return
#
# Function - Control Coils in a Specific Sequence
def control_coils(iModule: int, iChannel: int = 0, iOutputDataLength: int = 4, fCycleSleep: float = 0.100, iNumCycles: int = 10, liEnableCoilSeq: list = None):
    """
    Function to cycle a specific order of valves. 

    Parameters:
    iModule (int): Integer indicating the position of the IO-Link Master in the AP System.
    iChannel (int): Integer indicating the position of the valve terminal on the IO-Link Master. Port 0 (top) of the module is value 0.
    iOutputDataLength (int): Integer indicating the number of control bytes (i.e PLC to Valve Terminal) for the valve terminal. Can be found in FAS or the Webserver.
    fCycleSleep (float): Float indicating the time for the coil states to be maintained before the next step in the cycle, in seconds. 
    iNumCycles (int): Integer indicating the number of cycles to repeat the entire process. Not to exceed the maximum. 
    liEnableCoilSeq (list): List of coil positions from 0...(iNumCoils - 1) to be Enabled in a specific sequence. The order of this list indicates the sequence. 

    Returns:
    None
    """
    ### Import
    #
    from datetime import datetime, timedelta

    ### Variable Declaration
    fMinCycleSleep = 0.100              # Define minimum allowed sleep time between coil state changes, in milliseconds
    iMaxCycles = 1000                   # Define the maximum allowed cycles  
    iNumCoils = 8 * iOutputDataLength   # Calculate the number of coils

    # Input Check - Check if fCycleSleep is below the minimum allowed sleep time
    if fCycleSleep < fMinCycleSleep:
        print(f"Warning: fCycleSleep is below the minimum allowed value of {fMinCycleSleep} seconds. Modifying to {fMinCycleSleep} seconds.")
        fCycleSleep = fMinCycleSleep
    
    # Input Check - Check if iNumCycles exceeds the maximum allowed cycles
    if iNumCycles > iMaxCycles:
        print(f"Error: iNumCycles exceeds the maximum allowed value of {iMaxCycles}. Aborting function.")
        sys.exit()
    else: 
        # Calculate test total execution time in seconds
        total_execution_time = iNumCycles * len(liEnableCoilSeq) * 2 * fCycleSleep

        # Calculate the estimated completion time in real-world computer system time format
        start_time = datetime.now()
        estimated_completion_time = start_time + timedelta(seconds=total_execution_time)
        print(f"  > Estimated completion time: \t\t{estimated_completion_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Perform Test for iNumCycles of All Coils
    for i in range(iNumCycles):
        # Initialize the list of valve states to OFF
        xCoilStateList = [False] * iNumCoils

        for j in range(len(liEnableCoilSeq)):
            # Set the coil to ON
            xCoilStateList[liEnableCoilSeq[j]] = True
            bCoilStateList = boollist_to_bytes(xCoilStateList)
            iModule.write_channel(iChannel, bCoilStateList)

            # Wait for fCycleSleep seconds for valve to achieve their desired initialized state and hold                   
            time.sleep(fCycleSleep)

            # Reset the coil to OFF
            xCoilStateList[liEnableCoilSeq[j]] = False
            bCoilStateList = boollist_to_bytes(xCoilStateList)
            iModule.write_channel(iChannel, bCoilStateList)

            # Wait for fCycleSleep seconds for valve to achieve their desired initialized state and hold                   
            time.sleep(fCycleSleep)

        # Print current total cycle count
        print(f"  > Cycle {i + 1} Complete.")
    
    # Print current system time at the end of all cycles
    end_time = datetime.now()
    print(f"  > System Time at Test Completion: \t{end_time.strftime('%Y-%m-%d %H:%M:%S')}")  

    #Return nothing
    return
#
# -----------------------------------------------------------
#region Connect
### Connect
#
with CpxAp(ip_address=sIpAddress, timeout = fModbusTimeout) as myCPX:
    
    ### Print System Info to Default Docu_Path File
    print("SYSTEM DOCUMENTATION")
    print(f"  > Printing system documentation to docu_path folder: {myCPX.docu_path}")
    print("--------------------\n")
#
# -----------------------------------------------------------
#region Verify
    ### Test - Number of Modules
    print("TEST - NUMBER OF MODULES")        
    print(f"  > Number of modules: {len(myCPX.modules)}")
    if len(myCPX.modules) == iNumModules:
        print("TEST - PASSED")
        print("--------------------\n")
    else:
        print("TEST - FAILED")
        print(f"Aborting program. Please correct the number of system modules to {iNumModules} total and start program again.")
        print("--------------------\n")
        sys.exit("Aborting script: Condition not satisfied.")

    ### Test - Type of Modules
    # Module index 0 is 'CPX-AP-I-EP-M12' - refer to arrModuleTypecodes under Variable Declaration
    # Module index 1 is 'CPX-AP-I-4IOL-M12' - refer to arrModuleTypecodes under Variable Declaration
    print("TEST - TYPE OF MODULES")        
    for m in range(iNumModules):
        if myCPX.modules[m].name == arrModuleTypecodes[m]:
            print(f"  > Type of module: {myCPX.modules[m].name}")
            if m == (iNumModules - 1):
                print("TEST - PASSED")
                print("--------------------\n")
        else:
            print("TEST - FAILED")
            print(f"Aborting program. Please correct the type of module {m} to {arrModuleTypecodes[m]} and start program again.")
            print("--------------------\n")
            sys.exit("Aborting script: Condition not satisfied.")
    
    ### Test - Type of VAEM Valve Terminal Interface
    # VTUG Valve Terminal Interface for this test should be VAEM-L1-S-16-PT or VAEM-L1-S-16-PTL. 
    # Other models are not currently supported by this test code.
    print("TEST - TYPE OF VAEM VALVE TERMINAL INTERFACE") 
    currentModule = myCPX.modules[1]
    currentArrModuleParams = arrVAEMParams
    currentArrModuleParamValues = arrVAEMParamValues
    print(f"  > Valve Terminal at IO-Link Port: {iPort}")
    for i, p in currentModule.module_dicts.parameters.items():
        if p.name in currentArrModuleParams:
            bPortOutputDataLength = currentModule.read_module_parameter(i)[iPort]
            print(f"  > Number of Output Bytes: {bPortOutputDataLength}")
            if bPortOutputDataLength == arrVAEMParamValues[iPort]:
                print("TEST - PASSED")
                print("--------------------\n")
            else:
                print("TEST - FAILED")
                print(f"Aborting program. Incorrect VAEM module detected. Please correct the module type to and start program again.")
                print("--------------------\n")
                sys.exit("Aborting script: Condition not satisfied.") 
#
# -----------------------------------------------------------
    #region Setup
    ### Read Module Parameters for CPX-AP-I-EP-M12 Module
    print(f"SETUP - FIELDBUS MODULE - {currentModule.name}") 
    currentModule = myCPX.modules[0]
    currentArrModuleParams = arrModuleParams
    currentArrModuleParamValues = arrModuleParamValues
    for i, p in currentModule.module_dicts.parameters.items():
        if p.name in currentArrModuleParams:
            print(
                f"{f'  > Read {p.name} (ID {i}):':<64}"
                f"{f'{currentModule.read_module_parameter(i)} {p.unit}':<32}"
            )

    ### Write Module Parameters for CPX-AP-I-EP-M12 Module
    for parameter in range(len(currentArrModuleParams)):
        currentModule.write_module_parameter(currentArrModuleParams[parameter], currentArrModuleParamValues[parameter])
    print("SETUP - FIELDBUS MODULE - COMPLETE")
    print("--------------------\n")

    ### Read Module Parameters for CPX-AP-I-4IOL Module
    print(f"SETUP - IOLM MODULE - {currentModule.name}")
    currentModule = myCPX.modules[1]
    currentArrModuleParams = arrIolmParams
    currentArrModuleParamValues = arrIolmParamValues
    for i, p in currentModule.module_dicts.parameters.items():
        if p.name in currentArrModuleParams:
            print(
                f"{f'  > Read {p.name} (ID {i}):':<64}"
                f"{f'{currentModule.read_module_parameter(i)[iPort]} {p.unit}':<32}"    # Parameter reading is limited to the iPort channel only. It can show all ports if [iPort] is removed.
            ) 
    
    ### Write Module Parameters for CPX-AP-I-4IOL Module 
    for parameter in range(len(currentArrModuleParams)):
        currentModule.write_module_parameter(currentArrModuleParams[parameter], currentArrModuleParamValues[parameter], iPort)
    print("SETUP - IOLM MODULE - COMPLETE")
    print("--------------------\n")
#
# -----------------------------------------------------------
    #region Pre-Operate
    ### Wait for VTUG to reach OPERATE State
    print("PRE-OPERATE - VTUG IOLD Port Status Check") 
    portOpCheck = currentModule.read_fieldbus_parameters()
    print(f"  > IO-Link Device Port # is: {iPort}")

    attempts = 0
    max_attempts = 20

    while portOpCheck[iPort]["Port status information"] != "OPERATE" and attempts < max_attempts:
        portOpCheck = currentModule.read_fieldbus_parameters()
        time.sleep(1.000)
        attempts += 1
        print("........Waiting for OPERATE state")

        if attempts >= max_attempts:
            print("Reached maximum number of attempts. Exiting loop.")
            
            # Optionally, you can add diagnostic information here
            diagnosis_info = myCPX.modules[1].read_diagnosis_information()
            print(f"Diagnosis Information: {diagnosis_info}")
            break
    
    # Check if OPERATE state is achieved by VTUG
    if portOpCheck[iPort]["Port status information"] == "OPERATE":
        print("PRE-OPERATE - OPERATE STATUS ACHIEVED")
        print("--------------------\n")
    else:
        print("PRE-OPERATE - FAILED TO ACHIEVE OPERATE STATUS")
        print(f"Aborting program. Incorrect OPERATE statenot achieved. Please correct the situation and start program again.")
        print("--------------------\n")
        sys.exit("Aborting script: Condition not satisfied.") 
#
# -----------------------------------------------------------    
    #region Operate
    ### Valve Test
    print("OPERATE - VALVE TERMINAL TEST - IN PROGRESS") 
    # Initialize Valves
    initialize_all_coils(currentModule, iPort, arrVAEMParamValues[0], xAllCoilInitState)   # This function turns OFF all valve coils on the valve terminal.
    
    # Cycle Valves
    #cycle_all_coils(currentModule, iPort, arrVAEMParamValues[0], fSleepTime, iTestCycles)

    # Control Valves in a Specific Sequence
    control_coils(currentModule, iPort, arrVAEMParamValues[0], fSleepTime, iTestCycles, liTestSequence) # This function turns ON and then OFF a specific sequence of valve coils defined in Variable Declaration.
    print("OPERATE - VALVE TERMINAL TEST - COMPLETE") 
    print("--------------------\n")
#
# -----------------------------------------------------------    
#region Add'l Features
("""
---future IOLM and IOLM Port parameters to read/write: 20074, 20076, 20077, 20075
""")
#
# -----------------------------------------------------------
#region Termination
print("Program Completed")
print("--------------------\n")
myCPX.shutdown()
#
# -----------------------------------------------------------