"""GitHub Action CI/CD Integration Runner.

Executes within GitHub Actions runners to analyze pull requests or pushed commits,
generate targeted tests, run the suite, write to GITHUB_STEP_SUMMARY, and
optionally comment on the Pull Request via GitHub REST API.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests

from qa_agent.core.analyzer import ProjectAnalyzer
from qa_agent.core.generator import TestGenerator
from qa_agent.core.models import TestType
from qa_agent.core.planner import TestPlanner
from qa_agent.core.reporter import QAReporter
from qa_agent.core.runner import TestRunner


def run_github_action():
    """Main entrypoint for GitHub Action workflows."""
    print("::group::QA AI Agent CI/CD Runner")

    target_path = Path(os.getenv("INPUT_TARGET_PATH", ".")).resolve()
    api_key = os.getenv("INPUT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    model_name = os.getenv("INPUT_MODEL_NAME", "gemini-2.5-flash")
    types_str = os.getenv("INPUT_TEST_TYPES", "unit,api,e2e")
    post_comment = os.getenv("INPUT_POST_PR_COMMENT", "true").lower() == "true"
    fail_on_error = os.getenv("INPUT_FAIL_ON_ERROR", "true").lower() == "true"
    github_token = os.getenv("INPUT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN", "")

    print(f"Target Directory: {target_path}")
    print(f"Test Types:       {types_str}")
    print(f"Model:            {model_name}")

    # 1. Analyze
    print("\n--- 1. Analyzing Codebase ---")
    analyzer = ProjectAnalyzer(target_path)
    profile = analyzer.analyze()
    print(f"Project:   {profile.project_name}")
    print(f"Language:  {profile.primary_language}")
    print(f"Endpoints: {len(profile.endpoints)}")
    print(f"Functions: {len(profile.functions)}")

    # 2. Plan
    print("\n--- 2. Formulating Test Plan ---")
    types = []
    for t in types_str.split(","):
        t_clean = t.strip().lower()
        if t_clean in ["unit", "api", "e2e"]:
            types.append(TestType(t_clean))

    planner = TestPlanner(profile)
    plan = planner.create_plan(types)
    print(f"Planned {len(plan.items)} test suites.")

    # 3. Generate
    print("\n--- 3. Generating Test Suites in tests/qa_agent/ ---")
    generator = TestGenerator(
        project_root=target_path,
        profile=profile,
        api_key=api_key,
        model_name=model_name,
    )
    generated_files = generator.generate(plan)
    print(f"Generated {len(generated_files)} files.")

    # 4. Run Tests
    print("\n--- 4. Executing Automated Tests ---")
    runner = TestRunner(target_path, profile)
    result = runner.run_tests(log_callback=print)

    # 5. Report
    print("\n--- 5. Generating QA Report ---")
    reporter = QAReporter(profile, plan)
    markdown_report = reporter.generate_markdown_report(result)
    html_report = reporter.generate_html_report(result)

    qa_dir = target_path / "tests" / "qa_agent"
    qa_dir.mkdir(parents=True, exist_ok=True)
    report_file = qa_dir / "qa_report.md"
    report_file.write_text(markdown_report, encoding="utf-8")
    (qa_dir / "qa_report.html").write_text(html_report, encoding="utf-8")

    print(f"Report written to {report_file}")
    print("::endgroup::")

    # Output to GitHub Step Summary
    step_summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if step_summary_path:
        try:
            with open(step_summary_path, "a", encoding="utf-8") as f:
                f.write(markdown_report + "\n")
            print("Successfully written to GitHub Actions Job Summary.")
        except Exception as e:
            print(f"Warning: Could not write GITHUB_STEP_SUMMARY: {e}")

    # Set GitHub Action Outputs
    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        try:
            with open(github_output_path, "a", encoding="utf-8") as f:
                f.write(f"total={result.total_tests}\n")
                f.write(f"passed={result.passed}\n")
                f.write(f"failed={result.failed}\n")
                f.write(f"skipped={result.skipped}\n")
                f.write(f"success={'true' if result.success else 'false'}\n")
                f.write(f"report_path={report_file}\n")
        except Exception as e:
            print(f"Warning: Could not write GITHUB_OUTPUT: {e}")

    # Post comment to PR if available
    if post_comment and github_token:
        post_pr_comment_if_applicable(markdown_report, github_token)

    # Print summary to console
    status_str = "SUCCESS" if result.success else "FAILED"
    print(f"\n[QA Agent CI] Final Result: {status_str} ({result.passed}/{result.total_tests} passed)")

    if not result.success and fail_on_error:
        sys.exit(1)


def post_pr_comment_if_applicable(report_md: str, token: str):
    """Detects PR event from GITHUB_EVENT_PATH and posts a PR comment."""
    event_path = os.getenv("GITHUB_EVENT_PATH")
    repo = os.getenv("GITHUB_REPOSITORY")

    if not event_path or not repo or not os.path.exists(event_path):
        return

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            event_data = json.load(f)

        pr_number = None
        if "pull_request" in event_data:
            pr_number = event_data["pull_request"].get("number")
        elif "issue" in event_data:
            pr_number = event_data["issue"].get("number")

        if not pr_number:
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        payload = {"body": f"### 🛡️ QA AI Agent Automated Test Report\n\n{report_md}"}

        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code in [200, 201]:
            print(f"Successfully posted QA report comment to PR #{pr_number}")
        else:
            print(f"Failed to post comment to PR #{pr_number}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Notice: PR comment skipped ({e})")


if __name__ == "__main__":
    run_github_action()

