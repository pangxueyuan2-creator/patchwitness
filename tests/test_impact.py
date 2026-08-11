from pathlib import Path

from patchwitness.impact import analyze_impact
from patchwitness.models import FileChange


def changed(path: str) -> FileChange:
    return FileChange(path, "M", 4, 1, False, "before", "after")


def test_python_transitive_blast_radius_and_cache(tmp_path: Path) -> None:
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "app" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "src" / "app" / "service.py").write_text(
        "from app.core import VALUE\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "test_service.py").write_text(
        "from app.service import VALUE\n", encoding="utf-8"
    )
    first = analyze_impact(tmp_path, [changed("src/app/core.py")])
    second = analyze_impact(tmp_path, [changed("src/app/core.py")])
    assert first["direct_dependents"] == ["src/app/service.py"]
    assert first["transitive_dependents"] == ["tests/test_service.py"]
    assert first["affected_tests"] == ["tests/test_service.py"]
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True


def test_javascript_relative_imports(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core.ts").write_text("export const value = 1\n", encoding="utf-8")
    (tmp_path / "src" / "app.ts").write_text("import { value } from './core'\n", encoding="utf-8")
    result = analyze_impact(tmp_path, [changed("src/core.ts")], use_cache=False)
    assert result["direct_dependents"] == ["src/app.ts"]
