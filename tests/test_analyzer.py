"""Unit tests for QA Agent ProjectAnalyzer."""

from pathlib import Path
import pytest
from qa_agent.core.analyzer import ProjectAnalyzer


def test_analyzer_fastapi_project():
    sample_dir = Path(__file__).resolve().parent.parent / "sample_projects" / "fastapi_calculator"
    analyzer = ProjectAnalyzer(sample_dir)
    profile = analyzer.analyze()

    assert profile.project_name == "fastapi_calculator"
    assert profile.primary_language == "Python"
    assert "FastAPI" in profile.frameworks
    assert len(profile.endpoints) >= 4
    assert any(ep.path == "/calculate/add" for ep in profile.endpoints)
    assert any(fn.name == "add" for fn in profile.functions)


def test_analyzer_js_project():
    sample_dir = Path(__file__).resolve().parent.parent / "sample_projects" / "js_todo_app"
    analyzer = ProjectAnalyzer(sample_dir)
    profile = analyzer.analyze()

    assert profile.project_name == "js_todo_app"
    assert "JavaScript" in profile.primary_language
    assert "Express" in profile.frameworks
    assert any(ep.path == "/api/todos" for ep in profile.endpoints)

