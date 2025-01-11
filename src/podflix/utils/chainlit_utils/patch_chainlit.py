# ruff: noqa
import json

from chainlit.data import get_data_layer
from chainlit.session import WebsocketSession
from chainlit.telemetry import trace_event
from chainlit.user_session import user_sessions


async def custom_resume_thread(session: WebsocketSession):
    """Resume a thread and set the user session parameters.

    NOTE: This is a workaround to fix the issue of the chatbot not resuming the thread
    on sqlite data layer.
    """
    data_layer = get_data_layer()
    if not data_layer or not session.user or not session.thread_id_to_resume:
        return
    thread = await data_layer.get_thread(thread_id=session.thread_id_to_resume)
    if not thread:
        return

    author = thread.get("userIdentifier")
    user_is_author = author == session.user.identifier

    if user_is_author:
        metadata = thread.get("metadata") or {}

        # NOTE: Original code
        # user_sessions[session.id] = metadata.copy()

        # NOTE: Patched code
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        if isinstance(metadata, dict):
            user_sessions[session.id] = metadata.copy()
        else:
            user_sessions[session.id] = {}
        # End of patch

        if chat_profile := metadata.get("chat_profile"):
            session.chat_profile = chat_profile
        if chat_settings := metadata.get("chat_settings"):
            session.chat_settings = chat_settings

        trace_event("thread_resumed")

        return thread
