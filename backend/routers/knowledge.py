from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from backend.database import engine
from backend.models.knowledge import KnowledgeFile
from backend.schemas.api import KnowledgeFileOut

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])

MAX_FILE_SIZE = 128 * 1024 * 1024


def _to_out(f: KnowledgeFile) -> KnowledgeFileOut:
    return KnowledgeFileOut(
        id=f.id,
        name=f.name,
        size=f.size,
        status=f.status,
        chunks=f.chunks,
        uploadDate=f.upload_date,
        fakeUrl=f"https://rag-storage.internal/kb/docs/{f.name}",
    )


def _do_index(kb_file_id: str, name: str, text: str) -> tuple[int, str]:
    source_path = f"kb://{kb_file_id}/{name}"
    from rag import RAG
    rag = RAG(table_name="test_chunks_16d", embedding_dim=16)
    rag.delete_by_source(source_path)
    ids = rag.ingest_text(text, source_path=source_path, dedup=False)
    rag.close()
    return len(ids), source_path


@router.get("/files", response_model=list[KnowledgeFileOut])
def list_files():
    with Session(engine) as session:
        files = session.exec(select(KnowledgeFile).order_by(KnowledgeFile.upload_date.desc())).all()
        return [_to_out(f) for f in files]


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        return _error("仅允许上传 .txt 文件", 400)

    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        return _error("文件大小超过 128MB 限制", 400)

    text = raw.decode("utf-8", errors="replace")

    with Session(engine) as session:
        kb_file = KnowledgeFile(
            name=file.filename,
            size=len(raw),
            status="processing",
            content=text,
        )
        session.add(kb_file)
        session.commit()
        session.refresh(kb_file)

    try:
        n_chunks, source_path = _do_index(kb_file.id, file.filename, text)
    except Exception as e:
        with Session(engine) as session:
            f = session.get(KnowledgeFile, kb_file.id)
            if f:
                f.status = "failed"
                session.add(f)
                session.commit()
        return _error(f"索引失败: {e}", 500)

    with Session(engine) as session:
        f = session.get(KnowledgeFile, kb_file.id)
        if f:
            f.status = "indexed"
            f.chunks = n_chunks
            f.source_path = source_path
            session.add(f)
            session.commit()
            session.refresh(f)
            return _to_out(f)

    return _error("内部错误", 500)


@router.delete("/files/{file_id}")
def delete_file(file_id: str):
    with Session(engine) as session:
        kb_file = session.get(KnowledgeFile, file_id)
        if not kb_file:
            return _error("文件不存在", 404)

        source_path = kb_file.source_path
        session.delete(kb_file)
        session.commit()

    if source_path:
        try:
            from rag import RAG
            rag = RAG(table_name="test_chunks_16d", embedding_dim=16)
            rag.delete_by_source(source_path)
            rag.close()
        except Exception:
            pass

    return {"ok": True}


@router.post("/files/{file_id}/retry")
def retry_index(file_id: str):
    with Session(engine) as session:
        kb_file = session.get(KnowledgeFile, file_id)
        if not kb_file:
            return _error("文件不存在", 404)

        if not kb_file.content:
            return _error("文件原始内容已丢失，请重新上传", 400)

        kb_file.status = "processing"
        kb_file.chunks = 0
        session.add(kb_file)
        session.commit()
        session.refresh(kb_file)

        try:
            n_chunks, source_path = _do_index(kb_file.id, kb_file.name, kb_file.content)
        except Exception as e:
            kb_file.status = "failed"
            session.add(kb_file)
            session.commit()
            return _error(f"重新索引失败: {e}", 500)

        kb_file.status = "indexed"
        kb_file.chunks = n_chunks
        kb_file.source_path = source_path
        session.add(kb_file)
        session.commit()
        session.refresh(kb_file)

        return _to_out(kb_file)


def _error(msg: str, code: int):
    return JSONResponse({"error": msg}, status_code=code)
