"""Tests for cpx-ap system"""

import pytest

import time

from cpx_io.cpx_system.cpx_ap import *


@pytest.fixture(scope="function")
def test_cpxap():
    with CpxAp(ip_address="172.16.1.41", port=502, timeout=500) as cpxap:
        yield cpxap


def test_init(test_cpxap):
    assert test_cpxap


def test_module_count(test_cpxap):
    assert test_cpxap.read_module_count() == 6


def test_read_module_information(test_cpxap):
    modules = []
    time.sleep(0.05)
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

    assert all(isinstance(item, CpxApModule) for item in test_cpxap.modules)

    for m in test_cpxap.modules:
        assert m.information["Input Size"] >= 0

    assert test_cpxap.modules[0].information["Module Code"] == 8323
    assert test_cpxap.modules[0].position == 0

    assert test_cpxap.modules[0].output_register == None  # EP
    assert test_cpxap.modules[1].output_register == None  # 8DI
    assert test_cpxap.modules[2].output_register == 0  # 4DI4DO
    assert test_cpxap.modules[3].output_register == None  # 4AIUI
    assert test_cpxap.modules[4].output_register == 1  # 4IOL
    assert test_cpxap.modules[5].output_register == None  # 4Di

    assert test_cpxap.modules[0].input_register == None  # EP
    assert test_cpxap.modules[1].input_register == 5000  # 8DI
    assert test_cpxap.modules[2].input_register == 5001  # 4DI4DO
    assert test_cpxap.modules[3].input_register == 5002  # 4AIUI
    assert test_cpxap.modules[4].input_register == 5006  # 4IOL
    assert test_cpxap.modules[5].input_register == 5024  # 4Di


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
    time.sleep(0.05)
    assert test_cpxap.modules[2].read_channels()[:4] == [False] * 4
    assert test_cpxap.modules[2].read_channels()[4:] == data

    data = [False, True, False, True]
    test_cpxap.modules[2].write_channels(data)
    time.sleep(0.05)
    assert test_cpxap.modules[2].read_channels()[:4] == [False] * 4
    assert test_cpxap.modules[2].read_channels()[4:] == data

    test_cpxap.modules[2].write_channels([False, False, False, False])

    test_cpxap.modules[2].set_channel(0)
    time.sleep(0.05)
    assert test_cpxap.modules[2].read_channel(0, output_numbering=True) == True
    assert test_cpxap.modules[2].read_channel(4) == True

    test_cpxap.modules[2].clear_channel(0)
    time.sleep(0.05)
    assert test_cpxap.modules[2].read_channel(0, output_numbering=True) == False
    assert test_cpxap.modules[2].read_channel(4) == False

    test_cpxap.modules[2].toggle_channel(0)
    time.sleep(0.05)
    assert test_cpxap.modules[2].read_channel(0, output_numbering=True) == True
    assert test_cpxap.modules[2].read_channel(4) == True

    test_cpxap.modules[2].clear_channel(0)


def test_4AiUI_None(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert len(a4aiui.read_channels()) == 4


def test_4AiUI_5V_CH1(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    a4aiui.configure_channel_range(1, "0-10V")
    time.sleep(0.05)
    a4aiui.configure_linear_scaling(1, False)
    time.sleep(0.05)

    assert 15900 < test_cpxap.modules[3].read_channel(1) < 16100


def test_4AiUI_5V_CH1_with_scaling(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    a4aiui.configure_channel_range(1, "0-10V")
    time.sleep(0.05)
    a4aiui.configure_channel_limits(1, upper=10000)
    time.sleep(0.05)
    a4aiui.configure_channel_limits(1, lower=0)
    time.sleep(0.05)

    assert 4900 < test_cpxap.modules[3].read_channel(1) < 5100

    a4aiui.configure_channel_limits(1, upper=32767, lower=-32768)
    time.sleep(0.05)
    a4aiui.configure_linear_scaling(1, False)


def test_ep_param_read(test_cpxap):
    ep = test_cpxap.modules[0]
    param = ep.read_parameters()

    assert param["active_ip_address"] == "172.16.1.41"
    assert param["active_subnet_mask"] == "255.255.0.0"
    assert param["active_gateway_address"] == "0.0.0.0"
    assert param["mac_address"] == "00:0e:f0:7d:3b:15"
    # TODO: this returns 0 (might be same error as uint8 shifting required)
    # assert param["setup_monitoring_load_supply"] == 1


def test_4AiUI_configures_channel_unit(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    a4aiui.configure_channel_temp_unit(0, "C")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20032, 0) == [0]

    a4aiui.configure_channel_temp_unit(1, "F")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20032, 1) == [1]

    a4aiui.configure_channel_temp_unit(2, "K")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20032, 2) == [2]

    a4aiui.configure_channel_temp_unit(3, "F")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20032, 3) == [1]

    # reset
    a4aiui.configure_channel_temp_unit(0, "C")
    a4aiui.configure_channel_temp_unit(1, "C")
    a4aiui.configure_channel_temp_unit(2, "C")
    a4aiui.configure_channel_temp_unit(3, "C")


