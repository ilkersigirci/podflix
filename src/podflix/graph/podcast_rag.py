"""Define the RAG-based graph for the Podflix agent."""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger

from podflix.utils.model import get_chat_model


class AgentState(TypedDict):
    """A dictionary representing the state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: str


async def retrieve(state: AgentState) -> AgentState:
    """Retrieve relevant context based on the user's question."""
    # TODO: Implement actual retrieval logic
    # This is a placeholder that should be replaced with your vector store retrieval
    # question = state["messages"][-1].content
    # context = f"Retrieved context for: {question}"
    # return {"messages": state["messages"]}
    return {}


async def generate(state: AgentState) -> AgentState:
    """Generate a response using the retrieved context."""
    question = state["messages"][-1].content
    context = state["context"]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Use the following context to answer the question: {context}"),
            ("human", "{question}"),
        ]
    )

    model = get_chat_model()
    chain = prompt | model | StrOutputParser()

    response = await chain.ainvoke({"context": context, "question": question})

    return {
        "messages": [AIMessage(content=response)],
    }


# Create the graph
graph = StateGraph(AgentState)

# Add nodes for retrieval and generation
graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)

# Define the edges
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)

# Set the entry point
graph.set_entry_point("retrieve")

# Compile the graph
compiled_graph = graph.compile()

if __name__ == "__main__":
    inputs = {
        "messages": [HumanMessage(content="What can you tell me about RAG?")],
        "context": "RAG is a method for generating responses based on retrieved context.",
    }
    logger.info(compiled_graph.stream(inputs, stream_mode="messages"))
