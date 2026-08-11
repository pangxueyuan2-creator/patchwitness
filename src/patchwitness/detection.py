"""Deterministic project-stack and verification-command detection."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DetectedCheck:
    id: str
    command: str
    ecosystem: str
    reason: str
    executable: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectProfile:
    ecosystems: tuple[str, ...]
    checks: tuple[DetectedCheck, ...]
    signals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystems": list(self.ecosystems),
            "checks": [check.to_dict() for check in self.checks],
            "signals": list(self.signals),
        }


def detect_project(root: Path) -> ProjectProfile:
    """Detect safe, repository-owned test commands without executing project code."""
    repository = root.resolve()
    ecosystems: list[str] = []
    checks: list[DetectedCheck] = []
    signals: list[str] = []

    _detect_python(repository, ecosystems, checks, signals)
    _detect_node(repository, ecosystems, checks, signals)
    _detect_file_ecosystem(
        repository,
        ecosystems,
        checks,
        signals,
        marker="go.mod",
        ecosystem="Go",
        check=DetectedCheck("go-tests", "go test ./...", "Go", "go.mod", "go"),
    )
    _detect_file_ecosystem(
        repository,
        ecosystems,
        checks,
        signals,
        marker="Cargo.toml",
        ecosystem="Rust",
        check=DetectedCheck(
            "rust-tests", "cargo test --workspace", "Rust", "Cargo.toml", "cargo"
        ),
    )
    _detect_dotnet(repository, ecosystems, checks, signals)
    _detect_file_ecosystem(
        repository,
        ecosystems,
        checks,
        signals,
        marker="pom.xml",
        ecosystem="Maven",
        check=DetectedCheck("maven-tests", "mvn test", "Maven", "pom.xml", "mvn"),
    )
    _detect_ruby(repository, ecosystems, checks, signals)
    _detect_php(repository, ecosystems, checks, signals)
    _detect_make(repository, ecosystems, checks, signals)

    return ProjectProfile(tuple(ecosystems), tuple(checks), tuple(signals))


def _detect_python(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
) -> None:
    markers = (
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "uv.lock",
    )
    present = [marker for marker in markers if (root / marker).is_file()]
    test_signal = _first_python_test_signal(root)
    if not present and test_signal is None:
        return
    ecosystems.append("Python")
    signals.extend(present)
    if test_signal is None:
        return
    signals.append(test_signal)
    if (root / "uv.lock").is_file():
        command, executable, manager = "uv run pytest", "uv", "uv.lock"
    elif (root / "poetry.lock").is_file():
        command, executable, manager = "poetry run pytest", "poetry", "poetry.lock"
    elif (root / "Pipfile").is_file():
        command, executable, manager = "pipenv run pytest", "pipenv", "Pipfile"
    else:
        command, executable, manager = "python -m pytest", "python", "Python"
    checks.append(
        DetectedCheck(
            "python-tests",
            command,
            "Python",
            f"{test_signal}; runner selected from {manager}",
            executable,
        )
    )


def _first_python_test_signal(root: Path) -> str | None:
    for marker in ("pytest.ini", "conftest.py"):
        if (root / marker).is_file():
            return marker
    for directory_name in ("tests", "test"):
        directory = root / directory_name
        if directory.is_dir() and next(directory.rglob("test*.py"), None) is not None:
            return f"{directory_name}/test*.py"
    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject is not None and _contains_key_or_value(pyproject, "pytest"):
        return "pytest in pyproject.toml"
    return None


def _detect_node(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
) -> None:
    package_path = root / "package.json"
    if not package_path.is_file():
        return
    ecosystems.append("Node.js")
    signals.append("package.json")
    package = _read_json(package_path)
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    test_script = scripts.get("test") if isinstance(scripts, dict) else None
    if not isinstance(test_script, str) or not test_script.strip():
        return
    normalized = test_script.lower().replace(" ", "")
    if "no test specified" in test_script.lower() or normalized in {"exit1", "exit 1"}:
        return
    if (root / "pnpm-lock.yaml").is_file():
        command, executable, manager = "pnpm test", "pnpm", "pnpm-lock.yaml"
    elif (root / "yarn.lock").is_file():
        command, executable, manager = "yarn test", "yarn", "yarn.lock"
    elif (root / "bun.lock").is_file() or (root / "bun.lockb").is_file():
        command, executable, manager = "bun test", "bun", "bun.lock"
    else:
        command, executable, manager = "npm test", "npm", "package.json"
    signals.append(manager)
    checks.append(
        DetectedCheck(
            "node-tests",
            command,
            "Node.js",
            f"scripts.test in package.json; runner selected from {manager}",
            executable,
        )
    )


def _detect_dotnet(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
) -> None:
    marker = next(root.glob("*.sln"), None) or next(root.glob("*.csproj"), None)
    if marker is None:
        return
    ecosystems.append(".NET")
    signals.append(marker.name)
    checks.append(
        DetectedCheck("dotnet-tests", "dotnet test", ".NET", marker.name, "dotnet")
    )


def _detect_ruby(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
) -> None:
    if not (root / "Gemfile").is_file():
        return
    ecosystems.append("Ruby")
    signals.append("Gemfile")
    if (root / ".rspec").is_file() or (root / "spec").is_dir():
        checks.append(
            DetectedCheck("ruby-tests", "bundle exec rspec", "Ruby", "spec/ or .rspec", "bundle")
        )
    elif (root / "Rakefile").is_file():
        checks.append(
            DetectedCheck("ruby-tests", "bundle exec rake test", "Ruby", "Rakefile", "bundle")
        )


def _detect_php(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
) -> None:
    composer_path = root / "composer.json"
    if not composer_path.is_file():
        return
    ecosystems.append("PHP")
    signals.append("composer.json")
    composer = _read_json(composer_path)
    scripts = composer.get("scripts", {}) if isinstance(composer, dict) else {}
    if isinstance(scripts, dict) and "test" in scripts:
        checks.append(
            DetectedCheck(
                "php-tests", "composer test", "PHP", "scripts.test in composer.json", "composer"
            )
        )


def _detect_make(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
) -> None:
    if checks:
        return
    makefile = next(
        (root / name for name in ("Makefile", "makefile") if (root / name).is_file()),
        None,
    )
    if makefile is None:
        return
    text = _read_text(makefile)
    if text is None or not any(line.startswith("test:") for line in text.splitlines()):
        return
    ecosystems.append("Make")
    signals.append(makefile.name)
    checks.append(DetectedCheck("make-tests", "make test", "Make", "test target", "make"))


def _detect_file_ecosystem(
    root: Path,
    ecosystems: list[str],
    checks: list[DetectedCheck],
    signals: list[str],
    *,
    marker: str,
    ecosystem: str,
    check: DetectedCheck,
) -> None:
    if not (root / marker).is_file():
        return
    ecosystems.append(ecosystem)
    signals.append(marker)
    checks.append(check)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _read_toml(path: Path) -> dict[str, Any] | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _contains_key_or_value(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(
            needle in str(key).lower() or _contains_key_or_value(item, needle)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key_or_value(item, needle) for item in value)
    return needle in str(value).lower()