def test_4AiUI_configures_channel_range(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    a4aiui.configure_channel_range(0, "-10-+10V")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20043, 0) == [1]

    a4aiui.configure_channel_range(1, "0-10V")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20043, 1) == [3]

    a4aiui.configure_channel_range(2, "-5-+5V")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20043, 2) == [2]

    a4aiui.configure_channel_range(3, "1-5V")
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20043, 3) == [4]

    # reset
    a4aiui.configure_channel_range(0, "None")
    a4aiui.configure_channel_range(1, "None")
    a4aiui.configure_channel_range(2, "None")
    a4aiui.configure_channel_range(3, "None")


def test_4AiUI_configures_hysteresis_monitoring(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    a4aiui.configure_hysteresis_limit_monitoring(0, 101)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20046, 0) == [101]

    a4aiui.configure_hysteresis_limit_monitoring(1, 202)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20046, 1) == [202]

    a4aiui.configure_hysteresis_limit_monitoring(2, 303)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20046, 2) == [303]

    a4aiui.configure_hysteresis_limit_monitoring(3, 404)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20046, 3) == [404]

    # reset
    a4aiui.configure_hysteresis_limit_monitoring(0, 100)
    a4aiui.configure_hysteresis_limit_monitoring(1, 100)
    a4aiui.configure_hysteresis_limit_monitoring(2, 100)
    a4aiui.configure_hysteresis_limit_monitoring(3, 100)


def test_4AiUI_configures_channel_smoothing(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    a4aiui.configure_channel_smoothing(0, 1)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20107, 0) == [1]

    a4aiui.configure_channel_smoothing(1, 2)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20107, 1) == [2]

    a4aiui.configure_channel_smoothing(2, 3)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20107, 2) == [3]

    a4aiui.configure_channel_smoothing(3, 4)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20107, 3) == [4]

    # reset
    a4aiui.configure_channel_smoothing(0, 5)
    a4aiui.configure_channel_smoothing(1, 5)
    a4aiui.configure_channel_smoothing(2, 5)
    a4aiui.configure_channel_smoothing(3, 5)


def test_4AiUI_configures_linear_scaling(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    a4aiui.configure_linear_scaling(0, True)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20111, 0) == [1]

    a4aiui.configure_linear_scaling(1, False)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20111, 1) == [0]

    a4aiui.configure_linear_scaling(2, True)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20111, 2) == [1]

    a4aiui.configure_linear_scaling(3, False)
    time.sleep(0.05)
    assert a4aiui.base._read_parameter(3, 20111, 3) == [0]

    # reset
    a4aiui.configure_linear_scaling(0, False)
    a4aiui.configure_linear_scaling(1, False)
    a4aiui.configure_linear_scaling(2, False)
    a4aiui.configure_linear_scaling(3, False)


