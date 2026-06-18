"""
Agency 代运营 Agent — 多 Session + 双重记忆 + LangGraph 编排

用法:
    python chat.py           # 交互对话
    python chat.py 你的问题   # 单次提问

命令:
    /new        新建会话
    /sessions   列出所有会话
    /switch <id>  切换会话
    /delete <id>  删除会话
    /history    查看当前会话历史
    /search <q> 语义搜索历史消息
    /memory     查看短期记忆
    /exit       退出
"""

import sys
import time
import threading
import itertools

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openai import OpenAI
from langchain_core.messages import HumanMessage
from rag import RAG
from memory import MemoryManager
from session import SessionManager
from config import config
from skills import registry
from graph import create_agent_graph

FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# ── 初始化 ──────────────────────────────────────────────────────────────────
registry.load_all()

knowledge_rag = RAG(table_name="test_chunks_16d", embedding_dim=16)
llm = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)
memory = MemoryManager(rag_knowledge=knowledge_rag, llm=llm)
sessions = SessionManager(llm=llm)
agent_graph = create_agent_graph()

# 创建或恢复当前会话
current_session = sessions.create_session()

print(f"  知识库: {config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE}")
print(f"  会话ID: {current_session}  |  短期: {config.SHORT_TERM_ROUNDS} 轮")
print(f"  技能: {len(registry._skills)} 个  |  输入 /help 查看命令")


# ── Prompt 拼装 ─────────────────────────────────────────────────────────────
def _build_messages(query, short, long_results, rag_results, skill_results):
    """组合记忆 + 图谱结果 → LLM messages。"""
    system_parts = [
        "你是 Agency 代运营智能助手。请综合以下信息回答用户问题。"
        "回答简洁结构化，引用来源时标注类型。"
    ]

    # 长期记忆
    if long_results:
        long_block = "\n".join(
            f"[长期记忆] {r['content']} (重要度:{r.get('metadata',{}).get('importance','?')})"
            for r in long_results
        )
        system_parts.append(f"## 长期记忆\n{long_block}")

    # 知识库 (来自图谱 RAG 节点)
    if rag_results:
        kb_block = "\n\n---\n\n".join(
            f"[知识库/{i}] {r['content']}" for i, r in enumerate(rag_results, 1)
        )
        system_parts.append(f"## 知识库参考\n{kb_block}")

    # 工具执行结果 (来自图谱 Skill 节点)
    if skill_results and skill_results != "无需调用工具":
        system_parts.append(f"## 工具执行结果\n{skill_results}")

    user_content = f"## 短期记忆 (最近对话)\n{short}\n\n## 用户问题\n{query}"

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": user_content},
    ]


# ── 核心 ─────────────────────────────────────────────────────────────────────
def ask(query: str) -> str:
    global current_session

    # 保存用户消息
    sessions.add_message(current_session, "user", query)

    # ── ① 记忆检索 ────────────────────────────────────────────────────
    short, long_results, _ = memory.retrieve_context(query)

    # ── ② 图谱编排: 意图分析 → RAG / Skill ──────────────────────────
    result = agent_graph.invoke({"messages": [HumanMessage(content=query)]})
    rag_results = result.get("rag_results", [])
    skill_results = result.get("skill_results", "")

    # ── ③ 拼装 prompt ─────────────────────────────────────────────────
    msgs = _build_messages(query, short, long_results, rag_results, skill_results)

    # ── ④ 流式生成 + 思考动画 ─────────────────────────────────────────
    print(f"  [AI] ", end="", flush=True)

    stop_spin = threading.Event()

    def spin():
        for f in itertools.cycle(FRAMES):
            if stop_spin.is_set():
                break
            sys.stdout.write(f"\r  [AI] {f} 思考中…")
            sys.stdout.flush()
            time.sleep(0.08)

    t = threading.Thread(target=spin, daemon=True)
    t.start()
    full_response = ""

    try:
        stream = llm.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=msgs,
            stream=True,
            temperature=0.7,
        )
        first_token = True
        for chunk in stream:
            if chunk.choices[0].delta.content:
                if first_token:
                    stop_spin.set()
                    t.join(timeout=0.3)
                    sys.stdout.write("\r" + " " * 30 + "\r")
                    sys.stdout.write("  [AI] ")
                    sys.stdout.flush()
                    first_token = False
                token = chunk.choices[0].delta.content
                sys.stdout.write(token)
                sys.stdout.flush()
                full_response += token
    finally:
        stop_spin.set()

    print()

    # ── ⑤ 持久化 + 记忆 ────────────────────────────────────────────────
    sessions.add_message(current_session, "assistant", full_response)
    memory.add_turn(query, full_response)

    # 第一条消息后自动生成标题
    msg_count = sum(1 for _ in sessions.get_messages(current_session))
    if msg_count == 2:
        sessions.auto_title(current_session)

    return full_response


