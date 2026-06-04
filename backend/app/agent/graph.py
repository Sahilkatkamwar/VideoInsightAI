import operator
from typing import TypedDict, Annotated, List, Dict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .nodes import retrieve_node, generate_node


class ChatState(TypedDict, total=False):
    query: str

    metadata_a: Dict[str, Any]
    metadata_b: Dict[str, Any]

    context_chunks: List[Dict[str, Any]]

    # accumulates automatically across turns
    messages: Annotated[list, operator.add]

    last_response: str

    # optional frontend citations
    sources: List[Dict[str, Any]]

    # non-streaming compatibility
    answer: str


def build_graph():
    graph = StateGraph(ChatState)

    graph.add_node("retrieve", retrieve_node)

    graph.add_edge(START, "retrieve")

    checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer
    )


# shared singleton instance
agent_graph = build_graph()