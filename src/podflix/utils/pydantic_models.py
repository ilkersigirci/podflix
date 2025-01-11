"""Pydantic models for Podflix."""

from pydantic import BaseModel, Field

from podflix.env_settings import env_settings


def get_available_models():
    """Return available models based on environment settings."""
    if env_settings.enable_openai_api:
        return ["gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"]
    return [env_settings.model_name]


def get_default_model():
    """Return the default model based on environment settings."""
    return (
        env_settings.model_name if not env_settings.enable_openai_api else "gpt-4o-mini"
    )


class OpenAIChatGenerationSettings(BaseModel):
    """Pydantic model for OpenAI chat settings."""

    model: str = Field(
        default=get_default_model(),
        description="Model to use for chat completion",
        choices=get_available_models(),
    )
    temperature: float = Field(
        default=0.7, ge=0, le=2, description="Controls randomness in the output"
    )
    max_tokens: int = Field(
        default=2000, ge=1, le=32000, description="Maximum number of tokens to generate"
    )
    top_p: float = Field(
        default=1.0, ge=0, le=1, description="Controls diversity via nucleus sampling"
    )
    frequency_penalty: float = Field(
        default=0.0, ge=-2, le=2, description="Reduces repetition of token sequences"
    )
    presence_penalty: float = Field(
        default=0.0,
        ge=-2,
        le=2,
        description="Reduces likelihood of repeating information",
    )
    seed: int = Field(
        default=-1,
        ge=-1,
        le=2**32 - 1,
        description="Random seed for deterministic completions",
    )
    n: int = Field(
        default=1, ge=1, le=5, description="Number of completions to generate"
    )
    response_format: str = Field(
        default="text",
        description="Format for model responses",
        choices=["text", "json_object"],
    )
    logprobs: bool = Field(
        default=False, description="Return log probabilities of tokens"
    )
