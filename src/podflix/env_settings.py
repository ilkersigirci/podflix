"""Application configuration for environment variables."""

from functools import partial  # noqa: F401
from typing import Annotated, Literal

from loguru import logger
from pydantic import AfterValidator, AnyHttpUrl, Field, PlainValidator, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

AnyHttpUrlAdapter = TypeAdapter(AnyHttpUrl)

CustomHttpUrlStr = Annotated[
    str,
    PlainValidator(lambda x: AnyHttpUrlAdapter.validate_strings(x)),
    AfterValidator(lambda x: str(x).rstrip("/")),
]

# NOTE: Alternative for Literal values
# from pydantic.functional_validators import AfterValidator
# login_type: Annotated[str, AfterValidator(partial(allowed_values, values=["a", "b"]))]


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

    chainlit_auth_secret: str = "cKSq*mqAQmd+m5,^Z1tjvEUp5q=kepTNNkHT93:zAe44gL-9pua35pPR?I0Ag:rT"
    cross_encoder_host: CustomHttpUrlStr
    embedding_host: CustomHttpUrlStr
    embedding_model_name: str
    enable_starter_questions: bool = True
    hf_token: str | None = None
    langfuse_host: CustomHttpUrlStr
    langfuse_public_key: str
    langfuse_secret_key: str
    library_base_path: str = Field(default=..., description="Path to the library base directory")
    login_type: Literal["password", "header"] = "password"
    model_host: CustomHttpUrlStr
    model_name: str
    openai_api_key: str | None = None
    postgres_db: str | None = None
    postgres_host: str | None = None
    postgres_password: str | None = None
    postgres_port: int | None = None
    postgres_user: str | None = None
    sqlaclhemy_db_type: Literal["sqlite", "postgres"] = "sqlite"
    timeout_limit: int = 30

env_settings = EnvSettings()
# fmt: on

if __name__ == "__main__":
    env_settings = EnvSettings()

    logger.info(env_settings.library_base_path, type(env_settings.library_base_path))
    logger.info(env_settings.login_type, type(env_settings.login_type))