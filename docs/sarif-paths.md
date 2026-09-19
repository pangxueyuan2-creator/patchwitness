# SARIF filename identity

The unreleased URI-encoding fix preserves repository filenames when producing
`patchwitness report evidence.json --format sarif`. It does not change the gate
result, evidence schema, original finding paths, or evidence digest.

SARIF's `artifactLocation.uri` is a URI reference, not a raw filename. A literal
`#` must not become a fragment, `?` must not become a query, and a literal `%2F`
in a filename must not become a directory separator after URI decoding.

| Repository path | SARIF URI |
| --- | --- |
| `src/app.py` | `src/app.py` |
| `src/hash#part.py` | `src/hash%23part.py` |
| `src/space name.py` | `src/space%20name.py` |
| `src/literal%2Fname.py` | `src/literal%252Fname.py` |
| `scheme:file.py` | `scheme%3Afile.py` |

Consumers should resolve the URI using their normal URI library, decoding its
path once. Do not treat the SARIF URI string as an already-decoded filesystem
path. Non-ASCII characters are UTF-8 percent-encoded. Plain relative ASCII paths
keep their existing representation. Existing backslash separator normalization
is retained; this is not a change to Git path collection or literal-backslash
handling elsewhere in the tool.

On v0.3.0 the raw URI can identify the wrong location even when the original
Change Passport contains the correct filename. Keep that original evidence and
regenerate the report with the fixed revision when available. A valid report or
URI does not turn a policy failure into an approval.

Validation covers round-trip URI identity, report-file serialization, and a
real trusted-base Git/CLI fixture with a Unicode/hash/percent filename. These
are maintainer-run synthetic checks, not a claim of successful GitHub Code
Scanning upload or independent adoption. GitHub-hosted ingestion still needs a
separate integration check.

## Analysis completion is not gate approval (unreleased)

SARIF `runs[0].invocations[0].executionSuccessful` describes whether analysis
completed, not whether the proposed change should pass its policy. A completed
PatchWitness analysis can correctly detect violations and return a failing
Change Passport. Its SARIF report now has `executionSuccessful: true` while
`invocations[0].properties.gateStatus` explicitly retains `"fail"`. Passing
Passports retain `"pass"` in that property. Findings, severity, filename URIs and
the evidence digest remain unchanged.

This also applies to reported failed, timed-out, skipped or missing required
checks and observed source drift: these facts still reject the change. A
completed report is **not** a claim that verification checks passed or were
complete. Gate exit codes remain 0 for a passing policy result and 1 for a
failing result; reporting a valid failing Passport still exits 0. No historical
capture exit code is fabricated, because `capture` and `gate` have different
exit semantics.

Consumers that used `executionSuccessful` as a merge decision must instead use
`patchwitness gate` or inspect the verified Passport's `summary.status` under
their trusted policy. The additional `gateStatus` report property is convenient
for display, not an authenticated approval. Missing or unfamiliar statuses must
not be interpreted as `"pass"`. This native evidence-v1 renderer still rejects
unsupported statuses; the separate Safe Delivery `UNKNOWN`/`REVIEW_REQUIRED`
contract is unchanged.

The CLI verifies evidence integrity before exporting. Invalid JSON, a digest
mismatch, or an unsupported native status returns exit 2 before a report is
emitted or an existing report file is overwritten. An output write error also
returns exit 2; consumers must check that exit code rather than trust a leftover
report from an earlier run. A digest is not producer authentication, and this
change does not establish the trustworthiness of a supplied Passport.

Existing evidence can be re-exported with the fixed revision; no recapture or
evidence schema migration is required for this presentation-only change. Tests
exercise real trusted-policy Git/CLI cases, stdout/file output, check failures
and timeouts, rejected inputs and preservation of original evidence bytes. They
do not establish successful ingestion by a hosted SARIF consumer.

References:
- [SARIF 2.1.0 artifact locations, section 3.4](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html)
- [GitHub SARIF support and source roots](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/sarif-support)
- [SARIF invocation success, section 3.20.14](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html)
