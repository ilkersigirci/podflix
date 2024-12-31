"""Model utilities."""

from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from podflix.env_settings import env_settings


def mock_llm(message: str = "MOCK MESSAGE") -> FakeListChatModel | StrOutputParser:
    """Create a mock language model for testing purposes.

    Examples:
        >>> model = mock_llm("Test response")
        >>> isinstance(model, (FakeListChatModel, StrOutputParser))
        True
        >>> model = mock_llm()
        >>> isinstance(model, (FakeListChatModel, StrOutputParser))
        True

    Args:
        message: The message to be returned by the mock model. Defaults to "MOCK MESSAGE".

    Returns:
        A chain of FakeListChatModel and StrOutputParser that returns the specified message.
    """
    model = FakeListChatModel(responses=[message])

    return model | StrOutputParser()


def get_chat_model(
    model_name: str | None = None,
    chat_model_kwargs: dict[Any] | None = None,
) -> ChatOpenAI:
    """Create and configure a ChatOpenAI model instance.

    Examples:
        >>> model = get_chat_model()
        >>> isinstance(model, ChatOpenAI)
        True
        >>> model = get_chat_model("gpt-4o-mini", {"temperature": 0.7})
        >>> isinstance(model, ChatOpenAI)
        True

    Args:
        model_name: The name of the model to use. If None, uses the default from env_settings.
        chat_model_kwargs: Additional keyword arguments to pass to ChatOpenAI. Defaults to None.

    Returns:
        A configured ChatOpenAI model instance ready for use.
    """
    if chat_model_kwargs is None:
        chat_model_kwargs = {}

    openai_api_base = f"{env_settings.model_api_base}/v1"

    if model_name is None:
        model_name = env_settings.model_name

    return ChatOpenAI(
        model_name=model_name, openai_api_base=openai_api_base, **chat_model_kwargs
    )
