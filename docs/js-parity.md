# JS runtime parity inventory

Scope of this comparison: the String, Array, Math/Number, JSON, Map/Set,
Date, typed-array, dynamic/object, and RegExp surfaces of `tsonic_python_js`
measured against `Tsonic.CSharp.Js` and the Rust inventory in
`rust-js/docs/js-parity.md`. Dispositions used:

- **implemented** — present in `tsonic_python_js` (module and public symbol
  given; symbols are exported from the package root).
- **rejected-by-architecture** — deliberately out of scope for the closed
  Python carrier model; callers get a deterministic error or the construct
  is simply not emitted.
- **requires-\<contract\>** — implementable only once the named runtime
  contract exists; tracked as a gap, not silently approximated.

## String

All helpers are UTF-16-explicit: indexes, lengths, and search positions are
in UTF-16 code units (`strings.utf16_code_units`), and lone surrogates are
carried faithfully.

| Member | Disposition |
| --- | --- |
| `length` | implemented — `strings.utf16_len` |
| `charAt` / `charCodeAt` | implemented — `strings.char_at` / `strings.char_code_at` (NaN out of range, as in JS) |
| `at` | implemented — `strings.at` (negative from end; `undefined` sentinel out of range) |
| `codePointAt` | implemented — `strings.code_point_at` (surrogate-pair combining; `undefined` out of range) |
| `slice` / `substring` / `substr` | implemented — `strings.string_slice` / `strings.substring` / `strings.substr` |
| `indexOf` / `lastIndexOf` / `includes` / `startsWith` / `endsWith` | implemented — `strings.index_of` / `strings.last_index_of` / `strings.includes` / `strings.starts_with` / `strings.ends_with` |
| `concat` | implemented — `strings.concat` (string arguments only; coercion is the compiler's job) |
| `replace` (string form) | implemented — `strings.replace`: first occurrence, literal search, JS GetSubstitution tokens `$$`, `$&`, `` $` ``, `$'` for a captureless search; other `$` sequences stay literal |
| `split` (string form) | implemented — `strings.split` |
| `trim` / `trimStart` / `trimEnd` | implemented — `strings.trim` / `strings.trim_start` / `strings.trim_end` (JS whitespace set) |
| `repeat` / `padStart` / `padEnd` | implemented — `strings.repeat` / `strings.pad_start` / `strings.pad_end` |
| `toUpperCase` / `toLowerCase` | implemented — `strings.to_upper_case` / `strings.to_lower_case`: Unicode default full case mappings via CPython (`str.upper`/`str.lower`), mirroring the Rust runtime's standard-library mappings; divergence from a JS engine is limited to Unicode-version skew |
| `String.fromCharCode` / `String.fromCodePoint` | implemented — `strings.from_char_code` / `strings.from_code_point` |
| `match` / `matchAll` | requires-regexp-match-carrier — same gap as the Rust inventory; see the RegExp row in `API_LEDGER.md` |
| `localeCompare`, `toLocale*`, `normalize` | requires-icu-contract — locale/normalization tables are not part of the closed runtime |
| `isWellFormed` / `toWellFormed` | requires-wellformedness-emission — the UTF-16 carrier can represent lone surrogates (unlike Rust `str`), but the members are not part of the closed surface until the compiler emits them |
| `String.raw` | rejected-by-architecture — tagged-template plumbing is a compiler concern, not a runtime member |

## Array

`arrays.JsArray` is the hole-preserving sparse carrier, mirroring the C#
`JSArray` and Rust `array::JsArray` split. Index reads (`get`), index writes
(`set` — grows with holes past `length`, updates `length`), `delete`
(hole-punching, length-preserving), and the `length` setter (truncate or
extend with holes) match the Rust `js_array_sparse` expectations.

| Member | Disposition |
| --- | --- |
| `at`, `includes`, `indexOf`, `slice`, `concat`, `join`, `keys`, `values`, `entries`, `push`, `pop`, `shift`, `unshift`, `fill`, `copyWithin`, `reverse`, `splice`, `map`, `filter`, `reduce`, `some`, `every`, `find`, `findIndex`, `forEach`, `toString` | implemented — methods on `arrays.JsArray` |
| `lastIndexOf` | requires-array-emission — trivially expressible once the compiler emits it; not part of the closed surface (Rust implements it on the dense lane only) |
| `flat` | requires-array-emission — the Rust dense lane implements depth-1 `flat`; the Python sparse carrier adds it when the compiler emits it |
| `sort` / `toSorted` and other ES2023 copying methods | requires-comparator-contract — JS comparator/stability semantics need a specified contract before they are claimed |
| `findLast` / `findLastIndex` | rejected-by-architecture for the ledger until the compiler emits them (same disposition as Rust); expressible as reversed `find`/`findIndex` |

## Math / Number

Implemented in `numbers.py`: `is_finite`, `is_nan`, `is_integer`,
`is_safe_integer`, `parse_int`, `parse_float`, `to_number`, `to_int32`,
`to_uint32`, and `math_abs`/`math_ceil`/`math_floor`/`math_trunc`/
`math_round`/`math_max`/`math_min`/`math_sign`/`math_pow`/`math_sqrt`/
`math_imul`/`math_clz32`. This matches the C# `Math.cs`/`Number.cs` subset
the backends consume; remaining `Math.*` transcendentals are
requires-math-emission (Python `math` covers them the day the compiler emits
them). NaN is Python-native `float("nan")`, and negative zero is preserved.

## JSON

`json.json_parse` / `json.json_stringify` are implemented over the closed
carriers (`JsObject`, `JsArray`, primitives). `replacer`/`reviver`/custom
`toJSON` and `stringify` spacing are requires-formatting-contract, matching
the Rust disposition (`stringify_pretty` normalizes to compact output there).

## Map / Set

Core surface (`get`/`set`/`has`/`add`/`delete`/`clear`/`keys`/`values`/
`entries`/`size`, SameValueZero keys) is implemented in `collections.py`
(`JsMap`, `JsSet`). `forEach` is requires-collection-emission: the compiler
lowers iteration to the list-returning accessors instead. The ES2025
set-algebra methods shipped by the C# side
(`union`, `intersection`, `difference`, `symmetricDifference`, `isSubsetOf`,
`isSupersetOf`, `isDisjointFrom`) are requires-set-algebra-emission, as in
the Rust inventory. WeakMap/WeakSet are rejected-by-architecture: GC/lifetime
semantics are unclaimed by the closed runtime.

## Date

UTC-based surface is implemented in `dates.py`: the `JsDate` epoch-ms
carrier (`now`, `parse`, `get_time`, `to_iso_string`, UTC getters) plus the
statics `date_now` (whole epoch milliseconds) and `date_parse`. `date_parse`
accepts the same closed UTC ISO-8601 subset as Rust `date::JsDate::parse`
(`YYYY-MM-DDTHH:MM:SS[.fff]Z`, digit-only fields, proleptic Gregorian) and
returns NaN for anything else; Rust's additional raw-numeric-string
acceptance is not claimed. Local-time getters/setters, `getTimezoneOffset`,
and locale renderers are requires-timezone-contract (no IANA tzdata source);
`Date.UTC`-style construction and setters are
requires-date-mutation-contract (the carrier is an immutable millisecond
value). Both dispositions match the Rust inventory.

## Typed arrays

`typed_arrays.py` implements `ArrayBuffer` (`byte_length`, `slice`),
`DataView` (all int8/16/32 and float32/64 accessors with endianness), and
the nine concrete `TypedArray` classes with `get`, element `set`, JS bulk
`set(source, offset)` (typed-array or list source, per-class wrap/clamp
conversion, RangeError when the source does not fit, no partial writes),
`values`, `slice`, and `subarray`. BigInt64/BigUint64 arrays are
requires-bigint-carrier. `ArrayBuffer` resizing/transfer and
`SharedArrayBuffer` are rejected-by-architecture (no shared-memory or
detachment model in the closed runtime).

## Dynamic / object lanes

`objects.py` implements the closed own-property carrier `JsObject`
(insertion-ordered string keys) and the carrier-dispatched `get_property` /
`set_property` / `delete_property` over the closed set: `JsObject`,
`JsArray` (index keys and `length`), and read-only `str` (index reads and
`length`; writes/deletes are silent no-ops as in non-strict JS).
`dynamic.JsValue` is the tagged carrier for compat lanes
(undefined/null/boolean/number/string/array/object) and forwards property
operations to the same functions. Prototypes, getters/setters, property
descriptors, `Proxy`, and `Symbol` keys are rejected-by-architecture: the
carrier model is own-property, string-keyed, and closed.

## RegExp

RegExp disposition, engine status, and the supported subset are tracked in
the RegExp row of `API_LEDGER.md`, which is the single source of truth for
this lane; this inventory intentionally does not duplicate it. The
match-object gap noted under String (`match`/`matchAll`) remains
requires-regexp-match-carrier either way, as in the Rust inventory.
