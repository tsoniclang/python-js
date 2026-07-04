"""Oracle-backed backtracking RegExp engine for a closed JS subset.

Supported syntax: literal characters, ``.``, character classes (``[abc]``,
``[a-z]``, ``[^...]``), class escapes ``\\d \\D \\w \\W \\s \\S`` (inside and
outside classes), identity/control/hex escapes (``\\.``, ``\\\\``, ``\\n``,
``\\r``, ``\\t``, ``\\f``, ``\\v``, ``\\0``, ``\\xHH``, ``\\uHHHH``), greedy
quantifiers ``* + ? {n} {n,} {n,m}``, anchors ``^ $``, alternation ``|``,
capturing ``( )`` and non-capturing ``(?: )`` groups. Supported flags: ``i``,
``g`` (drives ``replace``/``split`` iteration), ``m``.

Everything else -- lazy quantifiers, backreferences, lookaround, named groups,
``\\b``/``\\B`` assertions, ``\\p{...}`` property escapes, ``\\c`` control
escapes, legacy octal escapes, bare braces, and every flag outside ``i g m``
-- is rejected at construction: valid-JS constructs outside the subset raise
``JsUnsupportedError`` and malformed patterns raise ``JsSyntaxError``.
``split`` additionally rejects patterns with capturing groups (JS splices
capture values into the result); use a non-capturing group ``(?:...)``.

Matching operates on UTF-16 code units exactly like a non-``u``-flag JS
RegExp: ``.`` consumes one code unit (astral characters are two), indexes
returned by ``search`` are code-unit indexes, empty matches advance by one
code unit, and ``i`` uses the ECMAScript Canonicalize simple case folding.
``JsRegExp.last_index`` mirrors the observable JS ``lastIndex`` state:
``test`` on a ``g`` regexp resumes from it and updates it, ``replace`` with
``g`` leaves it at 0, and ``search``/``split``/non-``g`` operations leave it
untouched.
Acceptance of the supported subset is proven against Node's engine by the
committed vectors in ``tests/oracle/regexp-vectors.json``.
"""

from dataclasses import dataclass

from tsonic_python_js.errors import JsSyntaxError, JsUnsupportedError
from tsonic_python_js.strings import utf16_code_units

REGEXP_STATUS = (
    "hard-reject: RegExp constructs outside the oracle-backed subset "
    "(lazy quantifiers, backreferences, lookaround, named groups, "
    "\\b/\\B assertions, \\p{...} property escapes, flags other than i/g/m)"
)

_MAX_QUANTIFIER_BOUND = 1000

_LINE_TERMINATORS = frozenset({0x0A, 0x0D, 0x2028, 0x2029})

_JS_WHITESPACE = frozenset(
    {
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x20,
        0xA0,
        0x1680,
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
        0xFEFF,
    }
    | set(range(0x2000, 0x200B))
)


def unsupported_regexp(*_args: object, **_kwargs: object) -> object:
    raise JsUnsupportedError(REGEXP_STATUS)


def _unsupported(reason: str) -> JsUnsupportedError:
    return JsUnsupportedError(f"RegExp: {reason}")


def _syntax_error(reason: str) -> JsSyntaxError:
    return JsSyntaxError(f"RegExp: {reason}")


# --- pattern AST -------------------------------------------------------------


@dataclass(frozen=True)
class _ClassSingle:
    unit: int


@dataclass(frozen=True)
class _ClassRange:
    low: int
    high: int


@dataclass(frozen=True)
class _ClassShorthand:
    kind: str  # one of "d" "D" "w" "W" "s" "S"


_ClassItem = _ClassSingle | _ClassRange | _ClassShorthand


@dataclass(frozen=True)
class _Char:
    unit: int


@dataclass(frozen=True)
class _Dot:
    pass


@dataclass(frozen=True)
class _ClassAtom:
    negated: bool
    items: tuple[_ClassItem, ...]


@dataclass(frozen=True)
class _AnchorStart:
    pass


@dataclass(frozen=True)
class _AnchorEnd:
    pass


@dataclass(frozen=True)
class _Group:
    index: int | None
    body: "_Ast"


