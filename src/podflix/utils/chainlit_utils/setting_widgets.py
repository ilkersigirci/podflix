"""Utility functions for converting Pydantic models to Chainlit settings."""

from typing import Type

import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch
from loguru import logger
from pydantic import BaseModel

from podflix.utils.pydantic_models import OpenAIChatGenerationSettings


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

        label = f"{prefix}{field_name.replace('_', ' ').title()}"

        # Default widget mapping
        if field_type is bool:
            chat_settings.append(
                Switch(
                    id=field_name,
                    label=label,
                    initial=current_value,
                    description=description,
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
                    id=field_name,
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
                logger.debug(f"Skipping {field_name} due to non-string choices")
                continue

            chat_settings.append(
                Select(
                    id=field_name,
                    label=label,
                    initial_value=current_value,
                    values=choices,
                    description=description,
                )
            )

    return cl.ChatSettings(chat_settings)


def get_openai_chat_settings():
    """Get chat settings for OpenAI chat completion parameters."""
    return convert_pydantic_model_to_chainlit_settings(
        model_class=OpenAIChatGenerationSettings
    )


if __name__ == "__main__":
    chat_settings = get_openai_chat_settings()
