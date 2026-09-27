# MCP input and Git evidence hardening (unreleased)

These changes apply to source after v0.3.0; installing the v0.3.0 release wheel
alone does not include them. The evidence-v1 schema, tool names, protocol version,
defaults, policy rules and runtime dependencies are unchanged.

## MCP callers: use declared JSON types

`patchwitness_capture` accepts `execute_checks` only as a JSON boolean. Omit the
field or send `false` for a structural capture; send `true` only when the caller
intends to run the configured checks. Strings (including `"false"`), numbers,
arrays, objects and `null` are rejected **before** the contract is loaded or any
check is executed. The same schema validation applies to all declared tool
arguments. Paths and revisions must be nonempty strings without NUL characters;
meaningful spaces in paths are not trimmed. `patchwitness_verify` requires an
`evidence` path. Existing repository-root path containment remains in place.

Requests must be JSON-RPC 2.0 objects with a method string and a string/integer
request ID. Boolean, fractional and null IDs are rejected. `params` and tool
`arguments`, when supplied, must be objects; they are not coerced from arrays of
pairs. Existing defaults still apply when optional fields are omitted. Unknown
argument properties retain their previous ignored behavior; this is not a new
closed-schema contract.

Malformed JSON produces `-32700`, invalid request objects produce `-32600`, and
invalid parameter envelopes produce `-32602`. Tool argument validation errors
use the existing tool-result `isError: true` shape. A valid request after a bad
input line is still processed. Notifications receive no response and cannot
invoke tools, even if their method is `tools/call`. This remains the existing
small newline-delimited stdio adapter, not a claim of full MCP conformance or a
new authorization boundary. Explicit check execution still requires a trusted
repository/environment; it is not an operating-system sandbox.

## MCP stdio: unambiguous, bounded wire messages

The stdio adapter rejects duplicate JSON object keys at every nesting level,
including escaped spellings of the same key. It does not select the first or
last value of a duplicated execution flag. Non-finite values (`NaN`, `Infinity`,
and numeric overflow such as `1e10000`) are rejected, including in otherwise
ignored extension fields. These failures occur before tool dispatch, contract
loading, Git access or check execution. Normal finite JSON extension values,
valid tool defaults and explicit boolean opt-in retain their existing behavior.

Each physical input line has a **1 MiB UTF-8 byte limit, including its newline
or CRLF delimiter**. Oversized input is discarded through the next newline (or
EOF), with one `-32600` response and a null ID; a valid-looking suffix is not
reinterpreted as another request. Reads and discarded-tail chunks are bounded.
For caller-supplied text streams, reads are character-bounded and the UTF-8 byte
limit is also checked before parsing. This is a PatchWitness adapter budget,
not a limit imposed by the MCP specification. It does not limit response size,
add a wall-clock deadline or protect against a peer that never finishes a line.

The CLI reads raw stdin bytes and explicitly decodes UTF-8 instead of relying
on the platform locale or JSON byte-encoding autodetection. Invalid UTF-8,
UTF-16/32 input, BOM-prefixed JSON, duplicate keys, non-finite numbers and parser
resource failures produce a sanitized `-32700` parse error without echoing the
payload. The following complete valid line can still be handled. CRLF input,
ordinary blank lines, valid Unicode and the legacy final line without a newline
remain supported. Embedded callers may still supply a decoded text stream to
`MCPServer.serve`; for byte-accurate wire framing, supply a binary stream.
Underlying stream-read errors propagate instead of retrying a broken stream
or pretending they are malformed JSON.

These changes apply only to decoding the stdio wire input. `handle()` already
receives a Python object, so it cannot detect keys discarded by an upstream
parser. Callers that parse messages themselves must enforce equivalent JSON
rules before invoking it. This is neither an authentication layer nor permission
to run untrusted repository commands.

References: [MCP 2025-11-25 transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and [Python JSON decoder extensions](https://docs.python.org/3/library/json.html#standard-compliance-and-interoperability).

## Git collection: literal paths and complete responses

NUL-delimited `git diff --numstat -z` records split only the two numeric fields
on tabs. The rest is the literal path: tabs, spaces, Unicode and display-like
`old => new` / `{old => new}` text are not rewritten into another filename.
Rename/copy paths come only from the separate NUL-delimited records. Truncated
records, empty rename paths and malformed/negative counts now fail instead of
silently becoming zero-count changes. Existing line-budget rule PW011 is not
changed; it now receives the actual counts for these filenames.

Git subprocess output is decoded without text-mode CR/CRLF normalization, and
flagged index filenames retain their leading/trailing whitespace. Newline and
carriage-return paths are resolved through one argument-vector value to an
object ID before entering the newline-delimited `cat-file --batch` protocol.
The same handling applies to index blobs.

Batch hashing alternates a request with its complete response, avoiding the
write-all/read-all pipe deadlock. Blob content is hashed in chunks of at most
64 KiB. Non-blob bodies are drained before the next header; incomplete bodies,
bad headers and missing terminators fail rather than produce partial hashes.
Pipes and a still-running child are cleaned up on detected errors. Binary
classification now reads only its existing 8 KiB prefix instead of loading the
entire file first. Neither change introduces a new total Git-data quota or a
general deadline for every Git read.

## Compatibility and remaining boundaries

This is not a fix for all possible Git pathname encodings. Existing backslash
normalization and replacement decoding of non-UTF-8 paths are unchanged and
remain separate review topics. POSIX-only pathname fixtures are explicitly
skipped on Windows; the parser and protocol tests run on every supported OS.
Existing symlink checks remain unchanged; no new race-free filesystem-snapshot
claim is made. SHA-256 proves the recorded bytes' identity, not provenance or
correctness. Re-capture evidence for affected changes after upgrading rather
than treating old passports as corrected retroactively.

The focused regression suites are:

```bash
python -m pytest -q tests/test_mcp.py tests/test_mcp_validation.py tests/test_mcp_transport.py \
  tests/test_git.py tests/test_git_path_identity.py tests/test_git_batch_streaming.py
```

They cover rejection before side effects (including a real disposable check),
positive boolean opt-in, stdio recovery, real Git diffs and PW011 enforcement,
index flags, line-break paths, mixed object types, bounded batch reads and child
cleanup. Normal repository CI remains responsible for the full test matrix,
strict mypy, Ruff, packaging and platform-specific checks. Do not infer that
those checks passed merely because the targeted tests did.
