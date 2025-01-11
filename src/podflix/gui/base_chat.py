import chainlit as cl
from chainlit.types import ThreadDict
from langchain_community.chat_message_histories import ChatMessageHistory
from literalai.helper import utc_now
from loguru import logger
from openai import AsyncOpenAI

from podflix.env_settings import env_settings
from podflix.utils.chainlit_utils.data_layer import apply_sqlite_data_layer_fixes
from podflix.utils.chainlit_utils.general import (
    create_message_history_from_db_thread,
    set_extra_user_session_params,
    simple_auth_callback,
)
from podflix.utils.chainlit_utils.setting_widgets import get_openai_chat_settings
from podflix.utils.pydantic_models import OpenAIChatGenerationSettings

if env_settings.enable_sqlite_data_layer is True:
    apply_sqlite_data_layer_fixes()

async_openai_client = AsyncOpenAI(
    base_url=f"{env_settings.model_api_base}/v1",
    api_key=env_settings.openai_api_key,
)


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(
            label="About",
            message="Tell me about yourself.",
            icon="🚀",
        ),
        cl.Starter(
            label="Json Format",
            message="Write some random things in json format.",
            icon="🚀",
        ),
        cl.Starter(
            label="Code Snippet",
            message="Implement a code snippet in python.",
            icon="🚀",
        ),
    ]


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    return simple_auth_callback(username, password)


@cl.on_settings_update
async def settings_update(settings: cl.ChatSettings):
    """Update settings when changed in UI"""
    cl.user_session.set("settings", OpenAIChatGenerationSettings(**settings))


@cl.on_chat_start
async def on_chat_start():
    message_history = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Respond to user messages using markdown.",
        }
    ]

    set_extra_user_session_params(message_history=message_history)

    chat_settings = get_openai_chat_settings()
    cl.user_session.set("settings", OpenAIChatGenerationSettings())

    await chat_settings.send()


# TODO: Get dict message history from db
@cl.on_chat_resume
def setup_chat_resume(thread: ThreadDict):
    # thread["metadata"] = {}
    logger.debug(f"Type of thread metadata on chat resume: {type(thread['metadata'])}")
    message_history = create_message_history_from_db_thread(thread=thread)

    set_extra_user_session_params(
        user_id=thread["userIdentifier"], message_history=message_history
    )


@cl.on_message
async def on_message(msg: cl.Message):
    message_history: ChatMessageHistory = cl.user_session.get("message_history")
    settings: OpenAIChatGenerationSettings = cl.user_session.get("settings")

    message_history.append({"role": "user", "content": msg.content})

    assistant_message = cl.Message(
        content=" ",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
    )

    stream = await async_openai_client.chat.completions.create(
        messages=message_history,
        stream=True,
        response_format={"type": settings.response_format},
        **settings.model_dump(exclude={"response_format"}),
    )

    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await assistant_message.stream_token(token)

    message_history.append({"role": "assistant", "content": assistant_message.content})

    await assistant_message.update()
