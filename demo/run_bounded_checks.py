"""Exercise bounded checks through the real CLI without modifying the source tree."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(argv: list[str], cwd: Path, env: dict[str, str], expected: int = 0) -> str:
    result = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=30, check=False,
    )
    if result.returncode != expected:
        raise RuntimeError("synthetic bounded-check demo returned an unexpected exit code")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", action="store_true", help="use only the installed package")
    args = parser.parse_args()
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if not args.installed:
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    results = []
    with tempfile.TemporaryDirectory(prefix="patchwitness-capture-demo-") as directory:
        workspace = Path(directory)
        repo = workspace / "subject"
        repo.mkdir()
        (repo / "check.py").write_text(
            "import sys\nsys.stdout.buffer.write(b'x' * int(sys.argv[1]))\n",
            encoding="utf-8",
        )
        for name, size in (("quiet", 16), ("overflow", 1_048_577)):
            (repo / f"{name}.toml").write_text(
                'version = 1\n[policy]\nrequire_tests = true\n'
                f'[[checks]]\nid = "check"\ncommand = "python check.py {size}"\n'
                'required = true\ntimeout_seconds = 5\n', encoding="utf-8",
            )
        for argv in (
            ["init", "-b", "main"], ["config", "user.name", "Synthetic Demo"],
            ["config", "user.email", "demo@example.invalid"],
            ["add", "."], ["commit", "-m", "synthetic trusted base"],
        ):
            run(["git", *argv], repo, env)
        for clean_room in (False, True):
            for name, expected in (("quiet", 0), ("overflow", 1)):
                output = workspace / f"{name}-{clean_room}.json"
                argv = [
                    sys.executable, "-m", "patchwitness", "--json", "gate",
                    "--policy-ref", "HEAD", "--contract", f"{name}.toml",
                    "--output", str(output),
                ]
                if clean_room:
                    argv.append("--clean-room")
                run(argv, repo, env, expected)
                run([sys.executable, "-m", "patchwitness", "verify", str(output)], repo, env)
                pack = json.loads(output.read_text(encoding="utf-8"))
                if pack["summary"]["status"] != ("pass" if expected == 0 else "fail"):
                    raise RuntimeError("synthetic bounded-check demo has inconsistent evidence")
                results.append({
                    "case": name, "clean_room": clean_room, "gate_exit": expected,
                    "check_exit": pack["checks"][0]["exit_code"], "integrity_verified": True,
                })
    summary = {"synthetic": True, "installed": args.installed, "cases": results}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
