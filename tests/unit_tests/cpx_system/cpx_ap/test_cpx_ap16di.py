"""Contains tests for CpxAp16Di class"""
from unittest.mock import Mock
import pytest

from cpx_io.cpx_system.cpx_ap.ap16di import CpxAp16Di


class TestCpxAp16Di:
    "Test CpxAp16Di"

    def test_constructor_correct_type(self):
        """Test constructor"""
        # Arrange

        # Act
        cpxap16di = CpxAp16Di()

        # Assert
        assert isinstance(cpxap16di, CpxAp16Di)

    def test_read_channels_correct_values(self):
        """Test read channels"""
        # Arrange
        cpxap16di = CpxAp16Di()

        cpxap16di.base = Mock(read_reg_data=Mock(return_value=[0xCAFE]))

        # Act
        channel_values = cpxap16di.read_channels()

        # Assert
        assert channel_values == [
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            False,
            True,
            False,
            True,
            False,
            False,
            True,
            True,
        ]

    def test_read_channel_correct_values(self):
        """Test read channel"""
        # Arrange
        cpxap16di = CpxAp16Di()

        cpxap16di.base = Mock(read_reg_data=Mock(return_value=[0xCAFE]))

        # Act
        channel_values = [cpxap16di.read_channel(idx) for idx in range(16)]

        # Assert
        assert channel_values == [
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            False,
            True,
            False,
            True,
            False,
            False,
            True,
            True,
        ]

    def test_get_item_correct_values(self):
        """Test get item"""
        # Arrange
        cpxap16di = CpxAp16Di()

        cpxap16di.base = Mock(read_reg_data=Mock(return_value=[0xCAFE]))

        # Act
        channel_values = [cpxap16di[idx] for idx in range(16)]

        # Assert
        assert channel_values == [
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            False,
            True,
            False,
            True,
            False,
            False,
            True,
            True,
        ]

    @pytest.mark.parametrize("input_value, expected_value", [(1, 1), (2, 2), (3, 3)])
    def test_configure_debounce_time_successful_configuration(
        self, input_value, expected_value
    ):
        """Test configure_debounce_time and expect success"""
        # Arrange
        MODULE_POSITION = 1  # pylint: disable=invalid-name

        cpxap16di = CpxAp16Di()
        cpxap16di.position = MODULE_POSITION

        cpxap16di.base = Mock(write_parameter=Mock())

        # Act
        PARAMETER_ID = 20014  # pylint: disable=invalid-name
        cpxap16di.configure_debounce_time(input_value)

        # Assert
        cpxap16di.base.write_parameter.assert_called_with(
            MODULE_POSITION, PARAMETER_ID, 0, expected_value
        )

    @pytest.mark.parametrize("input_value", [-1, 4])
    def test_configure_debounce_time_raise_error(self, input_value):
        """Test configure_debounce_time and expect error"""
        # Arrange
        MODULE_POSITION = 1  # pylint: disable=invalid-name

        cpxap16di = CpxAp16Di()
        cpxap16di.position = MODULE_POSITION

        cpxap16di.base = Mock(write_parameter=Mock())

        # Act & Assert
        with pytest.raises(ValueError):
            cpxap16di.configure_debounce_time(input_value)