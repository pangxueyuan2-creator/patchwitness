import os
from pathlib import Path

import pytest

from patchwitness import passport, tasktopr

LOADERS = [
    (passport.load_passport, passport, "MAX_PASSPORT_BYTES", passport.PassportError),
    (tasktopr.load_tasktopr_handoff, tasktopr, "MAX_HANDOFF_BYTES", tasktopr.TaskToPREvidenceError),
]


@pytest.mark.parametrize("loader,module,budget,error", LOADERS)
def test_growing_input_stops_reading_at_budget(
    tmp_path, monkeypatch, loader, module, budget, error
):
    path = tmp_path / "growing.json"
    path.write_bytes(b"{}")
    monkeypatch.setattr(module, budget, 2)
    original_read = os.read
    original_read_bytes = Path.read_bytes
    grown = False
    captured = []

    def grow():
        nonlocal grown
        if not grown:
            grown = True
            with path.open("ab") as writer:
                writer.write(b" " * 128)

    # Schedule the same real-file growth after stat on both the historical
    # whole-file reader and the descriptor reader. Assert actual bytes retained.
    def legacy_read(self):
        grow()
        data = original_read_bytes(self)
        captured.append(len(data))
        return data

    def descriptor_read(fd, count):
        grow()
        data = original_read(fd, count)
        captured.append(len(data))
        return data

    monkeypatch.setattr(Path, "read_bytes", legacy_read)
    monkeypatch.setattr(os, "read", descriptor_read)
    with pytest.raises(error, match="byte budget"):
        loader(path)
    assert sum(captured) <= 3  # two-byte budget plus a single overflow probe


def test_handoff_replacement_with_same_size_and_mtime_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "handoff.json"
    replacement = tmp_path / "replacement.json"
    path.write_bytes(b"{}")
    replacement.write_bytes(b"{}")
    before = path.stat()
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
    original_read = os.read
    original_read_bytes = Path.read_bytes
    replaced = False

    def replace():
        nonlocal replaced
        if not replaced:
            replaced = True
            replacement.replace(path)

    def legacy_read(self):
        data = original_read_bytes(self)
        replace()
        return data

    def descriptor_read(fd, count):
        data = original_read(fd, count)
        replace()
        return data

    monkeypatch.setattr(Path, "read_bytes", legacy_read)
    monkeypatch.setattr(os, "read", descriptor_read)
    with pytest.raises(tasktopr.TaskToPREvidenceError, match=r"changed|unable"):
        tasktopr.load_tasktopr_handoff(path)


@pytest.mark.parametrize("loader,module,budget,error", LOADERS)
def test_deep_integration_json_is_a_domain_error(tmp_path, loader, module, budget, error):
    path = tmp_path / "deep.json"
    depth = 10_000
    path.write_bytes(b"[" * depth + b"0" + b"]" * depth)
    # Decoder nesting limits differ across supported interpreters. Either parser
    # rejection or root-type rejection must remain the public domain error.
    with pytest.raises(error):
        loader(path)


@pytest.mark.parametrize("loader,module,budget,error", LOADERS)
@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_integration_fifo_is_rejected_without_waiting(tmp_path, loader, module, budget, error):
    path = tmp_path / "fifo"
    os.mkfifo(path)
    with pytest.raises(error, match="regular"):
        loader(path)
