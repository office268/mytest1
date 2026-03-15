import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Code Preview App")

app.mount("/static", StaticFiles(directory="static"), name="static")


class RunRequest(BaseModel):
    code: str
    language: str = "python"


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index.html").read_text()


@app.post("/run")
async def run_code(req: RunRequest):
    if req.language != "python":
        return JSONResponse({"error": "Only Python execution is supported server-side."})

    try:
        result = subprocess.run(
            [sys.executable, "-c", req.code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return JSONResponse({"stdout": "", "stderr": "Timeout: execution exceeded 10 seconds.", "returncode": -1})
    except Exception as e:
        return JSONResponse({"stdout": "", "stderr": str(e), "returncode": -1})
