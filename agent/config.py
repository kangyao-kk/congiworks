import os
from dotenv import load_dotenv

_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "env/.env.develop")
load_dotenv(_ENV_FILE)


class Config:
    # ── DeepSeek ─────────────────────────────────────────────────────────
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ── PostgreSQL / pgvector ────────────────────────────────────────────
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DATABASE = os.getenv("PG_DATABASE", "agency")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "")
    PG_VECTOR_TABLE = os.getenv("PG_VECTOR_TABLE", "document_chunks")

    # ── Embedding (阿里云百炼 DashScope) ──────────────────────────────
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL = os.getenv(
        "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

    # ── Chunking ─────────────────────────────────────────────────────────
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "256"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

    # ── Memory ───────────────────────────────────────────────────────────
    SHORT_TERM_ROUNDS = int(os.getenv("SHORT_TERM_ROUNDS", "10"))
    MEMORY_TABLE = os.getenv("MEMORY_TABLE", "agent_memories")
    MEMORY_MIN_IMPORTANCE = int(os.getenv("MEMORY_MIN_IMPORTANCE", "3"))


config = Config()
