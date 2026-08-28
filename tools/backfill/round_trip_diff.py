#!/usr/bin/env python3
"""
round_trip_diff.py — compare a source spec markdown against its re-rendered form.

Normalizes whitespace the way the user specified (2026-08-28): CRLF→LF, trailing
whitespace stripped line-by-line, and blank-line collapse around block boundaries.
Emits (a) a list of post-normalization differences and (b) a unified diff body for
the PR comment.

Exit code 0 if no post-normalization differences; 1 if there are; 2 on usage error.
"""

import re
import sys
import difflib


def normalize(text):
    """CRLF→LF, strip trailing spaces per line, collapse 3+ blank lines to one."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    out = []
    prev_blank = False
    for ln in lines:
        s = ln.rstrip()
        if s == "":
            if prev_blank:
                continue  # collapse consecutive blanks to a single blank line
            prev_blank = True
        else:
            prev_blank = False
        out.append(s)
    # drop the single trailing blank line if present
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) != 3:
        print("usage: round_trip_diff.py <source.md> <rendered.md>", file=sys.stderr)
        sys.exit(2)
    src_path, ren_path = sys.argv[1], sys.argv[2]
    with open(src_path, "r", encoding="utf-8") as f:
        src = f.read()
    with open(ren_path, "r", encoding="utf-8") as f:
        ren = f.read()

    src_n = normalize(src)
    ren_n = normalize(ren)

    if src_n == ren_n:
        print("NORMALIZED-IDENTICAL")
        print("all differences were normalizeable whitespace (CRLF, trailing-space, blank-line)")
        sys.exit(0)

    src_lines = src_n.split("\n")
    ren_lines = ren_n.split("\n")
    diff = list(difflib.unified_diff(src_lines, ren_lines, fromfile="source", tofile="rendered", lineterm=""))

    print("DIFF-CONTENT")
    for line in diff:
        print(line)
    print("---")
    print(f"{len(diff)} diff lines across {len(src_lines)} source / {len(ren_lines)} rendered lines")
    sys.exit(1)


if __name__ == "__main__":
    main()