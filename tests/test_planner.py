"""Unit tests for QA Agent TestPlanner."""

from pathlib import Path
import pytest
from qa_agent.core.analyzer import ProjectAnalyzer
from qa_agent.core.models import TestType
from qa_agent.core.planner import TestPlanner


def test_planner_creates_all_test_dimensions():
    sample_dir = Path(__file__).resolve().parent.parent / "sample_projects" / "fastapi_calculator"
    analyzer = ProjectAnalyzer(sample_dir)
    profile = analyzer.analyze()

    planner = TestPlanner(profile)
    plan = planner.create_plan([TestType.UNIT, TestType.API, TestType.E2E])

    assert plan.primary_language == "Python"
    assert plan.recommended_framework == "pytest"
    assert len(plan.items) >= 3

    types_planned = {item.test_type for item in plan.items}
    assert TestType.UNIT in types_planned
    assert TestType.API in types_planned
    assert TestType.E2E in types_planned

