"""Correctness-first Luau obfuscator.

The old implementation used a partial VM and scope-blind identifier renaming.
That is unsafe for general Luau: unsupported syntax was either dropped or
executed through a different environment. This module only rewrites quoted
string literals, leaving every other token byte-for-byte intact.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass

MAX_INPUT = 8 * 1024 * 1024
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ObfuscationError(ValueError):
    pass


@dataclass
class Result:
    code: str
    changed: int
    warnings: list[str]


def _long_bracket(src: str, i: int) -> int | None:
    if i >= len(src) or src[i] != "[":
        return None
    j = i + 1
    while j < len(src) and src[j] == "=":
        j += 1
    if j < len(src) and src[j] == "[":
        return j - i - 1
    return None


def _long_end(src: str, i: int, equals: int) -> int:
    close = "]" + "=" * equals + "]"
    end = src.find(close, i + 2 + equals)
    return len(src) if end < 0 else end + len(close)


def validate_luau(src: str) -> list[str]:
    """Perform conservative lexical checks without pretending to be a parser."""
    if not src.strip():
        raise ObfuscationError("Input is empty.")
    if len(src.encode("utf-8", "surrogatepass")) > MAX_INPUT:
        raise ObfuscationError("Input exceeds the 8 MiB limit.")

    stack: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    quote: str | None = None
    i = 0
    while i < len(src):
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if src.startswith("--", i):
            eq = _long_bracket(src, i + 2)
            if eq is not None:
                i = _long_end(src, i + 2, eq)
            else:
                end = src.find("\n", i + 2)
                i = len(src) if end < 0 else end
            continue
        eq = _long_bracket(src, i)
        if eq is not None:
            i = _long_end(src, i, eq)
            continue
        if c in "'\"":
            quote = c
        elif c in "([{":
            stack.append(c)
        elif c in ")]}":
            if not stack or stack[-1] != pairs[c]:
                raise ObfuscationError(f"Unmatched '{c}' at character {i + 1}.")
            stack.pop()
        i += 1
    if quote:
        raise ObfuscationError("Unterminated string literal.")
    if stack:
        raise ObfuscationError(f"Unclosed delimiter '{stack[-1]}'.")
    return []


def _luau_quote(value: str) -> str:
    # %q is not used because its output is Python-specific. JSON strings are
    # valid Luau strings for these characters and preserve Unicode as UTF-8.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode_lua_string(raw: str) -> str | None:
    # Decode only the escapes we can reproduce confidently. If a literal has
    # an unusual Luau escape, leave it unchanged rather than changing meaning.
    body = raw[1:-1]
    out: list[str] = []
    i = 0
    simple = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
              "v": "\v", "a": "\a", "\\": "\\", "\"": "\"", "'": "'"}
    while i < len(body):
        if body[i] != "\\":
            out.append(body[i])
            i += 1
            continue
        if i + 1 >= len(body):
            return None
        e = body[i + 1]
        if e in simple:
            out.append(simple[e])
            i += 2
        elif e.isdigit():
            j = i + 1
            while j < len(body) and j < i + 4 and body[j].isdigit():
                j += 1
            n = int(body[i + 1:j])
            if n > 255:
                return None
            out.append(chr(n))
            i = j
        elif e == "x" and i + 3 < len(body):
            try:
                out.append(chr(int(body[i + 2:i + 4], 16)))
            except ValueError:
                return None
            i += 4
        else:
            return None
    return "".join(out)


def obfuscate(src: str, mode: str = "safe-strings", seed: int | None = None) -> Result:
    validate_luau(src)
    if mode == "safe":
        return Result(src, 0, ["Safe mode returned the source unchanged."])
    if mode not in {"safe-strings", "safe"}:
        raise ObfuscationError("Unknown mode. Choose safe or safe-strings.")

    rng = random.Random(seed)
    key = rng.randint(17, 239)
    parts: list[str] = []
    changed = 0
    i = 0
    while i < len(src):
        if src.startswith("--", i):
            eq = _long_bracket(src, i + 2)
            if eq is not None:
                end = _long_end(src, i + 2, eq)
            else:
                newline = src.find("\n", i + 2)
                end = len(src) if newline < 0 else newline
            parts.append(src[i:end])
            i = end
            continue
        eq = _long_bracket(src, i)
        if eq is not None:
            end = _long_end(src, i, eq)
            parts.append(src[i:end])
            i = end
            continue
        if src[i] not in "'\"":
            parts.append(src[i])
            i += 1
            continue
        q = src[i]
        j = i + 1
        while j < len(src):
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == q:
                j += 1
                break
            j += 1
        raw = src[i:j]
        value = _decode_lua_string(raw)
        if value is None:
            parts.append(raw)
        else:
            encoded = "".join(f"\\{(b ^ key) & 255:03d}" for b in value.encode("utf-8"))
            helper = "(function(s,k)local t={} for i=1,#s do t[i]=string.char(bit32.bxor(string.byte(s,i),k)) end return table.concat(t) end)"
            parts.append(f'{helper}("{encoded}",{key})')
            changed += 1
        i = j
    warnings = [
        "Only quoted string literals were transformed.",
        "Identifiers, scopes, control flow, tables, calls, events, and Roblox API expressions were preserved.",
    ]
    return Result("".join(parts), changed, warnings)


if __name__ == "__main__":
    import sys
    print(obfuscate(sys.stdin.read()).code)