import json
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from backend.schemas.api import MessageIn
from backend.services.chat_service import generate_sse_stream
from backend.services.agent_service import (
    add_agent_activity,
    delete_conversation_messages,
    get_agent,
    get_conversation_messages,
    save_conversation_message,
    update_agent_metrics,
)

router = APIRouter(prefix="/api/agents", tags=["conversations"])


@router.get("/{agent_id}/conversations")
def list_conversations(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return get_conversation_messages(agent_id)


@router.delete("/{agent_id}/conversations")
def clear_conversations(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    count = delete_conversation_messages(agent_id)
    return {"ok": True, "deleted": count}


@router.post("/{agent_id}/conversations")
async def send_message(agent_id: str, body: MessageIn):
    agent = get_agent(agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    if agent.status != "online":
        return JSONResponse({"error": "Agent is offline"}, status_code=400)

    content = body.content
    task_label = content[:40] + "..." if len(content) > 40 else content

    # 持久化用户消息
    save_conversation_message(agent_id, "user", content)

    add_agent_activity(agent_id, "task_received", f'收到任务："{task_label}"')
    add_agent_activity(agent_id, "thinking_started", f"{agent.name} 开始分析任务...")

    start_time = time.time()
    full_response_ref = [""]
    total_tokens_ref = [0]

    def event_stream():
        for line in generate_sse_stream(agent_id, content):
            yield line
            try:
                _, json_str = line.split("data: ", 1)
                event = json.loads(json_str.strip())
                if event.get("type") == "assistant_message":
                    full_response_ref[0] = event.get("data", {}).get("content", "")
                elif event.get("type") == "usage":
                    total_tokens_ref[0] = event.get("data", {}).get("total_tokens", 0)
            except Exception:
                pass

        ai_content = full_response_ref[0]
        if ai_content:
            save_conversation_message(
                agent_id, "assistant", ai_content,
                thinking=[
                    {"title": "分析输入", "description": "正在处理用户消息...", "status": "success"},
                    {"title": "生成回复", "description": "基于上下文生成回复内容...", "status": "success"},
                ],
            )

        elapsed = time.time() - start_time
        add_agent_activity(agent_id, "task_completed", f"任务完成，{len(ai_content)} 字符")
        update_agent_metrics(agent_id, total_tokens=total_tokens_ref[0], response_time=elapsed, success=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
