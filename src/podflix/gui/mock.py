import webbrowser

import chainlit as cl
from chainlit.types import ThreadDict
from langchain_community.chat_message_histories import ChatMessageHistory
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
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
from podflix.utils.general import get_lf_traces_url
from podflix.utils.graph_runner import GraphRunner

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


mock_commands = [
    {"id": "Picture", "icon": "image", "description": "Use DALL-E"},
    {"id": "Search", "icon": "globe", "description": "Find on the web"},
    {
        "id": "Canvas",
        "icon": "pen-line",
        "description": "Collaborate on writing and code",
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


@cl.on_chat_start
async def on_chat_start():
    set_extra_user_session_params()

    await cl.context.emitter.set_commands(mock_commands)

    sidebar_mock_elements = [
        cl.Text(content="Here is a side text document", name="text1"),
        cl.Image(
            path=f"{env_settings.library_base_path}/configs/chainlit/public/banner.png",
            name="banner",
        ),
    ]

    await cl.ElementSidebar.set_elements(sidebar_mock_elements)
    await cl.ElementSidebar.set_title("Sidebar Mock Title")


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

    if msg.command is not None:
        logger.debug(f"Command used: {msg.command}")

        # NOTE: Removes commands from the UI
        # await cl.context.emitter.set_commands([])

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

    lf_traces_url = get_lf_traces_url(langchain_run_id=graph_runner.run_id)

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
    await assistant_message.send()

    message_history.add_user_message(msg.content)
    message_history.add_ai_message(assistant_message.content)
