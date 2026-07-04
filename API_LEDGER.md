# python-js API Ledger

All rows are runtime-only. Unsupported rows are intentional closed hard-rejects
or unexported lanes.

| Area | Public symbols | Status | Parity references |
| --- | --- | --- | --- |
| Values | `undefined`, `is_undefined`, `is_nullish` | implemented | starter spec undefined/null catalog |
| Errors | `JsError`, `JsTypeError`, `JsRangeError`, `JsSyntaxError`, `JsReferenceError`, `JsURIError`, `JsUnsupportedError` | implemented | C# `ErrorTests.cs`, `RangeErrorTests.cs` |
| Equality | `strict_equal`, `same_value_zero`, `object_is` | implemented | Rust `equality_tests.rs`, C# sparse search tests |
| Objects | `JsObject`, `property_key`, `get_property`, `set_property`, `delete_property` | implemented over the closed carrier set (`JsObject`, `JsArray`, read-only `str`) with write/delete round-trip tests | C# `ObjectTests.cs`, Rust `object_tests.rs` behavior subset |
| Dynamic values | `JsValue` | implemented for closed compat lanes; property writes/deletes forward to the objects lane | Rust `JsValue` equality/property expectations |
| Arrays | `JsArray` methods | implemented, including sparse index write `set(index, value)` (grows with holes, updates `length`) | C# `ArrayTests.cs`, Rust `js_array_sparse_tests.rs` |
| Strings | UTF-16 and common non-RegExp helpers, including `at`, `code_point_at`, `concat`, string-form `replace` (first occurrence, JS `$$`/`$&`/backtick/`$'` tokens), `to_upper_case`, `to_lower_case` (Unicode default mappings, no locale variants) | implemented | C# `StringTests.cs`, Rust `string_tests.rs` |
| Numbers | predicates, conversions, parsing | implemented | C# `NumberTests.cs`, Rust `number_tests.rs` |
| Math | `math_abs`, `math_ceil`, `math_floor`, `math_trunc`, `math_round`, `math_max`, `math_min`, `math_sign`, `math_pow`, `math_sqrt`, `math_imul`, `math_clz32` | implemented | Rust `math_tests.rs`, JS edge catalog |
| JSON | `json_parse`, `json_stringify` | implemented without replacer/reviver/custom `toJSON` | C# `JSONTests.cs`, Rust `json_tests.rs` |
| Collections | `JsMap`, `JsSet` | implemented | C# `MapTests.cs`/`SetTests.cs`, Rust `map_tests.rs`/`set_tests.rs` |
| Date | `JsDate`, `date_now`, `date_parse` | implemented UTC epoch-ms subset; `date_parse` covers the closed ISO-8601 UTC subset of Rust `date.rs` and returns NaN on failure | C# `DateTests.cs`, Rust `date_tests.rs` |
| Typed arrays | `ArrayBuffer`, `DataView`, `TypedArray`, concrete typed arrays | implemented practical set, including JS bulk `set(source, offset)` with per-class wrap/clamp conversion and RangeError on out-of-bounds | C# `TypedArrayTests.cs`, Rust `typed_array_tests.rs`/`array_buffer_tests.rs` |
| RegExp | `REGEXP_STATUS`, `unsupported_regexp` | hard-reject with reason | C#/Rust RegExp tests require a proven engine/subset; Python `re` is not used |
| WeakMap/WeakSet | none | unsupported: GC/lifetime semantics unclaimed | C# weak collection tests remain outside python-js export |
| Timers/console/fetch/DOM/Node/Web | none | hard-reject: outside runtime boundary | starter spec runtime boundary |
