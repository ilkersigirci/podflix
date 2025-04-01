from pathlib import Path
from typing import BinaryIO

import chainlit as cl
from chainlit.types import ThreadDict
from langchain_community.chat_message_histories import ChatMessageHistory
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from literalai.helper import utc_now
from loguru import logger  # noqa: F401

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
from podflix.utils.youtube import convert_vtt_to_segments, download_youtube_subtitles

if env_settings.enable_sqlite_data_layer is True:
    apply_sqlite_data_layer_fixes()


@cl.set_chat_profiles
async def chat_profile() -> list[cl.ChatProfile]:
    return [
        cl.ChatProfile(
            name="Local.Audio",
            markdown_description="Transcribe your own audio file",
            icon="https://picsum.photos/250",
        ),
        cl.ChatProfile(
            name="Youtube.Audio",
            markdown_description="Transcribe a Youtube video",
            icon="https://picsum.photos/200",
        ),
    ]


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    return simple_auth_callback(username, password)


@cl.step(name="Transcribe Audio", type="tool")
async def transcribing_tool(file: BinaryIO | Path):
    # NOTE: Workaround to show the tool progres on the ui
    step_message = cl.Message(content="")
    await step_message.stream_token("Transcribing the audio file...")

    transcription = await transcribe_audio_file(
        file=file, response_format="verbose_json"
    )
    whole_text = transcription.text

    # Format segments for the UI
    segments = [
        {"id": seg.id, "start": seg.start, "end": seg.end, "text": seg.text.strip()}
        for seg in transcription.segments
    ]

    await step_message.remove()

    return whole_text, segments


@cl.step(name="Transcribe Youtube", type="tool")
async def transcribing_tool_yt(url: str):
    # NOTE: Workaround to show the tool progres on the ui
    step_message = cl.Message(content="")
    await step_message.stream_token("Transcribing the youtube video...")

    vtt_content = await download_youtube_subtitles(url=url)
    transcription = convert_vtt_to_segments(vtt_content=vtt_content)
    whole_text = transcription.text

    # Format segments for the UI
    segments = transcription.model_dump()["segments"]

    await step_message.remove()

    return whole_text, segments


@cl.on_chat_start
async def on_chat_start():
    set_extra_user_session_params()

    chat_profile = cl.user_session.get("chat_profile")

    system_message = cl.Message(
        content=" ",
        author="System",
        type="system_message",
        created_at=utc_now(),
    )

    if chat_profile == "Local.Audio":
        files = None

        # Wait for the user to upload a file
        while files is None:
            ask_file_message = cl.AskFileMessage(
                content="Please upload a audio file to start the conversation",
                accept=["audio/*"],
                max_files=1,
                max_size_mb=50,
                timeout=360,
            )
            files = await ask_file_message.send()

        ask_file_message.content = ""
        await ask_file_message.update()

        file = files[0]

        audio_text, segments = await transcribing_tool(file=Path(file.path))

        # NOTE: Workaround to get s3 url of the uploaded file in the current thread
        thread_id = get_current_chainlit_thread_id()
        audio_url = await get_read_url_of_file(thread_id=thread_id, file_id=file.id)
        name = file.name
        element_name = "AudioWithTranscript"
    elif chat_profile == "Youtube.Audio":
        url = "https://www.youtube.com/watch?v=7ARBJQn6QkM"

        audio_text, segments = await transcribing_tool_yt(url=url)
        audio_url = url
        name = url.split("v=")[-1]

        element_name = "VideoWithTranscript"
    else:
        raise ValueError(f"Unknown chat profile: {chat_profile}")

    await cl.context.emitter.send_toast(
        message="Audio transcribed successfully", type="info"
    )

    cl.user_session.set("audio_text", audio_text)

    # Create an element with transcript and segments
    element = cl.CustomElement(
        name=element_name,
        props={
            "name": name,
            "url": audio_url,
            "segments": segments,
        },
        display="side",
    )

    system_message.elements.append(element)
    system_message.content = element_name

    await system_message.send()


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
