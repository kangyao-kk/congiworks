"""
双重记忆管理: 短期记忆(deque, 10轮) + 长期记忆(pgvector, LLM 经验提炼).

短满 → LLM 压缩旧轮次 → LLM 提取经验 → 重要性过滤 → 写入长期记忆
"""

import json
import re
from collections import deque
from typing import Any

from openai import OpenAI

from rag import RAG
from config import config


class MemoryManager:
    """短期双端队列 + 长期 pgvector 记忆。"""

    def __init__(
        self,
        *,
        rag_knowledge: RAG,
        knowledge_table: str | None = None,
        max_rounds: int | None = None,
        min_importance: int | None = None,
        llm: OpenAI | None = None,
    ):
        max_rounds = max_rounds or config.SHORT_TERM_ROUNDS
        self.min_importance = min_importance or config.MEMORY_MIN_IMPORTANCE

        # ── 短期记忆 ─────────────────────────────────────────────────────
        self.short_term: deque[tuple[str, str]] = deque(maxlen=max_rounds * 2)

        # ── 长期记忆 (独立的 RAG 实例) ──────────────────────────────────
        kt = knowledge_table or config.MEMORY_TABLE
        self.long_term = RAG(table_name=kt, embedding_dim=config.EMBEDDING_DIM)

        # ── 知识库 RAG (只读) ────────────────────────────────────────────
        self.knowledge = rag_knowledge

        # ── LLM ──────────────────────────────────────────────────────────
        self.llm = llm or OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )

    # ── 对话管理 ────────────────────────────────────────────────────────────
    def add_turn(self, user_msg: str, assistant_msg: str):
        """写入一轮对话，满时自动压缩 + 提取长期记忆。"""
        self.short_term.append(("user", user_msg))
        self.short_term.append(("assistant", assistant_msg))
        # 满时压缩最旧 2 轮 (4 条消息)
        if len(self.short_term) >= self.short_term.maxlen:
            self._compress_and_extract()

    def _compress_and_extract(self):
        """弹出最旧 2 轮对话，压缩为摘要并提取长期记忆。"""
        # 弹出最旧 4 条 (2 轮)
        old_turns: list[tuple[str, str]] = []
        for _ in range(4):
            if self.short_term:
                old_turns.append(self.short_term.popleft())

        text = _turns_to_text(old_turns)

        # ── 压缩摘要 (同步) ──────────────────────────────────────────
        summary = self._llm_compress(text)
        if summary:
            self.short_term.appendleft(("system", f"[历史摘要] {summary}"))

        # ── 经验提炼 (同步) ──────────────────────────────────────────
        experiences = self._llm_extract(text)
        for exp in experiences:
            imp = exp.get("importance", 0)
            if imp >= self.min_importance:
                try:
                    self.long_term.ingest_text(
                        exp["content"],
                        source_path=f"memory://{exp.get('memory_type', 'fact')}",
                        metadata={
                            "importance": imp,
                            "memory_type": exp.get("memory_type", "fact"),
                        },
                        dedup=False,
                    )
                except Exception as e:
                    print(f"  [memory] 写入长期记忆失败: {e}")

    # ── 上下文检索 ──────────────────────────────────────────────────────────
    def retrieve_context(self, query: str) -> tuple[str, str, list[dict]]:
        """返回 (短期上下文, 长期记忆, 知识库结果)。"""
        short = _turns_to_text(list(self.short_term))
        if not short:
            short = "(暂无短期记忆)"

        # 长期记忆检索
        long_results = self.long_term.search(query, top_k=5)

        # 知识库检索
        knowledge_results = self.knowledge.search(query, top_k=10)

        return short, long_results, knowledge_results

    def build_prompt(
        self, query: str, *, short: str, long_results: list[dict], knowledge_results: list[dict]
    ) -> list[dict]:
        """拼装完整的 LLM messages。"""
        # 长期记忆块
        if long_results:
            long_block = "\n".join(
                f"[长期记忆] {r['content']} (重要度:{r.get('metadata',{}).get('importance','?')})"
                for r in long_results
            )
        else:
            long_block = "(暂无长期记忆)"

        # 知识库块
        if knowledge_results:
            kb_block = "\n\n---\n\n".join(
                f"[知识库/{i}] {r['content']}" for i, r in enumerate(knowledge_results, 1)
            )
        else:
            kb_block = "(知识库未找到相关内容)"

        return [
            {
                "role": "system",
                "content": (
                    "你是 Agency 代运营助手，拥有短期对话记忆和长期经验记忆。\n"
                    "请综合以下信息回答用户问题:\n"
                    "1. 短期记忆 — 最近的对话上下文\n"
                    "2. 长期记忆 — 历史对话中提炼的重要经验和偏好\n"
                    "3. 知识库 — 用户上传的文档内容\n\n"
                    "要求: 回答简洁结构化；引用来源时标注类型，如 [知识库/3] 或 [长期记忆]。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## 短期记忆 (最近对话)\n{short}\n\n"
                    f"## 长期记忆\n{long_block}\n\n"
                    f"## 知识库\n{kb_block}\n\n"
                    f"## 用户问题\n{query}"
                ),
            },
        ]

    # ── LLM 调用 ────────────────────────────────────────────────────────────
    def _llm_compress(self, dialogue_text: str) -> str:
        """将旧对话压缩为 1-2 句摘要。"""
        try:
            resp = self.llm.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "将以下对话轮次压缩为 1-2 句简洁摘要，保留关键信息、决策和偏好。只输出摘要文本，不加说明。",
                    },
                    {"role": "user", "content": f"对话:\n{dialogue_text}"},
                ],
                temperature=0.3,
                max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [memory] 压缩失败: {e}")
            return ""

    def _llm_extract(self, dialogue_text: str) -> list[dict[str, Any]]:
        """从对话中提炼结构化长期记忆。"""
        prompt = (
            "分析以下对话，提炼用户的关键偏好、决策、目标和重要信息，作为长期记忆。\n\n"
            "返回 JSON 数组 (不要 markdown 代码块，纯 JSON):\n"
            '[\n  {"content": "记忆内容", "importance": 1-10, "memory_type": "preference|fact|decision|goal"}\n]\n\n'
            "重要度标准: 1-2=闲聊忽略, 3-5=一般参考, 6-8=重要偏好/决策, 9-10=必须记住\n"
            "只返回有意义的记忆 (importance>=3)，如果对话无实质内容，返回 []。\n\n"
            f"对话:\n{dialogue_text}"
        )
        try:
            resp = self.llm.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "你是记忆提炼引擎，输出纯 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            text = resp.choices[0].message.content.strip()
            return _parse_json_array(text)
        except Exception as e:
            print(f"  [memory] 记忆提取失败: {e}")
            return []

    def close(self):
        self.long_term.close()


# ── 辅助 ──────────────────────────────────────────────────────────────────────
def _turns_to_text(turns: list[tuple[str, str]]) -> str:
    return "\n".join(f"[{role}]: {content}" for role, content in turns)


def _parse_json_array(text: str) -> list[dict]:
    """从 LLM 输出中提取 JSON 数组。"""
    # 去掉可能的 markdown 代码块标记
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试匹配 [...] 部分
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return []