@dataclass(frozen=True)
class _Repeat:
    body: "_Ast"
    low: int
    high: int | None


@dataclass(frozen=True)
class _Concat:
    items: tuple["_Ast", ...]


@dataclass(frozen=True)
class _Alternation:
    branches: tuple["_Ast", ...]


_Ast = (
    _Char
    | _Dot
    | _ClassAtom
    | _AnchorStart
    | _AnchorEnd
    | _Group
    | _Repeat
    | _Concat
    | _Alternation
)


@dataclass(frozen=True)
class _Flags:
    ignore_case: bool
    is_global: bool
    multiline: bool


def _parse_flags(flags: str) -> _Flags:
    ignore_case = False
    is_global = False
    multiline = False
    for flag in flags:
        if flag == "i":
            if ignore_case:
                raise _syntax_error("duplicate RegExp flag `i`")
            ignore_case = True
        elif flag == "g":
            if is_global:
                raise _syntax_error("duplicate RegExp flag `g`")
            is_global = True
        elif flag == "m":
            if multiline:
                raise _syntax_error("duplicate RegExp flag `m`")
            multiline = True
        else:
            raise _unsupported(f"flag `{flag}` is outside the supported subset `i g m`")
    return _Flags(ignore_case=ignore_case, is_global=is_global, multiline=multiline)


# --- parser ------------------------------------------------------------------


