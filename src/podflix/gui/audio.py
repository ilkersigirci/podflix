from pathlib import Path
from typing import BinaryIO

import chainlit as cl
from chainlit.types import ThreadDict
from langchain_community.chat_message_histories import ChatMessageHistory
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from literalai.helper import utc_now

from podflix.env_settings import env_settings
from podflix.graph.podcast_rag import compiled_graph
from podflix.utils.chainlit_utils.data_layer import (
    apply_sqlite_data_layer_fixes,
    get_read_url_of_file,
)
from podflix.utils.chainlit_utils.general import (
    create_message_history_from_db_thread,
    get_current_chainlit_thread_id,
    set_extra_user_session_params,
    simple_auth_callback,
)
from podflix.utils.general import get_lf_traces_url
from podflix.utils.graph_runner import GraphRunner
from podflix.utils.model import transcribe_audio_file

if env_settings.enable_sqlite_data_layer is True:
    apply_sqlite_data_layer_fixes()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    return simple_auth_callback(username, password)


@cl.step(type="tool")
async def transcribing_tool(file: BinaryIO | Path):
    transcription = transcribe_audio_file(file=file, response_format="verbose_json")
    whole_text = transcription.text

    # Format segments for the UI
    segments = [
        {"id": seg.id, "start": seg.start, "end": seg.end, "text": seg.text.strip()}
        for seg in transcription.segments
    ]

    return whole_text, segments


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
            timeout=360,
        ).send()

    file = files[0]

    # NOTE: Workaround to show the tool progres on the ui
    await system_message.stream_token("Transcribing the audio file...")

    audio_text, segments = await transcribing_tool(file=Path(file.path))

    cl.user_session.set("audio_text", audio_text)

    # NOTE: Workaround to get s3 url of the uploaded file in the current thread
    thread_id = get_current_chainlit_thread_id()
    audio_url = await get_read_url_of_file(thread_id=thread_id, file_name=file.name)

    # Create audio element with transcript and segments
    audio_element = cl.CustomElement(
        name="AudioWithTranscript",
        props={
            "name": file.name,
            "url": audio_url,
            "segments": segments,
        },
        display="side",
    )

    system_message.elements.append(audio_element)

    system_message.content = "Audio transcribed successfully 🎉"
    system_message.content += "\nOfficialAudio AudioWithTranscript"

    await system_message.update()


@cl.on_chat_resume
def setup_chat_resume(thread: ThreadDict):
    # thread["metadata"] = {}
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

    message_history.add_user_message(msg.content)

    assistant_message = cl.Message(
        content=" ",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
    )

    graph_inputs = {"messages": message_history.messages, "context": audio_text}

    graph_runner = GraphRunner(
        graph=compiled_graph,
        graph_inputs=graph_inputs,
        graph_streamable_node_names=["generate"],
        lf_cb_handler=lf_cb_handler,
        session_id=session_id,
        assistant_message=assistant_message,
    )

    await graph_runner.run_graph()

    lf_traces_url = get_lf_traces_url(langchain_run_id=graph_runner.run_id)

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
