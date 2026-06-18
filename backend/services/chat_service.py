import json
import time
from datetime import datetime, timezone
from typing import Generator

from sqlmodel import Session, select

from backend.database import engine
from backend.models.agent import AgentConfig
from backend.models.conversation import ConversationMessage
from backend.schemas.api import MessageOut


def _get_agent_system_prompt(agent_id: str) -> str:
    with Session(engine) as session:
        agent = session.get(AgentConfig, agent_id)
        if agent and agent.system_prompt:
            return agent.system_prompt
    return "你是 Agency 代运营智能助手。请综合以下信息回答用户问题。回答简洁结构化。"


def _load_rag_context(query: str) -> list[dict]:
    try:
        from rag import RAG
        rag = RAG(table_name="test_chunks_16d", embedding_dim=16)
        results = rag.search(query, top_k=5)
        rag.close()
        return [{"content": r["content"], "similarity": r["similarity"]} for r in results]
    except Exception:
        return []


def _load_conversation_history(agent_id: str, max_turns: int = 10) -> str:
    """从 conversation_messages 表读取最近对话作为短期记忆。"""
    try:
        with Session(engine) as session:
            msgs = session.exec(
                select(ConversationMessage)
                .where(ConversationMessage.agent_id == agent_id)
                .order_by(ConversationMessage.timestamp.desc())
                .limit(max_turns * 2)
            ).all()
        if not msgs:
            return ""
        lines = []
        for m in reversed(msgs):
            role = "用户" if m.role == "user" else "AI"
            lines.append(f"[{role}]: {m.content[:300]}")
        return "\n".join(lines)
    except Exception:
        return ""


def _load_long_term_memory(query: str) -> list[dict]:
    """从 pgvector agent_memories 表检索相关长期记忆。"""
    try:
        from rag import RAG
        from backend.config import config as be_config
        memory_rag = RAG(
            table_name="agent_memories",
            embedding_dim=be_config.EMBEDDING_DIM,
        )
        results = memory_rag.search(query, top_k=5)
        memory_rag.close()
        return results
    except Exception:
        return []


def _store_long_term_memory(user_msg: str, ai_msg: str):
    """从本轮对话提炼经验，写入长期记忆。"""
    try:
        import sys, os
        _agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agent")
        sys.path.insert(0, _agent_dir)

        from openai import OpenAI
        from config import config as agent_config

        llm = OpenAI(api_key=agent_config.DEEPSEEK_API_KEY, base_url=agent_config.DEEPSEEK_BASE_URL)

        prompt = (
            "分析以下对话，提炼用户的关键偏好、决策、目标和重要信息，作为长期记忆。\n\n"
            "返回 JSON 数组 (不要 markdown 代码块，纯 JSON):\n"
            '[\n  {"content": "记忆内容", "importance": 1-10, "memory_type": "preference|fact|decision|goal"}\n]\n\n'
            "重要度标准: 1-2=闲聊忽略, 3-5=一般参考, 6-8=重要偏好/决策, 9-10=必须记住\n"
            "只返回有意义的记忆 (importance>=3)，如果对话无实质内容，返回 []。\n\n"
            f"用户: {user_msg[:500]}\n\nAI: {ai_msg[:500]}"
        )

        resp = llm.chat.completions.create(
            model=agent_config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是记忆提炼引擎，输出纯 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
        )

        text = resp.choices[0].message.content.strip()

        import re as _re
        text = _re.sub(r"^```(?:json)?\s*", "", text)
        text = _re.sub(r"\s*```$", "", text)
        experiences = json.loads(text) if text.startswith("[") else []

        from rag import RAG
        from backend.config import config as be_config
        memory_rag = RAG(
            table_name="agent_memories",
            embedding_dim=be_config.EMBEDDING_DIM,
        )
        for exp in experiences:
            imp = exp.get("importance", 0)
            if imp >= 3:
                memory_rag.ingest_text(
                    exp["content"],
                    source_path=f"memory://{exp.get('memory_type', 'fact')}",
                    metadata={
                        "importance": imp,
                        "memory_type": exp.get("memory_type", "fact"),
                    },
                    dedup=False,
                )
        memory_rag.close()
    except Exception:
        pass


def build_system_message(agent_id: str, query: str) -> str:
    parts = [_get_agent_system_prompt(agent_id)]

    # RAG 知识库
    rag_results = _load_rag_context(query)
    if rag_results:
        kb_block = "\n\n---\n\n".join(
            f"[知识库/{i}] {r['content']}" for i, r in enumerate(rag_results, 1)
        )
        parts.append(f"## 知识库参考\n{kb_block}")

    # 长期记忆
    long_results = _load_long_term_memory(query)
    if long_results:
        long_block = "\n".join(
            f"[长期记忆] {r['content']} (重要度:{r.get('metadata', {}).get('importance', '?')})"
            for r in long_results
        )
        parts.append(f"## 长期记忆\n{long_block}")

    # 短期记忆 (从 DB 读取最近对话历史)
    conv_history = _load_conversation_history(agent_id)
    if conv_history:
        parts.append(f"## 短期记忆 (最近对话)\n{conv_history}")

    return "\n\n".join(parts)


def generate_sse_stream(agent_id: str, user_content: str) -> Generator[str, None, None]:
    import sys
    import os
    _agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agent")
    sys.path.insert(0, _agent_dir)

    from openai import OpenAI
    from config import config as agent_config

    system_prompt = build_system_message(agent_id, user_content)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    msg_id = f"msg-{int(time.time() * 1000)}"
    user_msg = MessageOut(
        id=f"{msg_id}-user",
        role="user",
        content=user_content,
        timestamp=datetime.now(timezone.utc),
    )

    yield f"data: {json.dumps({'type': 'user_message', 'data': user_msg.model_dump(mode='json')})}\n\n"

    try:
        client = OpenAI(api_key=agent_config.DEEPSEEK_API_KEY, base_url=agent_config.DEEPSEEK_BASE_URL)
        stream = client.chat.completions.create(
            model=agent_config.DEEPSEEK_MODEL,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            temperature=0.7,
        )

        full_response = ""
        chunk_count = 0
        usage_info = None

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                chunk_count += 1
                yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
            if hasattr(chunk, "usage") and chunk.usage:
                usage_info = {
                    "prompt_tokens": chunk.usage.prompt_tokens or 0,
                    "completion_tokens": chunk.usage.completion_tokens or 0,
                    "total_tokens": chunk.usage.total_tokens or 0,
                }

        if usage_info:
            total_tokens = usage_info["total_tokens"]
        else:
            prompt_tokens = int(len(system_prompt.encode("utf-8")) * 0.4) + int(len(user_content.encode("utf-8")) * 0.4)
            completion_tokens = max(chunk_count, 1)
            total_tokens = prompt_tokens + completion_tokens

        ai_msg = MessageOut(
            id=f"{msg_id}-assistant",
            role="assistant",
            content=full_response,
            timestamp=datetime.now(timezone.utc),
            thinking=[
                {"title": "分析输入", "description": "正在处理用户消息...", "status": "success"},
                {"title": "生成回复", "description": "基于上下文生成回复内容...", "status": "success"},
            ],
        )

        yield f"data: {json.dumps({'type': 'assistant_message', 'data': ai_msg.model_dump(mode='json')})}\n\n"

        yield f"data: {json.dumps({'type': 'usage', 'data': {'total_tokens': total_tokens}})}\n\n"
        yield "data: [DONE]\n\n"

        _store_long_term_memory(user_content, full_response)

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
        yield "data: [DONE]\n\n"