class _Parser:
    """Recursive-descent parser over the pattern's UTF-16 code units."""

    def __init__(self, pattern: str) -> None:
        self._units: list[str] = [chr(unit) for unit in utf16_code_units(pattern)]
        self._pos: int = 0
        self.group_count: int = 0

    def parse(self) -> _Ast:
        ast = self._parse_alternation()
        if self._pos < len(self._units):
            raise _syntax_error("unmatched `)` in pattern")
        return ast

    def _peek(self) -> str | None:
        if self._pos < len(self._units):
            return self._units[self._pos]
        return None

    def _peek_at(self, offset: int) -> str | None:
        index = self._pos + offset
        if index < len(self._units):
            return self._units[index]
        return None

    def _bump(self) -> str | None:
        unit = self._peek()
        if unit is not None:
            self._pos += 1
        return unit

    def _eat(self, expected: str) -> bool:
        if self._peek() == expected:
            self._pos += 1
            return True
        return False

    def _parse_alternation(self) -> _Ast:
        branches = [self._parse_concat()]
        while self._eat("|"):
            branches.append(self._parse_concat())
        if len(branches) == 1:
            return branches[0]
        return _Alternation(tuple(branches))

    def _parse_concat(self) -> _Ast:
        items: list[_Ast] = []
        while True:
            unit = self._peek()
            if unit is None or unit in "|)":
                break
            items.append(self._parse_term())
        if len(items) == 1:
            return items[0]
        return _Concat(tuple(items))

    def _parse_term(self) -> _Ast:
        atom = self._parse_atom()
        bounds = self._parse_quantifier()
        if bounds is None:
            return atom
        if isinstance(atom, _AnchorStart | _AnchorEnd):
            raise _syntax_error("quantifier on `^`/`$` anchor is not supported")
        low, high = bounds
        return _Repeat(atom, low, high)

    def _parse_atom(self) -> _Ast:
        unit = self._bump()
        if unit is None:
            raise _syntax_error("unexpected end of pattern")
        if unit == "^":
            return _AnchorStart()
        if unit == "$":
            return _AnchorEnd()
        if unit == ".":
            return _Dot()
        if unit == "(":
            return self._parse_group()
        if unit == "[":
            return self._parse_class()
        if unit == "\\":
            return self._parse_escape_atom()
        if unit in "*+?":
            raise _syntax_error(f"quantifier `{unit}` has nothing to repeat")
        if unit == "{":
            raise _unsupported("bare `{` is not supported in pattern")
        if unit == "}":
            raise _unsupported("bare `}` is not supported in pattern")
        return _Char(ord(unit))

    def _parse_group(self) -> _Ast:
        index: int | None
        if self._eat("?"):
            modifier = self._peek()
            if modifier == ":":
                self._pos += 1
                index = None
            elif modifier == "=":
                raise _unsupported("lookahead `(?=` is not supported")
            elif modifier == "!":
                raise _unsupported("negative lookahead `(?!` is not supported")
            elif modifier == "<":
                after = self._peek_at(1)
                if after == "=":
                    raise _unsupported("lookbehind `(?<=` is not supported")
                if after == "!":
                    raise _unsupported("negative lookbehind `(?<!` is not supported")
                raise _unsupported("named capture group `(?<name>` is not supported")
            else:
                raise _syntax_error("unrecognized group modifier after `(?`")
        else:
            self.group_count += 1
            index = self.group_count
        body = self._parse_alternation()
        if not self._eat(")"):
            raise _syntax_error("unterminated group: missing `)`")
        return _Group(index, body)

    def _parse_quantifier(self) -> tuple[int, int | None] | None:
        unit = self._peek()
        if unit == "*":
            self._pos += 1
            bounds: tuple[int, int | None] = (0, None)
            label = "*?"
        elif unit == "+":
            self._pos += 1
            bounds = (1, None)
            label = "+?"
        elif unit == "?":
            self._pos += 1
            bounds = (0, 1)
            label = "??"
        elif unit == "{":
            braced = self._parse_braced_quantifier()
            if braced is None:
                raise _unsupported("bare `{` is not supported in pattern")
            bounds = braced
            label = "{n,m}?"
        else:
            return None
        if self._peek() == "?":
            raise _unsupported(f"lazy quantifier `{label}` is not supported")
        return bounds

    def _parse_braced_quantifier(self) -> tuple[int, int | None] | None:
        """Parse ``{n}``/``{n,}``/``{n,m}``; ``None`` when not well-formed."""

        start = self._pos
        self._pos += 1  # consume `{`
        low = self._parse_bound()
        if low is None:
            self._pos = start
            return None
        high: int | None
        if self._eat(","):
            if self._peek() == "}":
                high = None
            else:
                high = self._parse_bound()
                if high is None:
                    self._pos = start
                    return None
        else:
            high = low
        if not self._eat("}"):
            self._pos = start
            return None
        if high is not None and low > high:
            raise _syntax_error("numbers out of order in `{n,m}` quantifier")
        return (low, high)

    def _parse_bound(self) -> int | None:
        digits = 0
        value = 0
        while True:
            unit = self._peek()
            if unit is None or not ("0" <= unit <= "9"):
                break
            self._pos += 1
            digits += 1
            value = value * 10 + (ord(unit) - 0x30)
            if value > _MAX_QUANTIFIER_BOUND:
                raise _unsupported(
                    f"quantifier bound exceeds the supported limit of {_MAX_QUANTIFIER_BOUND}"
                )
        if digits == 0:
            return None
        return value

    def _parse_escape_atom(self) -> _Ast:
        escaped = self._bump()
        if escaped is None:
            raise _syntax_error("pattern ends with a trailing `\\`")
        if escaped in "dDwWsS":
            return _ClassAtom(negated=False, items=(_ClassShorthand(escaped),))
        if escaped in "bB":
            raise _unsupported(f"word-boundary assertion `\\{escaped}` is not supported")
        if escaped in "pP":
            raise _unsupported(f"unicode property escape `\\{escaped}` is not supported")
        if escaped == "k":
            raise _unsupported("named backreference `\\k` is not supported")
        if escaped == "c":
            raise _unsupported("control escape `\\c` is not supported")
        if "1" <= escaped <= "9":
            raise _unsupported(f"backreference `\\{escaped}` is not supported")
        return _Char(self._finish_common_escape(escaped))

    def _parse_class(self) -> _ClassAtom:
        negated = self._eat("^")
        items: list[_ClassItem] = []
        while True:
            unit = self._peek()
            if unit is None:
                raise _syntax_error("unterminated character class: missing `]`")
            if unit == "]":
                self._pos += 1
                break
            first = self._parse_class_member()
            is_range = self._peek() == "-" and self._peek_at(1) not in (None, "]")
            if is_range:
                self._pos += 1  # consume `-`
                second = self._parse_class_member()
                if isinstance(first, _ClassShorthand) or isinstance(second, _ClassShorthand):
                    raise _unsupported(
                        "character class range bounded by a class escape is not supported"
                    )
                if first > second:
                    raise _syntax_error("character class range out of order")
                items.append(_ClassRange(first, second))
            elif isinstance(first, _ClassShorthand):
                items.append(first)
            else:
                items.append(_ClassSingle(first))
        return _ClassAtom(negated=negated, items=tuple(items))

    def _parse_class_member(self) -> int | _ClassShorthand:
        unit = self._bump()
        if unit is None:
            raise _syntax_error("unterminated character class: missing `]`")
        if unit != "\\":
            return ord(unit)
        escaped = self._bump()
        if escaped is None:
            raise _syntax_error("pattern ends with a trailing `\\`")
        if escaped in "dDwWsS":
            return _ClassShorthand(escaped)
        if escaped == "b":
            return 0x08
        if escaped in "pP":
            raise _unsupported(f"unicode property escape `\\{escaped}` is not supported")
        if escaped == "c":
            raise _unsupported("control escape `\\c` is not supported")
        if "1" <= escaped <= "9":
            raise _unsupported(f"octal escape `\\{escaped}` in character class is not supported")
        return self._finish_common_escape(escaped)

    def _finish_common_escape(self, escaped: str) -> int:
        """Escapes valid both inside and outside character classes."""

        if escaped == "n":
            return 0x0A
        if escaped == "r":
            return 0x0D
        if escaped == "t":
            return 0x09
        if escaped == "f":
            return 0x0C
        if escaped == "v":
            return 0x0B
        if escaped == "0":
            follower = self._peek()
            if follower is not None and "0" <= follower <= "9":
                raise _unsupported(
                    "legacy octal escape (`\\0` followed by a digit) is not supported"
                )
            return 0x00
        if escaped == "x":
            return self._parse_hex_escape(2)
        if escaped == "u":
            if self._peek() == "{":
                raise _unsupported("`\\u{...}` escape requires the unsupported `u` flag")
            return self._parse_hex_escape(4)
        if "0" <= escaped <= "9" or "a" <= escaped <= "z" or "A" <= escaped <= "Z":
            raise _unsupported(f"unrecognized escape `\\{escaped}` in pattern")
        return ord(escaped)

    def _parse_hex_escape(self, digits: int) -> int:
        value = 0
        for _ in range(digits):
            unit = self._bump()
            if unit is None or unit not in "0123456789abcdefABCDEF":
                raise _unsupported("malformed hex escape in pattern")
            value = value * 16 + int(unit, 16)
        return value


