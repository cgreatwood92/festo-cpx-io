"""Contains tests for cpx_e4iol class"""

from unittest.mock import Mock, call
import pytest

from cpx_io.cpx_system.cpx_e.e4iol import CpxE4Iol
from cpx_io.cpx_system.cpx_e.cpx_e_enums import OperatingMode, AddressSpace
from cpx_io.cpx_system.cpx_dataclasses import StartRegisters


class TestCpxE4Iol:
    """Test cpx-e-4iol"""

    def test_constructor_default(self):
        """Test initialize function"""
        # Arrange

        # Act
        cpxe4iol = CpxE4Iol()
        # Assert
        assert cpxe4iol.base is None
        assert cpxe4iol.position is None

    def test_constructor_raise_error(self):
        """Test initialize function"""
        # Arrange

        # Act & Assert
        with pytest.raises(ValueError):
            CpxE4Iol(3)

    @pytest.mark.parametrize(
        "address_space, module_position, expected_insize, expected_outsize",
        [
            (2, 1, 1, 1),
            (8, 1, 4, 4),
            (AddressSpace.PORT_2E2A, 1, 1, 1),
            (AddressSpace.PORT_8E8A, 1, 4, 4),
        ],
    )
    def test_configure(
        self, address_space, module_position, expected_insize, expected_outsize
    ):
        """Test configure function"""
        # Arrange
        cpxe4iol = CpxE4Iol(address_space)
        mocked_base = Mock(next_input_register=0, next_output_register=0, modules=[])

        # Act
        cpxe4iol.configure(mocked_base, module_position)

        # Assert
        assert cpxe4iol.base == mocked_base
        assert cpxe4iol.position == module_position
        assert cpxe4iol.module_input_size == expected_insize
        assert cpxe4iol.module_output_size == expected_outsize

    def test_read_status(self):
        """Test read channels"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.start_registers = StartRegisters(inputs=0)
        cpxe4iol.base = Mock(read_reg_data=Mock(return_value=b"\xAA\xAA"))

        # Act
        status = cpxe4iol.read_status()

        # Assert
        assert status == [False, True] * 8

    def test_read_2byte_channel_0_to_3(self):
        """Test read channels"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.base = Mock(
            read_reg_data=Mock(return_value=b"\xA0\xA1\xB0\xB1\xC0\xC1\xD0\xD1")
        )

        # Act
        channel_values = [cpxe4iol.read_channel(idx) for idx in range(4)]

        # Assert
        assert channel_values == [b"\xA0\xA1", b"\xB0\xB1", b"\xC0\xC1", b"\xD0\xD1"]
        cpxe4iol.base.read_reg_data.assert_called_with(
            cpxe4iol.start_registers.inputs, length=4
        )

    def test_read_8byte_channel_0_to_3(self):
        """Test read channels"""
        # Arrange
        cpxe4iol = CpxE4Iol(8)
        cpxe4iol.base = Mock(
            read_reg_data=Mock(
                return_value=b"\xA1\x10\xA1\x11\xA1\x13\xA1\x14\xB1\x10\xB1\x11\xB1\x13\xB1\x14"
                b"\xC1\x10\xC1\x11\xC1\x13\xC1\x14\xD1\x10\xD1\x11\xD1\x13\xD1\x14"
            )
        )

        # Act
        channel_values = [cpxe4iol.read_channel(idx) for idx in range(4)]

        # Assert
        assert channel_values == [
            b"\xA1\x10\xA1\x11\xA1\x13\xA1\x14",
            b"\xB1\x10\xB1\x11\xB1\x13\xB1\x14",
            b"\xC1\x10\xC1\x11\xC1\x13\xC1\x14",
            b"\xD1\x10\xD1\x11\xD1\x13\xD1\x14",
        ]
        cpxe4iol.base.read_reg_data.assert_called_with(
            cpxe4iol.start_registers.inputs, length=16
        )

    def test_getitem_0_to_3(self):
        """Test get item"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.base = Mock(
            read_reg_data=Mock(return_value=b"\x00\xAB\x00\xCD\x00\xEF\x00\x12")
        )

        # Act
        channel_values = [cpxe4iol[idx] for idx in range(4)]

        # Assert
        assert channel_values == [b"\x00\xAB", b"\x00\xCD", b"\x00\xEF", b"\x00\x12"]
        cpxe4iol.base.read_reg_data.assert_called_with(
            cpxe4iol.start_registers.inputs, length=4
        )

    @pytest.mark.parametrize(
        "output_register, input_value, expected_value",
        [
            (0, (0, b"\x00\xAB"), (b"\x00\xAB", 0)),
            (0, (1, b"\x00\xCD"), (b"\x00\xCD", 1)),
            (1, (0, b"\x00\xAB"), (b"\x00\xAB", 1)),
            (1, (1, b"\x00\xCD"), (b"\x00\xCD", 2)),
        ],
    )
    def test_write_channel(self, output_register, input_value, expected_value):
        """test write channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.start_registers = StartRegisters(outputs=output_register)
        cpxe4iol.base = Mock(write_reg_data=Mock())

        # Act
        cpxe4iol.write_channel(*input_value)

        # Assert
        cpxe4iol.base.write_reg_data.assert_called_with(*expected_value)

    def test_set_channel_0(self):
        """Test set channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.start_registers = StartRegisters(outputs=0)
        cpxe4iol.base = Mock(write_reg_data=Mock())

        # Act
        cpxe4iol[0] = b"\xFE\x00"

        # Assert
        cpxe4iol.base.write_reg_data.assert_called_with(
            b"\xFE\x00", cpxe4iol.start_registers.outputs
        )

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (True, (4892, 0xAE)),
            (False, (4892, 0xAA)),
        ],
    )
    def test_configure_monitoring_uload(self, input_value, expected_value):
        """Test configure_monitoring_uload"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act
        cpxe4iol.configure_monitoring_uload(input_value)

        # Assert
        cpxe4iol.base.read_function_number.assert_called_with(expected_value[0])
        cpxe4iol.base.write_function_number.assert_called_with(*expected_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (True, (4892 + 1, 0xAB)),
            (False, (4892 + 1, 0xAA)),
        ],
    )
    def test_configure_behaviour_after_scl(self, input_value, expected_value):
        """Test configure_behaviour_after_scl"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act
        cpxe4iol.configure_behaviour_after_scl(input_value)

        # Assert
        cpxe4iol.base.read_function_number.assert_called_with(expected_value[0])
        cpxe4iol.base.write_function_number.assert_called_with(*expected_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (True, (4892 + 1, 0xAA)),
            (False, (4892 + 1, 0xA8)),
        ],
    )
    def test_configure_behaviour_after_sco(self, input_value, expected_value):
        """Test configure_behaviour_after_sco"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act
        cpxe4iol.configure_behaviour_after_sco(input_value)

        # Assert
        cpxe4iol.base.read_function_number.assert_called_with(expected_value[0])
        cpxe4iol.base.write_function_number.assert_called_with(*expected_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (True, (4892 + 6, 0xAB)),
            (False, (4892 + 6, 0xAA)),
        ],
    )
    def test_configure_ps_supply(self, input_value, expected_value):
        """Test configure_ps_supply"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act
        cpxe4iol.configure_ps_supply(input_value)

        # Assert
        cpxe4iol.base.read_function_number.assert_called_with(expected_value[0])
        cpxe4iol.base.write_function_number.assert_called_with(*expected_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (
                ((10, 20), None),
                [
                    call(4892 + 8, 10),
                    call(4892 + 9, 20),
                    call(4892 + 12, 10),
                    call(4892 + 13, 20),
                    call(4892 + 16, 10),
                    call(4892 + 17, 20),
                    call(4892 + 20, 10),
                    call(4892 + 21, 20),
                ],
            ),
            (
                ((10, 20), 0),
                [
                    call(4892 + 8, 10),
                    call(4892 + 9, 20),
                ],
            ),
            (
                ((10, 20), [1, 2]),
                [
                    call(4892 + 12, 10),
                    call(4892 + 13, 20),
                    call(4892 + 16, 10),
                    call(4892 + 17, 20),
                ],
            ),
        ],
    )
    def test_configure_cycle_time(self, input_value, expected_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(write_function_number=Mock())

        # Act
        cpxe4iol.configure_cycle_time(*input_value)

        # Assert
        cpxe4iol.base.write_function_number.assert_has_calls(
            expected_value, any_order=False
        )

    @pytest.mark.parametrize(
        "input_value",
        [
            (True, -1),
            (True, 4),
        ],
    )
    def test_configure_cycle_time_raise_error(self, input_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act & Assert
        with pytest.raises(ValueError):
            cpxe4iol.configure_cycle_time(*input_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (
                (True, None),
                [
                    call(4892 + 10, 0xAB),
                    call(4892 + 14, 0xAB),
                    call(4892 + 18, 0xAB),
                    call(4892 + 22, 0xAB),
                ],
            ),
            (
                (False, None),
                [
                    call(4892 + 10, 0xAA),
                    call(4892 + 14, 0xAA),
                    call(4892 + 18, 0xAA),
                    call(4892 + 22, 0xAA),
                ],
            ),
            (
                (True, 0),
                [
                    call(4892 + 10, 0xAB),
                ],
            ),
            (
                (False, 0),
                [
                    call(4892 + 10, 0xAA),
                ],
            ),
            (
                (True, [1, 2]),
                [
                    call(4892 + 14, 0xAB),
                    call(4892 + 18, 0xAB),
                ],
            ),
            (
                (False, [1, 2]),
                [
                    call(4892 + 14, 0xAA),
                    call(4892 + 18, 0xAA),
                ],
            ),
        ],
    )
    def test_configure_pl_supply(self, input_value, expected_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act
        cpxe4iol.configure_pl_supply(*input_value)

        # Assert
        cpxe4iol.base.write_function_number.assert_has_calls(
            expected_value, any_order=False
        )

    @pytest.mark.parametrize(
        "input_value",
        [
            (True, -1),
            (True, 4),
        ],
    )
    def test_configure_pl_supply_raise_error(self, input_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act & Assert
        with pytest.raises(ValueError):
            cpxe4iol.configure_pl_supply(*input_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (
                (3, None),
                [
                    call(4892 + 11, 0xAB),
                    call(4892 + 15, 0xAB),
                    call(4892 + 19, 0xAB),
                    call(4892 + 23, 0xAB),
                ],
            ),
            (
                (3, 0),
                [
                    call(4892 + 11, 0xAB),
                ],
            ),
            (
                (3, [1, 2]),
                [
                    call(4892 + 15, 0xAB),
                    call(4892 + 19, 0xAB),
                ],
            ),
            (
                (OperatingMode.IO_LINK, None),
                [
                    call(4892 + 11, 0xAB),
                    call(4892 + 15, 0xAB),
                    call(4892 + 19, 0xAB),
                    call(4892 + 23, 0xAB),
                ],
            ),
        ],
    )
    def test_configure_operating_mode(self, input_value, expected_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(
            read_function_number=Mock(return_value=0xAA), write_reg_data=Mock()
        )

        # Act
        cpxe4iol.configure_operating_mode(*input_value)
        # Assert
        cpxe4iol.base.write_function_number.assert_has_calls(
            expected_value, any_order=False
        )

    @pytest.mark.parametrize(
        "input_value",
        [
            (4, 0),
            (-1, 0),
            (0, [-1]),
            (0, [4]),
            (0, -1),
            (0, 4),
        ],
    )
    def test_configure_operating_mode_raise_error(self, input_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock()

        # Act & Assert
        with pytest.raises(ValueError):
            cpxe4iol.configure_operating_mode(*input_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (
                (None),
                [
                    call(4892 + 24),
                    call(4892 + 27),
                    call(4892 + 30),
                    call(4892 + 33),
                ],
            ),
            (
                (0),
                [
                    call(4892 + 24),
                ],
            ),
            (
                ([1, 2]),
                [
                    call(4892 + 27),
                    call(4892 + 30),
                ],
            ),
        ],
    )
    def test_read_line_state(self, input_value, expected_value):
        """Test read_line_state per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(read_function_number=Mock(return_value=0xAD))

        # Act
        state = cpxe4iol.read_line_state(input_value)

        # Assert
        assert (
            state == ["OPERATE"] * len(expected_value)
            if len(expected_value) > 1
            else "OPERATE"
        )
        cpxe4iol.base.read_function_number.assert_has_calls(
            expected_value, any_order=False
        )

    @pytest.mark.parametrize(
        "input_value",
        [
            ([4]),
            ([-1]),
            (4),
            (-1),
        ],
    )
    def test_read_line_state_raise_error(self, input_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock()

        # Act & Assert
        with pytest.raises(ValueError):
            cpxe4iol.read_line_state(input_value)

    @pytest.mark.parametrize(
        "input_value, expected_value",
        [
            (
                (None),
                [("0xb", "0xb")] * 4,
            ),
            (
                (0),
                ("0xb", "0xb"),
            ),
            (
                ([1, 2]),
                [("0xb", "0xb")] * 2,
            ),
        ],
    )
    def test_read_device_error(self, input_value, expected_value):
        """Test read_device_error per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock(read_function_number=Mock(return_value=0xAB))

        # Act
        state = cpxe4iol.read_device_error(input_value)

        # Assert
        assert state == expected_value
        cpxe4iol.base.read_function_number.assert_has_calls(
            [
                call(4892 + 25),
                call(4892 + 26),
                call(4892 + 28),
                call(4892 + 29),
                call(4892 + 31),
                call(4892 + 32),
                call(4892 + 34),
                call(4892 + 35),
            ],
            any_order=False,
        )

    @pytest.mark.parametrize(
        "input_value",
        [
            ([4]),
            ([-1]),
            (4),
            (-1),
        ],
    )
    def test_read_device_error_raise_error(self, input_value):
        """Test configure_cycle_time per channel"""
        # Arrange
        cpxe4iol = CpxE4Iol()
        cpxe4iol.position = 1
        cpxe4iol.base = Mock()

        # Act & Assert
        with pytest.raises(ValueError):
            cpxe4iol.read_device_error(input_value)
