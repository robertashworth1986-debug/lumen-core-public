# ProofLock canonical payload contract

Active outcome 2: reproducible outside review of the existing decision-control
surface. These rules bind receipt identity; they do not authenticate a signer,
validate a benchmark, authorize actuation or establish engineering acceptance.

## V2: `lumencore.prooflock_c14n.binary64.v2`

A v2 receipt declares schema `lumencore.prooflock_receipt.v2` and the exact
`canonicalization` identifier above. Remove only the top-level
`receipt_sha256` member, serialize the remaining payload by the following
recursive grammar, UTF-8 encode that text and SHA-256 those bytes. The schema
and canonicalization members themselves are included in the payload hash.
The tagged representation is an identity encoding, not a JSON document.

| Input | Identity encoding |
|---|---|
| `null` | `null` |
| Boolean | `true` or `false` |
| Number | `N` + 16 lowercase hex digits of big-endian IEEE-754 binary64 + `;` |
| String | JSON quoted string with the escaping rules below |
| Array | `[` + comma-separated recursive encodings, retaining order + `]` |
| Object | `{` + comma-separated quoted key, `:`, recursive value + `}` |

Numbers are finite binary64 values. Integers outside
`[-9007199254740991, 9007199254740991]` are rejected, including decimal or
exponent spellings that parse as unsafe integral binary64 values. Integer and
floating representations of the same accepted value have the same encoding.
Positive and negative zero both encode as `N0000000000000000;`.
For example, `1` and `1.0` encode as `N3ff0000000000000;`. A decimal token is
interpreted by correctly rounded binary64 parsing, not as an exact decimal;
spellings that round to the same accepted binary64 value intentionally have
the same identity. Exact decimal or arbitrary-precision requirements need
string fields and an explicit quantity contract.

Strings and keys contain Unicode scalar values only; unpaired UTF-16
surrogates are rejected. Preserve the scalar sequence without NFC or other
normalization. Quote and backslash use `\"` and `\\`. Backspace, tab, newline,
form feed and carriage return use `\b`, `\t`, `\n`, `\f`, `\r`. Other U+0000–001F
characters use lowercase four-digit `\u` escapes. U+0020–007E remain literal
except quote and backslash. U+007F and every larger scalar use lowercase
four-digit `\u` escapes; astral scalars use their two UTF-16 surrogate escapes.
Slash is literal. Object keys are sorted lexicographically by their original
Unicode scalar sequences, with the shorter prefix first. Array order is never
sorted. No insignificant whitespace is inserted.

Both entrypoints accept only JSON data types, a maximum nesting depth of 100
(root depth zero), and raw input of at most 2,000,000 UTF-8 bytes. Duplicate
decoded object keys are prohibited recursively, including escaped aliases
such as `a` and `\u0061`. Nonfinite JSON extensions and malformed syntax are
rejected. Object APIs cannot recover duplicates or lexical spelling discarded
by a caller's previous parser; callers handling external text must use
`parseStrictJson` / `strict_json_loads` before verification.

## V1 compatibility: `lumencore.prooflock_c14n.legacy.v1`

The implicit v1 profile preserves the old sorted, compact, ASCII-escaped JSON
identity for its portable subset: nulls, booleans, safe integer values, arrays,
ASCII object keys, and valid Unicode string values excluding U+007F. Raw
numeric tokens must be plain integer lexemes excluding `-0`. The JavaScript
object API cannot distinguish `1` from an already parsed `1.0`; the raw-text
entrypoint enforces that lexical condition. Python floats are rejected even
when integral. Non-ASCII keys, floats/exponents, signed zero, DEL and invalid
Unicode are rejected explicitly rather than normalized under a historical
hash. The retained demo is in the portable subset and is not resealed.

V1 and v2 are distinct receipt identities. Migration is explicit and produces
a separately retained v2 receipt; verification does not mutate, upgrade or
rewrite a v1 receipt. A v1 receipt outside the portable subset remains a
historical record requiring qualified review, rather than a portable verified
receipt. The authority gates are unchanged in both versions: resealing
self-authored PASS declarations cannot create trusted external or human
authority, and PROMOTE remains blocked.
