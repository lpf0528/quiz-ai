import json
import logging
import uuid
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from langgraph.store.memory import InMemoryStore
from fastapi.responses import Response, StreamingResponse
from langgraph.types import Command

from src.config.configuration import get_str_env, get_bool_env, get_recursion_limit
from src.config.report_style import ReportStyle
from src.graph.builder import build_graph_with_memory
from src.graph.checkpoint import chat_stream_message
from src.rag.retriever import Resource
from src.server.chat_request import ChatRequest

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Quiz AI",
    version="1.0",
    description="Quiz AI API",
)

allowed_origins_str = get_str_env("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.info(f"Allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restrict to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Use the configured list of methods
    allow_headers=["*"],  # Now allow all headers, but can be restricted further
)

in_memory_store = InMemoryStore()
graph = build_graph_with_memory()


def _make_event(event_type: str, data: dict[str, any]):
    if data.get('content') == "":
        data.pop('content')

    try:
        json_data = json.dumps(data, ensure_ascii=False)
        finish_reason = data.get('finish_reason', '')
        chat_stream_message(
            data.get("thread_id", ""),
            f"event: {event_type}\ndata: {json_data}\n\n",
            finish_reason,
        )
        return f"event: {event_type}\ndata: {json_data}\n\n"
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing event data: {e}")
        # Return a safe error event
        error_data = json.dumps({"error": "Serialization failed"}, ensure_ascii=False)
        return f"event: error\ndata: {error_data}\n\n"


def _create_interrupt_event(thread_id, event_data):
    return _make_event(
        "interrupt",
        {
            "thread_id": thread_id,
            "id": event_data["__interrupt__"][0].ns[0],
            "role": "assistant",
            "content": event_data["__interrupt__"][0].value,
            "finish_reason": "interrupt",
            "options": [
                {"text": "Edit plan", "value": "edit_plan"},
                {"text": "Start research", "value": "accepted"},
            ],
        },
    )


async def _stream_graph_events(graph, workflow_input, workflow_config, thread_id):
    async for agent, _, event_data in graph.astream(workflow_input,
                                                    config=workflow_config,
                                                    stream_mode=["messages", "updates"],
                                                    subgraphs=True):
        if isinstance(event_data, dict):
            if '__interrupt__' in event_data:
                yield _create_interrupt_event(event_data)
            continue

        yield event_data


async def _astream_workflow_generator(messages: List[dict],
                                      thread_id: str,
                                      resources: List[Resource],
                                      max_plan_iterations: int,
                                      max_step_num: int,
                                      max_search_results: int,
                                      auto_accepted_plan: bool,
                                      interrupt_feedback: str,
                                      mcp_settings: dict,
                                      enable_background_investigation: bool,
                                      report_style: ReportStyle,
                                      enable_deep_thinking: bool, ):
    # for message in messages:
    #     if isinstance(message, dict) and 'content' in message:
    #         _process_initial_messages(message, thread_id)

    workflow_input = {
        'messages': messages,
        'observations': [],
        'plan_iterations': 0,
        'current_plan': None,
        'final_report': '',
        'auto_accepted_plan': auto_accepted_plan,
        'enable_background_investigation': enable_background_investigation,
        "research_topic": messages[-1]["content"] if messages else "",
    }
    if not auto_accepted_plan and interrupt_feedback:
        # 没有自动接受计划，但是有中断反馈
        resume_msg = f'[{interrupt_feedback}]'
        if messages:
            resume_msg += f' {messages[-1]["content"]}'
        workflow_input = Command(resume=resume_msg)

    workflow_config = {
        "thread_id": thread_id,
        "resources": resources,
        "max_plan_iterations": max_plan_iterations,
        "max_step_num": max_step_num,
        "max_search_results": max_search_results,
        "mcp_settings": mcp_settings,
        "report_style": report_style.value,
        "enable_deep_thinking": enable_deep_thinking,
        "recursion_limit": get_recursion_limit(),  # 递归限制
    }

    async for event in _stream_graph_events(
            graph, workflow_input, workflow_config, thread_id
    ):
        yield event


@app.post('api/chat/stream')
async def chat_stream(request: ChatRequest):
    mcp_enabled = get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False)
    if request.mcp_settings and not mcp_enabled:
        raise HTTPException(status_code=403,
                            detail="Not enough parameters for MCP server configuration, please check the documentation")

    if request.thread_id == '__default__':
        request.thread_id = str(uuid.uuid4())

    return StreamingResponse(_astream_workflow_generator(), media_type="text/event-stream")
