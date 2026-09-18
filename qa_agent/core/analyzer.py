"""Polyglot project analyzer for QA Agent.

Extracts architecture, languages, frameworks, endpoints, and key functions
from any uploaded codebase or directory.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from qa_agent.core.models import (
    EndpointInfo,
    FileNode,
    FunctionInfo,
    ProjectProfile,
    SourceFileInfo,
)

# Common directories and files to ignore during analysis
IGNORED_DIRS: Set[str] = {
    "qa_agent",
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".idea",
    ".vscode",
    "coverage",
    ".coverage",
    "target",
    "bin",
    "obj",
    ".turbo",
    ".cache",
    "vendor",
}

IGNORED_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".zip",
    ".tar",
    ".gz",
    ".pyc",
    ".pyo",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".lock",
}

# Mapping of file extensions to programming languages
EXTENSION_TO_LANG: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".cpp": "C++",
    ".c": "C",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
}


class ProjectAnalyzer:
    """Analyzes projects across multiple languages and architectures."""

    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise FileNotFoundError(f"Project directory not found: {self.root_path}")

    def analyze(self) -> ProjectProfile:
        """Runs complete inspection on the project directory."""
        file_tree = self._build_file_tree(self.root_path)
        all_files = self._collect_source_files(self.root_path)

        lang_counts: Dict[str, int] = {}
        source_file_infos: List[SourceFileInfo] = []
        all_endpoints: List[EndpointInfo] = []
        all_functions: List[FunctionInfo] = []
        dependencies: List[str] = []
        frameworks: Set[str] = set()
        existing_test_runner: Optional[str] = None
        total_lines = 0

        # Scan project manifests for dependencies and frameworks
        dependencies = self._extract_dependencies()
        frameworks.update(self._detect_frameworks(dependencies))

        for file_path in all_files:
            rel_path = str(file_path.relative_to(self.root_path)).replace("\\", "/")
            ext = file_path.suffix.lower()
            lang = EXTENSION_TO_LANG.get(ext, "Unknown")

            if lang != "Unknown":
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

            # Check if existing tests exist
            if any(test_keyword in rel_path.lower() for test_keyword in ["test", "spec", "_tests", "tests/"]):
                if not existing_test_runner:
                    if ext == ".py":
                        existing_test_runner = "pytest"
                    elif ext in [".js", ".ts"]:
                        existing_test_runner = "jest"

            # Parse content
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                line_count = len(lines)
                total_lines += line_count
                size_bytes = file_path.stat().st_size

                funcs: List[FunctionInfo] = []
                endpoints: List[EndpointInfo] = []

                if ext == ".py":
                    funcs, endpoints, detected_fw = self._parse_python_file(content, rel_path)
                    frameworks.update(detected_fw)
                elif ext in [".js", ".ts", ".jsx", ".tsx"]:
                    funcs, endpoints, detected_fw = self._parse_js_file(content, rel_path)
                    frameworks.update(detected_fw)
                elif ext == ".go":
                    funcs, endpoints, detected_fw = self._parse_go_file(content, rel_path)
                    frameworks.update(detected_fw)

                all_functions.extend(funcs)
                all_endpoints.extend(endpoints)

                source_file_infos.append(
                    SourceFileInfo(
                        relative_path=rel_path,
                        language=lang,
                        line_count=line_count,
                        size_bytes=size_bytes,
                        functions=funcs,
                        endpoints=endpoints,
                    )
                )
            except Exception:
                continue

        # Determine primary language
        primary_language = "General"
        if lang_counts:
            primary_language = max(lang_counts.items(), key=lambda x: x[1])[0]

        detected_languages = sorted(list(lang_counts.keys()))

        return ProjectProfile(
            project_name=self.root_path.name,
            root_path=str(self.root_path).replace("\\", "/"),
            primary_language=primary_language,
            detected_languages=detected_languages,
            frameworks=sorted(list(frameworks)),
            existing_test_runner=existing_test_runner,
            file_count=len(all_files),
            total_lines=total_lines,
            file_tree=file_tree,
            endpoints=all_endpoints,
            functions=all_functions,
            source_files=source_file_infos,
            dependencies=dependencies,
        )

    def _build_file_tree(self, current_dir: Path, max_depth: int = 4, depth: int = 0) -> List[FileNode]:
        """Builds a hierarchical tree of files and directories."""
        if depth > max_depth:
            return []

        nodes: List[FileNode] = []
        try:
            entries = sorted(list(current_dir.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            for entry in entries:
                if entry.name in IGNORED_DIRS or entry.name.startswith("."):
                    continue
                if entry.is_file() and entry.suffix.lower() in IGNORED_EXTENSIONS:
                    continue

                rel_path = str(entry.relative_to(self.root_path)).replace("\\", "/")

                if entry.is_dir():
                    children = self._build_file_tree(entry, max_depth, depth + 1)
                    nodes.append(
                        FileNode(
                            name=entry.name,
                            path=rel_path,
                            type="directory",
                            children=children,
                        )
                    )
                else:
                    nodes.append(
                        FileNode(
                            name=entry.name,
                            path=rel_path,
                            type="file",
                            size=entry.stat().st_size,
                        )
                    )
        except PermissionError:
            pass

        return nodes

    def _collect_source_files(self, current_dir: Path) -> List[Path]:
        """Collects all relevant source code files."""
        collected: List[Path] = []
        for root, dirs, files in os.walk(current_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in IGNORED_EXTENSIONS or file.startswith("."):
                    continue
                if ext in EXTENSION_TO_LANG or file in ["requirements.txt", "package.json", "Dockerfile"]:
                    collected.append(Path(root) / file)
        return collected

    def _extract_dependencies(self) -> List[str]:
        """Extracts declared dependencies from common manifest files."""
        deps: List[str] = []

        # Python requirements.txt
        req_file = self.root_path / "requirements.txt"
        if req_file.is_file():
            try:
                for line in req_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        deps.append(line.split("==")[0].split(">=")[0].split("<")[0].strip())
            except Exception:
                pass

        # Node package.json
        pkg_file = self.root_path / "package.json"
        if pkg_file.is_file():
            try:
                import json
                data = json.loads(pkg_file.read_text(encoding="utf-8"))
                for group in ["dependencies", "devDependencies"]:
                    if group in data:
                        deps.extend(list(data[group].keys()))
            except Exception:
                pass

        # Go go.mod
        gomod_file = self.root_path / "go.mod"
        if gomod_file.is_file():
            try:
                for line in gomod_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("require "):
                        parts = line.split()
                        if len(parts) >= 2:
                            deps.append(parts[1])
            except Exception:
                pass

        return sorted(list(set(deps)))

    def _detect_frameworks(self, dependencies: List[str]) -> Set[str]:
        """Detects frameworks from known dependencies."""
        fw: Set[str] = set()
        dep_lower = [d.lower() for d in dependencies]

        # Python
        if "fastapi" in dep_lower:
            fw.add("FastAPI")
        if "flask" in dep_lower:
            fw.add("Flask")
        if "django" in dep_lower:
            fw.add("Django")
        if "pytest" in dep_lower:
            fw.add("pytest")

        # JavaScript / TypeScript
        if "express" in dep_lower:
            fw.add("Express")
        if "next" in dep_lower:
            fw.add("Next.js")
        if "react" in dep_lower:
            fw.add("React")
        if "vue" in dep_lower:
            fw.add("Vue")
        if "jest" in dep_lower:
            fw.add("Jest")
        if "vitest" in dep_lower:
            fw.add("Vitest")
        if "playwright" in dep_lower or "@playwright/test" in dep_lower:
            fw.add("Playwright")

        return fw

    def _parse_python_file(self, content: str, rel_path: str) -> Tuple[List[FunctionInfo], List[EndpointInfo], Set[str]]:
        """Uses AST to extract Python functions and API routes."""
        funcs: List[FunctionInfo] = []
        endpoints: List[EndpointInfo] = []
        detected_fw: Set[str] = set()

        try:
            tree = ast.parse(content)
        except Exception:
            return funcs, endpoints, detected_fw

        for node in ast.walk(tree):
            # Functions and methods
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("__"):
                    params = [arg.arg for arg in node.args.args]
                    docstring = ast.get_docstring(node)
                    funcs.append(
                        FunctionInfo(
                            name=node.name,
                            file_path=rel_path,
                            line_number=node.lineno,
                            parameters=params,
                            docstring=docstring,
                            is_async=isinstance(node, ast.AsyncFunctionDef),
                        )
                    )

                # Check decorators for API routes (FastAPI / Flask / Django)
                for decorator in node.decorator_list:
                    # FastAPI / Flask: @app.get("/path"), @router.post("/path")
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        method = decorator.func.attr.upper()
                        if method in ["GET", "POST", "PUT", "DELETE", "PATCH", "ROUTE"]:
                            route_path = "/"
                            if decorator.args:
                                first_arg = decorator.args[0]
                                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                                    route_path = first_arg.value

                            endpoints.append(
                                EndpointInfo(
                                    method=method if method != "ROUTE" else "GET",
                                    path=route_path,
                                    handler_name=node.name,
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    parameters=[arg.arg for arg in node.args.args],
                                )
                            )
                            if "app" in getattr(decorator.func.value, "id", "") or "router" in getattr(decorator.func.value, "id", ""):
                                detected_fw.add("FastAPI")

        return funcs, endpoints, detected_fw

    def _parse_js_file(self, content: str, rel_path: str) -> Tuple[List[FunctionInfo], List[EndpointInfo], Set[str]]:
        """Extracts JS/TS functions and API routes using regex patterns."""
        funcs: List[FunctionInfo] = []
        endpoints: List[EndpointInfo] = []
        detected_fw: Set[str] = set()

        # Route matching: app.get('/api/users', ...), router.post('/login', ...)
        route_pattern = re.compile(
            r"""(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"`]([^'"`]+)['"`]\s*,\s*(?:async\s*)?(?:function\s*([a-zA-Z0-9_]*)|(?:\(([^\)]*)\)|([a-zA-Z0-9_]+))\s*=>|([a-zA-Z0-9_]+))""",
            re.IGNORECASE,
        )

        for match in route_pattern.finditer(content):
            method = match.group(1).upper()
            route_path = match.group(2)
            handler = match.group(3) or match.group(5) or match.group(6) or "anonymous_handler"
            endpoints.append(
                EndpointInfo(
                    method=method,
                    path=route_path,
                    handler_name=handler,
                    file_path=rel_path,
                )
            )
            detected_fw.add("Express")

        # Function matching: function foo(...) or const foo = (...) => ...
        func_pattern = re.compile(r"""(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)""")
        for match in func_pattern.finditer(content):
            name = match.group(1)
            params = [p.strip() for p in match.group(2).split(",") if p.strip()]
            funcs.append(
                FunctionInfo(
                    name=name,
                    file_path=rel_path,
                    parameters=params,
                )
            )

        return funcs, endpoints, detected_fw

    def _parse_go_file(self, content: str, rel_path: str) -> Tuple[List[FunctionInfo], List[EndpointInfo], Set[str]]:
        """Extracts Go functions and API routes using regex."""
        funcs: List[FunctionInfo] = []
        endpoints: List[EndpointInfo] = []
        detected_fw: Set[str] = set()

        # Gin / Chi / Echo: r.GET("/path", handler)
        route_pattern = re.compile(r"""\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["']([^"']+)["']\s*,\s*([a-zA-Z0-9_.]+)""")
        for match in route_pattern.finditer(content):
            endpoints.append(
                EndpointInfo(
                    method=match.group(1).upper(),
                    path=match.group(2),
                    handler_name=match.group(3),
                    file_path=rel_path,
                )
            )
            detected_fw.add("Go-Web")

        # func Name(args) ...
        func_pattern = re.compile(r"""func\s+(?:\([^)]+\)\s+)?([A-Z][a-zA-Z0-9_]*)\s*\(([^)]*)\)""")
        for match in func_pattern.finditer(content):
            name = match.group(1)
            params = [p.strip() for p in match.group(2).split(",") if p.strip()]
            funcs.append(
                FunctionInfo(
                    name=name,
                    file_path=rel_path,
                    parameters=params,
                )
            )

        return funcs, endpoints, detected_fw
