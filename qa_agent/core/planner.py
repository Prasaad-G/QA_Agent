"""Test Strategy Planner for QA Agent.

Analyzes a ProjectProfile to produce an organized test strategy covering
Unit, API, and E2E testing dimensions.
"""

from __future__ import annotations

from typing import List
from qa_agent.core.models import (
    ProjectProfile,
    TestPlan,
    TestPlanItem,
    TestType,
)


class TestPlanner:
    """Plans test cases based on project architecture and detected components."""
    __test__ = False


    def __init__(self, profile: ProjectProfile):
        self.profile = profile

    def create_plan(self, requested_types: List[TestType] | None = None) -> TestPlan:
        """Creates a comprehensive test plan for the requested test types."""
        if not requested_types:
            requested_types = [TestType.UNIT, TestType.API, TestType.E2E]

        items: List[TestPlanItem] = []
        counter = 1

        # Determine recommended framework
        recommended_framework = self._determine_framework()

        # 1. Plan Unit Tests
        if TestType.UNIT in requested_types:
            unit_items = self._plan_unit_tests(counter)
            items.extend(unit_items)
            counter += len(unit_items)

        # 2. Plan API Tests
        if TestType.API in requested_types:
            api_items = self._plan_api_tests(counter)
            items.extend(api_items)
            counter += len(api_items)

        # 3. Plan E2E Tests
        if TestType.E2E in requested_types:
            e2e_items = self._plan_e2e_tests(counter)
            items.extend(e2e_items)
            counter += len(e2e_items)

        summary = (
            f"Generated test plan with {len(items)} suites for {self.profile.project_name} "
            f"({self.profile.primary_language}). Target runner: {recommended_framework}."
        )

        return TestPlan(
            project_name=self.profile.project_name,
            primary_language=self.profile.primary_language,
            recommended_framework=recommended_framework,
            summary=summary,
            items=items,
        )

    def _determine_framework(self) -> str:
        lang = self.profile.primary_language.lower()
        if "python" in lang:
            return "pytest"
        elif "javascript" in lang or "typescript" in lang:
            if "vitest" in [f.lower() for f in self.profile.frameworks]:
                return "vitest"
            return "jest"
        elif "go" in lang:
            return "go test"
        elif "java" in lang:
            return "junit5"
        elif "c#" in lang or "csharp" in lang:
            return "dotnet test"
        elif "rust" in lang:
            return "cargo test"
        return "generic-runner"

    def _plan_unit_tests(self, start_id: int) -> List[TestPlanItem]:
        items: List[TestPlanItem] = []
        current_id = start_id

        # Group functions by file
        functions_by_file = {}
        for fn in self.profile.functions:
            functions_by_file.setdefault(fn.file_path, []).append(fn)

        # Cap unit suites for large projects to ensure fast HTTP response times
        MAX_UNIT_SUITES = 20
        sorted_files = sorted(functions_by_file.items(), key=lambda item: len(item[1]), reverse=True)[:MAX_UNIT_SUITES]

        for file_path, fns in sorted_files:
            fn_names = [fn.name for fn in fns[:6]]  # Take top functions per file
            cases = [
                f"Test happy path execution with valid arguments for {name}"
                for name in fn_names
            ]
            cases.append("Test edge cases: boundary values, None/null inputs, and type mismatches")
            cases.append("Verify error handling and exception raising on invalid states")

            items.append(
                TestPlanItem(
                    id=f"plan-unit-{current_id}",
                    title=f"Unit tests for {file_path}",
                    test_type=TestType.UNIT,
                    target_file=file_path,
                    target_symbol=", ".join(fn_names),
                    description=f"Unit verification of key functions and methods defined in {file_path}",
                    test_cases=cases,
                )
            )
            current_id += 1

        # Fallback if no specific functions extracted
        if not items and self.profile.source_files:
            target = self.profile.source_files[0].relative_path
            items.append(
                TestPlanItem(
                    id=f"plan-unit-{current_id}",
                    title=f"Core unit tests for {target}",
                    test_type=TestType.UNIT,
                    target_file=target,
                    description="Standard unit test suite covering exported logic and modules",
                    test_cases=[
                        "Validate component initialization and default parameters",
                        "Verify edge cases and expected return structures",
                    ],
                )
            )

        return items

    def _plan_api_tests(self, start_id: int) -> List[TestPlanItem]:
        items: List[TestPlanItem] = []
        current_id = start_id

        if self.profile.endpoints:
            # Group endpoints by resource/path prefix
            grouped_endpoints = {}
            for ep in self.profile.endpoints:
                prefix = ep.path.strip("/").split("/")[0] if ep.path.strip("/") else "root"
                grouped_endpoints.setdefault(prefix, []).append(ep)

            # Cap API suites to top 15 route groups for large projects
            MAX_API_SUITES = 15
            sorted_groups = list(grouped_endpoints.items())[:MAX_API_SUITES]

            for prefix, eps in sorted_groups:
                endpoints_desc = ", ".join([f"{ep.method} {ep.path}" for ep in eps[:5]])
                cases = []
                for ep in eps[:5]:
                    cases.append(f"Verify {ep.method} {ep.path} returns expected 200/201 response structure")
                    cases.append(f"Verify {ep.method} {ep.path} returns 400/422 on malformed or missing payload")

                target_file = eps[0].file_path
                items.append(
                    TestPlanItem(
                        id=f"plan-api-{current_id}",
                        title=f"API tests for /{prefix} endpoints",
                        test_type=TestType.API,
                        target_file=target_file,
                        target_symbol=endpoints_desc,
                        description=f"Integration and contract tests for endpoints: {endpoints_desc}",
                        test_cases=cases,
                    )
                )
                current_id += 1
        elif "fastapi" in [f.lower() for f in self.profile.frameworks] or "express" in [f.lower() for f in self.profile.frameworks]:
            # Framework detected even if endpoints list was sparse
            target = self.profile.source_files[0].relative_path if self.profile.source_files else "app"
            items.append(
                TestPlanItem(
                    id=f"plan-api-{current_id}",
                    title="API route integration tests",
                    test_type=TestType.API,
                    target_file=target,
                    description="HTTP endpoint status code and payload validation tests",
                    test_cases=[
                        "Verify health check / root route returns 200 OK",
                        "Verify error handlers return proper JSON error models",
                    ],
                )
            )

        return items

    def _plan_e2e_tests(self, start_id: int) -> List[TestPlanItem]:
        items: List[TestPlanItem] = []
        target = self.profile.source_files[0].relative_path if self.profile.source_files else "main"

        items.append(
            TestPlanItem(
                id=f"plan-e2e-{start_id}",
                title=f"End-to-End user flow test for {self.profile.project_name}",
                test_type=TestType.E2E,
                target_file=target,
                description="High-level workflow simulating complete user journey across components",
                test_cases=[
                    "Simulate full lifecycle: setup state -> execute actions -> verify final output",
                    "Verify system maintains data integrity across chained operations",
                    "Validate graceful failure and recovery on unexpected sequence interruption",
                ],
            )
        )
        return items