# --- bytecode compiler -------------------------------------------------------


@dataclass
class _IChar:
    unit: int


@dataclass
class _IDot:
    pass


@dataclass
class _IClass:
    negated: bool
    items: tuple[_ClassItem, ...]


@dataclass
class _ISplit:
    """Try `first`; on failure resume at `second`."""

    first: int
    second: int


@dataclass
class _IJmp:
    target: int


@dataclass
class _ISave:
    slot: int


@dataclass
class _IClearCaps:
    """Clear capture slots in `lo..hi` (start of a repeat iteration)."""

    lo: int
    hi: int


@dataclass
class _ISetLoop:
    """Record the current position for the empty-iteration check."""

    slot: int


@dataclass
class _ILoop:
    """Fail on an empty iteration; else continue at `back` (or fall through)."""

    slot: int
    back: int | None


@dataclass
class _IAssertStart:
    pass


@dataclass
class _IAssertEnd:
    pass


@dataclass
class _IMatch:
    pass


_Inst = (
    _IChar
    | _IDot
    | _IClass
    | _ISplit
    | _IJmp
    | _ISave
    | _IClearCaps
    | _ISetLoop
    | _ILoop
    | _IAssertStart
    | _IAssertEnd
    | _IMatch
)


@dataclass
class _Program:
    insts: list[_Inst]
    group_count: int
    loop_count: int


def _compile(ast: _Ast, group_count: int) -> _Program:
    compiler = _Compiler()
    compiler.insts.append(_ISave(0))
    compiler.emit(ast)
    compiler.insts.append(_ISave(1))
    compiler.insts.append(_IMatch())
    return _Program(insts=compiler.insts, group_count=group_count, loop_count=compiler.loop_count)


