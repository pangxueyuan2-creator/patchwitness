# Exact-subject Safe Delivery evidence

`patchwitness.safe_delivery` composes reports from explicitly pinned producers.
It is a library boundary, with a local integration demonstration; it does not
introduce a new CLI, repository, remote collector, or automatic merge authority.

Each `ComponentEvidence` binds a repository identity, exact base/head Git SHA,
changed-file manifest digest, reviewer-owned policy digest, producer name and
40-character producer Git revision. The caller supplies its own trusted producer
pin map independently of candidate-controlled files. A producer's details digest
is an assertion until an adapter has obtained and hashed those details.

The report covers API, dependencies, tests, complexity, privacy, artifacts,
policy, execution, CI and review. Decision precedence is:

1. `FAIL`: a known unsafe result, a different subject or an untrusted producer pin.
2. `UNKNOWN`: missing or incomplete required evidence; incomplete `PASS` is downgraded.
3. `REVIEW_REQUIRED`: evidence needs review before progressing.
4. `PASS`: every required component supplied complete, matching evidence and passed.

At the `pr` stage, absent hosted CI or human review requests review. This cannot
authorize merge or release; the `merge` and `release` stages require that evidence.
PR-stage dependencies may require review while the impact planner safely expands
to the full suite. Static AST completeness never establishes runtime completeness.

Rule identifiers `SD001` through `SD005` mean missing evidence, subject mismatch,
producer pin mismatch, incomplete pass and non-passing component respectively.
JSON, SARIF and the Markdown summary all retain non-passing results. The verifier
reconstructs the report's decision and checks the exact schema and digest. Merely
rehashing a forged overall pass or inserting raw fields does not make it valid.

## Local nine-component demonstration

Run `scripts/demo_safe_delivery.py` from a reviewed PatchWitness checkout with
Python 3.11+ and Node 24 (including `node:module.stripTypeScriptTypes`). Its trusted
runtime needs TaskToPR's declared Python dependencies and PyYAML already available.
The demonstration does not install packages or obtain credentials.

Create a **reviewer-controlled** JSON pin file outside the candidate repository:

```json
{
  "tasktopr": {"repository": "/reviewed/tasktopr", "revision": "<exact 40-character Git SHA>"},
  "patchwitness": {"repository": "/reviewed/patchwitness", "revision": "<exact 40-character Git SHA>"},
  "code-api-surface": {"repository": "/reviewed/code-api-surface", "revision": "<exact 40-character Git SHA>"},
  "code-import-map": {"repository": "/reviewed/code-import-map", "revision": "<exact 40-character Git SHA>"},
  "code-test-impact": {"repository": "/reviewed/code-test-impact", "revision": "<exact 40-character Git SHA>"},
  "code-complexity-budget": {"repository": "/reviewed/code-complexity-budget", "revision": "<exact 40-character Git SHA>"},
  "repo-privacy-guard": {"repository": "/reviewed/repo-privacy-guard", "revision": "<exact 40-character Git SHA>"},
  "artifact-fence": {"repository": "/reviewed/artifact-fence", "revision": "<exact 40-character Git SHA>"},
  "rule-relay": {"repository": "/reviewed/rule-relay", "revision": "<exact 40-character Git SHA>"}
}
```

```text
python scripts/demo_safe_delivery.py --pins reviewed-pins.json --output new-demo-directory
```

All nine pins are mandatory. The entry point and materializer source must match
the pinned PatchWitness commit, allowing only Python's universal-newline
equivalence for Windows Git checkouts. Tool source comes from exact Git objects, never
from a possibly dirty tool worktree. The materializer rejects symlinks, gitlinks,
nonportable paths and budgets exceeded; it never invokes target code. A source
manifest and tool provenance are recorded. Node strips the pinned Rule Relay
TypeScript source into a temporary directory; its version, transformation and
transformed source digest are retained. No npm lifecycle scripts run.

The fixed benign fixture performs actual intake, deterministic model response
validation, safe patching, TaskToPR tests, local commit, static API/import/impact/
complexity analysis, strict privacy scan, Artifact Fence fail-closed workflow
scan, Rule Relay instruction discovery, separate exact-head full-suite tests,
PatchWitness scope checks and report composition. The model response is a
deterministic fixture, not a hosted model inference. TaskToPR's `no_pr` receipt
retains a null tested HEAD; the separate post-commit test record binds the actual
commit. Nothing pretends that an uncommitted run verified a commit.

The benign result is `REVIEW_REQUIRED`. The analyzer cannot establish arbitrary
runtime imports, Rule Relay does not authorize the meaning of instructions,
Artifact Fence does not yet attest a generated publication manifest, and there
is no hosted CI or human approval on this local fixture. Impact uncertainty
selects and runs the full fixed test inventory.

The unsafe fixture is refused at TaskToPR's protected-plan boundary. A separately
constructed unsafe local commit then exercises downstream workflow, API and
privacy checks. Its unified result must be `FAIL`. The credential-shaped text is
a deliberately invalid public fixture; no real credential is used. No workflow
is executed. No fixture is pushed and no hosted PR or CI result is fabricated.

## Trust and product limits

`patchwitness.hosted_evidence` normalizes explicitly supplied collector snapshots.
CI policy pins both check name and GitHub App ID, considers the latest run ID,
and rejects stale heads; queued, missing, truncated, neutral and skipped checks
cannot pass. Review policy requires exact-head non-author approvals and no
unresolved threads or requests for changes. Inputs and the actual selected check
or approval policy are bound into the details digest. The caller still must
authenticate the collector, its repository/PR association, freshness, pagination
and reviewer eligibility. The module does not fetch GitHub or authenticate JSON.

Digests provide content identity and integrity, **not confidentiality, signatures
or producer authentication**. Anyone controlling both an envelope and its hash
can replace it. The policy/pin source, adapters, Python/Node runtime and local OS
are trusted. A materialized exact commit does not prove its code trustworthy.
Public composition reports contain bounded codes, counts and hashes. Detailed
demo files contain only the fixed synthetic source; do not reuse that exporter
for private user prompts, arbitrary paths or command output.

TaskToPR's child limits reduce timeout/output/process-tree risks; they are not a
filesystem or network sandbox. This entry point accepts no arbitrary target and
executes only reviewed fixed fixture tests. Remote delivery needs an authenticated
exact-head CI/review collector, isolated execution, reviewed semantic policy and
generated publication-manifest attestation before unattended release is suitable.

PatchWitness's protected-control-plane rule `PW003` is unchanged. This integration
does not provide a maintenance exception or a route around required checks.
