from dataclasses import dataclass
from uuid import uuid4

import chainlit as cl
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.user import PersistedUser, User
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import AIMessageChunk, HumanMessage
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from literalai.helper import utc_now

from podflix.db.db_factory import DBInterfaceFactory
from podflix.graph.podcast_rag import compiled_graph

cl_data._data_layer = SQLAlchemyDataLayer(
    DBInterfaceFactory.create().async_connection(),
    ssl_require=False,
    show_logger=True,
)

Chainlit_User_Type = User | PersistedUser


@dataclass
class StartQuestions:
    label: str
    message: str
    icon: str | None = None


mock_starters = [
    StartQuestions(
        label="Start",
        message="Start the conversation",
        icon="🚀",
    ),
    StartQuestions(
        label="Middle",
        message="Middle the conversation",
        icon="🚀",
    ),
]


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(
            label=mock_starter.label,
            message=mock_starter.message,
            icon=mock_starter.icon,
        )
        for mock_starter in mock_starters
    ]


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    return None


@cl.on_chat_start
async def on_chat_start():
    session_id = str(uuid4())
    chainlit_user: Chainlit_User_Type = cl.user_session.get("user")
    chainlit_user_id = chainlit_user.identifier

    lf_cb_handler = LangfuseCallbackHandler(
        user_id=chainlit_user_id,
        session_id=session_id,
    )

    cl.user_session.set("lf_cb_handler", lf_cb_handler)
    cl.user_session.set("session_id", session_id)


@cl.on_message
async def on_message(msg: cl.Message):
    lf_cb_handler = cl.user_session.get("lf_cb_handler")
    session_id = cl.user_session.get("session_id")

    assistant_message = cl.Message(
        content=" ",
        author="Assistant",
        type="assistant_message",
        created_at=utc_now(),
        # elements=[
        #     cl.Text(
        #         name="DUMMY ELEMENT NAME",
        #         content="DUMMY ELEMENT CONTENT",
        #         display="inline",
        #     )
        # ],
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

    # elements = [
    #     cl.Text(
    #         name="DUMMY ELEMENT NAME",
    #         content="DUMMY ELEMENT CONTENT",
    #         display="inline",
    #     )
    # ]
    # assistant_message.elements.extend(elements)

    await assistant_message.update()