class _Compiler:
    def __init__(self) -> None:
        self.insts: list[_Inst] = []
        self.loop_count = 0

    def emit(self, ast: _Ast) -> None:
        if isinstance(ast, _Char):
            self.insts.append(_IChar(ast.unit))
        elif isinstance(ast, _Dot):
            self.insts.append(_IDot())
        elif isinstance(ast, _ClassAtom):
            self.insts.append(_IClass(ast.negated, ast.items))
        elif isinstance(ast, _AnchorStart):
            self.insts.append(_IAssertStart())
        elif isinstance(ast, _AnchorEnd):
            self.insts.append(_IAssertEnd())
        elif isinstance(ast, _Concat):
            for item in ast.items:
                self.emit(item)
        elif isinstance(ast, _Alternation):
            self._emit_alternation(ast.branches)
        elif isinstance(ast, _Group):
            if ast.index is not None:
                self.insts.append(_ISave(2 * ast.index))
            self.emit(ast.body)
            if ast.index is not None:
                self.insts.append(_ISave(2 * ast.index + 1))
        else:
            self._emit_repeat(ast.body, ast.low, ast.high)

    def _emit_alternation(self, branches: tuple[_Ast, ...]) -> None:
        end_jumps: list[_IJmp] = []
        for index, branch in enumerate(branches):
            is_last = index + 1 == len(branches)
            split: _ISplit | None = None
            if not is_last:
                split = _ISplit(first=len(self.insts) + 1, second=-1)
                self.insts.append(split)
            self.emit(branch)
            if not is_last:
                jump = _IJmp(-1)
                end_jumps.append(jump)
                self.insts.append(jump)
            if split is not None:
                split.second = len(self.insts)
        end = len(self.insts)
        for jump in end_jumps:
            jump.target = end

    def _emit_repeat(self, body: _Ast, low: int, high: int | None) -> None:
        clear = _capture_slot_range(body)
        for _ in range(low):
            self._emit_iteration_prologue(clear, None)
            self.emit(body)
        if high is None:
            slot = self._next_loop_slot()
            start = len(self.insts)
            split = _ISplit(first=start + 1, second=-1)
            self.insts.append(split)
            self._emit_iteration_prologue(clear, slot)
            self.emit(body)
            self.insts.append(_ILoop(slot=slot, back=start))
            split.second = len(self.insts)
        else:
            optional = high - low
            if optional == 0:
                return
            slot = self._next_loop_slot()
            splits: list[_ISplit] = []
            for _ in range(optional):
                split = _ISplit(first=len(self.insts) + 1, second=-1)
                self.insts.append(split)
                splits.append(split)
                self._emit_iteration_prologue(clear, slot)
                self.emit(body)
                self.insts.append(_ILoop(slot=slot, back=None))
            end = len(self.insts)
            for split in splits:
                split.second = end

    def _emit_iteration_prologue(
        self, clear: tuple[int, int] | None, loop_slot: int | None
    ) -> None:
        if loop_slot is not None:
            self.insts.append(_ISetLoop(loop_slot))
        if clear is not None:
            self.insts.append(_IClearCaps(lo=clear[0], hi=clear[1]))

    def _next_loop_slot(self) -> int:
        slot = self.loop_count
        self.loop_count += 1
        return slot


def _capture_slot_range(ast: _Ast) -> tuple[int, int] | None:
    """Inclusive capture-slot range used by capturing groups inside `ast`."""

    indexes: list[int] = []
    _collect_group_indexes(ast, indexes)
    if not indexes:
        return None
    return (2 * min(indexes), 2 * max(indexes) + 1)


def _collect_group_indexes(ast: _Ast, out: list[int]) -> None:
    if isinstance(ast, _Group):
        if ast.index is not None:
            out.append(ast.index)
        _collect_group_indexes(ast.body, out)
    elif isinstance(ast, _Concat):
        for item in ast.items:
            _collect_group_indexes(item, out)
    elif isinstance(ast, _Alternation):
        for branch in ast.branches:
            _collect_group_indexes(branch, out)
    elif isinstance(ast, _Repeat):
        _collect_group_indexes(ast.body, out)


