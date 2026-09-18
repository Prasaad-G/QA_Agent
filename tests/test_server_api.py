"""API endpoint tests for QA Agent server."""

from pathlib import Path
import zipfile
import io
import pytest
from fastapi.testclient import TestClient
from qa_agent.server.app import app

client = TestClient(app)


def test_server_load_local_and_full_cycle():
    sample_dir = Path(__file__).resolve().parent.parent / "sample_projects" / "fastapi_calculator"

    # 1. Load Local Project
    res = client.post("/api/load-local", json={"path": str(sample_dir)})
    assert res.status_code == 200
    data = res.json()
    project_id = data["project_id"]
    assert project_id is not None

    # 2. Analyze
    res_analyze = client.post(f"/api/projects/{project_id}/analyze")
    assert res_analyze.status_code == 200
    prof = res_analyze.json()
    assert prof["primary_language"] == "Python"
    assert "FastAPI" in prof["frameworks"]

    # 3. Plan
    res_plan = client.post(f"/api/projects/{project_id}/plan", json={"test_types": ["unit", "api"]})
    assert res_plan.status_code == 200
    plan = res_plan.json()
    assert len(plan["items"]) > 0

    # 4. Generate
    res_gen = client.post(f"/api/projects/{project_id}/generate", json={"model_name": "gemini-2.5-flash"})
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["generated_count"] > 0

    # 5. Download Project with Tests (ZIP)
    res_dl = client.get(f"/api/projects/{project_id}/download")
    assert res_dl.status_code == 200
    assert "application/zip" in res_dl.headers.get("content-type", "")

    # Verify downloaded bytes are a valid zip containing tests/qa_agent
    with zipfile.ZipFile(io.BytesIO(res_dl.content)) as z:
        filenames = z.namelist()
        assert any("tests/qa_agent" in f for f in filenames)
        assert any("calculator.py" in f for f in filenames)

    # 6. Execute Tests Automatically
    res_exec = client.post(f"/api/projects/{project_id}/execute")
    assert res_exec.status_code == 200
    exec_result = res_exec.json()
    assert exec_result["total_tests"] > 0
    assert exec_result["passed"] > 0

    # 7. Get Report
    res_rep_html = client.get(f"/api/projects/{project_id}/report?format=html")
    assert res_rep_html.status_code == 200
    assert "<html" in res_rep_html.text

    res_rep_md = client.get(f"/api/projects/{project_id}/report?format=md")
    assert res_rep_md.status_code == 200
    assert "QA Agent Automated Test Report" in res_rep_md.text

