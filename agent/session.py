"""
会话管理: 多 Session CRUD + 完整消息历史 + 语义检索。

表:
    chat_sessions  — 会话列表
    chat_messages  — 消息时间线 (带 pgvector 向量列)
"""

import psycopg2
import psycopg2.extras
from openai import OpenAI

from config import config


class SessionManager:
    """管理聊天会话和消息持久化。"""

    def __init__(self, llm: OpenAI | None = None):
        self._conn = psycopg2.connect(
            host=config.PG_HOST,
            port=config.PG_PORT,
            dbname=config.PG_DATABASE,
            user=config.PG_USER,
            password=config.PG_PASSWORD,
        )
        self._conn.autocommit = False
        # LLM (DeepSeek) — 用于生成标题
        self._client = llm or OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        # Embedding (百炼) — 用于向量化消息
        self._emb_client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
        )
        self._ensure_tables()

    # ── 建表 ────────────────────────────────────────────────────────────────
    def _ensure_tables(self):
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id          SERIAL PRIMARY KEY,
                    title       VARCHAR(200),
                    created_at  TIMESTAMP DEFAULT NOW(),
                    updated_at  TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id          SERIAL PRIMARY KEY,
                    session_id  INT REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role        VARCHAR(20)  NOT NULL,
                    content     TEXT         NOT NULL,
                    embedding   vector(1024),
                    created_at  TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON chat_messages(session_id)
            """)
        self._conn.commit()

    # ── Session CRUD ────────────────────────────────────────────────────────
    def create_session(self, title: str = "") -> int:
        """新建会话, 返回 session_id。"""
        title = title or "新对话"
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_sessions (title) VALUES (%s) RETURNING id",
                (title,),
            )
            sid = cur.fetchone()[0]
        self._conn.commit()
        return sid

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """列出最近会话。"""
        with self._conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute("""
                SELECT s.id, s.title, s.created_at, s.updated_at,
                       COUNT(m.id) AS message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_messages(self, session_id: int) -> list[dict]:
        """获取一个会话的全部消息。"""
        with self._conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "SELECT role, content, created_at FROM chat_messages "
                "WHERE session_id = %s ORDER BY id",
                (session_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def delete_session(self, session_id: int):
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        self._conn.commit()

    def rename_session(self, session_id: int, title: str):
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_sessions SET title = %s WHERE id = %s",
                (title, session_id),
            )
        self._conn.commit()

    # ── 消息写入 ────────────────────────────────────────────────────────────
    def add_message(self, session_id: int, role: str, content: str):
        """写入一条消息 (含向量化)。"""
        embedding = self._embed_text(content)
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages (session_id, role, content, embedding) "
                "VALUES (%s, %s, %s, %s)",
                (session_id, role, content, embedding),
            )
            cur.execute(
                "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                (session_id,),
            )
        self._conn.commit()

    # ── 语义搜索 ────────────────────────────────────────────────────────────
    def search_messages(self, query: str, top_k: int = 5) -> list[dict]:
        """跨 session 语义搜索历史消息。"""
        q_emb = self._embed_text(query)
        with self._conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "SELECT m.role, m.content, m.created_at, s.title AS session_title, "
                "       1 - (m.embedding <=> %s::vector) AS similarity "
                "FROM chat_messages m "
                "JOIN chat_sessions s ON s.id = m.session_id "
                "ORDER BY m.embedding <=> %s::vector "
                "LIMIT %s",
                (q_emb, q_emb, top_k),
            )
            return [dict(r) for r in cur.fetchall()]

    # ── 摘要生成 ────────────────────────────────────────────────────────────
    def auto_title(self, session_id: int):
        """用 LLM 为会话生成标题。"""
        msgs = self.get_messages(session_id)
        if len(msgs) < 2:
            return
        first_msg = msgs[0]["content"][:200]
        try:
            resp = self._client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "为对话生成简短标题(<=15字)，只输出标题。"},
                    {"role": "user", "content": f"对话第一句: {first_msg}"},
                ],
                max_tokens=30,
            )
            title = resp.choices[0].message.content.strip()
            self.rename_session(session_id, title)
        except Exception:
            pass

    # ── 内部 ────────────────────────────────────────────────────────────────
    def _embed_text(self, text: str) -> list[float]:
        try:
            resp = self._emb_client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=[text],
            )
            return resp.data[0].embedding
        except Exception:
            # 百炼 API 不可用时返回零向量
            return [0.0] * 1024

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
