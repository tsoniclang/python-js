"""ArrayBuffer, DataView, and practical typed-array carriers."""

import math
import struct
from collections.abc import Iterable
from typing import ClassVar

from tsonic_python_js.errors import JsRangeError

_SIGNED_LIMITS = {
    "b": (-128, 127, 8),
    "h": (-32768, 32767, 16),
    "i": (-2147483648, 2147483647, 32),
}
_UNSIGNED_LIMITS = {
    "B": (0, 255, 8),
    "H": (0, 65535, 16),
    "I": (0, 4294967295, 32),
}


class ArrayBuffer:
    __slots__ = ("bytes",)
    bytes: bytearray

    def __init__(self, byte_length: int) -> None:
        if byte_length < 0:
            raise JsRangeError("invalid ArrayBuffer length")
        self.bytes = bytearray(byte_length)

    @property
    def byte_length(self) -> int:
        return len(self.bytes)

    def slice(self, start: int = 0, end: int | None = None) -> "ArrayBuffer":
        from_index, to_index = _bounds(start, self.byte_length, end)
        result = ArrayBuffer(to_index - from_index)
        result.bytes[:] = self.bytes[from_index:to_index]
        return result


class DataView:
    __slots__ = ("buffer", "byte_length", "byte_offset")

    def __init__(
        self, buffer: ArrayBuffer, byte_offset: int = 0, byte_length: int | None = None
    ) -> None:
        length = buffer.byte_length - byte_offset if byte_length is None else byte_length
        _check_range(buffer, byte_offset, length)
        self.buffer = buffer
        self.byte_offset = byte_offset
        self.byte_length = length

    def get_int8(self, byte_offset: int) -> int:
        return int(self._unpack("b", byte_offset, False))

    def set_int8(self, byte_offset: int, value: int) -> None:
        self._pack("b", byte_offset, _coerce_integer(value, "b"), False)

    def get_uint8(self, byte_offset: int) -> int:
        return int(self._unpack("B", byte_offset, False))

    def set_uint8(self, byte_offset: int, value: int) -> None:
        self._pack("B", byte_offset, _coerce_integer(value, "B"), False)

    def get_int16(self, byte_offset: int, little_endian: bool = False) -> int:
        return int(self._unpack("h", byte_offset, little_endian))

    def set_int16(self, byte_offset: int, value: int, little_endian: bool = False) -> None:
        self._pack("h", byte_offset, _coerce_integer(value, "h"), little_endian)

    def get_uint16(self, byte_offset: int, little_endian: bool = False) -> int:
        return int(self._unpack("H", byte_offset, little_endian))

    def set_uint16(self, byte_offset: int, value: int, little_endian: bool = False) -> None:
        self._pack("H", byte_offset, _coerce_integer(value, "H"), little_endian)

    def get_int32(self, byte_offset: int, little_endian: bool = False) -> int:
        return int(self._unpack("i", byte_offset, little_endian))

    def set_int32(self, byte_offset: int, value: int, little_endian: bool = False) -> None:
        self._pack("i", byte_offset, _coerce_integer(value, "i"), little_endian)

    def get_uint32(self, byte_offset: int, little_endian: bool = False) -> int:
        return int(self._unpack("I", byte_offset, little_endian))

    def set_uint32(self, byte_offset: int, value: int, little_endian: bool = False) -> None:
        self._pack("I", byte_offset, _coerce_integer(value, "I"), little_endian)

    def get_float32(self, byte_offset: int, little_endian: bool = False) -> float:
        return self._unpack("f", byte_offset, little_endian)

    def set_float32(self, byte_offset: int, value: float, little_endian: bool = False) -> None:
        self._pack("f", byte_offset, value, little_endian)

    def get_float64(self, byte_offset: int, little_endian: bool = False) -> float:
        return self._unpack("d", byte_offset, little_endian)

    def set_float64(self, byte_offset: int, value: float, little_endian: bool = False) -> None:
        self._pack("d", byte_offset, value, little_endian)

    def _unpack(self, code: str, byte_offset: int, little_endian: bool) -> int | float:
        fmt = ("<" if little_endian else ">") + code
        size = struct.calcsize(fmt)
        absolute = self._absolute_offset(byte_offset, size)
        return struct.unpack_from(fmt, self.buffer.bytes, absolute)[0]

    def _pack(self, code: str, byte_offset: int, value: int | float, little_endian: bool) -> None:
        fmt = ("<" if little_endian else ">") + code
        size = struct.calcsize(fmt)
        absolute = self._absolute_offset(byte_offset, size)
        struct.pack_into(fmt, self.buffer.bytes, absolute, value)

    def _absolute_offset(self, byte_offset: int, size: int) -> int:
        if byte_offset < 0 or byte_offset + size > self.byte_length:
            raise JsRangeError("DataView offset out of bounds")
        return self.byte_offset + byte_offset


