#!/usr/bin/env python3
"""Implicit-global audit for the sp500-exec-comp JS bundle.

Catches the 2026-09-11 15:30 bug class: an identifier assigned without
var/let/const (usually inside an `if` branch) and then read unconditionally,
which throws ReferenceError at runtime for the users who skip the branch.
That bug broke the peer-network canvas for every default visitor for 16 days.

Usage:
    python3 implicit_global_audit.py ~/repos/sp500-exec-comp/js/app.js \
        ~/repos/sp500-exec-comp/js/charts.js \
        ~/repos/sp500-exec-comp/js/network.js \
        ~/repos/sp500-exec-comp/js/advanced-filters.js

Exit code is always 0: this is a triage aid, not a gate. A human must check
each reported candidate against the known false-positive classes below.

Known false-positive classes (verify by grepping the file):
  - HTML/SVG attribute names inside JS strings: class, fill, stroke, title,
    role, tabindex, viewBox, width, height, points, opacity, dasharray,
    data-* fragments (e.g. data-action='', data-sort=''). These appear as
    `name=''` after string stripping.
  - Text content inside HTML strings: Q1, Q4, "Click", etc.
  - Intentional module-level shared state assigned before any read in the
    event flow (e.g. _cfNormMode in network.js). Works in sloppy mode;
    flag only if a read can precede the first assignment.

Known limitation: regex literals are not tokenized (a `/` not followed by
/ or * is treated as division, and a quote inside a character class like
/[.,'']/ can desync the string scanner). Consequence: declarations swallowed
inside the desynced region show up as false "undeclared" hits, and real
issues inside the region could be missed. When triaging, confirm each
candidate with: grep -nE '(var|let|const)[^;]*\\b<name>\\b' <file>.

Method: single-pass tokenizer strips comments and string/template contents
(keeping ${} interpolation code), then collects var/let/const declarations
(brace-aware), function/catch/param names, bare-identifier assignments, and
reads. Reports identifiers that are assigned but never declared.
"""

import re
import sys

_WORD_RE = re.compile(r"[A-Za-z_$][\w$]*")
_NUM_RE = re.compile(r"\d[\w.]*")

BUILTINS = set(
    """undefined NaN Infinity null true false this arguments console window
    document localStorage sessionStorage navigator location history screen
    performance requestAnimationFrame cancelAnimationFrame setTimeout
    clearTimeout setInterval clearInterval fetch Promise Map Set WeakMap
    WeakSet Symbol BigInt Proxy Reflect JSON Math Date RegExp Error Object
    Array String Number Boolean Function Intl URL URLSearchParams Blob
    FileReader Image Audio Worker Notification indexedDB crypto
    getComputedStyle matchMedia devicePixelRatio innerWidth innerHeight
    scrollX scrollY pageXOffset pageYOffset alert confirm prompt open close
    blur focus print requestIdleCallback ResizeObserver IntersectionObserver
    MutationObserver CSS CustomEvent Event MouseEvent KeyboardEvent TouchEvent
    WheelEvent d3 topojson ClipboardItem""".split()
)


