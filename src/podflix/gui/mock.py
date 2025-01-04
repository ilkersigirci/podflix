import webbrowser

import chainlit as cl
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from chainlit.user import PersistedUser, User
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import AIMessageChunk, HumanMessage
from literalai.helper import utc_now
from loguru import logger

from podflix.db.db_factory import DBInterfaceFactory
from podflix.graph.mock import compiled_graph
from podflix.utils.chainlit_ui import (
    create_message_history_from_db_thread,
    set_extra_user_session_params,
    simple_auth_callback,
)
from podflix.utils.general import get_lf_traces_url

cl_data._data_layer = SQLAlchemyDataLayer(
    DBInterfaceFactory.create().async_connection(),
    ssl_require=False,
    show_logger=True,
)


Chainlit_User_Type = User | PersistedUser


# @cl.set_starters
# async def set_starters() -> list[cl.Starter]:
#     mock_starters = [
#         StartQuestions(
#             label="Start",
#             message="Start the conversation",
#             icon="🚀",
#         ),
#         StartQuestions(
#             label="Middle",
#             message="Middle the conversation",
#             icon="🚀",
#         ),
#     ]


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    return simple_auth_callback(username, password)


@cl.action_callback("Detailed Traces")
async def on_action(action: cl.Action):
    webbrowser.open(action.value, new=0)

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()


@cl.on_chat_start
async def on_chat_start():
    set_extra_user_session_params()


@cl.on_chat_resume
def setup_chat_resume(thread: ThreadDict):
    thread["metadata"] = {}
    message_history = create_message_history_from_db_thread(thread=thread)

    set_extra_user_session_params(
        user_id=thread["userIdentifier"], message_history=message_history
    )


@cl.on_message
async def on_message(msg: cl.Message):
    lf_cb_handler = cl.user_session.get("lf_cb_handler")
    session_id = cl.user_session.get("session_id")

    assistant_message = cl.Message(
        content=" ",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
    )

    graph_inputs = {"messages": [HumanMessage(content=msg.content)]}

    graph_runnable_config = RunnableConfig(
        callbacks=[
            lf_cb_handler,
            cl.LangchainCallbackHandler(),
        ],
        recursion_limit=10,
        configurable={"session_id": session_id},
    )

    streamable_node_names = [
        "mock_answer",
    ]

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

    elements = [
        cl.Text(
            name="DUMMY ELEMENT NAME",
            content="DUMMY ELEMENT CONTENT",
            display="inline",
        )
    ]
    assistant_message.elements.extend(elements)

    actions = [
        cl.Action(
            name="Detailed Traces",
            value=get_lf_traces_url(langchain_run_id=run_id),
            description="Detailed Logs in Langfuse",
        )
    ]

    assistant_message.actions.extend(actions)

    await assistant_message.update()
