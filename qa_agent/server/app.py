"""FastAPI Web Server for QA Agent.

Provides endpoints for project ingestion, analysis, test generation,
one-click project ZIP download, live test execution, and QA report export.
"""

from __future__ import annotations

import asyncio
import io
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from qa_agent.core.analyzer import ProjectAnalyzer
from qa_agent.core.generator import TestGenerator
from qa_agent.core.models import (
    ExecutionResult,
    ProjectProfile,
    TestPlan,
    TestType,
)
from qa_agent.core.planner import TestPlanner
from qa_agent.core.reporter import QAReporter
from qa_agent.core.runner import TestRunner

app = FastAPI(title="QA AI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project session storage in-memory
class ProjectSession:
    def __init__(self, project_id: str, root_path: Path, name: str, is_temp: bool = True):
        self.project_id = project_id
        self.root_path = root_path
        self.name = name
        self.is_temp = is_temp
        self.profile: Optional[ProjectProfile] = None
        self.plan: Optional[TestPlan] = None
        self.execution_result: Optional[ExecutionResult] = None


PROJECTS: Dict[str, ProjectSession] = {}
BASE_WORKSPACE = Path(tempfile.gettempdir()) / "qa_agent_workspace"
BASE_WORKSPACE.mkdir(parents=True, exist_ok=True)


class LocalPathRequest(BaseModel):
    path: str


class PlanRequest(BaseModel):
    test_types: List[str] = ["unit", "api", "e2e"]


class GenerateRequest(BaseModel):
    api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash"


@app.post("/api/upload")
async def upload_project_zip(file: UploadFile = File(...)):
    """Accepts a .zip file of the project, unpacks it into an isolated workspace directory."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a valid .zip file.")

    project_id = str(uuid.uuid4())[:8]
    extract_dir = BASE_WORKSPACE / f"proj_{project_id}"
    extract_dir.mkdir(parents=True, exist_ok=True)

    zip_bytes = await file.read()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        z.extractall(extract_dir)

    # Check if the zip extracted into a single nested root folder
    extracted_items = list(extract_dir.iterdir())
    actual_root = extract_dir
    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        actual_root = extracted_items[0]

    project_name = file.filename.replace(".zip", "")
    session = ProjectSession(project_id=project_id, root_path=actual_root, name=project_name, is_temp=True)
    PROJECTS[project_id] = session

    return {
        "project_id": project_id,
        "name": project_name,
        "path": str(actual_root).replace("\\", "/"),
        "message": "Project uploaded and extracted successfully.",
    }


@app.post("/api/load-local")
async def load_local_project(req: LocalPathRequest):
    """Loads a project directly from a local folder on disk (no upload needed)."""
    p = Path(req.path).resolve()
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=404, detail=f"Local path does not exist or is not a directory: {req.path}")

    project_id = str(uuid.uuid4())[:8]
    session = ProjectSession(project_id=project_id, root_path=p, name=p.name, is_temp=False)
    PROJECTS[project_id] = session

    return {
        "project_id": project_id,
        "name": p.name,
        "path": str(p).replace("\\", "/"),
        "message": "Local project loaded successfully.",
    }


@app.post("/api/projects/{project_id}/analyze")
async def analyze_project(project_id: str):
    """Analyzes the project structure, languages, frameworks, endpoints, and functions."""
    session = PROJECTS.get(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project session not found.")

    analyzer = ProjectAnalyzer(session.root_path)
    profile = analyzer.analyze()
    session.profile = profile

    return profile.model_dump()


@app.post("/api/projects/{project_id}/plan")
async def plan_tests(project_id: str, req: PlanRequest):
    """Generates the test plan according to selected test types."""
    session = PROJECTS.get(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project session not found.")
    if not session.profile:
        # Auto analyze if not done
        analyzer = ProjectAnalyzer(session.root_path)
        session.profile = analyzer.analyze()

    types = []
    for t in req.test_types:
        try:
            types.append(TestType(t.lower()))
        except ValueError:
            pass

    planner = TestPlanner(session.profile)
    plan = planner.create_plan(types)
    session.plan = plan

    return plan.model_dump()


@app.post("/api/projects/{project_id}/generate")
async def generate_tests(project_id: str, req: GenerateRequest):
    """Generates test files into tests/qa_agent/ using Gemini or fallback generator."""
    session = PROJECTS.get(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project session not found.")
    if not session.profile:
        analyzer = ProjectAnalyzer(session.root_path)
        session.profile = analyzer.analyze()
    if not session.plan:
        planner = TestPlanner(session.profile)
        session.plan = planner.create_plan()

    generator = TestGenerator(
        project_root=session.root_path,
        profile=session.profile,
        api_key=req.api_key,
        model_name=req.model_name,
    )

    generated_files = generator.generate(session.plan)

    return {
        "project_id": project_id,
        "generated_count": len(generated_files),
        "files": [f.model_dump() for f in generated_files],
        "message": f"Successfully generated {len(generated_files)} test files in tests/qa_agent/",
    }


@app.get("/api/projects/{project_id}/download")
async def download_project_with_tests(project_id: str):
    """Packages the complete project directory (including generated tests) into a downloadable ZIP."""
    session = PROJECTS.get(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project session not found.")

    zip_buffer = io.BytesIO()
    root_path = session.root_path

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(root_path):
            # Ignore git, cache, virtualenvs
            dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", ".venv", "venv", "node_modules"]]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(root_path)
                z.write(full_path, arcname=str(rel_path))

    zip_buffer.seek(0)
    filename = f"{session.name}_with_qa_tests.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/projects/{project_id}/execute")
async def execute_tests(project_id: str):
    """Executes the generated test suite and returns parsed results."""
    session = PROJECTS.get(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project session not found.")
    if not session.profile:
        analyzer = ProjectAnalyzer(session.root_path)
        session.profile = analyzer.analyze()

    runner = TestRunner(session.root_path, session.profile)
    result = runner.run_tests()

    # Generate reports
    reporter = QAReporter(session.profile, session.plan)
    result.report_markdown = reporter.generate_markdown_report(result)
    result.report_html = reporter.generate_html_report(result)
    session.execution_result = result

    return result.model_dump()


@app.websocket("/ws/execute/{project_id}")
async def websocket_execute_tests(websocket: WebSocket, project_id: str):
    """Streams test execution output line-by-line via WebSocket in real-time."""
    await websocket.accept()
    session = PROJECTS.get(project_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Project session not found."})
        await websocket.close()
        return

    if not session.profile:
        analyzer = ProjectAnalyzer(session.root_path)
        session.profile = analyzer.analyze()

    runner = TestRunner(session.root_path, session.profile)

    def send_line(line: str):
        try:
            asyncio.run(websocket.send_json({"type": "log", "data": line}))
        except Exception:
            pass

    # Run in executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    await websocket.send_json({"type": "status", "data": "STARTING_TESTS"})
    result = await loop.run_in_executor(None, lambda: runner.run_tests(log_callback=send_line))

    reporter = QAReporter(session.profile, session.plan)
    result.report_markdown = reporter.generate_markdown_report(result)
    result.report_html = reporter.generate_html_report(result)
    session.execution_result = result

    await websocket.send_json({
        "type": "completed",
        "result": result.model_dump(),
    })
    await websocket.close()


@app.get("/api/projects/{project_id}/report")
async def get_report(project_id: str, format: str = "html"):
    """Downloads or displays the test report in HTML or Markdown."""
    session = PROJECTS.get(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Project session not found.")
    if not session.execution_result:
        raise HTTPException(status_code=400, detail="Tests have not been executed yet. Run tests first.")

    if format.lower() == "html":
        return HTMLResponse(content=session.execution_result.report_html)
    else:
        return PlainTextResponse(
            content=session.execution_result.report_markdown,
            headers={"Content-Disposition": f'attachment; filename="{session.name}_qa_report.md"'},
        )


# Mount static directory for frontend
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main web dashboard single page application."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>QA Agent Backend is running. Static files loading...</h1>")

