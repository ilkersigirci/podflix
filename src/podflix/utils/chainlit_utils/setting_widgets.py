"""Utility functions for converting Pydantic models to Chainlit settings."""

from typing import Literal, Type

import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch
from pydantic import BaseModel, Field


def convert_pydantic_model_to_chainlit_settings(
    model_class: Type[BaseModel], prefix: str = ""
) -> cl.ChatSettings:
    """Convert a Pydantic model to Chainlit settings.

    Args:
        model_class: Pydantic model class to convert
        prefix: Prefix for widget labels (e.g., 'OpenAI - ')

    Returns:
        cl.ChatSettings instance
    """
    settings = model_class()
    model_fields = model_class.model_fields
    chat_settings = []

    for field_name, field_info in model_fields.items():
        current_value = getattr(settings, field_name)
        field_type = field_info.annotation
        description = field_info.description
        json_schema_extra = field_info.json_schema_extra or {}
        metadata = field_info.metadata or []

        id = field_name.title()
        label = f"{prefix}{field_name.replace('_', ' ').title()}"

        # Default widget mapping
        if field_type is bool:
            chat_settings.append(
                Switch(
                    id=id, label=label, initial=current_value, description=description
                )
            )
        elif field_type in (float, int):
            min_val = None
            max_val = None

            # Extract min/max from metadata
            for constraint in metadata:
                if hasattr(constraint, "ge"):
                    min_val = constraint.ge
                elif hasattr(constraint, "le"):
                    max_val = constraint.le

            # Use defaults if not found in metadata
            min_val = min_val if min_val is not None else -100
            max_val = max_val if max_val is not None else 32000
            step = 0.1 if field_type is float else 1

            chat_settings.append(
                Slider(
                    id=id,
                    label=label,
                    initial=current_value,
                    min=min_val,
                    max=max_val,
                    step=step,
                    description=description,
                )
            )
        elif "choices" in json_schema_extra:
            choices = json_schema_extra["choices"]
            if not isinstance(choices[0], str):
                continue

            chat_settings.append(
                Select(
                    id=id,
                    label=label,
                    initial_value=current_value,
                    values=choices,
                    description=description,
                )
            )

    return cl.ChatSettings(chat_settings)


class OpenAIChatSettings(BaseModel):
    """Pydantic model for OpenAI chat settings."""

    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use for chat completion",
        choices=["gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"],
    )
    streaming: bool = Field(default=True, description="Whether to stream tokens")
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
    logit_bias: int = Field(
        default=0, ge=-100, le=100, description="Modify likelihood of specific tokens"
    )
    response_format: Literal["text", "json_object"] = Field(
        default="text", description="Format for model responses"
    )
    tools_enabled: bool = Field(
        default=False, description="Enable function calling capability"
    )
    log_probs: bool = Field(
        default=False, description="Return log probabilities of tokens"
    )


def get_openai_chat_settings():
    """Get chat settings for OpenAI chat completion parameters."""
    return convert_pydantic_model_to_chainlit_settings(model_class=OpenAIChatSettings)


if __name__ == "__main__":
    chat_settings = get_openai_chat_settings()
