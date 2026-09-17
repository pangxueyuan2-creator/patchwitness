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
separate integration check. Invocation-success semantics are unchanged here.

References:
- [SARIF 2.1.0 artifact locations, section 3.4](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html)
- [GitHub SARIF support and source roots](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/sarif-support)
