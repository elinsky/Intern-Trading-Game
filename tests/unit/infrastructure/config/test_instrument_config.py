"""Tests for instrument configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from intern_trading_game.domain.exchange.models.instrument import Instrument
from intern_trading_game.infrastructure.config.loader import ConfigLoader


class TestInstrumentConfig:
    """Test loading instruments from configuration."""

    def test_load_instruments_from_config(self):
        """Test loading instrument definitions from YAML.

        Given - YAML config with instrument definitions
        When - Config loader reads the instruments
        Then - Returns list of Instrument objects
        """
        # Given - Config with instruments (all fields required)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "instruments": [
                    {
                        "symbol": "SPX_4500_CALL",
                        "strike": 4500.0,
                        "option_type": "call",
                        "underlying": "SPX",
                    },
                    {
                        "symbol": "SPX_4500_PUT",
                        "strike": 4500.0,
                        "option_type": "put",
                        "underlying": "SPX",
                    },
                    {
                        "symbol": "SPY_450_CALL",
                        "strike": 450.0,
                        "option_type": "call",
                        "underlying": "SPY",
                    },
                ]
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load instruments
            loader = ConfigLoader(config_path)
            instruments = loader.get_instruments()

            # Then - Should return list of Instrument objects
            assert len(instruments) == 3

            # Check first instrument
            inst1 = instruments[0]
            assert isinstance(inst1, Instrument)
            assert inst1.symbol == "SPX_4500_CALL"
            assert inst1.strike == 4500.0
            assert inst1.option_type == "call"
            assert inst1.underlying == "SPX"

            # Check second instrument
            inst2 = instruments[1]
            assert inst2.symbol == "SPX_4500_PUT"
            assert inst2.option_type == "put"
            assert inst2.strike == 4500.0
            assert inst2.underlying == "SPX"

            # Check third instrument
            inst3 = instruments[2]
            assert inst3.symbol == "SPY_450_CALL"
            assert inst3.strike == 450.0
            assert inst3.underlying == "SPY"

        finally:
            config_path.unlink()

    def test_missing_instruments_section_returns_empty_list(self):
        """Test that missing instruments section returns empty list.

        Given - Config without instruments section
        When - Request instruments
        Then - Returns empty list
        """
        # Given - Config without instruments
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"roles": {"market_maker": {}}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load instruments
            loader = ConfigLoader(config_path)
            instruments = loader.get_instruments()

            # Then - Should return empty list
            assert instruments == []

        finally:
            config_path.unlink()

    def test_empty_instruments_list(self):
        """Test empty instruments list in config.

        Given - Instruments section exists but is empty
        When - Load instruments
        Then - Returns empty list
        """
        # Given - Empty instruments list
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"instruments": []}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load instruments
            loader = ConfigLoader(config_path)
            instruments = loader.get_instruments()

            # Then - Should return empty list
            assert instruments == []

        finally:
            config_path.unlink()

    def test_invalid_option_type_raises_error(self):
        """Test that invalid option type raises error.

        Given - Instrument with invalid option_type
        When - Try to load instruments
        Then - Raises ValueError
        """
        # Given - Invalid option type
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "instruments": [
                    {
                        "symbol": "TEST",
                        "strike": 100.0,
                        "option_type": "invalid",  # Should be call or put
                        "underlying": "TEST",
                    }
                ]
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise ValueError
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_instruments()

            assert "Option type must be 'call' or 'put'" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raises error.

        Given - Instrument missing required fields
        When - Try to load instruments
        Then - Raises KeyError with field name
        """
        # Given - Missing strike
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "instruments": [
                    {
                        "symbol": "TEST",
                        # Missing strike
                        "option_type": "call",
                        "underlying": "TEST",
                    }
                ]
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise KeyError
            loader = ConfigLoader(config_path)
            with pytest.raises(KeyError) as exc_info:
                loader.get_instruments()

            assert "strike" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_config_enforces_all_required_fields(self):
        """Test that config loader enforces all required fields.

        Given - Instrument missing underlying field
        When - Try to load instruments
        Then - Raises KeyError
        """
        # Given - Missing underlying
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "instruments": [
                    {
                        "symbol": "TEST_100_CALL",
                        "strike": 100.0,
                        "option_type": "call",
                        # Missing underlying
                    }
                ]
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise KeyError
            loader = ConfigLoader(config_path)
            with pytest.raises(KeyError) as exc_info:
                loader.get_instruments()

            assert "underlying" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_instruments_with_different_underlyings(self):
        """Test loading instruments with different underlying assets.

        Given - Mix of SPX and SPY options
        When - Load instruments
        Then - All instruments loaded with correct underlyings
        """
        # Given - SPX and SPY options
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "instruments": [
                    {
                        "symbol": "SPX_4400_CALL",
                        "strike": 4400.0,
                        "option_type": "call",
                        "underlying": "SPX",
                    },
                    {
                        "symbol": "SPY_440_PUT",
                        "strike": 440.0,
                        "option_type": "put",
                        "underlying": "SPY",
                    },
                    {
                        "symbol": "SPX_4600_PUT",
                        "strike": 4600.0,
                        "option_type": "put",
                        "underlying": "SPX",
                    },
                ]
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load instruments
            loader = ConfigLoader(config_path)
            instruments = loader.get_instruments()

            # Then - All loaded correctly
            assert len(instruments) == 3

            # Group by underlying
            spx_instruments = [i for i in instruments if i.underlying == "SPX"]
            spy_instruments = [i for i in instruments if i.underlying == "SPY"]

            assert len(spx_instruments) == 2
            assert len(spy_instruments) == 1

            # Check SPY option
            spy_opt = spy_instruments[0]
            assert spy_opt.symbol == "SPY_440_PUT"
            assert spy_opt.strike == 440.0

        finally:
            config_path.unlink()
