# Launch readiness audit

Audit date: 2026-08-11. Scope: repository conversion and launch readiness, not core-engine redesign.

## Executive result

PatchWitness is ready for a controlled technical launch once the custom GitHub social preview is
uploaded and the maintainer approves the first public post. The repository now has a direct problem
statement, a real one-minute failure demo, a three-command try path, a release-asset installation
path, explicit differentiation from AI code review, and honest limitations.

## Audit

| Surface | Initial finding | Action taken | Current status |
|---|---|---|---|
| README: 20-second comprehension | Strong concept, but the first screen contained a generic sample and delayed the concrete proof. | Moved directly from problem to product, added “not another AI reviewer,” and placed the real failure demo above the fold. | Ready |
| Quick Start | Correct, but required installation and contract editing before seeing value. | Added a three-command, no-install demo and direct release-wheel installation. | Ready |
| Intuitive demo | No reproducible end-to-end scenario; displayed output was illustrative. | Added `demo/run_demo.py`, a committed real transcript/passport, visual terminal output, and an integration test. | Ready |
| GitHub Social Preview | Existing banner was 1280x360, not the recommended social-card shape. | Created and visually inspected `docs/assets/social-preview.png` at 1280x640 plus its editable SVG source. | Asset ready; GitHub upload pending |
| Release Notes | Professional but test count was stale and no immediate demo/install path existed. | Updated to the real test count, risk demo, wheel install, and explicit limitations. | Ready locally; sync with Release on push |
| Description | Accurate but generic. | Prepared a sharper trust-gate/Change Passport description. | Pending repository metadata update |
| Topics | Strong 16-topic baseline. | Prepared four additional discovery terms: `ai-security`, `llm-security`, `supply-chain-security`, `testing`. | Pending repository metadata update |
| Screenshot/GIF/terminal demo | Banner and Mermaid existed; no proof-oriented visual. | Added an exact terminal-style SVG based on a real execution and a social card. | Ready; GIF intentionally deferred |
| Architecture | Clear Mermaid diagram and dedicated architecture/threat-model docs already existed. | No redesign needed. | Ready |
| Examples | Python SDK example existed, but not a compelling user journey. | Added an end-to-end agent-risk example that needs only Git and Python. | Ready |
| FAQ | Important boundaries were spread across documents. | Added concise answers on AI review, correctness, supported agents, source upload, and integrations. | Ready |
| Badges | CI/release/license/runtime badges were useful. | Added a 60-second Demo badge linked to the proof section. | Ready |

## Why a static terminal visual instead of a GIF

The SVG loads immediately, remains sharp on high-DPI displays, exposes useful alt text, and can show
the exact verified output without video timing or compression. A GIF is worth adding only if real
launch feedback shows that an animated install-to-result path improves comprehension.

## 30-second conversion path

1. Tagline: independent evidence and policy gates for AI-generated changes.
2. Problem: the producer's summary is not independent evidence.
3. Differentiator: deterministic local trust gate, not another LLM reviewer.
4. Proof: tests pass while a protected CI change is blocked.
5. Trial: clone, enter directory, run one Python command.
6. Adoption: install the release wheel, initialize a contract, run against a trusted base.

## Remaining launch blockers

### Custom GitHub Social Preview upload

The finished image is `docs/assets/social-preview.png`. GitHub does not provide a supported `gh`
command or public REST endpoint for uploading a repository social preview. It must be uploaded from
**Repository Settings → General → Social preview** in a signed-in browser. Do not substitute a
different account.

### No external adoption evidence yet

The project still has no verified external user, integration, issue, PR, or release download. Launch
copy must continue to say “public alpha” and ask for technical feedback rather than claim adoption.

## Deliberately deferred

- PyPI publication: useful later, but release-wheel installation is sufficient for the first launch.
- Cryptographic signer identity/attestations: belongs on the roadmap, not in a documentation sprint.
- Additional language parsers: should be prioritized from real user repositories.
- Hosted dashboard or telemetry: unnecessary for a local-first launch and potentially harmful to the
  trust story.
