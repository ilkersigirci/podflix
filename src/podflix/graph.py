import random
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from podflix.utils.general import mock_llm


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


MOCK_RESPONSES = [
    "This is a long response from the mock model for showing streaming capabilities",
    "I am a mock model",
    "I am a mock model too",
]


async def mock_answer(state: AgentState):
    random_response = random.choice(MOCK_RESPONSES)

    model = mock_llm(message=random_response)
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
    print(compiled_graph.stream(inputs, stream_mode="messages"))