# --- case canonicalization (ECMAScript Canonicalize, non-unicode mode) --------

_CANON_CACHE: dict[int, int] = {}

_fold_cache: dict[int, tuple[int, ...]] | None = None


def _canonicalize(unit: int) -> int:
    cached = _CANON_CACHE.get(unit)
    if cached is not None:
        return cached
    folded = unit
    if not 0xD800 <= unit <= 0xDFFF:
        upper = chr(unit).upper()
        if len(upper) == 1:
            candidate = ord(upper)
            if candidate <= 0xFFFF and not (unit >= 0x80 and candidate < 0x80):
                folded = candidate
    _CANON_CACHE[unit] = folded
    return folded


def _fold_preimages() -> dict[int, tuple[int, ...]]:
    """Map every canonical code unit to all code units folding onto it."""

    global _fold_cache
    if _fold_cache is None:
        table: dict[int, list[int]] = {}
        for unit in range(0x10000):
            table.setdefault(_canonicalize(unit), []).append(unit)
        _fold_cache = {canon: tuple(units) for canon, units in table.items()}
    return _fold_cache


# --- backtracking interpreter --------------------------------------------------


def _is_word_unit(unit: int) -> bool:
    return 0x30 <= unit <= 0x39 or 0x41 <= unit <= 0x5A or 0x61 <= unit <= 0x7A or unit == 0x5F


def _class_item_matches(item: _ClassItem, unit: int) -> bool:
    if isinstance(item, _ClassSingle):
        return unit == item.unit
    if isinstance(item, _ClassRange):
        return item.low <= unit <= item.high
    if item.kind == "d":
        return 0x30 <= unit <= 0x39
    if item.kind == "D":
        return not 0x30 <= unit <= 0x39
    if item.kind == "w":
        return _is_word_unit(unit)
    if item.kind == "W":
        return not _is_word_unit(unit)
    if item.kind == "s":
        return unit in _JS_WHITESPACE
    return unit not in _JS_WHITESPACE


def _class_matches(inst: _IClass, unit: int, ignore_case: bool) -> bool:
    candidates = _fold_preimages().get(_canonicalize(unit), (unit,)) if ignore_case else (unit,)
    member = any(
        _class_item_matches(item, candidate) for item in inst.items for candidate in candidates
    )
    return member != inst.negated


def _char_matches(expected: int, actual: int, ignore_case: bool) -> bool:
    if actual == expected:
        return True
    return ignore_case and _canonicalize(actual) == _canonicalize(expected)


def _exec_at(
    program: _Program,
    units: tuple[int, ...],
    start: int,
    ignore_case: bool,
    multiline: bool,
) -> list[int | None] | None:
    """Run the program anchored at code-unit index `start`.

    On success returns the capture slots (`2k` = group-k start, `2k + 1` =
    group-k end, group 0 being the whole match) as code-unit indexes.
    """

    size = len(units)
    insts = program.insts
    caps: list[int | None] = [None] * (2 * (program.group_count + 1))
    loops: list[int] = [0] * program.loop_count
    undo: list[tuple[bool, int, int | None]] = []
    frames: list[tuple[int, int, int]] = []
    pc = 0
    pos = start
    while True:
        inst = insts[pc]
        failed = False
        if isinstance(inst, _IChar):
            if pos < size and _char_matches(inst.unit, units[pos], ignore_case):
                pos += 1
                pc += 1
            else:
                failed = True
        elif isinstance(inst, _IDot):
            if pos < size and units[pos] not in _LINE_TERMINATORS:
                pos += 1
                pc += 1
            else:
                failed = True
        elif isinstance(inst, _IClass):
            if pos < size and _class_matches(inst, units[pos], ignore_case):
                pos += 1
                pc += 1
            else:
                failed = True
        elif isinstance(inst, _ISplit):
            frames.append((inst.second, pos, len(undo)))
            pc = inst.first
        elif isinstance(inst, _IJmp):
            pc = inst.target
        elif isinstance(inst, _ISave):
            undo.append((False, inst.slot, caps[inst.slot]))
            caps[inst.slot] = pos
            pc += 1
        elif isinstance(inst, _IClearCaps):
            for slot in range(inst.lo, inst.hi + 1):
                undo.append((False, slot, caps[slot]))
                caps[slot] = None
            pc += 1
        elif isinstance(inst, _ISetLoop):
            undo.append((True, inst.slot, loops[inst.slot]))
            loops[inst.slot] = pos
            pc += 1
        elif isinstance(inst, _ILoop):
            if pos == loops[inst.slot]:
                failed = True
            else:
                pc = inst.back if inst.back is not None else pc + 1
        elif isinstance(inst, _IAssertStart):
            if pos == 0 or (multiline and units[pos - 1] in _LINE_TERMINATORS):
                pc += 1
            else:
                failed = True
        elif isinstance(inst, _IAssertEnd):
            if pos == size or (multiline and units[pos] in _LINE_TERMINATORS):
                pc += 1
            else:
                failed = True
        else:
            return caps
        if failed:
            if not frames:
                return None
            pc, pos, undo_len = frames.pop()
            while len(undo) > undo_len:
                is_loop, slot, previous = undo.pop()
                if is_loop:
                    loops[slot] = previous if previous is not None else 0
                else:
                    caps[slot] = previous


