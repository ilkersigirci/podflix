"""General utility functions."""

import importlib
import os

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser


def check_env_vars(env_vars: list[str] | None = None) -> None:
    """Checks if the required environment variables are set.

    Examples:
        >>> check_env_vars(['API_KEY', 'SECRET_KEY'])
        None
        >>> check_env_vars(None)
        None
        >>> check_env_vars(['NONEXISTENT_VAR'])
        Traceback (most recent call last):
        ValueError: Please set NONEXISTENT_VAR env var.

    Args:
        env_vars: List of environment variables to check. Defaults to None.

    Returns:
        None

    Raises:
        ValueError: If any of the environment variables are not set.
    """
    if env_vars is None:
        return

    for env_var in env_vars:
        if os.getenv(env_var) is None:
            raise ValueError(f"Please set {env_var} env var.")


def is_module_installed(module_name: str, throw_error: bool = False) -> bool:
    """Check if the module is installed or not.

    Examples:
        >>> is_module_installed(module_name="yaml", throw_error=False)
        True
        >>> is_module_installed(module_name="numpy", throw_error=False)
        False
        >>> is_module_installed(module_name="numpy", throw_error=True)
        Traceback (most recent call last):
        ImportError: Module numpy is not installed.

    Args:
        module_name: Name of the module to be checked.
        throw_error: If True, raises ImportError if module is not installed.

    Returns:
        Returns True if module is installed, False otherwise.

    Raises:
        ImportError: If throw_error is True and module is not installed.
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError as e:
        if throw_error:
            message = f"Module {module_name} is not installed."
            raise ImportError(message) from e
        return False


def mock_llm(message: str = "MOCK MESSAGE") -> FakeListChatModel | StrOutputParser:
    """Create a mock language model for testing purposes.

    Examples:
        >>> model = mock_llm("Test response")
        >>> isinstance(model, (FakeListChatModel, StrOutputParser))
        True

    Args:
        message: The message to be returned by the mock model. Defaults to "MOCK MESSAGE".

    Returns:
        A chain of FakeListChatModel and StrOutputParser that returns the specified message.
    """
    model = FakeListChatModel(responses=[message])

    return model | StrOutputParser()
