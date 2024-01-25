# CPX-SYSTEM

## festo-cpx-io 
Python modbus implementation for Festo cpx remote-io systems
### CPX-E
The automation system CPX-E is a high-performance control and automation system focusing primarily on motion control functions for handling technology. It comprises individual function modules that allow a very flexible system structure. Depending on the combination, the automation system CPE-X can be configured and used purely as a remote I/O system or as a control system. The following modules are available:
- Controller
- Bus modules
- Input/output modules
- Counter modules
- IO-Link master modules

In this implementation, the control (PLC) will be your pc. The cpx-system will be connected via modbus on ethernet/ip. Therefore the bus module CPX-E-EP is required to use this software.

#### Import
Import the required cpx-system
```
from cpx_io.cpx_system.cpx_e.cpx_e import CpxE
```

#### Instantiate your cpx-system
You can use the typecode from your CPX order (www.festo.com) to get the correct modules and their order.
```
myCPX = CpxE("60E-EP-MLNINO", ip_address="192.168.1.1")
```
You can also instantiate an "empty" cpx system and add modules later. This requires to import the module itself first.
```
from cpx_io.cpx_system.cpx_e.e8do import CpxE8Do

myCPX = CpxE(ip_address="192.168.1.1")
e8do = myCPX.add_module(CpxE8Do())
```
You can also instantiate "empty" modules first and add them to the cpx system later. Either in the constructor or later via add_module()

```
from cpx_io.cpx_system.cpx_e.e8do import CpxE8Do
from cpx_io.cpx_system.cpx_e.eep import CpxEEP

# add via constructor. Here you should always provide the -EP module first
eep = CpxEEp()
e8do = CpxE8Do()
myCPX = CpxE(ip_address="192.168.1.1", modules=[eep, e8do])


# alternatively, add them later via add_module
eep = CpxEEp()
e8do = CpxE8Do()
myCPX = CpxE(ip_address="192.168.1.1") # this will already put an CpxEEp module on position 0
myCPX.add_module(e8Do)
```

All of the above can be used with a context manager, for example
```
with CpxE("60E-EP-MLNINO", ip_address="192.168.1.1") as myCPX:
    # read system information
    module_count = cpx_e.read_module_count()
    module_list = cpx_e.modules
```

#### Module naming
The modules in the CPX system will be named automatically, if no name is given. If there are more of one module of the same type in the system, an underscore and rising number will be added to the name. You can rename the modules to your liking by setting the name variable.
```
from cpx_io.cpx_system.cpx_e.cpx_e import CpxE
from cpx_io.cpx_system.cpx_e.eep import CpxEEp
from cpx_io.cpx_system.cpx_e.e16di import CpxE16Di

with CpxE(ip_address="192.168.1.1", modules = [CpxEEp(), CpxE16Di()]) as myCPX:
    # assuming you have one CpxE16Di in your system
    print(myCPX.modules[1])
    # will return "cpxe16di (idx: 1, type: CpxE16Di)" where cpxe16di is the automatically generated name
    # you can access the module by its name
    print(myCPX.cpxe16di)
    # will also return "cpxe16di (idx: 1, type: CpxE16Di)"
    myCPX.cpxe16di.name = "my16di" # rename the module
    # you can access the module with the new name
    cpx.my16di
    # and the myCPX.modules[1] will return the new name "my16di (idx: 1, type: CpxE16Di)"
```

#### Use the modules functions
The modules offer different functions but most of them have read_channel() and depending on the kind of module write_channel() as well as very individual configure functions. Read the [doc](https://festo.gitlab-pages.festo.company/electric-automation/remote-io/festo-cpx-io/) and have a look at the [examples](./examples) for more information.

### CPX-AP
CPX-AP is a modular and lightweight IO system with IP65/IP67 protection. it
- Can be adapted to Festo valve terminals
- Highly flexible remote IO system with maximum performance 
- Parameterisable and scalable
- Up to 15 modules in one automation system CPX-AP-A
- Complete IO-Link master V1.1 with data storage mechanism including device parameterisation tool

In this implementation, the control (PLC) will be your pc. The cpx-system will be connected via modbus on ethernet/ip. Therefore the bus module CPX-A-EP or CPX-I-EP is required to use this software.

#### Import
Import the required cpx-system
```
from cpx_io.cpx_system.cpx_e.cpx_ap import CpxAP
```

#### Instantiate your cpx-system
On CPX-AP, the modules will be read out automatically when the CpxAP object is instantiated. Optionally, a modbus timeout in seconds can be set in the constructor.
```
myCPX = CpxAp(ip_address="192.168.1.1", timeout=1.5)
```

The easiest way, is to use it with a context manager, for example
```
with CpxAp(ip_address="192.168.1.1") as myCPX:
    # read system information
    module_count = cpx_ap.read_module_count()
    module_information = [
        cpx_ap.read_module_information(i) for i in range(module_count)
    ]
```
#### Module naming
The modules in the CPX system will be named automatically, if no name is given. If there are more of one module of the same type in the system, an underscore and rising number will be added to the name. You can rename the modules to your liking by setting the name variable.
```
with CpxAp(ip_address="192.168.1.1") as myCPX:
    # assuming you have one CpxAp8Di in your system
    print(myCPX.modules[1])
    # will return "cpxap8di (idx: 1, type: CpxAp8Di)" where cpxap8di is the automatically generated name
    # you can access the module by its name
    print(myCPX.cpxap8di)
    # will also return "cpxap8di (idx: 1, type: CpxAp8Di)"
    cpx.cpxap8di.name = "my8di" # rename the module
    # you can access the module with the new name
    print(cpx.my8di)
    # and the myCPX.modules[1] will return the new name "my8di (idx: 1, type: CpxAp8Di)"
```

#### Use the modules functions
The modules offer different functions but most of them have read_channel() and depending on the kind of module write_channel() as well as very individual configure functions. Read the [doc](https://festo.gitlab-pages.festo.company/electric-automation/remote-io/festo-cpx-io/) and have a look at the [examples](./examples) for more information.