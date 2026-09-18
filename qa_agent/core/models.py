"""Data models for QA Agent."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestType(str, Enum):
    __test__ = False
    UNIT = "unit"
    API = "api"
    E2E = "e2e"



class EndpointInfo(BaseModel):
    method: str = "GET"
    path: str
    handler_name: str
    file_path: str
    line_number: Optional[int] = None
    parameters: List[str] = Field(default_factory=list)


class FunctionInfo(BaseModel):
    name: str
    file_path: str
    line_number: Optional[int] = None
    parameters: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    is_async: bool = False


class SourceFileInfo(BaseModel):
    relative_path: str
    language: str
    line_count: int = 0
    size_bytes: int = 0
    functions: List[FunctionInfo] = Field(default_factory=list)
    endpoints: List[EndpointInfo] = Field(default_factory=list)


class FileNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    children: Optional[List["FileNode"]] = None


FileNode.model_rebuild()


class ProjectProfile(BaseModel):
    project_name: str
    root_path: str
    primary_language: str
    detected_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    existing_test_runner: Optional[str] = None
    file_count: int = 0
    total_lines: int = 0
    file_tree: List[FileNode] = Field(default_factory=list)
    endpoints: List[EndpointInfo] = Field(default_factory=list)
    functions: List[FunctionInfo] = Field(default_factory=list)
    source_files: List[SourceFileInfo] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class TestPlanItem(BaseModel):
    id: str
    title: str
    test_type: TestType
    target_file: str
    target_symbol: Optional[str] = None
    description: str
    test_cases: List[str] = Field(default_factory=list)


class TestPlan(BaseModel):
    project_name: str
    primary_language: str
    recommended_framework: str
    summary: str
    items: List[TestPlanItem] = Field(default_factory=list)


class GeneratedTestFile(BaseModel):
    relative_path: str
    content: str
    test_type: TestType
    target_source_file: Optional[str] = None


class TestRunItem(BaseModel):
    name: str
    status: str  # "PASSED", "FAILED", "SKIPPED", "ERROR"
    duration: float = 0.0
    error_message: Optional[str] = None
    suite: Optional[str] = None


class ExecutionResult(BaseModel):
    success: bool
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    command_executed: str = ""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    test_items: List[TestRunItem] = Field(default_factory=list)
    report_markdown: str = ""
    report_html: str = ""
