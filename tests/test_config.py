"""Tests for the config module."""

import os
from pathlib import Path
from unittest.mock import patch


from pyhub.config import Config, get_default_env_path, get_default_toml_path


class TestConfig:
    """Test cases for Config class."""

    def test_default_paths(self):
        """Test default configuration paths."""
        toml_path = Config.get_default_toml_path()
        env_path = Config.get_default_env_path()

        assert toml_path == Path.home() / ".pyhub-rag" / "config.toml"
        assert env_path == Path.home() / ".pyhub-rag" / ".env"

    def test_convenience_functions(self):
        """Test convenience functions."""
        assert get_default_toml_path() == Config.get_default_toml_path()
        assert get_default_env_path() == Config.get_default_env_path()

    @patch.dict(os.environ, {"PYHUB_CONFIG_DIR": "/custom/config"})
    def test_custom_config_dir(self):
        """Test custom configuration directory via environment variable."""
        config_dir = Config.get_config_dir()
        assert config_dir == Path("/custom/config")

        toml_path = Config.get_default_toml_path()
        env_path = Config.get_default_env_path()

        assert toml_path == Path("/custom/config/config.toml")
        assert env_path == Path("/custom/config/.env")

    @patch.dict(os.environ, {"PYHUB_TOML_PATH": "/explicit/path/config.toml"})
    def test_explicit_toml_path(self):
        """Test explicit TOML path via environment variable."""
        toml_path = Config.get_default_toml_path()
        assert toml_path == Path("/explicit/path/config.toml")

        # Env path should still use default
        env_path = Config.get_default_env_path()
        assert env_path == Path.home() / ".pyhub-rag" / ".env"

    @patch.dict(os.environ, {"PYHUB_ENV_PATH": "/explicit/path/.env"})
    def test_explicit_env_path(self):
        """Test explicit env path via environment variable."""
        env_path = Config.get_default_env_path()
        assert env_path == Path("/explicit/path/.env")

        # TOML path should still use default
        toml_path = Config.get_default_toml_path()
        assert toml_path == Path.home() / ".pyhub-rag" / "config.toml"

    @patch.dict(os.environ, {"PYHUB_CONFIG_DIR": "/config", "PYHUB_TOML_PATH": "/explicit/config.toml"})
    def test_explicit_path_precedence(self):
        """Test that explicit paths take precedence over config dir."""
        toml_path = Config.get_default_toml_path()
        assert toml_path == Path("/explicit/config.toml")

        # Env path should use config dir
        env_path = Config.get_default_env_path()
        assert env_path == Path("/config/.env")

    def test_resolve_path_with_none(self):
        """Test resolve_path with None input."""
        result = Config.resolve_path(None, Config.get_default_toml_path)
        assert result == Config.get_default_toml_path()

    def test_resolve_path_with_string(self):
        """Test resolve_path with string input."""
        result = Config.resolve_path("/custom/path.toml", Config.get_default_toml_path)
        assert result == Path("/custom/path.toml")

    def test_resolve_path_with_path(self):
        """Test resolve_path with Path input."""
        custom_path = Path("/custom/path.toml")
        result = Config.resolve_path(custom_path, Config.get_default_toml_path)
        assert result == custom_path
