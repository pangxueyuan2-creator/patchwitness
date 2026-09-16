import json
import os
from pathlib import Path

import pytest

from patchwitness import evidence
from patchwitness.cli import main
from patchwitness.evidence import EvidenceError, load_evidence, verify_evidence


def sample() -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": evidence.SCHEMA_VERSION,
        "tool": {}, "repository": {}, "contract": {}, "changes": [], "checks": [],
        "findings": [], "summary": {"status": "pass"}, "captured_at": "fixture",
        "extensions": {},
    }
    value["payload_sha256"] = evidence._digest(value)
    return value


def test_valid_file_and_exact_byte_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "passport.json"
    content = json.dumps(sample()).encode()
    path.write_bytes(content)
    monkeypatch.setattr(evidence, "MAX_EVIDENCE_BYTES", len(content))
    assert verify_evidence(load_evidence(path)).status == "pass"
    path.write_bytes(content + b" ")
    with pytest.raises(EvidenceError, match="byte limit"):
        load_evidence(path)


@pytest.mark.parametrize("prefix", [
    '"summary":{"status":"fail"},',
    '"extensions":{"answer":0,"answer":1},',
])
def test_duplicate_keys_never_verify(tmp_path: Path, prefix: str) -> None:
    path = tmp_path / "ambiguous.json"
    path.write_text("{" + prefix + json.dumps(sample())[1:], encoding="utf-8")
    with pytest.raises(EvidenceError, match="duplicate JSON key"):
        verify_evidence(load_evidence(path))


@pytest.mark.parametrize("raw", [
    b"\xff", b'{"a":NaN}', b'{"a":Infinity}', b"[" * 2000 + b"0" + b"]" * 2000,
])
def test_malformed_input_returns_cli_error_without_traceback(
    tmp_path: Path, raw: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(raw)
    assert main(["verify", str(path)]) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "ok: True" not in captured.out


def test_directory_rejected(tmp_path: Path) -> None:
    with pytest.raises(EvidenceError, match="regular"):
        load_evidence(tmp_path)


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_non_finite_json_numbers_are_rejected(tmp_path: Path, number: str) -> None:
    path = tmp_path / "nonfinite.json"
    path.write_text('{"extensions":{"score":' + number + '}}', encoding="utf-8")
    with pytest.raises(EvidenceError, match="non-finite"):
        load_evidence(path)


def test_symlink_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text(json.dumps(sample()), encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(EvidenceError, match="regular"):
        load_evidence(link)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_fifo_rejected_without_waiting_for_writer(tmp_path: Path) -> None:
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(EvidenceError, match="regular"):
        load_evidence(fifo)


def test_path_replaced_before_open_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "passport.json"
    replacement = tmp_path / "replacement.json"
    path.write_text(json.dumps(sample()), encoding="utf-8")
    replacement.write_text(json.dumps(sample()), encoding="utf-8")
    original_open = os.open

    def racing_open(name: object, flags: int, *args: object, **kwargs: object) -> int:
        replacement.replace(path)
        return original_open(name, flags, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(EvidenceError, match="changed"):
        load_evidence(path)


def test_content_modified_during_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "passport.json"
    path.write_text(json.dumps(sample()), encoding="utf-8")
    original_read = os.read
    changed = False

    def racing_read(descriptor: int, length: int) -> bytes:
        nonlocal changed
        result = original_read(descriptor, length)
        if not changed:
            changed = True
            path.write_bytes(b"different")
        return result

    monkeypatch.setattr(os, "read", racing_read)
    with pytest.raises(EvidenceError, match="changed"):
        load_evidence(path)


def test_file_growth_cannot_exceed_read_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "passport.json"
    path.write_bytes(b"{}")
    monkeypatch.setattr(evidence, "MAX_EVIDENCE_BYTES", 20)
    original_read = os.read
    requested: list[int] = []

    def growing_read(descriptor: int, length: int) -> bytes:
        requested.append(length)
        with path.open("ab") as writer:
            writer.write(b" " * 100)
        return original_read(descriptor, length)

    monkeypatch.setattr(os, "read", growing_read)
    with pytest.raises(EvidenceError, match="byte limit"):
        load_evidence(path)
    assert sum(requested) == 21
