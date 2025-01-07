"""Helper class for running the graph."""

import chainlit as cl
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import AIMessageChunk
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph.state import CompiledStateGraph
from loguru import logger


class GraphRunner:
    """Helper class for on_message callback."""

    def __init__(  # noqa: PLR0913
        self,
        graph: CompiledStateGraph,
        graph_inputs: dict,
        graph_streamable_node_names: list[str],
        lf_cb_handler: LangfuseCallbackHandler,
        session_id: str,
        assistant_message: cl.Message,
    ):
        """Initialize the GraphRunner class.

        Args:
            graph: A CompiledStateGraph instance representing the graph to be executed.
            graph_inputs: A dictionary containing the inputs for the graph.
            graph_streamable_node_names: A list of node names that can be streamed.
            lf_cb_handler: A LangfuseCallbackHandler instance for tracking.
            session_id: A string representing the unique session identifier.
            assistant_message: A chainlit Message instance for displaying responses.
        """
        self.graph = graph
        self.graph_inputs = graph_inputs
        self.graph_streamable_node_names = graph_streamable_node_names
        self.lf_cb_handler = lf_cb_handler
        self.session_id = session_id
        self.assistant_message = assistant_message

        self.run_id = None

    async def run_graph(self):
        """Execute the graph asynchronously with the configured inputs.

        This method sets up the runnable configuration with callbacks and streams
        the graph events to process the LLM responses.

        Examples:
            >>> runner = GraphRunner(graph, inputs, nodes, handler, "session1", message)
            >>> await runner.run_graph()

        Returns:
            None
        """
        graph_runnable_config = RunnableConfig(
            callbacks=[
                self.lf_cb_handler,
                cl.LangchainCallbackHandler(),
            ],
            recursion_limit=10,
            configurable={"session_id": self.session_id},
        )

        async for event in self.graph.astream_events(
            self.graph_inputs,
            config=graph_runnable_config,
            version="v2",
        ):
            await self.stream_llm_response(event)

    async def stream_llm_response(self, event: dict):
        """Stream the LLM response to the assistant message.

        Process the event data and stream tokens to the assistant message if the
        event comes from a streamable node.

        Examples:
            >>> event = {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
            >>> await runner.stream_llm_response(event)

        Args:
            event: A dictionary containing the event data with the following structure:
                  - event: The type of event (str)
                  - metadata: Dictionary with event metadata
                  - data: The event payload

        Returns:
            None

        Notes:
            The method updates the assistant_message.content when streaming tokens.
            It also captures the run_id for Langfuse tracking when the chain ends.
        """
        event_kind = event["event"]
        langgraph_node = event["metadata"].get("langgraph_node", None)

        if event_kind == "on_chat_model_stream":
            if langgraph_node not in self.graph_streamable_node_names:
                return

            ai_message_chunk: AIMessageChunk = event["data"]["chunk"]
            ai_message_content = ai_message_chunk.content

            if ai_message_content:
                # NOTE: This automatically updates the assistant_message.content
                await self.assistant_message.stream_token(ai_message_content)

        # TODO: Find out more robust way to get run_id for langfuse
        if event["event"] == "on_chain_end":
            run_id = event.get("run_id")
            self.run_id = run_id
            logger.debug(f"Langfuse Run ID: {run_id}")