# --- public compiled-RegExp type -----------------------------------------------


def _units_to_str(units: tuple[int, ...] | list[int]) -> str:
    raw = bytearray()
    for unit in units:
        raw.append(unit & 0xFF)
        raw.append((unit >> 8) & 0xFF)
    return bytes(raw).decode("utf-16-le", "surrogatepass")


def _bounds(caps: list[int | None]) -> tuple[int, int]:
    start = caps[0]
    end = caps[1]
    if start is None or end is None:
        raise AssertionError("match bounds not recorded")
    return start, end


def _expand_replacement(
    out: list[int],
    replacement: tuple[int, ...],
    units: tuple[int, ...],
    caps: list[int | None],
    group_count: int,
) -> None:
    start, end = _bounds(caps)
    index = 0
    while index < len(replacement):
        current = replacement[index]
        if current != 0x24 or index + 1 >= len(replacement):  # `$`
            out.append(current)
            index += 1
            continue
        follower = replacement[index + 1]
        if follower == 0x24:  # `$$`
            out.append(0x24)
            index += 2
        elif follower == 0x26:  # `$&`
            out.extend(units[start:end])
            index += 2
        elif follower == 0x60:  # `` $` ``
            out.extend(units[:start])
            index += 2
        elif follower == 0x27:  # `$'`
            out.extend(units[end:])
            index += 2
        elif 0x30 <= follower <= 0x39:
            first = follower - 0x30
            two_digit: int | None = None
            if index + 2 < len(replacement) and 0x30 <= replacement[index + 2] <= 0x39:
                two_digit = first * 10 + (replacement[index + 2] - 0x30)
            if two_digit is not None and 1 <= two_digit <= group_count:
                group, consumed = two_digit, 3
            elif 1 <= first <= group_count:
                group, consumed = first, 2
            else:
                group, consumed = 0, 0
            if consumed == 0:
                out.append(0x24)
                index += 1
            else:
                group_start = caps[2 * group]
                group_end = caps[2 * group + 1]
                if group_start is not None and group_end is not None:
                    out.extend(units[group_start:group_end])
                index += consumed
        else:
            out.append(0x24)
            index += 1


