"""General utility functions."""

import importlib
import os

from langfuse import Langfuse
from loguru import logger

from podflix.env_settings import env_settings


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


def check_lf_credentials() -> None:
    """Check if the Langfuse credentials are correct.

    Examples:
        >>> check_lf_credentials()
        None

    Returns:
        None

    Raises:
        ValueError: If we can't connect to lanfuse using gived credentials.
    """
    try:
        langfuse_obj = Langfuse()
        lf_check_result = langfuse_obj.auth_check()

        if lf_check_result is False:
            raise Exception("Langfuse Auth Check Failed")

        logger.debug("Langfuse Auth Check Passed")
    except Exception as e:
        logger.error(f"Langfuse Auth Check Error: {e}")
        raise e


def get_lf_project_id() -> str:
    """Get the Langfuse project ID.

    Examples:
        >>> get_lf_project_id()
        'cm5a4jaff0006r8yk44cvas5a'

    Returns:
        Langfuse project ID.
    """
    langfuse_obj = Langfuse()
    projects = langfuse_obj.client.projects.get()
    return projects.data[0].id


def get_lf_session_url(session_id: str) -> str:
    """Get the Langfuse session URL.

    Examples:
        >>> get_lf_session_url("123")
        'https://YOUR_LANFUSE_HOST/project/YOUR_PROJECT_ID/sessions/123'

    Args:
        session_id: Session ID.

    Returns:
        Langfuse session URL.
    """
    langfuse_project_id = get_lf_project_id()

    return f"{env_settings.langfuse_host}/project/{langfuse_project_id}/sessions/{session_id}"


# TODO: Find out how to get langfuse traces_id for each llm call
def get_lf_traces_url(langchain_run_id: str) -> str:
    """Get the Langfuse traces URL.

    Examples:
        >>> get_lf_traces_url("123")
        'https://YOUR_LANFUSE_HOST/project/YOUR_PROJECT_ID/traces/123'

    Args:
        langchain_run_id: Langchain run ID.

    Returns:
        Langfuse traces URL.
    """
    if langchain_run_id is None:
        raise ValueError("langchain_run_id cannot be None")

    langfuse_project_id = get_lf_project_id()

    return f"{env_settings.langfuse_host}/project/{langfuse_project_id}/traces/{langchain_run_id}"
