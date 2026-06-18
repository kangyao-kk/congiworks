import json
from typing import Any

import psycopg2
import psycopg2.extras
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import config


class RAG:
    """RAG 知识库：文本分割 → 阿里云百炼 Embedding API 向量化 → pgvector 存储 → 相似检索。

    目前实现文本管道；图片和视频接口已预留。
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        table_name: str | None = None,
        embedding_model: str | None = None,
        embedding_dim: int | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        # ── 连接参数 ─────────────────────────────────────────────────────
        self._host = host or config.PG_HOST
        self._port = port or config.PG_PORT
        self._database = database or config.PG_DATABASE
        self._user = user or config.PG_USER
        self._password = password or config.PG_PASSWORD
        self._table = table_name or config.PG_VECTOR_TABLE
        self._target_dim = embedding_dim or config.EMBEDDING_DIM
        self._embedding_model = embedding_model or config.EMBEDDING_MODEL

        # ── 建立 PG 连接 ─────────────────────────────────────────────────
        self._conn = psycopg2.connect(
            host=self._host,
            port=self._port,
            dbname=self._database,
            user=self._user,
            password=self._password,
        )
        self._conn.autocommit = False

        # ── 百炼 Embedding API 客户端 (OpenAI 兼容) ──────────────────────
        self._client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
        )

        # ── 文本分割器 ───────────────────────────────────────────────────
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or config.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", "！", "？", " ", ""],
        )

        # ── 初始化表 ────────────────────────────────────────────────────
        self._ensure_table()

    # ── 数据库初始化 ────────────────────────────────────────────────────────
    def _ensure_table(self) -> None:
        """创建文档块表（如不存在）。"""
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id          SERIAL PRIMARY KEY,
                    content     TEXT NOT NULL,
                    embedding   vector({self._target_dim}),
                    source_type VARCHAR(50)  DEFAULT 'text',
                    source_path TEXT,
                    metadata    JSONB        DEFAULT '{{}}',
                    created_at  TIMESTAMP     DEFAULT NOW()
                )
            """)
        self._conn.commit()

    def _ensure_index(self) -> None:
        """创建 IVFFlat 索引（表有足够数据后调用更佳）。"""
        with self._conn.cursor() as cur:
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table}_embedding
                ON {self._table}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
        self._conn.commit()

    # ── 文本处理管道 ────────────────────────────────────────────────────────
    def split_text(self, text: str) -> list[str]:
        """将文本分割为带重叠窗口的块。"""
        docs = self._splitter.create_documents([text])
        return [d.page_content for d in docs]

    def embed(self, chunks: list[str]) -> list[list[float]]:
        """调用百炼 Embedding API 向量化（每批最多 10 条），截断到 target_dim。"""
        all_embeddings: list[list[float]] = []
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            response = self._client.embeddings.create(
                model=self._embedding_model,
                input=batch,
            )
            for d in response.data:
                emb = d.embedding
                if self._target_dim < len(emb):
                    emb = emb[: self._target_dim]
                all_embeddings.append(emb)
        return all_embeddings

    def store(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        *,
        source_type: str = "text",
        source_path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> list[int]:
        """将块与向量写入 PostgreSQL，返回插入的 id 列表。"""
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        ids: list[int] = []

        with self._conn.cursor() as cur:
            for chunk, emb in zip(chunks, embeddings):
                cur.execute(
                    f"INSERT INTO {self._table} (content, embedding, source_type, source_path, metadata) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (chunk, emb, source_type, source_path, meta_json),
                )
                ids.append(cur.fetchone()[0])
        self._conn.commit()
        return ids

    # ── 对外入口 ─────────────────────────────────────────────────────────────
    def ingest_text(
        self,
        text: str,
        *,
        source_path: str = "",
        metadata: dict[str, Any] | None = None,
        dedup: bool = True,
    ) -> list[int]:
        """完整文本入库管道：分割 → 向量化 → 存储。

        dedup=True 时先按 source_path 删除旧数据，保证幂等导入。
        """
        if dedup and source_path:
            self.delete_by_source(source_path)
        chunks = self.split_text(text)
        if not chunks:
            return []
        embeddings = self.embed(chunks)
        return self.store(
            chunks, embeddings, source_type="text",
            source_path=source_path, metadata=metadata,
        )

    def ingest_image(self, image_path: str, *, metadata: dict[str, Any] | None = None) -> list[int]:
        """图片入库（预留接口）。"""
        raise NotImplementedError("图片处理接口尚未实现")

    def ingest_video(self, video_path: str, *, metadata: dict[str, Any] | None = None) -> list[int]:
        """视频入库（预留接口）。"""
        raise NotImplementedError("视频处理接口尚未实现")

    # ── 检索 ─────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """语义检索：返回最相关的 top_k 个文档块。"""
        query_embedding = self.embed([query])[0]

        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if source_type:
                cur.execute(
                    f"SELECT id, content, source_type, source_path, metadata, "
                    f"       1 - (embedding <=> %s::vector) AS similarity "
                    f"FROM {self._table} "
                    f"WHERE source_type = %s "
                    f"ORDER BY embedding <=> %s::vector "
                    f"LIMIT %s",
                    (query_embedding, source_type, query_embedding, top_k),
                )
            else:
                cur.execute(
                    f"SELECT id, content, source_type, source_path, metadata, "
                    f"       1 - (embedding <=> %s::vector) AS similarity "
                    f"FROM {self._table} "
                    f"ORDER BY embedding <=> %s::vector "
                    f"LIMIT %s",
                    (query_embedding, query_embedding, top_k),
                )
            return [dict(row) for row in cur.fetchall()]

    # ── 管理 ─────────────────────────────────────────────────────────────────
    def delete_by_source(self, source_path: str) -> int:
        """按来源路径删除文档块，返回删除行数。"""
        with self._conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self._table} WHERE source_path = %s", (source_path,)
            )
            deleted = cur.rowcount
        self._conn.commit()
        return deleted

    def chunk_count(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._table}")
            return cur.fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "RAG":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
