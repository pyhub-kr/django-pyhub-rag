"""Central configuration module for pyhub.

This module provides a centralized location for configuration paths and settings,
eliminating the need for hardcoded paths throughout the codebase.
"""

import os
from pathlib import Path
from typing import Optional, Union


class Config:
    """Configuration management for pyhub."""

    # Default configuration file names
    DEFAULT_TOML_FILENAME = "config.toml"
    DEFAULT_ENV_FILENAME = ".env"

    # Environment variables for custom paths
    TOML_PATH_ENV = "PYHUB_TOML_PATH"
    ENV_PATH_ENV = "PYHUB_ENV_PATH"
    CONFIG_DIR_ENV = "PYHUB_CONFIG_DIR"

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory.

        Priority:
        1. PYHUB_CONFIG_DIR environment variable
        2. ~/.pyhub-rag directory
        """
        config_dir = os.environ.get(cls.CONFIG_DIR_ENV)
        if config_dir:
            return Path(config_dir)
        return Path.home() / ".pyhub-rag"

    @classmethod
    def get_default_toml_path(cls) -> Path:
        """Get the default path for config.toml file.

        Priority:
        1. PYHUB_TOML_PATH environment variable (absolute path)
        2. PYHUB_CONFIG_DIR / config.toml
        3. ~/.pyhub-rag/config.toml
        """
        # Check for explicit path
        toml_path = os.environ.get(cls.TOML_PATH_ENV)
        if toml_path:
            return Path(toml_path)

        # Use config directory
        return cls.get_config_dir() / cls.DEFAULT_TOML_FILENAME

    @classmethod
    def get_default_env_path(cls) -> Path:
        """Get the default path for .env file.

        Priority:
        1. PYHUB_ENV_PATH environment variable (absolute path)
        2. PYHUB_CONFIG_DIR / .env
        3. ~/.pyhub-rag/.env
        """
        # Check for explicit path
        env_path = os.environ.get(cls.ENV_PATH_ENV)
        if env_path:
            return Path(env_path)

        # Use config directory
        return cls.get_config_dir() / cls.DEFAULT_ENV_FILENAME

    @classmethod
    def resolve_path(cls, path: Optional[Union[str, Path]], default_getter: callable) -> Path:
        """Resolve a configuration file path.

        Args:
            path: User-provided path (optional)
            default_getter: Function to get default path

        Returns:
            Resolved Path object
        """
        if path is None:
            return default_getter()
        return Path(path) if isinstance(path, str) else path


# Convenience functions for backward compatibility
def get_default_toml_path() -> Path:
    """Get the default path for .pyhub.toml file."""
    return Config.get_default_toml_path()


def get_default_env_path() -> Path:
    """Get the default path for .pyhub.env file."""
    return Config.get_default_env_path()


# For use in Typer CLI default arguments
DEFAULT_TOML_PATH = Config.get_default_toml_path()
DEFAULT_ENV_PATH = Config.get_default_env_path()
