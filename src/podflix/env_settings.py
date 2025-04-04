"""Application configuration for environment variables."""

from functools import partial
from typing import Annotated, Literal  # noqa: F401

from loguru import logger
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    Field,
    PlainValidator,
    TypeAdapter,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

AnyHttpUrlAdapter = TypeAdapter(AnyHttpUrl)

CustomHttpUrlStr = Annotated[
    str,
    PlainValidator(lambda x: AnyHttpUrlAdapter.validate_strings(x)),
    AfterValidator(lambda x: str(x).rstrip("/")),
]


def allowed_values(v, values):
    """Validate if a value is in a set of allowed values.

    Examples:
        >>> allowed_values("a", ["a", "b"])
        'a'
        >>> allowed_values(1, [1, 2, 3])
        1

    Args:
        v: The value to validate
        values: A collection of allowed values

    Returns:
        The validated value if it exists in the allowed values

    Raises:
        AssertionError: If the value is not in the allowed values
    """
    assert v in values
    return v


# fmt: off
class EnvSettings(BaseSettings):
    """This class is used to load environment variables.

    They are either from environment or from a .env file and store them as class attributes.

    Note:
        - environment variables will always take priority over values loaded from a dotenv file
        - environment variable names are case-insensitive
        - environment variable type is inferred from the type hint of the class attribute
        - For environment variables that are not set, a default value should be provided

    For more info, see the related pydantic docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        validate_default=True,
        case_sensitive=False,
        env_ignore_empty=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    chainlit_app_type: Annotated[str, AfterValidator(partial(allowed_values, values=["base_chat", "mock", "audio"]))] = "mock"
    chainlit_user_name: str = "admin"
    chainlit_user_password: str = "admin"
    embedding_host: CustomHttpUrlStr
    embedding_model_name: str
    enable_openai_api: bool = False
    enable_sqlite_data_layer: bool = False
    hf_token: str | None = None
    langfuse_host: CustomHttpUrlStr
    langfuse_public_key: str
    langfuse_secret_key: str
    library_base_path: str = Field(default=..., description="Path to the library base directory")
    model_api_base: CustomHttpUrlStr
    model_name: str
    openai_api_key: str | None = None
    rerank_model_name: str
    timeout_limit: int = 30
    whisper_api_base: CustomHttpUrlStr
    whisper_model_name: str

    @field_validator("openai_api_key")
    def validate_openai_key(cls, value, values):
        """Validate the OpenAI API key."""
        if values.data.get("enable_openai_api") is True and value is None:
            message = "OpenAI API key should be set, when enable_openai_api is True."
            logger.error(message)
            raise ValueError(message)

        return value

    @field_validator("model_api_base")
    def validate_model_api_base(cls, value, values):
        """Validate the model API base URL."""
        if values.data.get("enable_openai_api") is True:
            logger.debug("When OpenAI API is enabled, `model_api_base` environment is ignored and set to OpenAI API.")

            return "https://api.openai.com"

        return value


env_settings = EnvSettings()
# fmt: on

if __name__ == "__main__":
    env_settings = EnvSettings()

    logger.info(env_settings.library_base_path, type(env_settings.library_base_path))
    logger.info(env_settings.model_api_base, type(env_settings.model_api_base))