def test_4AiUI_configures_channel_limits(test_cpxap):
    a4aiui = test_cpxap.modules[3]
    assert isinstance(a4aiui, CpxAp4AiUI)

    a4aiui.configure_channel_limits(0, upper=1111, lower=-1111)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20044, 0), data_type="int16")
        == 1111
    )
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20045, 0), data_type="int16")
        == -1111
    )

    a4aiui.configure_channel_limits(1, upper=2222, lower=-2222)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20044, 1), data_type="int16")
        == 2222
    )
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20045, 1), data_type="int16")
        == -2222
    )

    a4aiui.configure_channel_limits(2, upper=3333, lower=-3333)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20044, 2), data_type="int16")
        == 3333
    )
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20045, 2), data_type="int16")
        == -3333
    )

    a4aiui.configure_channel_limits(3, upper=4444, lower=-4444)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20044, 3), data_type="int16")
        == 4444
    )
    assert (
        CpxBase._decode_int(a4aiui.base._read_parameter(3, 20045, 3), data_type="int16")
        == -4444
    )

    # reset
    a4aiui.configure_channel_limits(0, upper=32767, lower=-32768)
    a4aiui.configure_channel_limits(1, upper=32767, lower=-32768)
    a4aiui.configure_channel_limits(2, upper=32767, lower=-32768)
    a4aiui.configure_channel_limits(3, upper=32767, lower=-32768)


def test_4Di4Do_configures(test_cpxap):
    a4di4do = test_cpxap.modules[2]
    assert isinstance(a4di4do, CpxAp4Di4Do)

    a4di4do.configure_debounce_time(3)
    time.sleep(0.05)
    assert CpxBase._decode_int(a4di4do.base._read_parameter(2, 20014, 0)) == 3

    a4di4do.configure_monitoring_load_supply(2)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(
            a4di4do.base._read_parameter(2, 20022, 0), data_type="uint8"
        )
        == 2
    )

    a4di4do.configure_behaviour_in_fail_state(1)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(
            a4di4do.base._read_parameter(2, 20052, 0), data_type="uint8"
        )
        == 1
    )

    # reset to default
    a4di4do.configure_debounce_time(1)
    time.sleep(0.05)
    a4di4do.configure_monitoring_load_supply(1)
    time.sleep(0.05)
    a4di4do.configure_behaviour_in_fail_state(0)


def test_getter(test_cpxap):
    a8di = test_cpxap.modules[1]
    a4di4do = test_cpxap.modules[2]
    a4ai = test_cpxap.modules[3]

    assert a8di[0] == a8di.read_channel(0)
    assert a4di4do[0] == a4di4do.read_channel(0)
    assert a4di4do[4] == a4di4do.read_channel(4)
    assert a4ai[0] == a4ai.read_channel(0)


def test_setter(test_cpxap):
    a4di4do = test_cpxap.modules[2]

    a4di4do[0] = True
    time.sleep(0.05)
    # read back the first output channel (it's on index 4)
    assert a4di4do[4] is True

    a4di4do[0] = False
    time.sleep(0.05)
    # read back the first output channel (it's on index 4)
    assert a4di4do[4] is False


def test_read_ap_parameter(test_cpxap):
    with pytest.raises(NotImplementedError):
        test_cpxap.modules[0].read_ap_parameter()

    info = test_cpxap.modules[4].information
    ap = test_cpxap.modules[4].read_ap_parameter()
    assert ap["Module Code"] == info["Module Code"]


