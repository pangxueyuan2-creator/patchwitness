"""Embeddable facade for CI systems, agents, and developer platforms."""

from __future__ import annotations

from pathlib import Path

from patchwitness.config import load_contract
from patchwitness.evidence import capture_evidence, load_evidence, verify_evidence
from patchwitness.impact import analyze_impact
from patchwitness.models import EvidencePack


class PatchWitness:
    def __init__(self, root: Path | str = ".") -> None:
        self.root = Path(root).resolve()

    def capture(
        self,
        *,
        contract: Path | str = ".patchwitness.toml",
        base: str = "HEAD",
        execute_checks: bool = True,
    ) -> EvidencePack:
        path = Path(contract)
        if not path.is_absolute():
            path = self.root / path
        return capture_evidence(
            self.root,
            load_contract(path),
            base=base,
            execute_checks=execute_checks,
        )

    def verify(self, evidence: Path | str) -> EvidencePack:
        return verify_evidence(load_evidence(Path(evidence)))

    def impact(self, pack: EvidencePack) -> dict[str, object]:
        from patchwitness.models import FileChange

        changes = tuple(FileChange(**value) for value in pack.changes)
        return analyze_impact(self.root, changes)
