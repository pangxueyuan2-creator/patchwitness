import subprocess
from pathlib import Path

from patchwitness.cleanroom import clean_room


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_clean_room_materializes_tracked_and_untracked_changes(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    (tmp_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("NEW = True\n", encoding="utf-8")

    with clean_room(tmp_path, "HEAD") as verifier:
        assert (verifier / "app.py").read_text(encoding="utf-8") == "VALUE = 2\n"
        assert (verifier / "new.py").read_text(encoding="utf-8") == "NEW = True\n"
    assert not list(tmp_path.parent.glob("patchwitness-cleanroom-*"))

