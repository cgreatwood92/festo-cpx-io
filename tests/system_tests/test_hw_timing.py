"""Tests for cpx-ap system run with 'pytest -s' to see output"""

import timeit
from cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp


def test_clean_apdd():
    """test init with clean apdd folder"""
    with CpxAp(ip_address="172.16.1.42") as cpxap:
        cpxap.delete_apdds()

    time = timeit.timeit(
        "with CpxAp(ip_address='172.16.1.42') as cpxap: pass",
        setup="from cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp",
        number=1,
    )
    print(f"Clean setup time: {time*1000} ms")


def test_load_apdd():
    "test init with loading apdds from module"
    time = timeit.timeit(
        "with CpxAp(ip_address='172.16.1.42') as cpxap: pass",
        setup="from cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp",
        number=1,
    )
    print(f"Load apdd setup time: {time*1000} ms")


def test_read_channel():
    "test init with loading apdds from module"

    time = timeit.timeit(
        "cpxap.modules[1].read_channel(0)",
        setup="from cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp; cpxap = CpxAp(ip_address='172.16.1.42')",
        number=1,
    )
    print(f"Read channel time: {time*1000} ms")


def test_read_parameter():
    "test init with loading apdds from module"

    time = timeit.timeit(
        "cpxap.read_parameter(0, cpxap.modules[0].parameters[20022])",
        setup="from cpx_io.cpx_system.cpx_ap.cpx_ap import CpxAp; cpxap = CpxAp(ip_address='172.16.1.42')",
        number=1,
    )
    print(f"Read parameter time: {time*1000} ms")
