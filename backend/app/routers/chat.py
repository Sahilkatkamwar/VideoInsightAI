import json
import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from langchain_core.messages import HumanMessage, AIMessage

from ..models.schemas import ChatRequest
from ..agent.graph import agent_graph
from ..agent.nodes import (
    llm,
    build_streaming_messages,
)

router = APIRouter()


def _persist_turn(
    config: dict,
    user_text: str,
    assistant_text: str,
):
    """
    Persist completed conversation turn
    into LangGraph MemorySaver.
    """

    snapshot = agent_graph.get_state(config)

    old_messages = []

    if snapshot and snapshot.values:
        old_messages = snapshot.values.get(
            "messages",
            []
        )

    new_messages = old_messages + [
        HumanMessage(content=user_text),
        AIMessage(content=assistant_text),
    ]

    agent_graph.update_state(
        config,
        {
            "messages": new_messages
        },
    )


@router.post("/chat")
async def chat(req: ChatRequest):

    async def event_stream():

        try:

            config = {
                "configurable": {
                    "thread_id": req.session_id
                }
            }

            # Load conversation history
            snapshot = agent_graph.get_state(config)

            prior_messages = []

            if snapshot and snapshot.values:
                prior_messages = snapshot.values.get(
                    "messages",
                    []
                )

            state = {
                "query": req.message,

                "metadata_a":
                    req.metadata_a.model_dump()
                    if req.metadata_a
                    else {},

                "metadata_b":
                    req.metadata_b.model_dump()
                    if req.metadata_b
                    else {},

                "messages": prior_messages,
            }

            #
            # Run retrieval graph
            #
            loop = asyncio.get_event_loop()

            retrieved_state = await loop.run_in_executor(
                None,
                lambda: agent_graph.invoke(
                    state,
                    config=config,
                ),
            )

            #
            # Build prompt
            #
            messages = build_streaming_messages(
                retrieved_state
            )

            #
            # Stream Gemini
            #
            full_response = ""

            async for chunk in llm.astream(messages):

                token = (
                    getattr(
                        chunk,
                        "content",
                        "",
                    )
                    or ""
                )
                

                if token:

                    full_response += token

                    payload = json.dumps(
                        {
                            "type": "token",
                            "content": token,
                        }
                    )

                    yield f"data: {payload}\n\n"
                    print(token)

            #
            # Sources
            #
            sources = (
                retrieved_state.get(
                    "sources",
                    [],
                )
            )

            yield (
                f"data: "
                f"{json.dumps({'type':'sources','sources':sources})}"
                f"\n\n"
            )

            #
            # Save memory
            #
            await loop.run_in_executor(
                None,
                _persist_turn,
                config,
                req.message,
                full_response,
            )

            #
            # Finish
            #
            yield (
                f"data: "
                f"{json.dumps({'type':'done'})}"
                f"\n\n"
            )

        except Exception as e:

            yield (
                f"data: "
                f"{json.dumps({'type':'error','message':str(e)})}"
                f"\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/chat/{session_id}")
async def clear_session(
    session_id: str,
):
    """
    MemorySaver is in-process memory.

    Restarting the server clears it.
    """

    return {
        "message":
            f"Session {session_id} cleared."
    }