def test_4iol_sdas(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_port_mode(2, channel=0)

    time.sleep(0.05)

    # example SDAS-MHS on port 0
    param = a4iol.read_fieldbus_parameters()
    assert param[0]["Port status information"] == "OPERATE"

    sdas_data = a4iol.read_channel(0)
    process_data = sdas_data[0]

    assert sdas_data[1] == 0
    assert sdas_data[2] == 0
    assert sdas_data[3] == 0

    ssc1 = bool(process_data & 0x1)
    ssc2 = bool(process_data & 0x2)
    ssc3 = bool(process_data & 0x4)
    ssc4 = bool(process_data & 0x8)
    pdv = (process_data & 0xFFF0) >> 4

    assert 0 <= pdv <= 4095

    assert a4iol[0] == a4iol.read_channel(0)


def test__swap_bytes():
    assert CpxBase._swap_bytes([0xABCD]) == [0xCDAB]
    assert CpxBase._swap_bytes([0xABCD, 0xCAFE]) == [0xCDAB, 0xFECA]


def test_4iol_ehps(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    def read_process_data_in(module, channel):
        # ehps provides 3 x 16bit "process data in".
        ehps_data = module.read_channel(channel)
        assert ehps_data[3] == 0

        process_data_in = {}
        # The register ordering is inverted to the information in the datasheet
        # also the byteorder is inverted
        ehps_data = CpxBase._swap_bytes(ehps_data)
        process_data_in["Error"] = bool((ehps_data[0] >> 15) & 1)
        process_data_in["DirectionCloseFlag"] = bool((ehps_data[0] >> 14) & 1)
        process_data_in["DirectionOpenFlag"] = bool((ehps_data[0] >> 13) & 1)
        process_data_in["LatchDataOk"] = bool((ehps_data[0] >> 12) & 1)
        process_data_in["UndefinedPositionFlag"] = bool((ehps_data[0] >> 11) & 1)
        process_data_in["ClosedPositionFlag"] = bool((ehps_data[0] >> 10) & 1)
        process_data_in["GrippedPositionFlag"] = bool((ehps_data[0] >> 9) & 1)
        process_data_in["OpenedPositionFlag"] = bool((ehps_data[0] >> 8) & 1)

        process_data_in["Ready"] = bool((ehps_data[0] >> 6) & 1)

        process_data_in["ErrorNumber"] = ehps_data[1]
        process_data_in["ActualPosition"] = ehps_data[2]

        return process_data_in

    def write_process_data_out(module, channel, data):
        # Handhake: First control word = 0x00
        data[0] &= 0xFFFE
        module.write_channel(channel, data)

        for i in range(100):
            process_data_in = read_process_data_in(module, channel)
            if process_data_in["LatchDataOk"] is False:
                break
            time.sleep(0.02)
        assert i < 99

        # Handshake: Second control word = 0x01
        data[0] |= 0x0001
        module.write_channel(channel, data)

        for i in range(100):
            process_data_in = read_process_data_in(module, channel)
            if process_data_in["LatchDataOk"] is True:
                break
            time.sleep(0.02)
        assert i < 99

        # Handshake: Third: Control word = 0x00
        data[0] &= 0xFFFE
        module.write_channel(channel, data)

        for i in range(100):
            process_data_in = read_process_data_in(module, channel)
            if process_data_in["LatchDataOk"] is False:
                break
            time.sleep(0.02)
        assert i < 99

    ehps_channel = 1
    a4iol.configure_port_mode(2, channel=ehps_channel)

    time.sleep(0.05)

    # example EHPS-20-A-LK on port 1
    param = a4iol.read_fieldbus_parameters()
    assert param[1]["Port status information"] == "OPERATE"

    process_data_in = read_process_data_in(a4iol, ehps_channel)
    assert process_data_in["Ready"] is True

    # demo of process data out
    control_word_msb = 0x00
    control_word_lsb = 0x01
    gripping_mode = 0x46  # universal
    workpiece_no = 0x00
    gripping_position = 0x0000
    gripping_force = 0x03  # ca. 85%
    gripping_tolerance = 0xF0

    process_data_out = [
        control_word_lsb + (control_word_msb << 8),
        workpiece_no + (gripping_mode << 8),
        gripping_position,
        gripping_tolerance + (gripping_force << 8),
    ]

    # Init: 0x 0001 4600 0000 0300
    # after cold start, initial data latch is required = Control Word = 1
    data = process_data_out
    a4iol.write_channel(ehps_channel, data)

    # Open command: 0x 0100 4600 0000 0300
    data = [0x0100, 0x4600, 0x0000, 0x03F0]
    write_process_data_out(a4iol, ehps_channel, data)

    # Close command 0x 0200 4600 0000 0300
    data = [0x0200, 0x4600, 0x0000, 0x03F0]
    write_process_data_out(a4iol, ehps_channel, data)

    for _ in range(10):
        a4iol.read_channel(1)
        time.sleep(0.05)
    pass


def test_4iol_write(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_port_mode(2, channel=0)

    time.sleep(0.05)

    a4iol.write_channel(0, [0, 0, 0, 0])
    # TODO: To be tested!


def test_read_pqi(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_port_mode(2, channel=0)
    time.sleep(0.05)

    pqi = a4iol.read_pqi()
    assert pqi[0]["Port Qualifier"] == "input data is valid"
    assert pqi[1]["Port Qualifier"] == "input data is invalid"


def test_4iol_configure_monitoring_load_supply(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_monitoring_load_supply(0)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20022, 0), data_type="uint8")
        == 0
    )

    a4iol.configure_monitoring_load_supply(1)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20022, 0), data_type="uint8")
        == 1
    )

    a4iol.configure_monitoring_load_supply(2)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20022, 0), data_type="uint8")
        == 2
    )

    a4iol.configure_monitoring_load_supply(1)


