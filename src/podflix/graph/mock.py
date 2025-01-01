"""Define the mock graph for the Podflix agent."""

import random
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger

from podflix.utils.model import get_mock_model


class AgentState(TypedDict):
    """A dictionary representing the state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


MOCK_RESPONSES = [
    "This is a long response from the mock model for showing streaming capabilities",
    "I am a mock model",
    "I am a mock model too",
]


async def mock_answer(state: AgentState):
    """Generate a mock response using a random choice from predefined messages.

    The function simulates an AI model's response by randomly selecting from a
    predefined list of messages and returning it as an AIMessage.

    Examples:
        >>> state = {"messages": [HumanMessage(content="Hello")]}
        >>> response = await mock_answer(state)
        >>> isinstance(response["messages"][0], AIMessage)
        True

    Args:
        state: A dictionary containing the current conversation state, including:
            - messages: A sequence of BaseMessage objects representing the conversation history.

    Returns:
        A dictionary containing:
            - messages: A list with a single AIMessage containing the random response.
    """
    random_response = random.choice(MOCK_RESPONSES)

    model = get_mock_model(message=random_response)
    _ = await model.ainvoke("mock")

    return {"messages": [AIMessage(random_response)]}


graph = StateGraph(AgentState)

# Define the two nodes we will cycle between
graph.add_node("mock_answer", mock_answer)
graph.add_edge("mock_answer", END)

graph.set_entry_point("mock_answer")
compiled_graph = graph.compile()

if __name__ == "__main__":
    inputs = {"messages": [HumanMessage(content="Hello")]}
    logger.info(compiled_graph.stream(inputs, stream_mode="messages"))
