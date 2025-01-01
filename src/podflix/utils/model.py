"""Model utilities."""

from pathlib import Path
from typing import Any, BinaryIO

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from openai import OpenAI

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

    if env_settings.enable_openai_api is True:
        openai_api_key = env_settings.openai_api_key
    else:
        openai_api_key = "DUMMY_KEY"

    return ChatOpenAI(
        model_name=model_name,
        openai_api_base=openai_api_base,
        openai_api_key=openai_api_key,
        **chat_model_kwargs,
    )


def transcribe_audio_file(
    file: BinaryIO | Path,
    model_name: str | None = None,
) -> str:
    """Transcribe an audio file using OpenAI's Whisper model.

    Examples:
        >>> with open('audio.mp3', 'rb') as f:
        ...     text = transcribe_audio_file(f)
        >>> isinstance(text, str)
        True
        >>> text = transcribe_audio_file(Path('audio.mp3'))
        >>> isinstance(text, str)
        True

    Args:
        file: The audio file to transcribe. Can be a file object or Path.
        model_name: The name of the Whisper model to use. If None, uses the default from env_settings.

    Returns:
        The transcribed text from the audio file.
    """
    if model_name is None:
        model_name = env_settings.whisper_model_name

    if env_settings.enable_openai_api is True:
        openai_api_key = env_settings.openai_api_key
    else:
        openai_api_key = "DUMMY_KEY"

    client = OpenAI(
        base_url=f"{env_settings.whisper_api_base}/v1", api_key=openai_api_key
    )

    if isinstance(file, Path):
        file = file.open("rb")

    try:
        transcription = client.audio.transcriptions.create(model=model_name, file=file)
        return transcription.text
    finally:
        if isinstance(file, Path):
            file.close()
