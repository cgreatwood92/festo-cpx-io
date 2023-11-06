import pytest

import time

from cpx_io.cpx_system.cpx_ap import *


@pytest.fixture(scope="function")
def test_cpxap():
    with CpxAp(host="172.16.1.41", tcp_port=502, timeout=500) as cpxap:
        yield cpxap

def test_init(test_cpxap):
    assert test_cpxap

def test_module_count(test_cpxap):
    assert test_cpxap.read_module_count() == 6

def test_read_module_information(test_cpxap):
    modules = []
    time.sleep(.05)
    cnt = test_cpxap.read_module_count()
    for i in range(cnt):
        modules.append(test_cpxap.read_module_information(i))
    assert modules[0]["Module Code"] == 8323
    
def test_modules(test_cpxap):
    assert isinstance(test_cpxap.modules[0], CpxApEp)
    assert isinstance(test_cpxap.modules[1], CpxAp8Di)
    assert isinstance(test_cpxap.modules[2], CpxAp4Di4Do)
    assert isinstance(test_cpxap.modules[3], CpxAp4AiUI)
    assert isinstance(test_cpxap.modules[4], CpxAp4Iol)
    assert isinstance(test_cpxap.modules[5], CpxAp4Di)

    for m in test_cpxap.modules:
        assert m.information["Input Size"] >= 0

    assert test_cpxap.modules[0].information["Module Code"] == 8323
    assert test_cpxap.modules[0].position == 0

    assert test_cpxap.modules[0].output_register == None # EP
    assert test_cpxap.modules[1].output_register == None # 8DI
    assert test_cpxap.modules[2].output_register == 0 # 4DI4DO
    assert test_cpxap.modules[3].output_register == None # 4AIUI
    assert test_cpxap.modules[4].output_register == 1 # 4IOL
    assert test_cpxap.modules[5].output_register == None # 4Di

    assert test_cpxap.modules[0].input_register == None # EP
    assert test_cpxap.modules[1].input_register == 5000 # 8DI
    assert test_cpxap.modules[2].input_register == 5001 # 4DI4DO
    assert test_cpxap.modules[3].input_register == 5002 # 4AIUI
    assert test_cpxap.modules[4].input_register == 5006 # 4IOL
    assert test_cpxap.modules[5].input_register == 5024 # 4Di
    
def test_8Di(test_cpxap):
    assert test_cpxap.modules[1].read_channels() == [False] * 8

def test_8Di_configure(test_cpxap):
    test_cpxap.modules[1].configure_debounce_time(1)

def test_4Di(test_cpxap):
    assert test_cpxap.modules[5].read_channels() == [False] * 4

def test_4Di4Do(test_cpxap):
    assert test_cpxap.modules[2].read_channels() == [False] * 8

    data = [True, False, True, False]
    test_cpxap.modules[2].write_channels(data)
    time.sleep(.05)
    assert test_cpxap.modules[2].read_channels()[:4] == [False] * 4
    assert test_cpxap.modules[2].read_channels()[4:] == data

    data = [False, True, False, True]
    test_cpxap.modules[2].write_channels(data)
    time.sleep(.05)
    assert test_cpxap.modules[2].read_channels()[:4] == [False] * 4
    assert test_cpxap.modules[2].read_channels()[4:] == data

    test_cpxap.modules[2].write_channels([False, False, False, False])

    test_cpxap.modules[2].set_channel(0)
    time.sleep(.05)
    assert test_cpxap.modules[2].read_channel(0, output_numbering=True) == True
    assert test_cpxap.modules[2].read_channel(4) == True

    test_cpxap.modules[2].clear_channel(0)
    time.sleep(.05)
    assert test_cpxap.modules[2].read_channel(0, output_numbering=True) == False
    assert test_cpxap.modules[2].read_channel(4) == False

    test_cpxap.modules[2].toggle_channel(0)
    time.sleep(.05)
    assert test_cpxap.modules[2].read_channel(0, output_numbering=True) == True
    assert test_cpxap.modules[2].read_channel(4) == True

    test_cpxap.modules[2].clear_channel(0)

def test_4AiUI(test_cpxap):
    test_cpxap.modules[3].read_channels() == [0] * 4
    # TODO: Test analog inputs != 0

def test_ep_param_read(test_cpxap):
    ep = test_cpxap.modules[0]
    param = ep.read_parameters()

    assert param["dhcp_enable"] == False
    assert param["ip_address"] == "172.16.1.41"
    #assert param["subnet_mask"] == "255.255.255.0"
    #assert param["gateway_address"] == "172.16.1.1"
    assert param["active_ip_address"] == "172.16.1.41"
    assert param["active_subnet_mask"] == "255.255.255.0"
    #assert param["active_gateway_address"] == "172.16.1.1"
    assert param["mac_address"] == "00:0e:f0:7d:3b:15"
    #assert param["setup_monitoring_load_supply"] == 1

    # TODO: Fix broken
    
def test_4AiUI_configures(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    # TODO: Channel 0 doesn't work every time with every function
    a4aiui.configure_channel_temp_unit(0, "F")
    time.sleep(.05)
    a4aiui.configure_channel_temp_unit(1, "K")
    time.sleep(.05)
    a4aiui.configure_channel_temp_unit(2, "C")
    time.sleep(.05)
    a4aiui.configure_channel_temp_unit(3, "K")
    time.sleep(.05)

    a4aiui.configure_channel_range(0, "-10-+10V")
    time.sleep(.05)
    a4aiui.configure_channel_range(1, "0-10V")
    time.sleep(.05)
    a4aiui.configure_channel_range(2, "-5-+5V")
    time.sleep(.05)
    a4aiui.configure_channel_range(3, "1-5V")
    time.sleep(.05)
    
    a4aiui.configure_hysteresis_limit_monitoring(0, 0)
    time.sleep(.05)
    a4aiui.configure_hysteresis_limit_monitoring(1, 100)
    time.sleep(.05)
    a4aiui.configure_hysteresis_limit_monitoring(2, 200)
    time.sleep(.05)
    a4aiui.configure_hysteresis_limit_monitoring(3, 300)
    time.sleep(.05)

    a4aiui.configure_channel_smoothing(0, 0)
    time.sleep(.05)
    a4aiui.configure_channel_smoothing(1, 1)
    time.sleep(.05)
    a4aiui.configure_channel_smoothing(2, 2)
    time.sleep(.05)
    a4aiui.configure_channel_smoothing(3, 3)
    time.sleep(.05)

    a4aiui.configure_linear_scaling(0, True)
    time.sleep(.05)
    a4aiui.configure_linear_scaling(1, False)
    time.sleep(.05)
    a4aiui.configure_linear_scaling(2, True)
    time.sleep(.05)
    a4aiui.configure_linear_scaling(3, False)
    time.sleep(.05)

    a4aiui.configure_linear_scaling(0, False)
    time.sleep(.05)
    a4aiui.configure_linear_scaling(2, False)
    time.sleep(.05)

    a4aiui.configure_channel_limits(0, upper=1111, lower=-1111)
    time.sleep(.05)
    a4aiui.configure_channel_limits(1, upper=2222, lower=-2222)
    time.sleep(.05)
    a4aiui.configure_channel_limits(2, upper=3333, lower=-3333)
    time.sleep(.05)
    a4aiui.configure_channel_limits(3, upper=4444, lower=-4444)
    time.sleep(.05)
    res = a4aiui.read_channel(0)

