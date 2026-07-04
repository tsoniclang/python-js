# python-js

Closed JavaScript compatibility runtime helpers for generated Python targets.

Package import name: `tsonic_python_js`.

## Runtime Boundary

This package is runtime-only. It does not embed a JavaScript engine, invoke Node,
use Python `eval`/`exec`, import compiler/TSTS facts, or provide GPU/Web/DOM
APIs.

## Implemented API Areas

- Core values: `undefined`, nullish predicates.
- JS errors: `JsError`, `JsTypeError`, `JsRangeError`, `JsSyntaxError`,
  `JsReferenceError`, `JsURIError`, `JsUnsupportedError`.
- Equality: `strict_equal`, `same_value_zero`, `object_is`.
- Objects and dynamic lanes: `JsObject`, `JsValue`, property get/set/delete.
- Sparse arrays: `JsArray` with holes, length mutation, search, copying,
  mutation, joining, iteration helpers, and callback helpers.
- Strings: UTF-16 length/code-unit helpers and common non-RegExp string methods.
- Numbers and Math: JS numeric predicates, conversions, parsing, and common Math
  helpers.
- JSON: parse/stringify over closed JS carriers.
- Collections: `JsMap`, `JsSet` with SameValueZero keys and insertion order.
- Dates: `JsDate` UTC epoch-ms carrier with parse, now, time, ISO, and UTC
  accessors covered by tests.
- Typed arrays: `ArrayBuffer`, `DataView`, and Int8/Uint8/Uint8Clamped/Int16/
  Uint16/Int32/Uint32/Float32/Float64 typed arrays.
- RegExp: `JsRegExp` implements `test`/`replace`/`split`/`search` over a closed
  syntax subset (literals, `.`, character classes, class escapes, greedy
  quantifiers, anchors, alternation, groups, flags `i g m`) with JS UTF-16
  code-unit and `lastIndex` semantics, proven against committed Node oracle
  vectors. Patterns outside the subset raise at construction;
  `unsupported_regexp`/`REGEXP_STATUS` name the rejected catalog.

## Unsupported API Areas

- RegExp constructs outside the `JsRegExp` subset (lazy quantifiers,
  backreferences, lookaround, named groups, `\b`/`\B`, `\p{...}`, flags other
  than `i g m`) raise `JsUnsupportedError` at construction.
- WeakMap/WeakSet, timers, console, fetch, DOM/Web APIs, Node APIs, prototype
  mutation, proxies, symbols, callback replacer/reviver, and custom `toJSON`
  are unclaimed.

See `API_LEDGER.md` for the exported API classification and parity references.