# ── 命令处理 ─────────────────────────────────────────────────────────────────
def handle_command(cmd: str) -> bool:
    """处理 / 命令, 返回 False 表示退出。"""
    global current_session
    parts = cmd.split(maxsplit=1)
    op = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if op in ("/exit", "/quit"):
        return False

    elif op == "/help":
        print("  /new         新建会话")
        print("  /sessions    列出所有会话")
        print("  /switch <id> 切换会话")
        print("  /delete <id> 删除会话")
        print("  /history     查看当前会话消息")
        print("  /search <q>  语义搜索所有历史消息")
        print("  /memory      查看短期记忆")
        print("  /exit        退出")

    elif op == "/new":
        current_session = sessions.create_session()
        print(f"  已创建新会话 #{current_session}")

    elif op == "/sessions":
        rows = sessions.list_sessions()
        cur = f" #{current_session}" if current_session else ""
        print(f"  会话列表 (当前:{cur}):")
        for r in rows:
            marker = " ←" if r["id"] == current_session else ""
            print(f"  [{r['id']}] {r['title'][:30]}  ({r['message_count']} 条消息){marker}")

    elif op == "/switch":
        try:
            sid = int(arg)
            msgs = sessions.get_messages(sid)
            if msgs:
                current_session = sid
                print(f"  已切换到会话 #{sid} ({len(msgs)} 条消息)")
                # 恢复短期记忆
                memory.short_term.clear()
                for m in msgs:
                    memory.short_term.append((m["role"], m["content"]))
            else:
                print(f"  会话 #{sid} 不存在")
        except ValueError:
            print(f"  用法: /switch <id>")

    elif op == "/delete":
        try:
            sid = int(arg)
            sessions.delete_session(sid)
            if sid == current_session:
                current_session = sessions.create_session()
                print(f"  已删除, 自动创建新会话 #{current_session}")
            else:
                print(f"  已删除会话 #{sid}")
        except ValueError:
            print(f"  用法: /delete <id>")

    elif op == "/history":
        msgs = sessions.get_messages(current_session)
        for m in msgs:
            role = "你" if m["role"] == "user" else "AI"
            print(f"  [{role}] {m['content'][:150]}…")

    elif op == "/search":
        if not arg:
            print("  用法: /search <关键词>")
        else:
            results = sessions.search_messages(arg, top_k=5)
            print(f"  搜索 '{arg}': {len(results)} 条")
            for r in results:
                print(f"  [{r['similarity']:.3f}] [{r['role']}] ({r['session_title']}) {r['content'][:100]}…")

    elif op == "/memory":
        for role, content in memory.short_term:
            print(f"  [{role}] {content[:120]}…")

    else:
        print(f"  未知命令: {op}  (输入 /help 查看)")

    return True


# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        ask(" ".join(sys.argv[1:]))
    else:
        print("=" * 60)
        print("  Agency 代运营 Agent")
        print("=" * 60)

        try:
            while True:
                line = input("\n你: ").strip()
                if not line:
                    continue
                if line.startswith("/"):
                    if not handle_command(line):
                        break
                else:
                    ask(line)
        except KeyboardInterrupt:
            print("\n")
        finally:
            print("再见~")
            memory.close()
            knowledge_rag.close()
            sessions.close()