class TypedArray:
    __slots__ = ("buffer", "byte_length", "byte_offset", "length")
    format_code: ClassVar[str]
    element_size: ClassVar[int]
    clamp: ClassVar[bool] = False
    float_kind: ClassVar[bool] = False

    def __init__(
        self,
        source: int | Iterable[object] | ArrayBuffer,
        byte_offset: int = 0,
        length: int | None = None,
    ) -> None:
        if isinstance(source, ArrayBuffer):
            remaining = source.byte_length - byte_offset
            count = remaining // self.element_size if length is None else length
            _check_range(source, byte_offset, count * self.element_size)
            self.buffer = source
            self.byte_offset = byte_offset
            self.length = count
            self.byte_length = count * self.element_size
            return
        values = [0] * source if isinstance(source, int) else list(source)
        self.buffer = ArrayBuffer(len(values) * self.element_size)
        self.byte_offset = 0
        self.length = len(values)
        self.byte_length = len(values) * self.element_size
        for index, value in enumerate(values):
            self.set(index, value)

    def get(self, index: int) -> int | float:
        self._check_index(index)
        return struct.unpack_from(self._fmt(), self.buffer.bytes, self._offset(index))[0]

    def set(self, index: int, value: object) -> None:
        self._check_index(index)
        struct.pack_into(self._fmt(), self.buffer.bytes, self._offset(index), self._coerce(value))

    def values(self) -> list[int | float]:
        return [self.get(index) for index in range(self.length)]

    def slice(self, start: int = 0, end: int | None = None) -> "TypedArray":
        from_index, to_index = _bounds(start, self.length, end)
        return type(self)(self.values()[from_index:to_index])

    def subarray(self, start: int = 0, end: int | None = None) -> "TypedArray":
        from_index, to_index = _bounds(start, self.length, end)
        return type(self)(
            self.buffer,
            self.byte_offset + from_index * self.element_size,
            to_index - from_index,
        )

    def _coerce(self, value: object) -> int | float:
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise JsRangeError("typed array value must be numeric")
        number = float(value)
        if self.clamp:
            if math.isnan(number):
                return 0
            return min(max(round(number), 0), 255)
        return number if self.float_kind else _coerce_integer(value, self.format_code)

    def _fmt(self) -> str:
        return "=" + self.format_code

    def _offset(self, index: int) -> int:
        return self.byte_offset + index * self.element_size

    def _check_index(self, index: int) -> None:
        if index < 0 or index >= self.length:
            raise JsRangeError("typed array index out of bounds")


class Int8Array(TypedArray):
    format_code = "b"
    element_size = 1


class Uint8Array(TypedArray):
    format_code = "B"
    element_size = 1


class Uint8ClampedArray(TypedArray):
    format_code = "B"
    element_size = 1
    clamp = True


class Int16Array(TypedArray):
    format_code = "h"
    element_size = 2


class Uint16Array(TypedArray):
    format_code = "H"
    element_size = 2


class Int32Array(TypedArray):
    format_code = "i"
    element_size = 4


class Uint32Array(TypedArray):
    format_code = "I"
    element_size = 4


class Float32Array(TypedArray):
    format_code = "f"
    element_size = 4
    float_kind = True


class Float64Array(TypedArray):
    format_code = "d"
    element_size = 8
    float_kind = True


def _bounds(start: int, length: int, end: int | None) -> tuple[int, int]:
    first = max(length + start, 0) if start < 0 else min(start, length)
    raw_end = length if end is None else end
    last = max(length + raw_end, 0) if raw_end < 0 else min(raw_end, length)
    return first, max(first, last)


def _check_range(buffer: ArrayBuffer, byte_offset: int, byte_length: int) -> None:
    if byte_offset < 0 or byte_length < 0 or byte_offset + byte_length > buffer.byte_length:
        raise JsRangeError("view out of bounds")


def _coerce_integer(value: object, format_code: str) -> int:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise JsRangeError("typed array value must be numeric")
    number = float(value)
    if not math.isfinite(number) or number == 0:
        integer = 0
    else:
        integer = int(math.copysign(math.floor(abs(number)), number))
    if format_code in _UNSIGNED_LIMITS:
        _minimum, _maximum, bits = _UNSIGNED_LIMITS[format_code]
        return integer % 2**bits
    minimum, _maximum, bits = _SIGNED_LIMITS[format_code]
    unsigned = integer % 2**bits
    sign_bit = 2 ** (bits - 1)
    return unsigned - 2**bits if unsigned >= sign_bit else max(unsigned, minimum)
