"""Test Execution Runner for QA Agent.

Safely executes generated test suites in an isolated subprocess, streaming live logs,
handling timeouts, and parsing test results into structured metrics.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, List, Optional

from qa_agent.core.models import (
    ExecutionResult,
    ProjectProfile,
    TestRunItem,
)


class TestRunner:
    """Executes tests safely and parses pass/fail metrics."""
    __test__ = False


    def __init__(self, project_root: str | Path, profile: ProjectProfile):
        self.project_root = Path(project_root).resolve()
        self.profile = profile

    def run_tests(
        self,
        test_path: str = "tests/qa_agent",
        timeout_seconds: int = 90,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> ExecutionResult:
        """Executes the test suite and captures output."""
        command, env = self._prepare_command(test_path)

        if log_callback:
            log_callback(f"[QA Agent Runner] Working Directory: {self.project_root}")
            log_callback(f"[QA Agent Runner] Executing: {' '.join(command)}")
            log_callback("-" * 60)

        start_time = time.time()
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        exit_code = -1

        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Read stdout line-by-line in real time
            if process.stdout:
                for line in process.stdout:
                    stdout_lines.append(line)
                    if log_callback:
                        log_callback(line.rstrip())

            # Read stderr if any
            if process.stderr:
                for line in process.stderr:
                    stderr_lines.append(line)
                    if log_callback:
                        log_callback(f"[stderr] {line.rstrip()}")

            exit_code = process.wait(timeout=timeout_seconds)

        except subprocess.TimeoutExpired:
            if log_callback:
                log_callback(f"[ERROR] Test execution timed out after {timeout_seconds} seconds.")
            if process:
                process.kill()
            exit_code = -99
            stderr_lines.append(f"Execution timed out after {timeout_seconds} seconds.")
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Execution failed: {str(e)}")
            stderr_lines.append(str(e))
            exit_code = -1

        duration = round(time.time() - start_time, 2)
        full_stdout = "".join(stdout_lines)
        full_stderr = "".join(stderr_lines)

        # Parse test metrics from stdout
        test_items, passed, failed, skipped, errors = self._parse_pytest_output(full_stdout)
        total = passed + failed + skipped + errors

        # Trigger Autonomous Self-Healing Engine if failures exist
        if (failed > 0 or errors > 0) and not getattr(self, "_is_healing_retry", False):
            if log_callback:
                log_callback("\n[Self-Healing Engine] Failures detected. Diagnosing tracebacks and patching test files...")

            initial_result = ExecutionResult(
                success=False,
                total_tests=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration_seconds=duration,
                command_executed=" ".join(command),
                exit_code=exit_code,
                stdout=full_stdout,
                stderr=full_stderr,
                test_items=test_items,
            )

            from qa_agent.core.self_healing import SelfHealingEngine
            healer = SelfHealingEngine(self.project_root)
            was_healed, count, details = healer.heal_failed_tests(initial_result)

            if was_healed:
                if log_callback:
                    for d in details:
                        log_callback(f"[Self-Healing Engine] {d}")
                    log_callback("[Self-Healing Engine] Re-executing test suite after self-healing patches...\n")

                self._is_healing_retry = True
                try:
                    return self.run_tests(test_path=test_path, timeout_seconds=timeout_seconds, log_callback=log_callback)
                finally:
                    self._is_healing_retry = False

        # If pytest didn't report exact numbers (e.g. execution error)
        if total == 0 and exit_code == 0:
            passed = 1
            total = 1

        success = exit_code == 0 and failed == 0 and errors == 0

        return ExecutionResult(
            success=success,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=duration,
            command_executed=" ".join(command),
            exit_code=exit_code,
            stdout=full_stdout,
            stderr=full_stderr,
            test_items=test_items,
        )

    def _prepare_command(self, test_path: str) -> tuple[List[str], dict]:
        """Prepares the execution command and environment."""
        lang = self.profile.primary_language.lower()
        env = os.environ.copy()

        # Add project root to PYTHONPATH so imports work without installation
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{self.project_root}{os.pathsep}{existing_pythonpath}"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        if "python" in lang:
            # Use current python executable to run pytest
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "-o",
                "python_files=test_*.py *_test.py",
            ]
            return cmd, env
        elif "javascript" in lang or "typescript" in lang:
            cmd = ["npm", "test", "--", test_path]
            return cmd, env
        elif "go" in lang:
            cmd = ["go", "test", "-v", f"./{test_path}/..."]
            return cmd, env
        else:
            # Fallback
            cmd = [sys.executable, "-m", "pytest", test_path, "-v"]
            return cmd, env

    def _parse_pytest_output(self, stdout: str) -> tuple[List[TestRunItem], int, int, int, int]:
        """Parses pytest verbose output into individual test run items and summary counts."""
        test_items: List[TestRunItem] = []
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        # Pattern for: tests/qa_agent/unit/test_foo.py::test_bar PASSED [ 50%]
        item_regex = re.compile(r"^(.*?)::(\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)", re.MULTILINE)

        for match in item_regex.finditer(stdout):
            suite_file = match.group(1).strip()
            test_name = match.group(2).strip()
            status = match.group(3).strip().upper()

            if status == "PASSED":
                passed += 1
            elif status == "FAILED":
                failed += 1
            elif status == "SKIPPED":
                skipped += 1
            elif status == "ERROR":
                errors += 1

            test_items.append(
                TestRunItem(
                    name=test_name,
                    suite=suite_file,
                    status=status,
                )
            )

        # Also search for summary line: = 3 passed, 1 failed, 1 skipped in 0.42s =
        summary_regex = re.compile(r"=+ (.*?) in \d+\.\d+s =+")
        summary_match = summary_regex.search(stdout)
        if summary_match and not test_items:
            summary_str = summary_match.group(1)
            p_match = re.search(r"(\d+)\s+passed", summary_str)
            f_match = re.search(r"(\d+)\s+failed", summary_str)
            s_match = re.search(r"(\d+)\s+skipped", summary_str)
            e_match = re.search(r"(\d+)\s+error", summary_str)

            if p_match:
                passed = int(p_match.group(1))
            if f_match:
                failed = int(f_match.group(1))
            if s_match:
                skipped = int(s_match.group(1))
            if e_match:
                errors = int(e_match.group(1))

        return test_items, passed, failed, skipped, errors
