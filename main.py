import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite+aiosqlite:///./codepreview.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Snippet(Base):
    __tablename__ = "snippets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunHistory(Base):
    __tablename__ = "run_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(Text)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Code Preview App", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    code: str
    language: str = "python"


class SnippetCreate(BaseModel):
    name: str
    language: str
    code: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index.html").read_text()


@app.post("/run")
async def run_code(req: RunRequest, db: AsyncSession = Depends(get_db)):
    stdout = ""
    stderr = ""
    returncode = 0

    if req.language != "python":
        result = {"stdout": "", "stderr": "Only Python execution is supported server-side.", "returncode": -1}
        return JSONResponse(result)

    try:
        proc = subprocess.run(
            [sys.executable, "-c", req.code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        stderr = "Timeout: execution exceeded 10 seconds."
        returncode = -1
    except Exception as e:
        stderr = str(e)
        returncode = -1

    # Save to run history
    db.add(RunHistory(language=req.language, code=req.code, stdout=stdout, stderr=stderr))
    await db.commit()

    return {"stdout": stdout, "stderr": stderr, "returncode": returncode}


# --- Snippets ---

@app.post("/snippets", status_code=201)
async def create_snippet(body: SnippetCreate, db: AsyncSession = Depends(get_db)):
    snippet = Snippet(name=body.name, language=body.language, code=body.code)
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return {"id": snippet.id, "name": snippet.name, "language": snippet.language, "created_at": snippet.created_at}


@app.get("/snippets")
async def list_snippets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Snippet).order_by(Snippet.created_at.desc()))
    rows = result.scalars().all()
    return [{"id": s.id, "name": s.name, "language": s.language, "created_at": s.created_at} for s in rows]


@app.get("/snippets/{snippet_id}")
async def get_snippet(snippet_id: int, db: AsyncSession = Depends(get_db)):
    snippet = await db.get(Snippet, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"id": snippet.id, "name": snippet.name, "language": snippet.language,
            "code": snippet.code, "created_at": snippet.created_at}


@app.delete("/snippets/{snippet_id}", status_code=204)
async def delete_snippet(snippet_id: int, db: AsyncSession = Depends(get_db)):
    snippet = await db.get(Snippet, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    await db.delete(snippet)
    await db.commit()


# --- Run History ---

@app.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunHistory).order_by(RunHistory.created_at.desc()).limit(50)
    )
    rows = result.scalars().all()
    return [{"id": r.id, "language": r.language, "code": r.code,
             "stdout": r.stdout, "stderr": r.stderr, "created_at": r.created_at} for r in rows]


@app.delete("/history", status_code=204)
async def clear_history(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(RunHistory))
    await db.commit()
