"""Exercise the batch protocol without relying on platform-dependent pipe sizes."""

import hashlib
import io
from pathlib import Path
from unittest.mock import Mock

import pytest

from patchwitness.git import GitError, _batch_git_blob_sha256, _is_binary


def test_batch_alternates_requests_and_reads_bounded_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b"a" * 200_000
    record = b"a" * 40 + b" blob 200000\n" + body + b"\n"
    waiting = False

    class Reader(io.BytesIO):
        def readline(self, size: int = -1) -> bytes:
            nonlocal waiting
            waiting = False
            return super().readline(size)

        def read(self, size: int = -1) -> bytes:
            assert 0 <= size <= 65_536, "blob content must be consumed in bounded chunks"
            return super().read(size)

    def write(query: bytes) -> int:
        nonlocal waiting
        assert not waiting, "read the response before writing the next request"
        waiting = True
        return len(query)

    process = Mock()
    process.stdin.write.side_effect = write
    process.stdout = Reader(record * 2)
    process.wait.return_value = 0
    process.poll.return_value = 0
    monkeypatch.setattr("patchwitness.git.subprocess.Popen", Mock(return_value=process))
    expected = hashlib.sha256(body).hexdigest()
    assert _batch_git_blob_sha256(tmp_path, "HEAD", ["first", "second"]) == {
        "first": expected, "second": expected,
    }
    assert process.stdin.write.call_count == 2
    assert process.stdout.closed


@pytest.mark.parametrize("payload", [b"", b"invalid\n", b"a blob bad\n", b"a blob 3\nab",
                                     b"a blob 1\naX", b"a tree 3\nab", b"invalid submodule\n"])
def test_invalid_batch_frames_fail_and_close_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes,
) -> None:
    process = Mock()
    process.stdin = io.BytesIO()
    process.stdout = io.BytesIO(payload)
    process.poll.return_value = None
    process.wait.return_value = 0
    monkeypatch.setattr("patchwitness.git.subprocess.Popen", Mock(return_value=process))
    with pytest.raises(GitError):
        _batch_git_blob_sha256(tmp_path, "HEAD", ["file"])
    assert process.stdin.closed and process.stdout.closed
    process.kill.assert_called_once()


def test_binary_detection_reads_only_the_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "large.bin"
    path.write_bytes(b"\0" + b"a" * 16_384)
    monkeypatch.setattr(Path, "read_bytes", Mock(side_effect=AssertionError("unbounded read")))
    assert _is_binary(path) is True


@pytest.mark.parametrize("header", [b":module missing\n", b"a" * 40 + b" submodule\n",
                                    b"a" * 64 + b" submodule\n"])
def test_absent_submodule_objects_keep_the_following_blob_aligned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, header: bytes,
) -> None:
    process = Mock()
    process.stdin = io.BytesIO()
    process.stdout = io.BytesIO(header + b"b" * 40 + b" blob 3\nabc\n")
    process.wait.return_value = 0
    process.poll.return_value = 0
    monkeypatch.setattr("patchwitness.git.subprocess.Popen", Mock(return_value=process))
    assert _batch_git_blob_sha256(tmp_path, "", ["module", "file"]) == {
        "module": None, "file": hashlib.sha256(b"abc").hexdigest(),
    }
