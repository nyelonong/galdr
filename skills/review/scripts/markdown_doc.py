#!/usr/bin/env python3
"""Line-oriented rendering of a markdown document for the document reviewer.

`rows(text)` returns one dict per *source* line, in order, 1-based.  The
reviewer shows them as a table so a comment on "line 42" always names exactly
one source line, which is why the row count is pinned to the line count:
never drop, merge, reorder or invent a row.

Every row is a plain, HTML-safe fragment: the source is escaped before any
formatting is applied, and no source text ever reaches the output as a raw
`<`, `>` or `&`.
"""
from __future__ import annotations

import re

BOM = chr(0xFEFF)  # a UTF-8 byte-order mark that survived decoding

# Block detection -----------------------------------------------------------
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*)$")
_HEADING_TAIL = re.compile(r"(?:[ \t]+#+)+[ \t]*$")
_QUOTE = re.compile(r"^>[ \t]?")
_LIST = re.compile(r"^(?:[-*+]|\d+[.)])(?:[ \t]|$)")
_TASK = re.compile(r"\[([ xX])\](?:[ \t]|$)")
_RULE = re.compile(r"^([*_-])(?:[ \t]*\1){2,}$")

# Inline formatting ---------------------------------------------------------
# Code spans and links are lifted out first, behind placeholders that carry no
# emphasis character, so the rest of the line can be formatted as a whole (a
# `**bold**` may span a code span) while the lifted text stays literal.
_CODE_SPAN = re.compile(r"(`+)([^`]*?)\1")
_LINK = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")
_PLACEHOLDER = re.compile("\x00(\\d+)\x00")
# The `[^\s*]`-style guards keep `***both***` from pairing a `**` against a
# `*`, which would produce `<b><i>x</b></i>` instead of a properly nested pair.
_BOLD = re.compile(r"\*\*(?=[^\s*])(.+?)(?<=[^\s*])\*\*|__(?=[^\s_])([^_]+?)(?<=[^\s_])__(?!\w)")
_STRIKE = re.compile(r"~~(?=[^\s~])(.+?)(?<=[^\s~])~~")
_ITALIC = re.compile(r"\*(?=[^\s*])([^*]+?)(?<=[^\s*])\*|(?<![\w*\\])_(?=[^\s_])([^_]+?)(?<=[^\s_])_(?!\w)")

CHECKED_MARK = "☑ "  # ☑ a task-list item that is done
UNCHECKED_MARK = "☐ "  # ☐ one that is not


