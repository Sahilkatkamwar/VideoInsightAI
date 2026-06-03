import operator
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .nodes import retrieve_node, generate_node


class AgentState(TypedDict):
    query: str
    metadata_a: dict
    metadata_b: dict
    context_chunks: list[dict]
    messages: Annotated[list, operator.add]  # accumulates across turns
    last_response: str


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    # MemorySaver = in-process memory keyed by thread_id (session_id from frontend)
    # No Redis, no external DB — free, works for single-server production
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Single compiled graph instance shared across all requests
agent_graph = build_graph()
