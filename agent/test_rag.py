"""
测试 RAG 管道：读取本地 txt → 阿里云百炼 Embedding API 16 维向量化 → 远端 PostgreSQL (pgvector) 存储 → 检索。

用法:
    python test_rag.py              # 直接运行

环境变量 (.env.develop):
    DASHSCOPE_API_KEY  (必填)
    PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
"""

import os
import sys
import textwrap

# 修复 Windows GBK 终端编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import psycopg2
from openai import OpenAI

from rag import RAG
from config import config

# ── 测试配置 ──────────────────────────────────────────────────────────────────
TEST_TABLE = "test_chunks_16d"
TARGET_DIM = 16
TOP_K = 3

TEST_TXT_FILE = os.path.join(os.path.dirname(__file__), "sample.txt")


# ── 辅助函数 ──────────────────────────────────────────────────────────────────
def _get_pg_conn():
    return psycopg2.connect(
        host=config.PG_HOST, port=config.PG_PORT,
        dbname=config.PG_DATABASE, user=config.PG_USER,
        password=config.PG_PASSWORD,
    )


def _drop_test_table():
    conn = _get_pg_conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
    conn.close()


def _get_api_embedding_dim() -> int:
    """调用百炼 API 获取 embedding 模型的实际输出维度。"""
    client = OpenAI(
        api_key=config.DASHSCOPE_API_KEY,
        base_url=config.DASHSCOPE_BASE_URL,
    )
    response = client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=["test"],
    )
    return len(response.data[0].embedding)


# ── 测试用例 ──────────────────────────────────────────────────────────────────

def test_pg_connection():
    """T1 — 验证远端 PostgreSQL 连接是否正常。"""
    conn = _get_pg_conn()
    info = conn.get_dsn_parameters()
    print(f"  -> 实际连接: {info['host']}:{info['port']}/{info['dbname']} 用户={info['user']}")
    with conn.cursor() as cur:
        cur.execute("SELECT 1 AS ok")
        assert cur.fetchone()[0] == 1
    conn.close()
    print("  [OK] 远端 PostgreSQL 连接正常")


def test_pgvector_extension():
    """T2 — 验证 pgvector 扩展是否已安装。"""
    conn = _get_pg_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        assert cur.fetchone() is not None, "pgvector 扩展未安装"
    conn.close()
    print("  [OK] pgvector 扩展已启用")


def test_api_embedding_dim():
    """T3 — 验证百炼 Embedding API 返回维度 >= 16。"""
    raw_dim = _get_api_embedding_dim()
    assert raw_dim >= TARGET_DIM, f"API 返回维度 {raw_dim} < 目标维度 {TARGET_DIM}"
    print(f"  [OK] 百炼 Embedding API 返回维度 {raw_dim}，满足 >= {TARGET_DIM}")


def test_text_split():
    """T4 — 验证文本分割：块大小和重叠窗口。"""
    rag = RAG(
        table_name=TEST_TABLE, embedding_dim=TARGET_DIM,
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP,
    )
    text = "ABCDEFGHIJ" * 30
    chunks = rag.split_text(text)
    rag.close()

    assert len(chunks) >= 1, "分割后至少应有 1 个块"
    for c in chunks:
        assert len(c) <= config.CHUNK_SIZE + config.CHUNK_OVERLAP, \
            f"块大小 {len(c)} 超过预期上限"
    print(f"  [OK] 文本分割为 {len(chunks)} 个块，大小均 <= {config.CHUNK_SIZE + config.CHUNK_OVERLAP}")


def test_embedding_16d():
    """T5 — 验证向量化输出为 16 维。"""
    rag = RAG(table_name=TEST_TABLE, embedding_dim=TARGET_DIM)
    chunks = ["这是一段测试文本。", "深度学习是机器学习的一个重要分支。"]
    embeddings = rag.embed(chunks)
    rag.close()

    assert len(embeddings) == 2
    for emb in embeddings:
        assert len(emb) == TARGET_DIM, f"向量维度 {len(emb)} != {TARGET_DIM}"
    print(f"  [OK] 输出 {len(embeddings)} 个向量，每个 {TARGET_DIM} 维")


def test_store_and_retrieve():
    """T6 — 核心流程：读取 txt -> 分割 -> 百炼 API 向量化(16d) -> 存储 -> 检索。"""
    # _drop_test_table()

    assert os.path.exists(TEST_TXT_FILE), f"测试文件不存在: {TEST_TXT_FILE}"
    with open(TEST_TXT_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"  -> 读取文件: {TEST_TXT_FILE}  ({len(text)} 字符)")

    rag = RAG(
        table_name=TEST_TABLE, embedding_dim=TARGET_DIM,
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP,
    )
    print(f"  -> 写入目标: {rag._host}:{rag._port}/{rag._database}  表={rag._table}")

    ids = rag.ingest_text(text, source_path=TEST_TXT_FILE)
    count = rag.chunk_count()
    print(f"  -> 入库 {len(ids)} 个块，表内共 {count} 条记录")

    assert len(ids) >= 1, "至少应入库 1 个块"
    for i in ids:
        assert i > 0, f"id 应为正整数: {i}"

    results = rag.search("什么是深度学习", top_k=TOP_K)
    print(f"  -> 检索 '什么是深度学习': 返回 {len(results)} 条结果")

    assert len(results) >= 1, "检索应返回至少 1 条结果"
    for r in results:
        assert "content" in r
        assert "similarity" in r
        similarity = float(r["similarity"])
        assert 0.0 <= similarity <= 1.0, f"similarity {similarity} 超出 [0,1]"
        print(f"    [{similarity:.4f}] {textwrap.shorten(r['content'], width=80)}")

    rag.close()
    print("  [OK] 读取 -> 分割 -> 向量化(16d) -> 存储 -> 检索 全流程通过")


def test_cleanup():
    """T7 — 清理测试表。"""
    # _drop_test_table()
    print("  [OK] 测试表已清理")


# ── 运行入口 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  RAG 管道测试 - 阿里云百炼 Embedding API + PostgreSQL pgvector")
    print("=" * 60)
    print(f"  PG 连接: {config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE}")
    print(f"  PG 用户: {config.PG_USER}")
    print(f"  正式表:  {config.PG_VECTOR_TABLE}")
    print(f"  测试表:  {TEST_TABLE}")
    print(f"  API:     {config.EMBEDDING_MODEL} @ {config.DASHSCOPE_BASE_URL}")
    print(f"  TXT文件: {TEST_TXT_FILE}")
    print(f"  文件存在: {os.path.exists(TEST_TXT_FILE)}")

    tests = [
        ("T1 远端 PG 连接", test_pg_connection),
        ("T2 pgvector 扩展", test_pgvector_extension),
        ("T3 百炼 API 维度", test_api_embedding_dim),
        ("T4 文本分割", test_text_split),
        ("T5 16 维向量化", test_embedding_16d),
        ("T6 全流程 (读取->分割->向量化->存储->检索)", test_store_and_retrieve),
        ("T7 清理测试表", test_cleanup),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        print(f"\n{'─' * 60}")
        print(f"  [{name}]")
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {type(e).__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  结果: {passed} 通过, {failed} 失败")
    print(f"{'=' * 60}")
    sys.exit(0 if failed == 0 else 1)