class JsRegExp:
    """A JS RegExp compiled over the closed subset (see the module docstring).

    Construction parses `pattern`/`flags` and rejects everything outside the
    subset; the compiled object exposes `test`, `search`, `replace` and
    `split` with JS UTF-16 code-unit semantics.

    The mutable `last_index` attribute mirrors JS `lastIndex` observably:
    `test` on a `g` regexp starts at `last_index`, sets it to the match end
    on success and resets it to 0 on failure (including `last_index` beyond
    the input); non-`g` `test`, `search` and `split` leave it untouched;
    `replace` on a `g` regexp always leaves it at 0.
    """

    def __init__(self, pattern: str, flags: str = "") -> None:
        parsed_flags = _parse_flags(flags)
        parser = _Parser(pattern)
        ast = parser.parse()
        self.source = pattern
        self.flags = flags
        self.last_index: int = 0
        self._ignore_case = parsed_flags.ignore_case
        self._global = parsed_flags.is_global
        self._multiline = parsed_flags.multiline
        self._program = _compile(ast, parser.group_count)

    def test(self, text: str) -> bool:
        """Mirror `RegExp.prototype.test`, including `lastIndex` on `g`.

        Non-`g` regexps always match from the start and never touch
        `last_index`. `g` regexps start at `last_index` (negative values
        clamp to 0 per ToLength), advance it to the match end on success,
        and reset it to 0 on failure.
        """

        units = utf16_code_units(text)
        if not self._global:
            return self._find_from(units, 0) is not None
        caps = self._find_from(units, max(self.last_index, 0))
        if caps is None:
            self.last_index = 0
            return False
        self.last_index = _bounds(caps)[1]
        return True

    def search(self, text: str) -> int:
        """Mirror `String.prototype.search`: code-unit index of the match or -1.

        Always searches from the start and preserves `last_index` across the
        call (the spec saves and restores `lastIndex`).
        """

        caps = self._find_from(utf16_code_units(text), 0)
        if caps is None:
            return -1
        return _bounds(caps)[0]

    def replace(self, text: str, replacement: str) -> str:
        """Mirror `String.prototype.replace(regexp, replacement)` with a string.

        Replaces the first match, or every match when the `g` flag is set.
        Supports the substitution tokens `$$`, `$&`, `` $` ``, `$'` and
        `$1`..`$99`. With `g` the whole input is scanned regardless of
        `last_index` and `last_index` is left at 0 afterwards (as JS
        `Symbol.replace` does); without `g`, `last_index` is untouched.
        """

        units = utf16_code_units(text)
        replacement_units = utf16_code_units(replacement)
        out: list[int] = []
        last = 0
        search_from = 0
        while search_from <= len(units):
            caps = self._find_from(units, search_from)
            if caps is None:
                break
            start, end = _bounds(caps)
            out.extend(units[last:start])
            _expand_replacement(out, replacement_units, units, caps, self._program.group_count)
            last = end
            if not self._global:
                break
            search_from = end + 1 if end == start else end
        if self._global:
            self.last_index = 0
        out.extend(units[last:])
        return _units_to_str(out)

    def split(self, text: str, limit: int | None = None) -> list[str]:
        """Mirror `String.prototype.split(regexp, limit)`.

        Patterns with capturing groups are rejected because JS splices capture
        values into the result; use a non-capturing group `(?:...)` instead.
        `last_index` is never touched (JS `Symbol.split` works on a fresh
        sticky copy of the regexp).
        """

        if self._program.group_count > 0:
            raise _unsupported(
                "split with capturing groups is not supported; use a non-capturing group `(?:...)`"
            )
        bound = 0xFFFFFFFF if limit is None else limit & 0xFFFFFFFF
        if bound == 0:
            return []
        units = utf16_code_units(text)
        size = len(units)
        if size == 0:
            return [] if self._exec_at(units, 0) is not None else [text]
        out: list[str] = []
        segment_start = 0
        cursor = 0
        while cursor < size:
            caps = self._exec_at(units, cursor)
            if caps is None:
                cursor += 1
                continue
            end = min(_bounds(caps)[1], size)
            if end == segment_start:
                cursor += 1
                continue
            out.append(_units_to_str(units[segment_start:cursor]))
            if len(out) == bound:
                return out
            segment_start = end
            cursor = end
        out.append(_units_to_str(units[segment_start:size]))
        return out

    def _exec_at(self, units: tuple[int, ...], at: int) -> list[int | None] | None:
        return _exec_at(self._program, units, at, self._ignore_case, self._multiline)

    def _find_from(self, units: tuple[int, ...], start: int) -> list[int | None] | None:
        for at in range(start, len(units) + 1):
            caps = self._exec_at(units, at)
            if caps is not None:
                return caps
        return None
