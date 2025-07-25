import webbrowser

import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.user import PersistedUser, User
from langchain_community.chat_message_histories import ChatMessageHistory
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from literalai.helper import utc_now
from loguru import logger

from podflix.env_settings import env_settings
from podflix.graph.mock import compiled_graph
from podflix.utils.chainlit_utils.data_layer import apply_sqlite_data_layer_fixes
from podflix.utils.chainlit_utils.general import (
    create_message_history_from_db_thread,
    set_extra_user_session_params,
    simple_auth_callback,
)
from podflix.utils.general import get_lf_trace_url
from podflix.utils.graph_runner import GraphRunner

Chainlit_User_Type = User | PersistedUser

if env_settings.enable_sqlite_data_layer is True:
    apply_sqlite_data_layer_fixes()


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(
            label="Mock",
            message="Mock the conversation",
            icon="🚀",
        ),
        cl.Starter(
            label="Mock2",
            message="Mock the conversation 2",
            icon="🚀",
        ),
    ]


@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    if current_user.metadata["role"] != "admin":
        return [
            cl.ChatProfile(
                name="GPT-4o-mini",
                markdown_description="Model is **GPT-4o-mini**",
                icon="https://picsum.photos/200",
            ),
        ]

    return [
        cl.ChatProfile(
            name="GPT-4",
            markdown_description="Model is **GPT-4**",
            icon="https://picsum.photos/250",
        ),
        cl.ChatProfile(
            name="GPT-4.5",
            markdown_description="Model is **GPT-4.5**",
            icon="https://picsum.photos/200",
        ),
    ]


mock_commands = [
    {
        "id": "Search",
        "icon": "globe",
        "description": "Find on the web",
        "button": True,
    },
    {
        "id": "Picture",
        "icon": "image",
        "description": "Use DALL-E",
        "button": False,
    },
    {
        "id": "Canvas",
        "icon": "pen-line",
        "description": "Collaborate on writing and code",
        "button": False,
    },
]


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    return simple_auth_callback(username, password)


@cl.action_callback("detailed_traces_button")
async def on_action(action: cl.Action):
    # FIXME: Doesn't work inside the docker container
    webbrowser.open(action.payload["lf_traces_url"], new=0)

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()


@cl.step(name="Mock Tool", type="tool")
async def mock_tool():
    step_message = cl.Message(content="")
    await step_message.stream_token("Streaming inside the mock tool.")


@cl.on_chat_start
async def on_chat_start():
    set_extra_user_session_params()

    await cl.context.emitter.set_commands(mock_commands)

    # chat_profile = cl.user_session.get("chat_profile")
    # await cl.Message(
    #     content=f"Starting chat using the {chat_profile} chat profile"
    # ).send()


@cl.on_chat_resume
def setup_chat_resume(thread: ThreadDict):
    message_history = create_message_history_from_db_thread(thread=thread)

    set_extra_user_session_params(
        user_id=thread["userIdentifier"], message_history=message_history
    )


@cl.on_message
async def on_message(msg: cl.Message):
    lf_cb_handler: LangfuseCallbackHandler = cl.user_session.get("lf_cb_handler")
    session_id: str = cl.user_session.get("session_id")
    message_history: ChatMessageHistory = cl.user_session.get("message_history")
    chainlit_user: Chainlit_User_Type = cl.user_session.get("user")

    if msg.command is not None:
        logger.debug(f"Command used: {msg.command}")

        # NOTE: Removes commands from the UI
        # await cl.context.emitter.set_commands([])

    # await mock_tool()

    assistant_message = cl.Message(
        content=" ",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
    )

    graph_inputs = {"messages": message_history.messages}

    graph_runner = GraphRunner(
        graph=compiled_graph,
        graph_inputs=graph_inputs,
        graph_streamable_node_names=["mock_answer"],
        lf_cb_handler=lf_cb_handler,
        user_id=chainlit_user.identifier,
        session_id=session_id,
        assistant_message=assistant_message,
    )

    await graph_runner.run_graph()

    elements = [
        cl.Text(
            name="DUMMY_ELEMENT_NAME",
            content="DUMMY ELEMENT CONTENT",
            display="side",
        )
    ]
    assistant_message.elements.extend(elements)

    lf_traces_url = get_lf_trace_url(langchain_trace_id=graph_runner.run_id)

    logger.debug(f"Langfuse traces URL: {lf_traces_url}")

    actions = [
        cl.Action(
            name="detailed_traces_button",
            payload={"lf_traces_url": lf_traces_url},
            label="Detailed Traces",
            tooltip="Detailed Logs in Langfuse",
        )
    ]

    assistant_message.actions.extend(actions)

    assistant_message.content += " DUMMY_ELEMENT_NAME"
    await assistant_message.update()

    message_history.add_user_message(msg.content)
    message_history.add_ai_message(assistant_message.content)
