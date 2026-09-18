"""Command Line Interface for QA Agent.

Allows developers to analyze repositories, generate test suites, and execute
automated tests directly inside their terminal without uploading code.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qa_agent.core.analyzer import ProjectAnalyzer
from qa_agent.core.generator import TestGenerator
from qa_agent.core.models import TestType
from qa_agent.core.planner import TestPlanner
from qa_agent.core.reporter import QAReporter
from qa_agent.core.runner import TestRunner

console = Console()


def run_cli():
    parser = argparse.ArgumentParser(
        prog="qa-agent",
        description="Autonomous Polyglot QA AI Agent - Generate and run test suites for any project.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: analyze
    p_analyze = subparsers.add_parser("analyze", help="Inspect and profile a project directory")
    p_analyze.add_argument("path", nargs="?", default=".", help="Target project root directory (default: current dir)")

    # Command: generate
    p_gen = subparsers.add_parser("generate", help="Generate Unit, API, and E2E test suites in tests/qa_agent/")
    p_gen.add_argument("path", nargs="?", default=".", help="Target project root directory")
    p_gen.add_argument("--types", default="unit,api,e2e", help="Comma-separated test types (default: unit,api,e2e)")
    p_gen.add_argument("--api-key", default="", help="Gemini API Key (optional, or set GEMINI_API_KEY)")
    p_gen.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name (default: gemini-2.5-flash)")

    # Command: test
    p_test = subparsers.add_parser("test", help="Safely execute generated tests in isolated sandbox")
    p_test.add_argument("path", nargs="?", default=".", help="Target project root directory")
    p_test.add_argument("--report", action="store_true", help="Generate HTML and Markdown reports after testing")

    # Command: run (all-in-one)
    p_all = subparsers.add_parser("run", help="Full lifecycle: analyze, generate tests, and execute")
    p_all.add_argument("path", nargs="?", default=".", help="Target project root directory")
    p_all.add_argument("--api-key", default="", help="Gemini API Key")

    args = parser.parse_args(sys.argv[2:] if len(sys.argv) > 1 and sys.argv[1] == "--cli" else sys.argv[1:])

    if not args.command:
        parser.print_help()
        return

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        console.print(f"[bold red]Error:[/bold red] Target directory not found: {target_path}")
        sys.exit(1)

    if args.command == "analyze":
        cmd_analyze(target_path)
    elif args.command == "generate":
        cmd_generate(target_path, args.types, args.api_key, args.model)
    elif args.command == "test":
        cmd_test(target_path, args.report)
    elif args.command == "run":
        cmd_run_all(target_path, args.api_key)


def cmd_analyze(project_path: Path):
    console.print(Panel.fit(f"[bold green]QA Agent Profiler[/bold green]\nTarget: [cyan]{project_path}[/cyan]"))
    analyzer = ProjectAnalyzer(project_path)
    profile = analyzer.analyze()

    table = Table(title="Project Profile", border_style="dim")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Project Name", profile.project_name)
    table.add_row("Primary Language", profile.primary_language)
    table.add_row("Detected Languages", ", ".join(profile.detected_languages) or "None")
    table.add_row("Frameworks", ", ".join(profile.frameworks) or "None")
    table.add_row("Existing Test Runner", profile.existing_test_runner or "None detected")
    table.add_row("Source Files", str(profile.file_count))
    table.add_row("Total Lines of Code", str(profile.total_lines))
    table.add_row("API Endpoints Found", str(len(profile.endpoints)))
    table.add_row("Key Functions Found", str(len(profile.functions)))

    console.print(table)


def cmd_generate(project_path: Path, types_str: str, api_key: str, model_name: str):
    cmd_analyze(project_path)
    analyzer = ProjectAnalyzer(project_path)
    profile = analyzer.analyze()

    test_types = []
    for t in types_str.split(","):
        t_clean = t.strip().lower()
        if t_clean in ["unit", "api", "e2e"]:
            test_types.append(TestType(t_clean))

    planner = TestPlanner(profile)
    plan = planner.create_plan(test_types)

    console.print(f"\n[bold yellow]Generating test suites into tests/qa_agent/...[/bold yellow]")
    generator = TestGenerator(
        project_root=project_path,
        profile=profile,
        api_key=api_key or os.getenv("GEMINI_API_KEY"),
        model_name=model_name,
    )

    def progress(desc, current, total):
        console.print(f"  [{current}/{total}] {desc}")

    files = generator.generate(plan, progress_callback=progress)
    console.print(f"\n[bold green]Success![/bold green] Generated {len(files)} test files in [cyan]{project_path}/tests/qa_agent/[/cyan]")


def cmd_test(project_path: Path, generate_report: bool = True):
    analyzer = ProjectAnalyzer(project_path)
    profile = analyzer.analyze()

    console.print(f"\n[bold cyan]Executing test suite for {profile.project_name}...[/bold cyan]")
    runner = TestRunner(project_path, profile)

    def log_line(line: str):
        print(line)

    result = runner.run_tests(log_callback=log_line)

    color = "green" if result.success else "red"
    console.print(
        f"\n[bold {color}]Execution Finished:[/bold {color}] "
        f"Total: {result.total_tests} | Passed: {result.passed} | Failed: {result.failed} | Skipped: {result.skipped} | Duration: {result.duration_seconds}s"
    )

    if generate_report:
        reporter = QAReporter(profile)
        md_content = reporter.generate_markdown_report(result)
        report_file = project_path / "tests" / "qa_agent" / "qa_report.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(md_content, encoding="utf-8")
        console.print(f"[bold green]Report saved to:[/bold green] [cyan]{report_file}[/cyan]")


def cmd_run_all(project_path: Path, api_key: str):
    cmd_generate(project_path, "unit,api,e2e", api_key, "gemini-2.5-flash")
    cmd_test(project_path, generate_report=True)


if __name__ == "__main__":
    run_cli()

