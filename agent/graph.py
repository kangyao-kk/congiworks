"""
Agent 编排图 — LangGraph 状态图。

路由:
    analyze_intent → (chat / knowledge / tool)
      chat:       build_prompt → END
      knowledge:  retrieve_rag → build_prompt → END
      tool:       execute_skill → build_prompt → END

对外接口:
    graph.invoke(state) → 返回包含 final_messages 的 state
"""

import json
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from rag import RAG
from config import config
from skills import registry


# ── State ──────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    intent: str
    rag_results: list[dict]
    skill_results: str
    final_messages: list[dict]


# ── 共享实例 ────────────────────────────────────────────────────────────────
_registry_loaded = False

INTENT_PROMPT = """分析用户输入，判断意图类型。严格按以下规则分类，只返回一个词。

示例:
- "统计这段话的字数" → tool
- "提取关键词" → tool
- "帮我计算" → tool
- "姚永康是谁" → knowledge
- "什么是深度学习" → knowledge
- "介绍一下量子计算" → knowledge
- "你好" → chat
- "今天天气怎么样" → chat

规则:
- 用户要求执行具体操作(统计、提取、计算、分析文本) → tool
- 用户问定义/概念/人物/原理，需要知识储备才能回答 → knowledge
- 以上都不匹配 → chat

用户输入: {query}

意图:"""


def _init():
    """延迟初始化: 加载 skill + 创建 RAG 实例。"""
    global _registry_loaded
    if not _registry_loaded:
        registry.load_all()
        _registry_loaded = True


def _get_rag() -> RAG:
    return RAG(table_name="test_chunks_16d", embedding_dim=16)


# ── Nodes ──────────────────────────────────────────────────────────────────
def analyze_intent(state: AgentState) -> dict:
    """意图分类: LLM 判断 chat / knowledge / tool。"""
    _init()

    from openai import OpenAI
    client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)

    last_msg = state["messages"][-1]
    query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    resp = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": INTENT_PROMPT.format(query=query)}],
        max_tokens=50,
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip().lower()
    intent = raw
    if intent not in ("chat", "knowledge", "tool"):
        intent = "chat"

    print(f"  [graph] 意图: {intent}")
    return {"intent": intent}


def retrieve_rag(state: AgentState) -> dict:
    """知识库检索。"""
    _init()
    rag = _get_rag()

    last_msg = state["messages"][-1]
    query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    results = rag.search(query, top_k=10)
    rag.close()

    print(f"  [graph] RAG: 命中 {len(results)} 条")
    for r in results[:3]:
        print(f"    [sim={r['similarity']:.3f}] {r['content'][:60]}…")

    return {"rag_results": results}


def execute_skill(state: AgentState) -> dict:
    """LLM Function Calling → 调用 Skill。"""
    _init()
    from openai import OpenAI

    client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)
    tools = registry.get_tool_specs()

    last_msg = state["messages"][-1]
    query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    msgs = [
        {
            "role": "system",
            "content": "你是工具调度助手。根据用户需求，调用合适的工具。调用完工具后，用工具返回的结果简洁回答用户。",
        },
        {"role": "user", "content": query},
    ]

    # 第一轮: LLM 决定是否调用工具
    resp = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=msgs,
        tools=tools,
        tool_choice="auto",
    )
    msg = resp.choices[0].message

    results_parts: list[str] = []

    if msg.tool_calls:
        print(f"  [graph] Skill 调用: {msg.tool_calls[0].function.name}")

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)
            result = registry.execute(tool_name, **tool_args)
            results_parts.append(f"[{tool_name}]: {result}")
            print(f"    → {result[:100]}…")

        skill_results = "\n".join(results_parts)
    else:
        skill_results = "无需调用工具"
        print(f"  [graph] 无需工具调用")

    return {"skill_results": skill_results}


def build_prompt(state: AgentState) -> dict:
    """拼装最终 messages, 给 chat.py 做流式生成。"""
    last_msg = state["messages"][-1]
    query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    intent = state.get("intent", "chat")
    rag_results = state.get("rag_results", [])
    skill_results = state.get("skill_results", "")

    # 系统提示
    system_content = "你是 Agency 代运营智能助手。"

    # 知识库上下文
    if rag_results:
        kb_block = "\n\n---\n\n".join(
            f"[知识库/{i}] {r['content']}" for i, r in enumerate(rag_results, 1)
        )
        system_content += f"\n\n## 知识库参考\n{kb_block}"

    # Skill 结果
    if skill_results and skill_results != "无需调用工具":
        system_content += f"\n\n## 工具执行结果\n{skill_results}"

    final_messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": query},
    ]

    return {"final_messages": final_messages}


# ── Router ─────────────────────────────────────────────────────────────────
def route_intent(state: AgentState) -> str:
    intent = state.get("intent", "chat")
    if intent == "knowledge":
        return "retrieve_rag"
    elif intent == "tool":
        return "execute_skill"
    return "build_prompt"


# ── Graph Builder ──────────────────────────────────────────────────────────
def create_agent_graph():
    """构建 Agent 编排图。

    流程:
        START → analyze_intent
          → chat:       build_prompt → END
          → knowledge:  retrieve_rag → build_prompt → END
          → tool:       execute_skill → build_prompt → END
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze_intent", analyze_intent)
    workflow.add_node("retrieve_rag", retrieve_rag)
    workflow.add_node("execute_skill", execute_skill)
    workflow.add_node("build_prompt", build_prompt)

    workflow.set_entry_point("analyze_intent")

    workflow.add_conditional_edges("analyze_intent", route_intent, {
        "retrieve_rag": "retrieve_rag",
        "execute_skill": "execute_skill",
        "build_prompt": "build_prompt",
    })

    workflow.add_edge("retrieve_rag", "build_prompt")
    workflow.add_edge("execute_skill", "build_prompt")
    workflow.add_edge("build_prompt", END)

    return workflow.compile()
