"""Materialize explicitly reviewed Git source pins without consulting their worktrees.

This helper authenticates no reviewer and runs no producer. The caller owns its
destination directory and decides which exact commits are trusted to import later.
Returned roots live in a fresh child directory; no existing output is overwritten.
Only UTF-8, portable regular-file paths are supported. Git object bytes are copied
verbatim, without checkout filters, attributes, hooks, or executable permissions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

MAX_FILES = 10_000
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_PATH_BYTES = 1024
MAX_PATH_DEPTH = 32
MAX_DIRECTORIES = 10_000
MAX_TOOLS = 32
GIT_TIMEOUT_SECONDS = 30
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_DEVICES = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    f"{prefix}{suffix}" for prefix in ("com", "lpt") for suffix in "123456789¹²³"
}


class SourceMaterializationError(ValueError):
    """A pin, Git object, portable path, or resource boundary failed validation."""


@dataclass(frozen=True)
class SourcePin:
    repository: Path
    revision: str


@dataclass(frozen=True)
class MaterializedSource:
    root: Path
    provenance: dict[str, object]


@dataclass(frozen=True)
class _File:
    path: str
    mode: str
    oid: str
    size: int


def _git_environment() -> dict[str, str]:
    # Also drop loader hooks, shell startup settings, credentials and PATH.
    # Executable discovery uses the caller's trusted PATH before this boundary.
    essentials = {"systemroot", "windir", "systemdrive", "temp", "tmp", "tmpdir"}
    env = {key: value for key, value in os.environ.items() if key.casefold() in essentials}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_NO_LAZY_FETCH="1",
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
        GIT_PROTOCOL_FROM_USER="0",
        LC_ALL="C",
    )
    return env


def _git(
    executable: Path,
    repository: Path,
    arguments: list[str],
    limit: int,
    input_bytes: bytes | None = None,
) -> bytes:
    """Drain both pipes with independent caps, including while sending batch input."""
    command = [
        str(executable),
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "protocol.allow=never",
        "-C",
        str(repository),
        *arguments,
    ]
    chunks: list[bytes] = []
    failures: list[str] = []
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_environment(),
        shell=False,
    )

    def read_pipe(which: str, budget: int) -> None:
        pipe = getattr(process, which)
        consumed = 0
        try:
            while True:
                chunk = pipe.read(min(65536, budget - consumed + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > budget:
                    failures.append("Git output exceeded its byte budget")
                    process.kill()
                    break
                if which == "stdout":
                    chunks.append(chunk)
        except OSError:
            failures.append("Git output could not be read")
        finally:
            pipe.close()

    def write_input() -> None:
        assert process.stdin is not None
        try:
            if input_bytes:
                process.stdin.write(input_bytes)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            failures.append("Git input was interrupted")

    threads = [
        threading.Thread(target=read_pipe, args=("stdout", limit), daemon=True),
        threading.Thread(target=read_pipe, args=("stderr", 32768), daemon=True),
        threading.Thread(target=write_input, daemon=True),
    ]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=GIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        failures.append("Git exceeded its time budget")
        process.kill()
        process.wait()
    finally:
        for thread in threads:
            thread.join(timeout=GIT_TIMEOUT_SECONDS)
    if failures or any(thread.is_alive() for thread in threads) or process.returncode:
        raise SourceMaterializationError(failures[0] if failures else "Git object read failed")
    return b"".join(chunks)


def _portable_path(raw: bytes) -> str:
    if not raw or len(raw) > MAX_PATH_BYTES:
        raise SourceMaterializationError("Invalid source path length")
    try:
        path = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceMaterializationError("Source path is not UTF-8") from exc
    if unicodedata.normalize("NFC", path) != path:
        raise SourceMaterializationError("Source path is not normalized")
    parts = path.split("/")
    if len(parts) > MAX_PATH_DEPTH:
        raise SourceMaterializationError("Source path depth exceeded")
    for part in parts:
        if (
            not part
            or part in {".", ".."}
            or part.casefold() == ".git"
            or part[-1:] in {".", " "}
            or len(part.encode("utf-8")) > 255
            or part.split(".")[0].casefold() in _DEVICES
            or any(
                char in '\\:<>"|?*' or unicodedata.category(char).startswith("C") for char in part
            )
        ):
            raise SourceMaterializationError("Source path is not a portable relative path")
    return path


def _inventory(raw: bytes) -> list[_File]:
    if raw and not raw.endswith(b"\0"):
        raise SourceMaterializationError("Malformed Git tree listing")
    records = raw.split(b"\0")[:-1]
    if len(records) > MAX_FILES:
        raise SourceMaterializationError("Source file count exceeded")
    files: list[_File] = []
    nodes: dict[str, tuple[str, bool]] = {}
    for record in records:
        try:
            metadata, path_bytes = record.split(b"\t", 1)
            mode, kind, oid, size_text = metadata.split()
            size = int(size_text)
        except (ValueError, TypeError) as exc:
            raise SourceMaterializationError("Malformed Git tree entry") from exc
        if mode not in (b"100644", b"100755") or kind != b"blob":
            raise SourceMaterializationError("Only tracked regular files are supported")
        if not re.fullmatch(rb"[0-9a-f]{40}", oid) or not 0 <= size <= MAX_FILE_BYTES:
            raise SourceMaterializationError("Invalid or oversized Git blob")
        path = _portable_path(path_bytes)
        parts = path.split("/")
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            is_file = index == len(parts)
            key = prefix.casefold()
            previous = nodes.get(key)
            if previous is not None and (previous[0] != prefix or previous[1] or is_file):
                raise SourceMaterializationError("Source paths alias or conflict")
            nodes[key] = (prefix, is_file)
            if len(nodes) > MAX_FILES + MAX_DIRECTORIES:
                raise SourceMaterializationError("Source tree node budget exceeded")
        files.append(_File(path, mode.decode("ascii"), oid.decode("ascii"), size))
    return files


def _check_directory(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise SourceMaterializationError("An absolute directory without traversal is required")
    for item in (path, *path.parents):
        if item.exists():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise SourceMaterializationError(
                    "Directory links or reparse points are unsupported"
                )
    if not path.is_dir():
        raise SourceMaterializationError("Directory does not exist")
    return path.resolve(strict=True)


def _source_pin(value: SourcePin | Mapping[str, object]) -> SourcePin:
    if isinstance(value, SourcePin):
        pin = value
    elif isinstance(value, Mapping) and set(value) == {"repository", "revision"}:
        repository, revision = value["repository"], value["revision"]
        if not isinstance(repository, (str, Path)) or not isinstance(revision, str):
            raise SourceMaterializationError("Invalid source pin fields")
        pin = SourcePin(Path(repository), revision)
    else:
        raise SourceMaterializationError("A repository and exact revision are required")
    if not isinstance(pin.revision, str) or not _SHA.fullmatch(pin.revision):
        raise SourceMaterializationError("Revision must be an exact lowercase 40-character Git SHA")
    return SourcePin(_check_directory(Path(pin.repository)), pin.revision)


def materialize_sources(
    pins: Mapping[str, SourcePin | Mapping[str, object]],
    destination: Path,
) -> dict[str, MaterializedSource]:
    """Read reviewed commit objects into a fresh child of an existing destination.

    File and byte budgets apply across all supplied pins. Missing objects, unsupported
    tree entries, ambiguous portable names, and any Git error fail the entire call.
    Nothing in a repository's working directory is read as producer source.
    The caller must keep the output directory exclusively owned during this call.
    """
    destination = _check_directory(Path(destination))
    if not isinstance(pins, Mapping) or not 1 <= len(pins) <= MAX_TOOLS:
        raise SourceMaterializationError("Between one and 32 reviewed pins are required")
    git_path = shutil.which("git")
    if not git_path:
        raise SourceMaterializationError("Git is unavailable")
    executable = Path(git_path).resolve(strict=True)
    if os.name == "nt" and executable.suffix.casefold() in {".cmd", ".bat"}:
        raise SourceMaterializationError("Git must not be a Windows shell shim")
    prepared: dict[str, tuple[SourcePin, str, list[_File]]] = {}
    names: set[str] = set()
    count = total = directory_count = 0
    for name, value in pins.items():
        if not isinstance(name, str) or not _NAME.fullmatch(name) or name.casefold() in names:
            raise SourceMaterializationError("Invalid or aliased tool name")
        _portable_path(name.encode("utf-8"))
        names.add(name.casefold())
        pin = _source_pin(value)
        if executable.is_relative_to(pin.repository):
            raise SourceMaterializationError("Git executable must be outside pinned repositories")
        commit = _git(
            executable, pin.repository, ["rev-parse", "--verify", f"{pin.revision}^{{commit}}"], 128
        )
        if commit.decode("ascii", errors="replace").strip() != pin.revision:
            raise SourceMaterializationError("Pin must identify a commit object directly")
        tree = _git(
            executable, pin.repository, ["rev-parse", "--verify", f"{pin.revision}^{{tree}}"], 128
        )
        tree_sha = tree.decode("ascii", errors="replace").strip()
        if not _SHA.fullmatch(tree_sha):
            raise SourceMaterializationError("Invalid Git tree identity")
        listing = _git(
            executable,
            pin.repository,
            ["ls-tree", "-rzl", "--full-tree", pin.revision],
            MAX_FILES * (MAX_PATH_BYTES + 128),
        )
        files = _inventory(listing)
        count += len(files)
        total += sum(file.size for file in files)
        directory_count += len(
            {
                "/".join(parts[:index])
                for file in files
                for parts in [file.path.split("/")]
                for index in range(1, len(parts))
            }
        )
        if count > MAX_FILES or total > MAX_TOTAL_BYTES or directory_count > MAX_DIRECTORIES:
            raise SourceMaterializationError("Combined source budget exceeded")
        prepared[name] = (pin, tree_sha, files)

    stage = Path(tempfile.mkdtemp(prefix="pinned-sources-", dir=destination))
    results: dict[str, MaterializedSource] = {}
    try:
        for name, (pin, tree_sha, files) in prepared.items():
            root = stage / name
            root.mkdir()
            data = _git(
                executable,
                pin.repository,
                ["cat-file", "--batch"],
                sum(file.size for file in files) + 128 * len(files),
                "".join(f"{file.oid}\n" for file in files).encode("ascii"),
            )
            offset = 0
            manifest: list[dict[str, object]] = []
            for file in files:
                end = data.find(b"\n", offset, offset + 128)
                expected = f"{file.oid} blob {file.size}".encode("ascii")
                if end < 0 or data[offset:end] != expected:
                    raise SourceMaterializationError("Git blob metadata changed or is missing")
                start = end + 1
                content = data[start : start + file.size]
                offset = start + file.size + 1
                if len(content) != file.size or data[offset - 1 : offset] != b"\n":
                    raise SourceMaterializationError("Truncated Git blob")
                identity = hashlib.sha1(
                    f"blob {len(content)}\0".encode("ascii") + content,
                    usedforsecurity=False,
                ).hexdigest()
                if identity != file.oid:
                    raise SourceMaterializationError("Git blob content does not match its identity")
                target = root.joinpath(*file.path.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                _check_directory(target.parent)
                with target.open("xb") as handle:
                    handle.write(content)
                manifest.append(
                    {
                        "path": file.path,
                        "mode": file.mode,
                        "git_blob": file.oid,
                        "size": file.size,
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
            if offset != len(data):
                raise SourceMaterializationError("Unexpected extra Git blob data")
            manifest_bytes = json.dumps(
                sorted(manifest, key=lambda item: str(item["path"])),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
            results[name] = MaterializedSource(
                root,
                {
                    "schema_version": 1,
                    "tool": name,
                    "git_revision": pin.revision,
                    "git_tree": tree_sha,
                    "file_count": len(files),
                    "total_bytes": sum(file.size for file in files),
                    "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                    "repository_path_sha256": hashlib.sha256(
                        str(pin.repository).encode()
                    ).hexdigest(),
                    "source": "git_commit_objects",
                    "execution": "none",
                },
            )
    except BaseException:
        # Only this newly created directory may be removed; never an existing source/output.
        checked = _check_directory(stage)
        if checked.parent != destination or not checked.name.startswith("pinned-sources-"):
            raise SourceMaterializationError("Unsafe cleanup directory") from None
        shutil.rmtree(checked)
        raise
    return results
