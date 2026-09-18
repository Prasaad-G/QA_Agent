"""Integration test for Generation, Execution, and Reporting."""

import shutil
import tempfile
from pathlib import Path
import pytest
from qa_agent.core.analyzer import ProjectAnalyzer
from qa_agent.core.generator import TestGenerator
from qa_agent.core.planner import TestPlanner
from qa_agent.core.reporter import QAReporter
from qa_agent.core.runner import TestRunner


def test_full_pipeline_sample_project():
    source_dir = Path(__file__).resolve().parent.parent / "sample_projects" / "fastapi_calculator"

    # Use a temporary directory for isolated testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_project = Path(temp_dir) / "fastapi_calculator"
        shutil.copytree(source_dir, temp_project)

        # 1. Analyze
        analyzer = ProjectAnalyzer(temp_project)
        profile = analyzer.analyze()
        assert profile.primary_language == "Python"

        # 2. Plan
        planner = TestPlanner(profile)
        plan = planner.create_plan()
        assert len(plan.items) > 0

        # 3. Generate
        generator = TestGenerator(temp_project, profile)
        generated_files = generator.generate(plan)
        assert len(generated_files) > 0

        # Verify files created on disk
        qa_tests_dir = temp_project / "tests" / "qa_agent"
        assert qa_tests_dir.exists()
        assert (qa_tests_dir / "unit").exists()
        assert (qa_tests_dir / "api").exists()
        assert (qa_tests_dir / "test_summary.md").exists()

        # 4. Run tests in sandbox
        runner = TestRunner(temp_project, profile)
        result = runner.run_tests()
        assert result.exit_code == 0
        assert result.total_tests > 0
        assert result.passed > 0
        assert result.failed == 0

        # 5. Report
        reporter = QAReporter(profile, plan)
        md_report = reporter.generate_markdown_report(result)
        html_report = reporter.generate_html_report(result)

        assert "QA Agent Automated Test Report" in md_report
        assert "PASSED" in md_report
        assert "<html" in html_report

