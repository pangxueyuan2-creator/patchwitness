import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s+([^#\s]+)(?:\s+#\s*(\S+))?\s*$")


def repository_automation_files() -> list[Path]:
    return [ROOT / "action.yml", *sorted((ROOT / ".github" / "workflows").glob("*.yml"))]


def test_external_actions_are_pinned_to_immutable_commits() -> None:
    for path in repository_automation_files():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES.match(line)
            if match is None:
                continue
            target, version_comment = match.groups()
            if target.startswith(("./", "docker://")):
                continue
            action, separator, revision = target.rpartition("@")
            assert separator and action, f"{path}:{line_number}: malformed action reference"
            assert FULL_COMMIT_SHA.fullmatch(revision), (
                f"{path}:{line_number}: external action must be pinned to a full commit SHA"
            )
            assert version_comment and version_comment.startswith("v"), (
                f"{path}:{line_number}: retain the human-readable release tag as a comment"
            )


def test_checkout_steps_do_not_persist_credentials() -> None:
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/checkout@" not in line:
                continue
            indentation = len(line) - len(line.lstrip())
            end = index + 1
            while end < len(lines):
                candidate = lines[end]
                candidate_indent = len(candidate) - len(candidate.lstrip())
                if candidate_indent == indentation and candidate.lstrip().startswith("- "):
                    break
                end += 1
            block = "\n".join(lines[index:end])
            assert "persist-credentials: false" in block, (
                f"{path}:{index + 1}: checkout must drop the repository credential"
            )


def test_workflows_use_explicit_minimum_permissions_and_safe_pr_trigger() -> None:
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "\npermissions:\n" in text.split("\njobs:\n", maxsplit=1)[0], (
            f"{path}: declare workflow permissions before jobs"
        )
        assert "pull_request_target" not in text
        assert "secrets." not in text


def test_common_local_secret_files_are_ignored() -> None:
    ignored = set((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
    expected = {".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", ".pypirc"}
    assert expected <= ignored