def test_4iol_configure_target_cycle_time(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_target_cycle_time(16, channel=0)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 0), data_type="uint8")
        == 16
    )

    a4iol.configure_target_cycle_time(73, channel=[1, 2])
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 1), data_type="uint8")
        == 73
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 2), data_type="uint8")
        == 73
    )

    a4iol.configure_target_cycle_time(158)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 0), data_type="uint8")
        == 158
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 1), data_type="uint8")
        == 158
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 2), data_type="uint8")
        == 158
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20049, 3), data_type="uint8")
        == 158
    )

    a4iol.configure_target_cycle_time(0)


def test_4iol_configure_device_lost_diagnostics(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_device_lost_diagnostics(False, channel=0)
    time.sleep(0.05)
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 0)) == False

    a4iol.configure_device_lost_diagnostics(False, channel=[1, 2])
    time.sleep(0.05)
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 1)) == False
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 2)) == False

    a4iol.configure_device_lost_diagnostics(False)
    time.sleep(0.05)
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 0)) == False
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 1)) == False
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 2)) == False
    assert CpxBase._decode_bool(a4iol.base._read_parameter(4, 20050, 3)) == False

    a4iol.configure_device_lost_diagnostics(True)


def test_4iol_configure_port_mode(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_port_mode(0, channel=0)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 0), data_type="uint8")
        == 0
    )

    a4iol.configure_port_mode(3, channel=[1, 2])
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 1), data_type="uint8")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 2), data_type="uint8")
        == 3
    )

    a4iol.configure_port_mode(97)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 0), data_type="uint8")
        == 97
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 1), data_type="uint8")
        == 97
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 2), data_type="uint8")
        == 97
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20071, 3), data_type="uint8")
        == 97
    )

    a4iol.configure_port_mode(0)


def test_4iol_configure_review_and_backup(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_review_and_backup(1, channel=0)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 0), data_type="uint8")
        == 1
    )

    a4iol.configure_review_and_backup(2, channel=[1, 2])
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 1), data_type="uint8")
        == 2
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 2), data_type="uint8")
        == 2
    )

    a4iol.configure_review_and_backup(3)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 0), data_type="uint8")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 1), data_type="uint8")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 2), data_type="uint8")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20072, 3), data_type="uint8")
        == 3
    )

    a4iol.configure_review_and_backup(0)


def test_4iol_configure_target_vendor_id(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_target_vendor_id(1, channel=0)
    a4iol.configure_port_mode(1, channel=0)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 0), data_type="uint16")
        == 1
    )

    a4iol.configure_target_vendor_id(2, channel=[1, 2])
    a4iol.configure_port_mode(1, channel=[1, 2])
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 1), data_type="uint16")
        == 2
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 2), data_type="uint16")
        == 2
    )

    a4iol.configure_target_vendor_id(3)
    a4iol.configure_port_mode(1)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 0), data_type="uint16")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 1), data_type="uint16")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 2), data_type="uint16")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20073, 3), data_type="uint16")
        == 3
    )

    a4iol.configure_target_vendor_id(0)
    a4iol.configure_port_mode(0)


def test_4iol_configure_setpoint_device_id(test_cpxap):
    a4iol = test_cpxap.modules[4]
    assert isinstance(a4iol, CpxAp4Iol)

    a4iol.configure_setpoint_device_id(1, channel=0)
    a4iol.configure_port_mode(1, channel=0)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 0), data_type="uint32")
        == 1
    )

    a4iol.configure_setpoint_device_id(2, channel=[1, 2])
    a4iol.configure_port_mode(1, channel=[1, 2])
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 1), data_type="uint32")
        == 2
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 2), data_type="uint32")
        == 2
    )

    a4iol.configure_setpoint_device_id(3)
    a4iol.configure_port_mode(1)
    time.sleep(0.05)
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 0), data_type="uint32")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 1), data_type="uint32")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 2), data_type="uint32")
        == 3
    )
    assert (
        CpxBase._decode_int(a4iol.base._read_parameter(4, 20080, 3), data_type="uint32")
        == 3
    )

    a4iol.configure_setpoint_device_id(0)
    a4iol.configure_port_mode(0)
