import webbrowser  # noqa: F401
from dataclasses import dataclass  # noqa: F401
from pathlib import Path

import chainlit as cl
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from langchain.schema.runnable.config import RunnableConfig
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessageChunk
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from literalai.helper import utc_now
from loguru import logger

from podflix.db.db_factory import DBInterfaceFactory
from podflix.graph.podcast_rag import compiled_graph
from podflix.utils.chainlit_ui import (
    create_message_history_from_db_thread,
    set_extra_user_session_params,
    simple_auth_callback,
)
from podflix.utils.general import get_lf_traces_url
from podflix.utils.model import transcribe_audio_file

cl_data._data_layer = SQLAlchemyDataLayer(
    DBInterfaceFactory.create().async_connection(),
    ssl_require=False,
    show_logger=True,
)


# TODO: Set starters  based on audio file
# @cl.set_starters
# async def set_starters() -> list[cl.Starter]:
#    pass


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    return simple_auth_callback(username, password)


# @cl.action_callback("Detailed Traces")
# async def on_action(action: cl.Action):
#     # FIXME: Doesn't work inside the docker container
#     webbrowser.open(action.value, new=0)

#     # await cl.Message(
#     #     content=f"Here's your link: [Open Trace]({action.value})", author="System"
#     # ).send()

#     # Optionally remove the action button
#     # await action.remove()


@cl.on_chat_start
async def on_chat_start():
    set_extra_user_session_params()

    system_message = cl.Message(
        content=" ",
        author="System",
        type="system_message",
        created_at=utc_now(),
    )

    files = None

    # Wait for the user to upload a file
    while files is None:
        files = await cl.AskFileMessage(
            content="Please upload a audio file to start the conversation",
            accept=["audio/*"],
            max_files=1,
            max_size_mb=50,
            timeout=180,
        ).send()

    file = files[0]

    async with cl.Step(name="Transcribing the audio file...", type="tool") as step:
        step.input = file

        # NOTE: Workaround to show loading spinner in the ui
        await system_message.stream_token(" ")

        audio_text = transcribe_audio_file(file=Path(file.path))
        step.output = audio_text

    cl.user_session.set("audio_text", audio_text)

    # NOTE: Only inline display is working :(
    # display = "inline" # "side" "page"
    # elements = [cl.Text(name="simple_text", content=audio_text, display=display)]
    # system_message.elements.extend(elements)

    system_message.content = "Audio transcribed successfully 🎉"

    await system_message.update()


@cl.on_chat_resume
def setup_chat_resume(thread: ThreadDict):
    thread["metadata"] = {}
    message_history = create_message_history_from_db_thread(thread=thread)

    set_extra_user_session_params(
        user_id=thread["userIdentifier"], message_history=message_history
    )

    # TODO: Set audio_text from the db
    # cl.user_session.set("audio_text", audio_text)


@cl.on_message
async def on_message(msg: cl.Message):
    lf_cb_handler: LangfuseCallbackHandler = cl.user_session.get("lf_cb_handler")
    session_id: str = cl.user_session.get("session_id")
    message_history: ChatMessageHistory = cl.user_session.get("message_history")
    audio_text: str = cl.user_session.get("audio_text")

    assistant_message = cl.Message(
        content=" ",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
    )

    message_history.add_user_message(msg.content)

    # graph_inputs = {"messages": [HumanMessage(content=msg.content)]}
    graph_inputs = {"messages": message_history.messages, "context": audio_text}

    graph_runnable_config = RunnableConfig(
        callbacks=[
            lf_cb_handler,
            cl.LangchainCallbackHandler(),
        ],
        recursion_limit=10,
        configurable={"session_id": session_id},
    )

    streamable_node_names = ["generate"]

    async for event in compiled_graph.astream_events(
        graph_inputs,
        config=graph_runnable_config,
        version="v2",
    ):
        event_kind = event["event"]
        langgraph_node = event["metadata"].get("langgraph_node", None)

        if event_kind == "on_chat_model_stream":
            if langgraph_node not in streamable_node_names:
                continue

            ai_message_chunk: AIMessageChunk = event["data"]["chunk"]
            ai_message_content = ai_message_chunk.content

            if ai_message_content:
                # NOTE: This automatically updates the assistant_message.content
                await assistant_message.stream_token(ai_message_content)

        # TODO: Find out more robust way to get run_id for langfuse
        if event_kind == "on_chain_end":
            run_id = event.get("run_id", None)

            logger.debug(f"Langfuse Run ID: {run_id}")

    lf_traces_url = get_lf_traces_url(langchain_run_id=run_id)

    # actions = [
    #     cl.Action(
    #         name="Detailed Traces",
    #         value=lf_traces_url,
    #         description="Detailed Logs in Langfuse",
    #     )
    # ]

    # assistant_message.actions.extend(actions)

    elements = [
        cl.Text(
            name="Detailed Traces",
            content=f"[Detailed Logs]({lf_traces_url})",
            display="inline",
        )
    ]
    assistant_message.elements.extend(elements)

    await assistant_message.update()
    message_history.add_ai_message(assistant_message.content)