def _escape(text: str) -> str:
    """HTML-escape; `&` first so the escapes introduced below stay literal."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _source_lines(text: str) -> list[str]:
    """Split on newlines only, so exotic Unicode separators stay inside a line."""
    if text.startswith(BOM):
        text = text[len(BOM) :]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":  # a trailing newline is a terminator, not a line
        lines.pop()
    return lines


def _emphasis(text: str) -> str:
    """Escape, then wrap the supported emphasis markers.  Applied to the parts
    of a line that lie outside code spans."""
    out = _escape(text)
    out = _BOLD.sub(lambda m: "<b>%s</b>" % (m.group(1) or m.group(2)), out)
    out = _STRIKE.sub(r"<s>\1</s>", out)
    out = _ITALIC.sub(lambda m: "<i>%s</i>" % (m.group(1) or m.group(2)), out)
    return out


def _inline(text: str) -> str:
    """Render inline markdown.  Links keep their label and lose their target:
    the reviewer is a local page with a locked-down CSP and has no use for
    navigation, so an `<a>` tag is never emitted."""
    stashed: list[str] = []

    def stash(rendered: str) -> str:
        stashed.append(rendered)
        return "\x00%d\x00" % (len(stashed) - 1)

    work = _CODE_SPAN.sub(lambda m: stash("<code>%s</code>" % _escape(m.group(2))), text)
    work = _LINK.sub(lambda m: stash(_emphasis(m.group(1))), work)
    out = _emphasis(work)

    def restore(match: re.Match) -> str:
        index = int(match.group(1))
        return stashed[index] if index < len(stashed) else match.group(0)  # a NUL in the source is not an index

    return _PLACEHOLDER.sub(restore, out)


def _fence_marker(stripped: str) -> tuple[str, int] | None:
    if stripped[:3] in ("```", "~~~"):
        return stripped[0], len(stripped) - len(stripped.lstrip(stripped[0]))
    return None


def _classify(stripped: str) -> str:
    if _HEADING.match(stripped):
        return "heading"
    if _QUOTE.match(stripped):
        return "quote"
    if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3:
        return "table"
    if _RULE.match(stripped):  # before the list rule, so `---` is not a bullet
        return "rule"
    if _LIST.match(stripped):
        return "list"
    if not stripped:
        return "blank"
    return "text"


def _row(number: int, stripped: str, raw: str = "") -> dict:
    kind = _classify(stripped)
    # `text` is the raw source line, kept beside the rendered html so a block can
    # hand a real markdown engine exactly the lines the comment will name.
    row: dict = {"n": number, "kind": kind, "text": raw if raw else stripped}
    if kind == "blank":
        row["html"] = ""
        return row
    if kind == "rule":
        row["html"] = _escape(stripped)
        return row

    # Block markers are structural: the row already reports kind/level/checked,
    # so the html carries the content only.
    if kind == "heading":
        match = _HEADING.match(stripped)
        row["level"] = min(len(match.group(1)), 6)
        row["html"] = _inline(_HEADING_TAIL.sub("", match.group(2).rstrip()))
        return row
    if kind == "quote":
        row["html"] = _inline(_QUOTE.sub("", stripped, count=1))
        return row
    if kind == "table":
        row["html"] = _inline(stripped[1:-1].strip())
        return row
    if kind == "text":
        row["html"] = _inline(stripped)
        return row

    content = stripped[_LIST.match(stripped).end() :]
    task = _TASK.match(content)
    if task:
        checked = task.group(1) in "xX"
        row["checked"] = checked
        prefix = CHECKED_MARK if checked else UNCHECKED_MARK
        row["html"] = prefix + _inline(content[task.end() :])
        return row
    row["html"] = _inline(content)
    return row


def rows(text: str) -> list[dict]:
    """One row per source line of `text`, in order.

    Each row is `{"n": int, "kind": str, "html": str}`, plus `"level"` for
    headings and `"checked"` for task-list items.  Malformed input never
    raises: anything unclassifiable is a `text` row.
    """
    out: list[dict] = []
    fence: tuple[str, int] | None = None
    for number, line in enumerate(_source_lines(text), start=1):
        stripped = line.strip()
        marker = _fence_marker(stripped)
        if fence is not None:
            # Inside a fence every line is code, blank ones included, and only
            # a matching closing marker ends the fence.
            if (
                marker
                and marker[0] == fence[0]
                and marker[1] >= fence[1]
                and not stripped[marker[1] :].strip()
            ):
                fence = None
            out.append({"n": number, "kind": "code", "html": _escape(line), "text": line})
            continue
        if marker:
            fence = marker
            out.append({"n": number, "kind": "code", "html": _escape(line), "text": line})
            continue
        out.append(_row(number, stripped, line))
    return out
# --------------------------------------------------------------------------
# blocks
# --------------------------------------------------------------------------

# A block is a run of source lines the page renders as one thing.  Every block
# carries the inclusive source range it came from, which is what keeps a comment
# anchored to the file even though the document is rendered as a document.
#
# The grouping below is deliberately boring: runs of the same kind, headings and
# rules on their own, and a list item that absorbs the wrapped lines beneath it
# rather than splitting into a bullet and a stray paragraph.
_RUN_KINDS = ("code", "table", "quote", "blank", "text")


def blocks(text: str) -> list[dict]:
    """Group `text` into rendered blocks, each carrying its source line range.

    Invariant: the ranges are contiguous, non-overlapping, and cover every
    source line exactly once, so a comment can name any line of the document
    and no line can fall outside every block.  Pure and deterministic: the same
    bytes always produce the same ranges, or an approval recorded against one
    rendering would point somewhere else on the next.
    """
    grouped: list[dict] = []
    lines = rows(text)
    index = 0
    while index < len(lines):
        row = lines[index]
        kind = row["kind"]
        if kind == "heading" or kind == "rule":
            grouped.append(_block(kind, [row]))
            index += 1
            continue
        if kind == "list":
            # The item plus any wrapped continuation lines: a bullet whose text
            # spills onto the next source line is still one block.
            taken = [row]
            index += 1
            while index < len(lines) and lines[index]["kind"] == "text":
                taken.append(lines[index])
                index += 1
            grouped.append(_block("list", taken))
            continue
        taken = [row]
        index += 1
        while index < len(lines) and lines[index]["kind"] == kind and kind in _RUN_KINDS:
            taken.append(lines[index])
            index += 1
        grouped.append(_block(kind, taken))
    return grouped


def _block(kind: str, taken: "list[dict]") -> dict:
    """One block from its rows: the range, and the rendered body."""
    block: dict = {
        "kind": kind,
        "start": taken[0]["n"],
        "end": taken[-1]["n"],
        "html": "\n".join(item["html"] for item in taken),
    }
    if taken[0].get("level") is not None:
        block["level"] = taken[0]["level"]
    if taken[0].get("checked") is not None:
        block["checked"] = taken[0]["checked"]
    # The raw source travels with every block: a real markdown engine renders
    # the inside of a block, and the reviewer needs the fence's language. The
    # html above stays the escaped fallback when no engine is available.
    block["source"] = "\n".join(item.get("text", "") for item in taken)
    return block