def strip(src):
    """Remove comments and string/template contents with a real tokenizer.

    Also consumes regex literals (heuristic: a `/` not starting a comment is
    a regex when the previous significant token cannot end an expression).
    Without this, a quote inside a regex character class (e.g. /[.,'']/)
    desyncs the string scanner and swallows subsequent declarations.
    """
    # chars after which a `/` starts a regex rather than division
    REGEX_AFTER = set("(,=:[!&|?{};+-*%<>^~")
    out = []
    i, n = 0, len(src)
    prev_sig = None  # last significant token emitted (None at start)

    while i < n:
        c = src[i]
        if c in " \t\n\r":
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in ("'", '"', "`"):
            q = c
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                if q == "`" and src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                    out.append("${")
                    i += 2
                    depth = 1
                    while i < n and depth:
                        if src[i] == "{":
                            depth += 1
                        elif src[i] == "}":
                            depth -= 1
                        out.append(src[i])
                        i += 1
                    continue
                i += 1
            out.append("S")
            prev_sig = "S"  # string literal end -> division follows
            continue
        if c == "/":
            # decide regex vs division by previous significant token
            if prev_sig is None or prev_sig in REGEX_AFTER or (
                    isinstance(prev_sig, str) and prev_sig.startswith("kw:")):
                # consume regex literal: /.../flags  (handles [..] and escapes)
                i += 1
                in_class = False
                while i < n:
                    ch = src[i]
                    if ch == "\\":
                        i += 2
                        continue
                    if ch == "[":
                        in_class = True
                    elif ch == "]":
                        in_class = False
                    elif ch == "/" and not in_class:
                        i += 1
                        break
                    elif ch == "\n":
                        break  # unterminated; bail
                    i += 1
                while i < n and src[i].isalpha():
                    i += 1  # flags
                out.append("R")
                prev_sig = "R"
                continue
            else:
                out.append(c)  # division operator
                prev_sig = c
                i += 1
                continue
        # keyword check for regex-after-keyword (return, typeof, etc.)
        m = _WORD_RE.match(src, i)
        if m:
            word = m.group(0)
            out.append(word)
            prev_sig = ("kw:" + word) if word in (
                "return", "typeof", "instanceof", "in", "of", "new",
                "delete", "void", "throw", "yield", "await", "case") else word[-1]
            i += len(word)
            continue
        m = _NUM_RE.match(src, i)
        if m:
            out.append("0")
            prev_sig = "0"
            i += len(m.group(0))
            continue
        out.append(c)
        prev_sig = c
        i += 1
    return "".join(out)


def find_semicolon(src, i):
    depth = 0
    while i < len(src):
        c = src[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return i
            depth -= 1
        elif c == ";" and depth == 0:
            return i
        i += 1
    return len(src)


def collect_declared(src):
    declared = set()
    for m in re.finditer(r"\b(?:var|let|const)\s", src):
        j = m.end()
        decl = src[j : find_semicolon(src, j)]
        parts, depth, cur = [], 0, ""
        for c in decl:
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            if c == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += c
        parts.append(cur)
        for part in parts:
            nm = re.match(r"\s*([A-Za-z_$][\w$]*)", part)
            if nm:
                declared.add(nm.group(1))
    for m in re.finditer(r"\bfunction\s+([A-Za-z_$][\w$]*)", src):
        declared.add(m.group(1))
    for m in re.finditer(r"\bcatch\s*\(\s*([A-Za-z_$][\w$]*)", src):
        declared.add(m.group(1))
    for m in re.finditer(r"function\s*[^(]*\(([^)]*)\)", src):
        for p in m.group(1).split(","):
            p = p.strip().split("=")[0].strip()
            if re.match(r"^[A-Za-z_$][\w$]*$", p):
                declared.add(p)
    for m in re.finditer(
        r"(?:\(\s*([A-Za-z_$][\w$, =]*?)\s*\)|([A-Za-z_$][\w$]*))\s*=>", src
    ):
        params = m.group(1) or m.group(2)
        for p in params.split(","):
            p = p.strip().split("=")[0].strip()
            if re.match(r"^[A-Za-z_$][\w$]*$", p):
                declared.add(p)
    for m in re.finditer(r"for\s*\(\s*(?:var|let|const)\s+([A-Za-z_$][\w$]*)", src):
        declared.add(m.group(1))
    return declared


def audit(path):
    src = strip(open(path).read())
    declared = collect_declared(src)
    assigns = {}
    for m in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*=(?![=>])", src):
        assigns.setdefault(m.group(1), []).append(m.start(1))
    for m in re.finditer(
        r"for\s*\(\s*(?!(?:var|let|const)\b)([A-Za-z_$][\w$]*)\s+(?:of|in)\b", src
    ):
        assigns.setdefault(m.group(1), []).append(m.start(1))
    reads = {}
    for m in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)(?!\s*=)", src):
        reads.setdefault(m.group(1), []).append(m.start(1))
    cands = {
        name: pos
        for name, pos in assigns.items()
        if name not in declared and name not in BUILTINS
    }
    print(f"== {path}: {len(cands)} assigned-but-never-declared identifiers")
    for name in sorted(cands):
        nr = len(reads.get(name, []))
        first = cands[name][0]
        ctx = src[max(0, first - 70) : first + 40].replace("\n", " ").strip()
        tag = "READ x%d" % nr if nr else "write-only"
        print(f"   {name}: assigned x{len(cands[name])}, {tag}")
        print(f"      ...{ctx[-110:]}")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        audit(f)
