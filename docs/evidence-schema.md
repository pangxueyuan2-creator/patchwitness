# Evidence schema v1

The machine-readable schema is [schemas/evidence-v1.schema.json](../schemas/evidence-v1.schema.json).

## Top-level fields

| Field | Meaning |
|---|---|
| `schema_version` | `patchwitness.dev/evidence/v1` |
| `tool` | Producer name and version |
| `repository` | Base/head revisions, branch, remote, dirty state |
| `contract` | Normalized policy plus authoritative source |
| `changes` | Status, line counts, binary marker, before/after SHA-256 per path |
| `checks` | Command, required flag, exit/timing, timeout, redacted output evidence |
| `findings` | Stable rule ID, severity, value-free message and optional location |
| `summary` | Gate status and aggregate counts |
| `captured_at` | UTC capture timestamp |
| `extensions` | Impact, analyzer, verification, and environment namespaces |
| `payload_sha256` | SHA-256 over canonical JSON excluding this field |

## Canonicalization

PatchWitness serializes the unsigned object as UTF-8 JSON with keys sorted, no insignificant
whitespace, and Unicode retained. SHA-256 is computed over those bytes. `patchwitness verify`
reconstructs the same representation and uses constant-time digest comparison.

The digest answers: **has this normalized payload changed?** It does not answer: **who produced or
approved it?** Bind the JSON artifact to a CI identity with GitHub artifact attestations, Sigstore,
or your organization's signing system when authentication is required.

## Offline file input

`verify`, `report`, and other evidence-file consumers accept regular, non-symlink
UTF-8 JSON files up to 16 MiB. Duplicate keys (including nested objects), non-finite
numbers and unreadable or excessively nested JSON are rejected. Reads stop at the
byte budget even if a file grows; descriptor identity, size and modification-time
checks reject observed replacement or mutation during capture. These checks are
best-effort race detection, not an atomic snapshot or a hostile-filesystem sandbox.
Copy a symlink target to an ordinary file before verification. Oversized artifacts
must be regenerated with a smaller evidence scope; do not truncate hashed content.
Rejected inputs return CLI exit 2, never an integrity success. The v1 digest format
and valid ordinary evidence files remain unchanged.

## Privacy

Source content and full patches are not included. Check output is redacted and truncated; its stored
hash is calculated after redaction. Secret findings never copy the matched value.
