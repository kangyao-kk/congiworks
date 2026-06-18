import os
import sys
from dotenv import load_dotenv

_AGENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent")
sys.path.insert(0, _AGENT_DIR)

_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "env/.env.develop")
load_dotenv(_ENV_FILE)


class BackendConfig:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DATABASE = os.getenv("PG_DATABASE", "agency")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "")

    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "256"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

    APP_PORT = int(os.getenv("APP_PORT", "8080"))


config = BackendConfig()
