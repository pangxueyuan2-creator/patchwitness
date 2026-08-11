import json
from pathlib import Path

import pytest

from patchwitness.detection import detect_project


def test_detects_uv_python_tests(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.pytest.ini_options]\n', encoding="utf-8"
    )
    (tmp_path / "uv.lock").touch()
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_demo.py").write_text("def test_demo(): assert True\n", encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile.ecosystems == ("Python",)
    assert [(check.id, check.command) for check in profile.checks] == [
        ("python-tests", "uv run pytest")
    ]


def test_detects_pnpm_test_script(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "vitest run"}}), encoding="utf-8"
    )
    (tmp_path / "pnpm-lock.yaml").touch()

    profile = detect_project(tmp_path)

    assert profile.ecosystems == ("Node.js",)
    assert profile.checks[0].command == "pnpm test"
    assert profile.checks[0].executable == "pnpm"


@pytest.mark.parametrize(
    ("marker", "ecosystem", "command"),
    [
        ("go.mod", "Go", "go test ./..."),
        ("Cargo.toml", "Rust", "cargo test --workspace"),
        ("demo.sln", ".NET", "dotnet test"),
        ("pom.xml", "Maven", "mvn test"),
    ],
)
def test_detects_common_compiled_ecosystems(
    tmp_path: Path, marker: str, ecosystem: str, command: str
) -> None:
    (tmp_path / marker).touch()

    profile = detect_project(tmp_path)

    assert ecosystem in profile.ecosystems
    assert command in [check.command for check in profile.checks]


def test_invalid_or_placeholder_node_manifest_does_not_invent_a_check(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"echo Error: no test specified && exit 1"}}', encoding="utf-8"
    )

    profile = detect_project(tmp_path)

    assert profile.ecosystems == ("Node.js",)
    assert profile.checks == ()


@pytest.mark.parametrize(
    ("lockfile", "command", "executable"),
    [
        ("poetry.lock", "poetry run pytest", "poetry"),
        ("Pipfile", "pipenv run pytest", "pipenv"),
    ],
)
def test_detects_python_environment_managers(
    tmp_path: Path, lockfile: str, command: str, executable: str
) -> None:
    (tmp_path / lockfile).touch()
    (tmp_path / "pytest.ini").touch()

    profile = detect_project(tmp_path)

    assert profile.checks[0].command == command
    assert profile.checks[0].executable == executable


def test_python_project_without_test_signal_is_structural_only(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )

    profile = detect_project(tmp_path)

    assert profile.ecosystems == ("Python",)
    assert profile.checks == ()
    assert profile.to_dict()["ecosystems"] == ["Python"]


@pytest.mark.parametrize(
    ("files", "command"),
    [
        ({"Gemfile": "", ".rspec": ""}, "bundle exec rspec"),
        ({"Gemfile": "", "Rakefile": "task :test\n"}, "bundle exec rake test"),
        ({"composer.json": '{"scripts":{"test":"phpunit"}}'}, "composer test"),
        ({"Makefile": "test:\n\t@echo ok\n"}, "make test"),
    ],
)
def test_detects_declared_ruby_php_and_make_checks(
    tmp_path: Path, files: dict[str, str], command: str
) -> None:
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")

    profile = detect_project(tmp_path)

    assert command in [check.command for check in profile.checks]


def test_malformed_manifests_are_read_safely(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not-json", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[broken", encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile.ecosystems == ("Python", "Node.js")
    assert profile.checks == ()
