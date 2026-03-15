"""Application configuration for environment variables."""

from functools import partial
from typing import Annotated, Literal

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
    PlainValidator(AnyHttpUrlAdapter.validate_strings),
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
    auth_type: Literal["password", "oauth"] = "password"
    auth_groups: str = "admin,dev,guest"
    oauth_generic_client_id: str | None = None
    oauth_generic_client_secret: str | None = None
    oauth_generic_auth_url: str | None = None
    oauth_generic_token_url: str | None = None
    oauth_generic_user_info_url: str | None = None
    oauth_generic_scopes: str | None = None
    oauth_generic_name: str = "generic"
    oauth_generic_user_identifier: str = "email"
    embedding_host: CustomHttpUrlStr
    embedding_model_name: str
    enable_openai_api: bool = False
    enable_sqlite_data_layer: bool = False
    hf_token: str | None = None
    langfuse_base_url: CustomHttpUrlStr
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

    @field_validator("auth_groups", mode="before")
    def validate_auth_groups(cls, value):
        """Validate AUTH_GROUPS."""
        VALID_AUTH_GROUPS = ("admin", "dev", "guest")

        if not isinstance(value, str):
            raise ValueError(
                "AUTH_GROUPS must be a comma-separated string of groups."
            )

        groups = [item.strip().lower() for item in value.split(",") if item.strip()]

        if not groups:
            raise ValueError("AUTH_GROUPS must include at least one group.")

        invalid_groups = [group for group in groups if group not in VALID_AUTH_GROUPS]
        if invalid_groups:
            invalid = ", ".join(invalid_groups)
            valid = ", ".join(VALID_AUTH_GROUPS)
            raise ValueError(
                f"Invalid AUTH_GROUPS values: {invalid}. Allowed values: {valid}."
            )

        return ",".join(dict.fromkeys(groups))

    @field_validator("oauth_generic_scopes")
    def validate_oauth_generic_env(cls, value, values):
        """Validate required Generic OAuth vars when AUTH_TYPE is oauth."""
        GENERIC_OAUTH_REQUIRED_ENV_VARS = (
            "OAUTH_GENERIC_CLIENT_ID",
            "OAUTH_GENERIC_CLIENT_SECRET",
            "OAUTH_GENERIC_AUTH_URL",
            "OAUTH_GENERIC_TOKEN_URL",
            "OAUTH_GENERIC_USER_INFO_URL",
            "OAUTH_GENERIC_SCOPES",
        )

        if values.data.get("auth_type") != "oauth":
            return value

        missing_env_vars: list[str] = []

        for env_var in GENERIC_OAUTH_REQUIRED_ENV_VARS:
            field_name = env_var.lower()
            field_value = value if field_name == "oauth_generic_scopes" else values.data.get(field_name)
            if not field_value or not str(field_value).strip():
                missing_env_vars.append(env_var)

        if missing_env_vars:
            missing = ", ".join(missing_env_vars)
            message = (
                "AUTH_TYPE=oauth requires Generic OAuth environment variables. "
                f"Missing: {missing}."
            )
            raise ValueError(message)

        return value


env_settings = EnvSettings()
# fmt: on

if __name__ == "__main__":
    env_settings = EnvSettings()

    logger.info(env_settings.library_base_path, type(env_settings.library_base_path))
    logger.info(env_settings.model_api_base, type(env_settings.model_api_base))
