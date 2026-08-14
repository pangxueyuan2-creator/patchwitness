import json
from pathlib import Path

from patchwitness.benchmark import run_benchmark

ROOT = Path(__file__).parents[1]


def test_required_open_source_files_exist() -> None:
    required = (
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "CHANGELOG.md",
        "ROADMAP.md",
        "PROJECT_STATUS.md",
        ".github/workflows/ci.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "action.yml",
        "Dockerfile",
    )
    assert all((ROOT / path).is_file() for path in required)


def test_sdist_excludes_generated_uv_lockfile() -> None:
    ignored_paths = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "uv.lock" in ignored_paths


def test_evidence_schema_has_runtime_required_fields() -> None:
    schema = json.loads((ROOT / "schemas/evidence-v1.schema.json").read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert {
        "schema_version",
        "repository",
        "contract",
        "changes",
        "checks",
        "findings",
        "summary",
        "payload_sha256",
    } <= required


def test_benchmark_result_is_measured_not_placeholder() -> None:
    result = json.loads(
        (ROOT / "benchmarks/results/windows-python314.json").read_text(encoding="utf-8")
    )
    assert result["parameters"] == {
        "repository_files": 250,
        "changed_files": 50,
        "rounds": 7,
    }
    assert result["results_ms"]["impact_warm"]["median"] > 0


def test_benchmark_harness_returns_measured_values() -> None:
    result = run_benchmark(files=10, rounds=1)
    assert result["parameters"]["changed_files"] == 2
    assert result["results_ms"]["git_change_collection"]["median"] > 0
