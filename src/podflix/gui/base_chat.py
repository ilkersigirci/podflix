import time
from typing import AsyncIterator

import chainlit as cl
from chainlit.types import ThreadDict
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages.utils import convert_to_openai_messages
from literalai.helper import utc_now
from loguru import logger  # noqa: F401
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

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
def auth_callback(username: str, password: str) -> bool:
    return simple_auth_callback(username, password)


@cl.on_settings_update
async def settings_update(settings: cl.ChatSettings) -> None:
    """Update settings when changed in UI"""
    cl.user_session.set("settings", OpenAIChatGenerationSettings(**settings))


@cl.on_chat_start
async def on_chat_start() -> None:
    set_extra_user_session_params()

    chat_settings = get_openai_chat_settings()
    cl.user_session.set("settings", OpenAIChatGenerationSettings())

    await chat_settings.send()


@cl.on_chat_resume
async def setup_chat_resume(thread: ThreadDict) -> None:
    message_history = create_message_history_from_db_thread(thread=thread)

    set_extra_user_session_params(
        user_id=thread["userIdentifier"], message_history=message_history
    )

    chat_settings = get_openai_chat_settings()
    cl.user_session.set("settings", OpenAIChatGenerationSettings())

    await chat_settings.send()


async def stream_tokens(
    stream: AsyncIterator[ChatCompletionChunk], assistant_message: cl.Message
) -> None:
    async for chunk in stream:
        if token := chunk.choices[0].delta.content or "":
            await assistant_message.stream_token(token)


async def handle_thinking_step(
    stream: AsyncIterator[ChatCompletionChunk],
    assistant_message: cl.Message,
    start_time: float,
) -> None:
    thinking = False

    async with cl.Step(name="Thinking") as thinking_step:
        async for chunk in stream:
            delta = chunk.choices[0].delta

            if not delta.content:
                continue

            if delta.content == "<think>":
                thinking = True
                continue

            if delta.content == "</think>":
                thinking = False
                thought_for = round(time.time() - start_time)
                thinking_step.name = f"Thought for {thought_for}s"
                await thinking_step.update()
                continue

            if thinking:
                await thinking_step.stream_token(delta.content)
            else:
                await assistant_message.stream_token(delta.content)


@cl.on_message
async def on_message(msg: cl.Message) -> None:
    message_history: ChatMessageHistory = cl.user_session.get("message_history")
    settings: OpenAIChatGenerationSettings = cl.user_session.get("settings")

    message_history.add_user_message(msg.content)

    assistant_message = cl.Message(
        content="",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
    )

    system_message = [
        {
            "role": "system",
            "content": "You are a helpful assistant called Ilkerflix. Respond to user messages using markdown.",
        }
    ]

    messages_openai = system_message + convert_to_openai_messages(
        message_history.messages
    )

    stream = await async_openai_client.chat.completions.create(
        messages=messages_openai,
        stream=True,
        response_format={"type": settings.response_format},
        **settings.model_dump(exclude={"response_format"}),
    )

    start = time.time()

    # TODO: Add more robust check your thinking models
    use_thinking = "R1" in env_settings.model_name

    if use_thinking is True:
        await handle_thinking_step(
            stream=stream, assistant_message=assistant_message, start_time=start
        )
    else:
        await stream_tokens(stream=stream, assistant_message=assistant_message)

    message_history.add_ai_message(assistant_message.content)
    await assistant_message.send()
