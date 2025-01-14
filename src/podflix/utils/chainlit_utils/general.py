"""Utilies for chainlit UI."""

from uuid import uuid4

import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.user import PersistedUser, User
from langchain_community.chat_message_histories import ChatMessageHistory
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from loguru import logger

from podflix.env_settings import env_settings
from podflix.utils.general import check_lf_credentials, get_lf_session_url

Chainlit_User_Type = User | PersistedUser


def simple_auth_callback(username: str, password: str) -> User:
    """Authenticate user with simple username and password check.

    Examples:
        >>> simple_auth_callback("admin", "admin")
        User(identifier="admin", metadata={"role": "admin", "provider": "credentials"})

    Args:
        username: A string representing the username for authentication.
        password: A string representing the password for authentication.

    Returns:
        A User object if authentication is successful.

    Raises:
        ValueError: If credentials are invalid.
    """
    if (username, password) == (
        env_settings.chainlit_user_name,
        env_settings.chainlit_user_password,
    ):
        return cl.User(
            identifier=username, metadata={"role": "admin", "provider": "credentials"}
        )

    raise ValueError("Invalid credentials")


def create_message_history_from_db_thread(
    thread: ThreadDict,
) -> ChatMessageHistory:
    """Create message history from the thread steps.

    Examples:
        >>> thread = {"steps": [{"type": "user_message", "output": "hello", "createdAt": 1}]}
        >>> history = create_message_history_from_db_thread(thread)
        >>> len(history.messages)
        1

    Args:
        thread: A ThreadDict object containing the conversation thread data.

    Returns:
        A ChatMessageHistory object containing the processed message history.
    """
    message_history = ChatMessageHistory()

    # TODO: This is a workaround to sort the messages based on createdAt.
    steps_messages = sorted(
        [
            message
            for message in thread["steps"]
            if message["type"] in ["user_message", "assistant_message"]
        ],
        key=lambda x: x["createdAt"],
    )

    for steps_message in steps_messages:
        if steps_message["type"] == "user_message":
            message_history.add_user_message(steps_message["output"])
        elif steps_message["type"] == "assistant_message":
            message_history.add_ai_message(steps_message["output"])

    return message_history


def set_extra_user_session_params(
    session_id: str | None = None,
    user_id: str | None = None,
    message_history: ChatMessageHistory | None = None,
):
    """Set extra user session parameters for the chainlit session.

    Examples:
        >>> set_extra_user_session_params(session_id="test123")
        >>> cl.user_session.get("session_id")
        'test123'

    Args:
        session_id: Optional string representing the session ID. If None, a new UUID is generated.
        user_id: Optional string representing the user ID. If None, gets from current user session.
        message_history: Optional ChatMessageHistory object. If None, creates new empty history.

    Returns:
        None
    """
    if session_id is None:
        session_id = str(uuid4())

    if user_id is None:
        chainlit_user: Chainlit_User_Type = cl.user_session.get("user")
        user_id = chainlit_user.identifier

    if message_history is None:
        message_history = ChatMessageHistory()

    check_lf_credentials()
    lf_cb_handler = LangfuseCallbackHandler(
        user_id=user_id,
        session_id=session_id,
    )

    cl.user_session.set("session_id", session_id)
    cl.user_session.set("lf_cb_handler", lf_cb_handler)
    cl.user_session.set("message_history", message_history)

    langfuse_session_url = get_lf_session_url(session_id=session_id)

    logger.debug(f"Langfuse Session URL: {langfuse_session_url}")


def get_current_chainlit_thread_id() -> str:
    """Get the current Chainlit thread ID."""
    return cl.context.session.thread_id
