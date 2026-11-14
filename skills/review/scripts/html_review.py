#!/usr/bin/env python3
"""A second reviewer backend for the task-review protocol: one local HTML page.

``RDG_CONTROL_COMMAND=/path/to/html_review.py`` makes the pre-commit gate in
``scripts/task_review.py`` open this reviewer instead of RDG. Both speak review
protocol v1 -- one JSON request on argv or stdin, one JSON result line on
stdout -- so the client cannot tell the two apart and either one can be chosen.

Shape of a run:

    html_review.py --review '{"version":"1", ...}'   # or the request on stdin
    -> validate the request exactly like RDG's ReviewRequest::validate
    -> collect the diff with the client's own snapshot code
    -> serve one self-contained page on 127.0.0.1 behind a random token
    -> wait for a human decision
    -> print exactly one JSON result line, exit 0

The diff comes from ``task_review`` rather than from a second implementation of
git plumbing, so this reviewer can never show a different change than the one
the client fingerprints and re-verifies.

A request it cannot understand is a diagnostic on stderr and a non-zero exit. A
window closed without a decision is ``cancelled`` with no annotations, which the
client treats as "no approval": this backend fails closed like the client does.

Environment:

    HTML_REVIEW_NO_BROWSER=1   serve the page without opening it; the URL is
                               printed on stderr either way
    HTML_REVIEW_URL_FILE=PATH  publish the live page URL to a private file for
                               callers that cannot read the streamed stderr;
                               remove the file when the review ends
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Sequence

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import markdown_doc  # noqa: E402  (line-oriented rendering, beside this script)
import task_review  # noqa: E402  (the client lives beside this script and is not a package)

PROTOCOL_VERSION = task_review.PROTOCOL_VERSION
PRODUCER = "html_review.py"
HOST = "127.0.0.1"

# Set to 1 (or any truthy word) to keep the review page from being opened. Tests
# set it; a human who prefers to paste the printed URL can too.
NO_BROWSER_ENV = "HTML_REVIEW_NO_BROWSER"

# The live URL file supports callers that cannot read streamed diagnostics.
# It is written 0600 while the review runs and removed when it ends.
URL_FILE_ENV = "HTML_REVIEW_URL_FILE"

# A review that nobody can finish must not outlive its usefulness: a client
# killed with SIGKILL cannot clean this process up, so the reviewer bounds
# itself. The lifetime matches the client's own default, and the idle bound
# catches a page that was printed but never opened.
LIFETIME_SECONDS = 1800.0
IDLE_SECONDS = 900.0
LIFETIME_ENV = "HTML_REVIEW_LIFETIME"
IDLE_ENV = "HTML_REVIEW_IDLE"

# A page that is closing is either gone or about to be replaced by a reload, and
# a browser may report the close before or after it requests the replacement.
# Each page served carries a number; a close withdraws the review only when it
# names the newest page and no newer page is requested within this long.
CLOSE_GRACE_SECONDS = 5.0

EXIT_OK = 0
EXIT_ERROR = 2

# JetBrains Mono, SIL Open Font License 1.1 (see assets/fonts/OFL.txt). It ships
# with the reviewer and is served from this same origin rather than fetched, so
# the page keeps working offline and its CSP still names no third party.
ASSET_FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
FONT_FILES = {
    "jetbrains-mono-400.woff2": ASSET_FONTS / "jetbrains-mono-400.woff2",
    "jetbrains-mono-700.woff2": ASSET_FONTS / "jetbrains-mono-700.woff2",
    "inter-latin-var.woff2": ASSET_FONTS / "inter-latin-var.woff2",
    "source-serif-4-latin-var.woff2": ASSET_FONTS / "source-serif-4-latin-var.woff2",
}

# Third-party code is vendored, never fetched: the page must work with no
# network, and its policy may keep naming no origin but this one.
ASSET_VENDOR = Path(__file__).resolve().parents[1] / "assets" / "vendor"
VENDOR_FILES = {
    "markdown-it.min.js": "text/javascript; charset=utf-8",
    "markdown-it-task-lists.min.js": "text/javascript; charset=utf-8",
    "markdown-it-footnote.min.js": "text/javascript; charset=utf-8",
    "highlight.min.js": "text/javascript; charset=utf-8",
    "mermaid.min.js": "text/javascript; charset=utf-8",
}

# Inline style and script are all the page needs, and same-origin requests are
# the only network it may make: the review payload, the decision, the beacon that
# reports a closed window, and the bundled code font. Everything else -- images,
# other origins, frames -- stays denied.
CONTENT_SECURITY_POLICY = (
    # One directive per name: a repeated script-src silently replaces the first,
    # which would block the page's own inline script.
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; font-src 'self'"
)
SECURITY_HEADERS = (
    ("Content-Security-Policy", CONTENT_SECURITY_POLICY),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Cache-Control", "no-store"),
)

MAX_BODY_BYTES = 8 << 20
MAX_RENDERED_LINES_PER_FILE = 1500

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
URL_PATTERN = re.compile(r"http://127\.0\.0\.1:\d+/[A-Za-z0-9_-]+/")

GitRunner = Callable[..., bytes]


class DecisionError(Exception):
    """The review page asked for something the protocol cannot carry."""


# --------------------------------------------------------------------------
# request
# --------------------------------------------------------------------------


def parse_request(text: str) -> task_review.ReviewRequest:
    """Validates a request the way RDG's ``ReviewRequest::validate`` does.

    The client already owns path normalisation, duplicate-root detection and the
    protocol version; this adds RDG's two remaining rules, that a review id and
    a criterion must be more than whitespace.
    """
    request = task_review.parse_request_json(text)
    if not request.review_id.strip():
        raise task_review.ResultError("review_id must not be empty")
    if not request.criterion.strip():
        raise task_review.ResultError("criterion must not be empty")
    return request


def read_request_text(argument: "str | None") -> str:
    """The request is the ``--review`` value, or stdin when the value is absent."""
    if argument:
        return argument
    return sys.stdin.read()


# --------------------------------------------------------------------------
# diff
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffLine:
    """One rendered patch line: ``context``, ``add``, ``remove`` or ``meta``.

    ``old_line`` and ``new_line`` are 1-based line numbers on that side of the
    diff, or ``None`` when the line does not exist there. Only the first three
    types anchor a comment; a header line has no position to point at.
    """

    type: str
    old_line: "int | None"
    new_line: "int | None"
    text: str

    @property
    def selectable(self) -> bool:
        return self.type in ("context", "add", "remove")

    def payload(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "old_line": self.old_line,
            "new_line": self.new_line,
            "text": self.text,
        }


@dataclass(frozen=True)
class FileDiff:
    repository: str
    path: str
    old_path: "str | None"
    status: str
    binary: bool
    added: int
    removed: int
    lines: tuple[DiffLine, ...]
    text: "str | None" = None
    language: "str | None" = None

    def payload(self) -> dict[str, Any]:
        payload = {
            "repository": self.repository,
            "path": self.path,
            "old_path": self.old_path,
            "status": self.status,
            "binary": self.binary,
            "added": self.added,
            "removed": self.removed,
            "lines": [line.payload() for line in self.lines],
        }
        if self.language:
            payload["language"] = self.language
        if self.text is not None:
            payload["text"] = self.text
        return payload


def parse_patch(patch: bytes) -> "tuple[list[DiffLine], int, int, bool]":
    """Splits one file patch into display lines.

    Returns the lines, how many were added and removed, and whether the patch is
    binary (a binary patch has no lines a human can comment on).
    """
    lines: list[DiffLine] = []
    added = 0
    removed = 0
    binary = False
    old_line: "int | None" = None
    new_line: "int | None" = None
    in_hunk = False

    for raw in task_review.split_patch_lines(patch.decode("utf-8", "replace")):
        header = HUNK_HEADER.match(raw)
        if header is not None:
            in_hunk = True
            # "@@ -0,0 +1,4 @@" has no old side yet; 0 means absent, not line 0.
            old_line = int(header.group(1)) or None
            new_line = int(header.group(3)) or None
            lines.append(DiffLine("meta", None, None, raw))
            continue
        if not in_hunk:
            if raw.startswith("Binary files ") or raw == "GIT binary patch":
                binary = True
            if raw:
                lines.append(DiffLine("meta", None, None, raw))
            continue
        if raw.startswith("\\"):
            lines.append(DiffLine("meta", None, None, raw))
        elif raw.startswith("+"):
            added += 1
            lines.append(DiffLine("add", None, new_line, raw[1:]))
            new_line = (new_line or 0) + 1
        elif raw.startswith("-"):
            removed += 1
            lines.append(DiffLine("remove", old_line, None, raw[1:]))
            old_line = (old_line or 0) + 1
        elif raw == "" or raw.startswith(" "):
            # git writes a bare empty line for a blank source line.
            lines.append(DiffLine("context", old_line, new_line, raw[1:] if raw else ""))
            old_line = (old_line or 0) + 1
            new_line = (new_line or 0) + 1
        else:
            lines.append(DiffLine("meta", None, None, raw))
    return lines, added, removed, binary


def status_for(entry: task_review.StatusEntry) -> str:
    """The change kind shown on a file, taken from the client's status entry."""
    if entry.kind == "untracked":
        return "added"
    if entry.original_path:
        return "renamed"
    if entry.mode_worktree == "000000":
        return "deleted"
    return "modified"


MAX_HIGHLIGHT_BYTES = 400_000

LANGUAGE_ALIASES = {
    "py": "python", "pyi": "python", "js": "javascript", "mjs": "javascript",
    "cjs": "javascript", "jsx": "javascript", "ts": "typescript", "tsx": "typescript",
    "rs": "rust", "go": "go", "yml": "yaml", "sh": "bash", "bash": "bash",
    "zsh": "bash", "md": "markdown", "markdown": "markdown", "html": "xml",
    "htm": "xml", "vue": "xml", "rb": "ruby", "pl": "perl", "cs": "csharp",
    "kt": "kotlin", "swift": "swift", "scala": "scala", "lua": "lua",
}


def language_for(path: str) -> "str | None":
    """The language hint for a path, or None when we should not guess."""
    name = path.split("/")[-1].lower()
    if name in ("makefile", "dockerfile", "gemfile", "rakefile"):
        return {"makefile": "makefile", "dockerfile": "dockerfile", "gemfile": "ruby", "rakefile": "ruby"}[name]
    dot = name.rfind(".")
    if dot <= 0:
        return None
    return LANGUAGE_ALIASES.get(name[dot + 1 :])


def read_for_highlighting(root: str, path: str, binary: bool) -> "str | None":
    """The new-side file text, so a reviewer can tokenize whole files.

    A removed line has no pre-image on disk, so the page shows those as plain
    text; added and context lines get the real thing. A file too large to be
    worth sending is simply not highlighted.
    """
    if binary:
        return None
    absolute = os.path.join(root, *path.split("/"))
    try:
        if os.path.getsize(absolute) > MAX_HIGHLIGHT_BYTES:
            return None
        with open(absolute, "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    return raw.decode("utf-8", "replace")


def collect_file_diffs(
    repository: task_review.Repository,
    git: GitRunner = task_review.run_git,
) -> "list[FileDiff]":
    """Reads one repository's diff through the client's own snapshot code."""
    root = repository.root
    baseline = task_review.resolve_baseline(root, git)
    entries = task_review.parse_porcelain_v2(
        git(root, ["status", "--porcelain=v2", "-z", "--untracked-files=all"])
    )
    selected = [entry for entry in entries if task_review.matches_scope(entry.path, repository.paths)]
    diffs: list[FileDiff] = []
    for entry in sorted(selected, key=lambda item: item.path):
        patch = task_review.entry_patch(root, baseline, entry, git)
        lines, added, removed, binary = parse_patch(patch)
        diffs.append(
            FileDiff(
                repository=root,
                path=entry.path,
                old_path=entry.original_path,
                status=status_for(entry),
                binary=binary,
                added=added,
                removed=removed,
                lines=tuple(lines),
                text=read_for_highlighting(root, entry.path, binary),
                language=language_for(entry.path),
            )
        )
    return diffs


def build_payload(
    request: task_review.ReviewRequest,
    git: GitRunner = task_review.run_git,
) -> dict[str, Any]:
    """The review document the page renders: criterion, repositories, diff."""
    if request.guide is not None:
        task_review.validate_guide_snapshot(request.guide, task_review.collect_snapshot(request.repositories, git))
    repositories = []
    total_files = total_added = total_removed = 0
    for repository in request.repositories:
        diffs = collect_file_diffs(repository, git)
        added = sum(item.added for item in diffs)
        removed = sum(item.removed for item in diffs)
        total_files += len(diffs)
        total_added += added
        total_removed += removed
        repositories.append(
            {
                "root": repository.root,
                "paths": list(repository.paths) if repository.paths else None,
                "added": added,
                "removed": removed,
                "files": [item.payload() for item in diffs],
            }
        )
    return {
        "version": PROTOCOL_VERSION,
        "review_id": request.review_id,
        "criterion": request.criterion,
        "repositories": repositories,
        "totals": {"files": total_files, "added": total_added, "removed": total_removed},
        "guide": build_guide(request.guide, repositories),
    }


def build_guide(guide: "dict[str, Any] | None", repositories: list[dict[str, Any]]) -> dict[str, Any]:
    files = [file for repo in repositories for file in repo["files"]]
    indices = {(file["repository"], file["path"]): index for index, file in enumerate(files)}
    chapters = []
    covered = set()
    if guide is not None:
        for chapter in guide["chapters"]:
            members = []
            for reference in chapter["files"]:
                identity = (reference["repository"], reference["path"])
                if identity not in indices:
                    raise task_review.ResultError(f"guide references a file outside the captured diff: {reference['path']}")
                index = indices[identity]
                if index in covered:
                    raise task_review.ResultError(f"duplicate guide file reference: {reference['path']}")
                covered.add(index)
                members.append(index)
            chapters.append({"title": chapter["title"], "summary": chapter["summary"], "file_indices": members})
        remaining = [index for index in range(len(files)) if index not in covered]
        if remaining:
            chapters.append({"title": "Other changes", "summary": "These files were not assigned to an authored chapter. Review them too.", "file_indices": remaining})
    else:
        groups: dict[tuple[str, str], list[int]] = {}
        for index, file in enumerate(files):
            directory = file["path"].rsplit("/", 1)[0] if "/" in file["path"] else "Root files"
            groups.setdefault((file["repository"], directory), []).append(index)
        for (root, directory), members in groups.items():
            title = f"{root} · {directory}" if len(repositories) > 1 else directory
            chapters.append({"title": title, "summary": "Grouped by directory, not by behavior.", "file_indices": members})
    result = {"authored": guide is not None, "chapters": chapters}
    if guide is not None:
        for key in ("summary", "before", "after", "flow"):
            if key in guide:
                result[key] = guide[key]
    else:
        result["summary"] = "No agent-authored guide was supplied. These directory groups show every scoped file without inferring what the change does."
    return result


def parse_document_request(text: str) -> task_review.DocumentRequest:
    """A document request names one markdown file and the criterion it is judged
    against. Everything else about it matches the diff request, so the approval
    the client records means the same thing in both modes."""
    try:
        payload = json.loads(text)
    except ValueError as error:
        raise task_review.DocumentError(f"parsing document request JSON: {error}") from None
    if not isinstance(payload, dict):
        raise task_review.DocumentError("a document request must be a JSON object")
    version = payload.get("version")
    if version != PROTOCOL_VERSION:
        raise task_review.DocumentError(f"unsupported review protocol version: {version}")
    review_id = payload.get("review_id")
    if not isinstance(review_id, str) or not review_id.strip():
        raise task_review.DocumentError("review_id must not be empty")
    criterion = payload.get("criterion")
    if not isinstance(criterion, str) or not criterion.strip():
        raise task_review.DocumentError("criterion must not be empty")
    raw_path = payload.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise task_review.DocumentError("a document review needs a document path")
    path = os.path.abspath(os.path.expanduser(raw_path))
    if not os.path.isfile(path):
        raise task_review.DocumentError(f"the document does not exist: {raw_path}")
    return task_review.DocumentRequest(
        version=version, review_id=review_id, criterion=criterion, path=path
    )


def build_document_payload(request: task_review.DocumentRequest) -> dict[str, Any]:
    """The document the page renders: criterion, path, and one row per line."""
    try:
        with open(request.path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as error:
        raise task_review.DocumentError(f"the document could not be read: {error}") from None
    # The page renders blocks; the ranges they carry are what a comment names,
    # so the two must come from the same grouping pass.
    grouped = mark_fence_languages(markdown_doc.blocks(text))
    return {
        "version": PROTOCOL_VERSION,
        "review_id": request.review_id,
        "criterion": request.criterion,
        "path": request.path,
        "name": os.path.basename(request.path),
        "lines": len(text.splitlines()),
        "rows": markdown_doc.rows(text),
        "blocks": grouped,
    }


def mark_fence_languages(blocks: "list[dict[str, Any]]") -> "list[dict[str, Any]]":
    """Record each fenced block's language, from its opening fence.

    The page does the tokenizing, with a real grammar engine; all the server
    owes it is which language a fence claims, so the badge and the engine agree.
    """
    for block in blocks:
        if block.get("kind") != "code" or "source" not in block:
            continue
        opening = block["source"].split("\n")[0].strip()
        info = opening.lstrip("`~").strip()
        block["language"] = info.split()[0] if info.split() else ""
    return blocks


def document_line_index(payload: dict[str, Any]) -> set[int]:
    """Every line number a comment may point at in this document.

    A block is rendered once but may span several source lines, so the whole
    range of every block is commentable: a comment on the first, a middle, or
    the last line of a paragraph is the same place in the file. A line no block
    covers stays invalid, so a stale page still cannot invent a position.
    """
    return {
        line
        for block in payload.get("blocks") or []
        for line in range(block["start"], block["end"] + 1)
    }



def line_index(payload: dict[str, Any]) -> "dict[tuple[str, str, str], set[int]]":
    """Every line number a comment may point at, keyed by target.

    A stale page cannot make up a position: a target outside this index is
    rejected rather than passed on to the client.
    """
    index: "dict[tuple[str, str, str], set[int]]" = {}
    for repository in payload["repositories"]:
        for item in repository["files"]:
            for line in item["lines"]:
                if line["new_line"] is not None:
                    index.setdefault((item["repository"], item["path"], "new"), set()).add(line["new_line"])
                if line["old_line"] is not None:
                    index.setdefault((item["repository"], item["path"], "old"), set()).add(line["old_line"])
    return index


# --------------------------------------------------------------------------
# decision
# --------------------------------------------------------------------------


def build_result(
    request: task_review.ReviewRequest,
    decision: str,
    annotations: "list[dict[str, Any]]",
) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "review_id": request.review_id,
        "decision": decision,
        "annotations": list(annotations),
    }


def cancelled_result(request: task_review.ReviewRequest) -> dict[str, Any]:
    return build_result(request, "cancelled", [])


SEMANTIC_MESSAGES = {
    "the reviewer requested changes without feedback": "a request for changes needs at least one comment",
    "the reviewer returned annotations for a cancelled review": "a cancelled review must not carry annotations",
}


def parse_decision(
    payload: Any,
    request: task_review.ReviewRequest,
    index: "dict[tuple[str, str, str], set[int]]",
) -> dict[str, Any]:
    """Validates a decision from the page and returns the protocol result.

    The states the client treats as errors are refused here instead, so a bug in
    the page can only ever cost a review, never produce a result the client has
    to distrust.
    """
    if not isinstance(payload, dict):
        raise DecisionError("the decision must be a JSON object")
    decision = payload.get("decision")
    if decision not in task_review.DECISIONS:
        raise DecisionError(f"unknown decision: {decision!r}")
    raw_annotations = payload.get("annotations")
    if not isinstance(raw_annotations, list):
        raise DecisionError("the annotations must be a list")

    annotations: list[dict[str, Any]] = []
    for item in raw_annotations:
        if not task_review.is_annotation(item):
            raise DecisionError("malformed annotation")
        text = item["text"].strip()
        if not text:
            raise DecisionError("an annotation must carry text")
        target = item["target"]
        if target.get("scope") != "line":
            # A review-level comment is exactly a scope and nothing else.
            annotations.append({"text": text, "target": {"scope": "review"}})
            continue
        key = (target["repository"], target["path"], target["side"])
        available = index.get(key)
        if available is None:
            raise DecisionError(f"the comment target {key[1]!r} is not part of this review")
        for field in ("start_line", "end_line"):
            if target[field] not in available:
                raise DecisionError(f"{field} {target[field]} is not a line of {key[1]!r} in this review")
        annotations.append(
            {
                "text": text,
                "target": {
                    "scope": "line",
                    "repository": target["repository"],
                    "path": target["path"],
                    "side": target["side"],
                    "start_line": target["start_line"],
                    "end_line": target["end_line"],
                },
            }
        )

    result = build_result(request, decision, annotations)
    # The client's own rules: no changes without feedback, no feedback on a
    # cancelled review. Its errors are this module's errors here.
    try:
        task_review.validate_decision_semantics(result)
    except task_review.TaskReviewError as error:
        # The rule is the client's; the wording is this reviewer's, because a
        # human reading it is looking at a page, not at RDG.
        raise DecisionError(SEMANTIC_MESSAGES.get(str(error), str(error))) from None
    return result


def parse_document_decision(
    payload: Any,
    request: task_review.DocumentRequest,
    lines: set[int],
) -> dict[str, Any]:
    """The document counterpart of :func:`parse_decision`.

    A comment may only name a line the document actually has, which is what
    makes "line 42" in a review mean the same thing in the page and in the
    approval the client records.
    """
    if not isinstance(payload, dict):
        raise DecisionError("the decision must be a JSON object")
    decision = payload.get("decision")
    if decision not in task_review.DECISIONS:
        raise DecisionError(f"unknown decision: {decision!r}")
    raw_annotations = payload.get("annotations")
    if not isinstance(raw_annotations, list):
        raise DecisionError("the annotations must be a list")

    annotations: list[dict[str, Any]] = []
    for item in raw_annotations:
        if not task_review.is_document_annotation(item, request.path):
            raise DecisionError("malformed annotation")
        text = item["text"].strip()
        if not text:
            raise DecisionError("an annotation must carry text")
        target = item["target"]
        if target.get("scope") != "line":
            annotations.append({"text": text, "target": {"scope": "review"}})
            continue
        for field in ("start_line", "end_line"):
            if target[field] not in lines:
                raise DecisionError(f"{field} {target[field]} is not a line of {request.path}")
        annotations.append(
            {
                "text": text,
                "target": {
                    "scope": "line",
                    "path": request.path,
                    "start_line": target["start_line"],
                    "end_line": target["end_line"],
                },
            }
        )

    result = {
        "version": PROTOCOL_VERSION,
        "review_id": request.review_id,
        "decision": decision,
        "annotations": annotations,
    }
    try:
        task_review.validate_decision_semantics(result)
    except task_review.TaskReviewError as error:
        raise DecisionError(SEMANTIC_MESSAGES.get(str(error), str(error))) from None
    return result


# --------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Task review</title>
<style>
:root{
  color-scheme: dark;
  --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --serif:"Source Serif 4",Georgia,"Iowan Old Style","Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",SFMono-Regular,Menlo,monospace;
  --nerd:"FiraCode Nerd Font Mono","JetBrains Mono NF","Hack Nerd Font Mono",
         "JetBrains Mono","Nerd Font",ui-monospace,monospace;
  --bg:#0b0d12; --surface:#12151d; --raised:#181c26; --sunken:#0e1118;
  --line:#232936; --line-soft:#1b202b;
  --fg:#e7ecf4; --muted:#93a0b5; --faint:#6a7a90;
  --accent:#6ea8fe; --accent-ink:#0b1220; --accent-soft:rgba(110,168,254,.16);
  --add-fg:#56d364; --del-fg:#ff7b72; --add-bg:rgba(86,211,100,.11); --del-bg:rgba(255,123,114,.11);
  --add-line:rgba(86,211,100,.34); --del-line:rgba(255,123,114,.34);
  --warn-bg:rgba(210,153,34,.14); --warn-fg:#e3b341;
  --danger:#ff7b72; --ring:rgba(110,168,254,.45);
  --shadow:0 1px 2px rgba(0,0,0,.4),0 12px 32px rgba(0,0,0,.45);
  --r-sm:6px; --r-md:10px; --r-lg:14px;
}
/* The code font ships with this reviewer and is served from the review's own
   origin, so the page needs no network and its CSP names no third party. */
@font-face{
  font-family:"JetBrains Mono"; src:url("font/jetbrains-mono-400.woff2") format("woff2");
  font-weight:400; font-style:normal; font-display:swap;
}
@font-face{
  font-family:"JetBrains Mono"; src:url("font/jetbrains-mono-700.woff2") format("woff2");
  font-weight:700; font-style:normal; font-display:swap;
}
@font-face{
  font-family:"Inter"; src:url("font/inter-latin-var.woff2") format("woff2");
  font-weight:100 900; font-style:normal; font-display:swap;
}
@font-face{
  font-family:"Source Serif 4"; src:url("font/source-serif-4-latin-var.woff2") format("woff2");
  font-weight:200 900; font-style:normal; font-display:swap;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font:14.5px/1.5 var(--sans);
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
  display:grid; grid-template-rows:auto auto 1fr auto; overflow:hidden;
}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto !important; transition:none !important}}
code,kbd,.mono,.rows{font-family:var(--mono); font-variant-ligatures:none;
  font-feature-settings:"liga" 0,"calt" 0,"dlig" 0}
/* In prose a snippet is read, not compared, so its ligatures are welcome. */
body.document .md code,body.document .blk.code pre code{
  font-variant-ligatures:normal; font-feature-settings:"liga" 1,"calt" 1}
button{
  font:inherit; color:inherit; background:var(--raised); border:1px solid var(--line);
  border-radius:var(--r-sm); padding:8px 14px; cursor:pointer; white-space:nowrap;
  transition:background .12s ease,border-color .12s ease,color .12s ease;
}
button:hover:not(:disabled){border-color:var(--accent); color:var(--accent)}
button:focus-visible,textarea:focus-visible,input:focus-visible,li:focus-visible,[tabindex]:focus-visible{
  outline:2px solid var(--ring); outline-offset:2px; border-radius:var(--r-sm);
}
button:disabled{opacity:.45; cursor:not-allowed}
button.primary{background:var(--accent); border-color:var(--accent); color:var(--accent-ink); font-weight:600}
button.primary:hover:not(:disabled){filter:brightness(1.08); color:var(--accent-ink)}
button.danger{color:var(--danger); border-color:transparent; background:transparent}
button.danger:hover:not(:disabled){border-color:var(--danger); color:var(--danger)}
button.link{border:0; background:none; padding:2px 4px; color:var(--accent); text-decoration:underline}
button.tiny{padding:5px 10px; font-size:13px; border-radius:var(--r-sm)}
button.ghost{background:transparent}
textarea,input{
  font:inherit; width:100%; background:var(--sunken); color:var(--fg);
  border:1px solid var(--line); border-radius:var(--r-sm); padding:9px 11px; resize:vertical;
}
textarea::placeholder,input::placeholder{color:var(--faint)}
ul{list-style:none; margin:0; padding:0}
h2{font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); font-weight:600; margin:0}

/* ---------------------------------------------------------------- header */
header{
  padding:14px 18px 12px; border-bottom:1px solid var(--line); background:var(--surface);
  min-height:0; max-height:34vh; overflow:auto;
}
/* The body is a four-row grid whose last row is the decision footer, and the
   body is overflow:hidden so the diff can scroll on its own. An unbounded
   header therefore does not just grow: a criterion with a long URL in it wraps
   until the header is taller than the window, the footer is pushed past the
   bottom edge, and every decision button becomes unreachable. Capping the
   header keeps the footer on screen; the header scrolls when it has to. */
header .top{display:flex; align-items:flex-start; gap:12px; justify-content:space-between}
header h1{
  font-size:17px; line-height:1.35; font-weight:650; margin:0; letter-spacing:-.01em;
  min-width:0; overflow-wrap:anywhere;
}
header .title{display:flex; align-items:center; gap:12px; flex-wrap:wrap; min-width:0}
#task-summary{margin:8px 0; max-width:90ch; color:var(--fg); overflow-wrap:anywhere; line-height:1.5}
#review-brief{margin-top:10px}
#review-brief summary{cursor:pointer; color:var(--muted); font-size:13px; width:fit-content}
#criterion{max-width:90ch; margin-top:10px; white-space:pre-wrap; overflow-wrap:anywhere; font-weight:400; line-height:1.65}
header .meta{color:var(--muted); font-size:13px; margin-top:5px; display:flex; gap:8px; align-items:center; flex-wrap:wrap}
header .meta code{font-size:13px; color:var(--faint)}
.chips{display:flex; gap:6px; align-items:center; flex-wrap:wrap}
.chip{
  display:inline-flex; align-items:center; gap:5px; padding:3px 9px; border-radius:999px;
  border:1px solid var(--line); background:var(--sunken); font-size:13px; color:var(--muted);
  font-variant-numeric:tabular-nums;
}
.chip b{color:var(--fg); font-weight:600}
.chip.add b{color:var(--add-fg)} .chip.del b{color:var(--del-fg)}
.chip.repo{font-family:var(--mono); font-size:13px; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.chev{
  border:0; background:none; padding:0 2px; width:16px; flex:none;
  color:var(--muted); font-size:11px; line-height:1;
}
.chev:hover{color:var(--accent); border:0}
.hint-list{margin:8px 0 0; padding:0 0 0 2px; list-style:none; color:var(--faint); font-size:13px; line-height:1.7}
.hint-list kbd{margin-left:6px}

/* --------------------------------------------------------------- toolbar */
#toolbar{
  display:flex; gap:10px; align-items:center; padding:8px 18px;
  border-bottom:1px solid var(--line); background:var(--surface);
}
#toolbar input{max-width:280px; font-size:13px; padding:7px 11px}
#toolbar .spacer{flex:1}
#toolbar .hint{color:var(--faint); font-size:13px}
#files li{gap:2px}
.fname{display:flex; align-items:center; gap:7px; min-width:0}
.fname .path{overflow-wrap:anywhere}
.path .directory{color:var(--muted); font-size:13px; font-weight:400}
.path strong{color:var(--fg); font-weight:650}
.fname .path,.file > h3 > .path,#current-file-path .path{display:flex; flex-direction:column-reverse; gap:2px}
/* File icons are Nerd Font private-use glyphs: the patched font is already on
   this machine, and --nerd falls back to the bundled code font if it is not. */
.ficon{font-family:var(--nerd); font-size:13px; line-height:1; flex:none; color:var(--faint)}
.ficon.add{color:var(--add-fg)} .ficon.del{color:var(--del-fg)}
.ficon.mod{color:var(--accent)} .ficon.moved{color:#c792ea}
.ficon{display:inline-block; line-height:1; transform:translateY(-1px)}
.file > h3 .ficon{font-size:12px}

/* ------------------------------------------------------------------ main */
main{display:grid; grid-template-columns:264px minmax(0,1fr) 340px; min-height:0}
body.comments-collapsed main{grid-template-columns:264px minmax(0,1fr)}
body.document.comments-collapsed main{grid-template-columns:232px minmax(0,1fr)}
aside{overflow:auto; min-height:0; background:var(--surface)}
#files-panel{border-right:1px solid var(--line)}
#threads-panel{border-left:1px solid var(--line)}
.panel-head{
  position:sticky; top:0; z-index:2; display:flex; align-items:center; justify-content:space-between;
  gap:8px; padding:10px 12px; border-bottom:1px solid var(--line-soft);
  background:var(--surface);
}
#diff{overflow:auto; min-height:0; padding:14px 18px; scroll-behavior:smooth}
#diff:focus-visible{outline:2px solid var(--accent); outline-offset:-2px}
#diff::after{content:""; display:block; height:45vh}
#review-pane{display:flex; flex-direction:column; min-height:0; min-width:0}
#review-pane #diff{flex:1}
#current-file{display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center; padding:10px 18px; border-bottom:1px solid var(--line); background:var(--raised)}
#current-file-path{min-width:0; flex:1 1 180px; overflow:auto; white-space:nowrap; font:400 13px/1.5 var(--mono)}
#current-file-position{flex:none; color:var(--muted); font-size:13px; font-variant-numeric:tabular-nums}
#change-navigation{display:flex; flex-wrap:wrap; align-items:center; gap:6px}
#change-position{color:var(--muted); font-size:13px; font-variant-numeric:tabular-nums}
body.document #current-file{display:none}

/* ------------------------------------------------------------- file list */
#files li{
  padding:9px 12px; border-bottom:1px solid var(--line-soft); cursor:pointer;
  display:flex; flex-direction:column; gap:3px; border-left:2px solid transparent;
}
#files li:hover{background:var(--raised)}
#files li.active{border-left-color:var(--accent); background:var(--accent-soft)}
#files li .path{font-family:var(--mono); font-size:13px; word-break:break-all; line-height:1.5}
#files li .counts{color:var(--muted); font-size:13px; display:flex; gap:6px; align-items:center; font-variant-numeric:tabular-nums}
#files li .dot{width:7px; height:7px; border-radius:50%; background:var(--muted); flex:none}
#files li .dot.add{background:var(--add-fg)} #files li .dot.del{background:var(--del-fg)}
#files li .open{color:var(--warn-fg); font-weight:600}

/* ----------------------------------------------------------------- files */
.file{
  margin:0 0 16px; border:1px solid var(--line); border-radius:var(--r-md);
  overflow:visible; background:var(--surface); box-shadow:0 1px 2px rgba(0,0,0,.18);
}
.file > h3{
  margin:0; padding:9px 12px; display:flex; gap:9px;
  align-items:center; flex-wrap:wrap; background:var(--raised);
  border-bottom:1px solid var(--line); border-radius:var(--r-md) var(--r-md) 0 0; font:600 13px/1.5 var(--mono);
}
.file > h3 .counts{margin-left:auto; color:var(--muted); font:13px/1.5 var(--sans); font-variant-numeric:tabular-nums}
.file > h3 > span{overflow-wrap:anywhere; min-width:0}
.badge{
  font:600 13px/1.7 var(--sans); text-transform:uppercase; letter-spacing:.06em;
  padding:0 7px; border-radius:999px; border:1px solid var(--line); color:var(--muted);
}
.badge.add{color:var(--add-fg); border-color:var(--add-line); background:var(--add-bg)}
.badge.del{color:var(--del-fg); border-color:var(--del-line); background:var(--del-bg)}
.rows{display:grid; grid-template-columns:minmax(0,1fr); font:400 15px/26px var(--mono); font-variant-numeric:tabular-nums}
.row{
  display:grid; grid-template-columns:52px 52px 18px minmax(0,1fr);
  border-left:2px solid transparent; scroll-margin-top:44px;
}
.row .ln{
  color:var(--faint); text-align:right; padding:0 8px; user-select:none;
  font-size:13px; cursor:pointer; font-variant-numeric:tabular-nums;
}
.row .ln:hover{color:var(--accent)}
.row .sign{text-align:center; user-select:none; color:var(--faint)}
.row .code{overflow-wrap:anywhere; white-space:pre-wrap; padding-right:14px}
.row.add{background:var(--add-bg); border-left-color:var(--add-line)}
.row.add .code,.row.add .sign{color:var(--add-fg)}
.row.remove{background:var(--del-bg); border-left-color:var(--del-line)}
.row.remove .code,.row.remove .sign{color:var(--del-fg)}
.row.meta{background:var(--sunken); color:var(--muted); font-size:13px}
.row.meta .code{padding:3px 10px; font-style:italic}
.row.sel{background:var(--accent-soft); border-left-color:var(--accent)}
.row.sel .code,.row.sel .sign,.row.sel .ln{color:var(--fg)}
.row.threaded .ln::after{content:""; display:inline-block; width:5px; height:5px; border-radius:50%;
  background:var(--warn-fg); margin-left:5px; vertical-align:middle}
.row.threaded.resolved-thread .ln::after{background:var(--accent)}
.row.flash{animation:flash .9s ease}
.diff-view-controls{display:flex; gap:3px}
.diff-view-controls button[aria-pressed="true"]{background:var(--accent-soft); border-color:var(--accent); color:var(--fg)}
.file.split .rows{grid-template-columns:repeat(2,minmax(0,1fr)); min-width:560px}
.split-row,.split-labels{display:contents}
.file.split .rows > .row{grid-column:1 / -1}
.split-row > .row{grid-template-columns:52px 18px minmax(0,1fr)}
.split-row > .row:first-child{border-right:1px solid var(--line)}
.split-row > .blank{background:var(--sunken); min-height:26px}
.split-labels span{position:sticky; top:0; z-index:2; padding:6px 12px; background:var(--raised); color:var(--muted); font:600 13px/1.5 var(--sans)}
.file.nowrap{min-width:max-content}
.file.nowrap .rows{grid-template-columns:minmax(max-content,1fr)}
.file.split.nowrap .rows{grid-template-columns:repeat(2,minmax(max-content,1fr))}
.file.nowrap .code{white-space:pre; overflow-wrap:normal}
.word-change{color:inherit; border-radius:2px}
.row.add .word-change{background:var(--add-line)}
.row.remove .word-change{background:var(--del-line)}
body.document .diff-view-controls,body.document #wrap-lines,body.document #review-tabs{display:none}
#review-tabs{display:flex; gap:4px}
#review-tabs [aria-selected="true"]{background:var(--accent-soft); border-color:var(--accent); color:var(--fg)}
#review-pane{container-type:inline-size}
.guide-overview{padding:20px; margin-bottom:24px; border:1px solid var(--line); border-radius:var(--r-md); background:var(--surface)}
.guide-overview h2,.guide-context h2{font-size:18px; color:var(--fg); text-transform:none; letter-spacing:-.01em; margin:0 0 10px}
.guide-overview p,.guide-context p{white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.65}
.guide-note{font-size:13px; color:var(--muted)}
.guide-comparison{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-top:18px}
.guide-side{padding:14px; border:1px solid var(--line); border-radius:var(--r-sm); background:var(--sunken)}
.guide-side h3{margin:0; font-size:14px}
.guide-side.after{border-color:var(--add-line); background:var(--add-bg)}
.guide-flow{display:flex; flex-wrap:wrap; gap:10px; padding:0; list-style:none}
.guide-flow li{border:1px solid var(--line); border-radius:5px; padding:6px 9px; font:13px/1.5 var(--mono); overflow-wrap:anywhere}
.guide-flow li:not(:last-child)::after{content:" →"; color:var(--muted)}
.guide-chapter{display:grid; grid-template-columns:minmax(200px,1fr) minmax(0,2.3fr); gap:22px; margin-bottom:32px; scroll-margin-top:10px}
.guide-context{position:sticky; top:0; align-self:start; padding:8px 0}
.guide-context .guide-position{font:13px/1.5 var(--mono); color:var(--muted)}
.guide-progress{display:flex; gap:7px; align-items:center; font-size:13px; color:var(--muted); margin:12px 0}
.guide-progress input{width:auto}
.guide-files{display:flex; flex-direction:column; gap:6px}
.guide-files button{text-align:left; overflow-wrap:anywhere; white-space:normal; font:13px/1.5 var(--mono)}
.guide-code{min-width:0}
@container(max-width:900px){
  .guide-chapter{grid-template-columns:minmax(0,1fr); gap:10px}
  .guide-context{position:static}
}
@container(max-width:500px){.guide-comparison{grid-template-columns:minmax(0,1fr)}}
@keyframes flash{from{background:var(--accent-soft)} to{background:transparent}}

/* --------------------------------------------------------------- threads */
.thread{padding:10px 12px; border-bottom:1px solid var(--line-soft); border-left:2px solid var(--warn-fg); cursor:pointer}
.thread:hover{background:var(--raised)}
.thread.resolved{opacity:.62; border-left-color:var(--accent)}
.thread .where{font:13px/1.5 var(--mono); color:var(--muted); word-break:break-all}
.thread .text{margin:5px 0 8px; white-space:pre-wrap; font-size:13.5px; line-height:1.55}
.thread .acts{display:flex; gap:6px; align-items:center}
.group{padding:9px 12px 4px; font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--faint); font-weight:600}
.empty{padding:14px 12px; color:var(--faint); font-size:13.5px; line-height:1.55}

/* -------------------------------------------------------------- composer */
#composer{
  position:fixed; left:50%; bottom:132px; transform:translateX(-50%); width:min(680px,92vw);
  background:var(--raised); border:1px solid var(--accent); border-radius:var(--r-lg);
  padding:12px; box-shadow:var(--shadow); z-index:20;
}
#composer .where{font:13px/1.5 var(--mono); color:var(--muted); margin-bottom:7px; word-break:break-all}
#composer .acts{display:flex; gap:8px; justify-content:flex-end; margin-top:9px}

/* ---------------------------------------------------------------- footer */
footer{
  border-top:1px solid var(--line); background:var(--surface); padding:10px 18px 12px;
  display:grid; grid-template-columns:minmax(260px,1fr) auto; gap:10px 18px; align-items:end;
}
footer label{display:block; color:var(--muted); font-size:13px; text-transform:uppercase;
  letter-spacing:.07em; font-weight:600; margin-bottom:5px}
footer .actions{display:flex; gap:8px; align-items:center; flex-wrap:wrap; justify-content:flex-end}
#counts{color:var(--muted); font-size:13px; margin-right:6px; font-variant-numeric:tabular-nums}
#message{grid-column:1 / -1; min-height:18px; font-size:13.5px; color:var(--muted)}
#message.warn{color:var(--warn-fg)} #message.error{color:var(--danger); font-weight:600}
kbd{
  font:13px/1.6 var(--mono); border:1px solid var(--line); border-bottom-width:2px;
  border-radius:4px; padding:0 4px; margin-left:6px; opacity:.7; color:var(--muted);
}
button.primary kbd{opacity:.85}
#banner{
  grid-column:1 / -1; background:var(--warn-bg); color:var(--warn-fg); border:1px solid var(--warn-fg);
  border-radius:var(--r-sm); padding:6px 10px; font-size:13px;
  display:flex; gap:12px; align-items:center; justify-content:space-between;
}

/* -------------------------------------------------------- dialog/overlay */
#backdrop{position:fixed; inset:0; background:rgba(4,6,10,.62); display:flex; align-items:center;
  justify-content:center; z-index:30; padding:24px; backdrop-filter:blur(2px)}
#dialog{
  background:var(--raised); border:1px solid var(--line); border-radius:var(--r-lg); padding:18px;
  max-width:520px; width:100%; box-shadow:var(--shadow);
}
#dialog h2{color:var(--fg); font-size:15px; text-transform:none; letter-spacing:0; font-weight:650}
#dialog .body{margin:8px 0 16px; color:var(--muted); white-space:pre-wrap; line-height:1.55}
#dialog .acts{display:flex; gap:8px; justify-content:flex-end}
#overlay{
  position:fixed; inset:0; background:var(--bg); z-index:40; display:flex;
  align-items:center; justify-content:center; font-size:15px; color:var(--muted);
}
#help{
  position:fixed; inset:0; background:rgba(4,6,10,.72); z-index:35; display:flex;
  align-items:center; justify-content:center; padding:24px; backdrop-filter:blur(2px);
}
#help .card{background:var(--raised); border:1px solid var(--line); border-radius:var(--r-lg);
  padding:20px 24px; box-shadow:var(--shadow); min-width:380px}
#help h2{color:var(--fg); font-size:15px; text-transform:none; letter-spacing:0; margin-bottom:12px}
#help table{border-collapse:collapse; font-size:13px}
#help td{padding:4px 0} #help td:first-child{width:110px}
#help kbd{margin:0}
/* ---------------------------------------------------------- document mode */
/* A specification renders as blocks, not as numbered lines: a heading looks
   like a heading, a paragraph is a paragraph. Each block still carries the
   source range it came from, which is what a comment names. */
body.document main{grid-template-columns:232px minmax(0,1fr) 340px}
body.document #files-panel{display:none}
body.document #chip-files,body.document #chip-add,body.document #chip-del{display:none}
body.document #file-filter,body.document #expand-all,body.document #collapse-all{display:none}
body.document .blk{position:relative; border-left:2px solid transparent; scroll-margin-top:70px}
body.document .blk:hover{background:var(--raised)}
body.document .blk.sel{background:var(--accent-soft); border-left-color:var(--accent)}
body.document .blk.threaded{border-left-color:var(--warn-fg)}
body.document .blk.threaded.resolved-thread{border-left-color:var(--accent)}
body.document .blk.flash{animation:flash .9s ease}
body.document .at{
  position:absolute; left:-46px; width:40px; text-align:right; color:var(--faint);
  font:13px/1.7 var(--mono); user-select:none; cursor:pointer; opacity:0;
  transition:opacity .12s ease;
}
body.document .blk:hover .at,body.document .blk.sel .at,body.document .blk.threaded .at{opacity:1}
body.document .blk.h1 .bd{font-family:var(--sans); font-size:27px; font-weight:700; color:var(--accent); line-height:1.28; margin:30px 0 8px; letter-spacing:-.02em}
body.document .blk.h2 .bd{font-family:var(--sans); font-size:20.5px; font-weight:650; margin:28px 0 6px; letter-spacing:-.015em}
body.document .blk.h3 .bd,body.document .blk.h4 .bd,body.document .blk.h5 .bd,body.document .blk.h6 .bd{
  font-size:14px; font-weight:700; margin:16px 0 3px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted)}
body.document .blk.p .bd{
  margin:0 0 1.1em; color:var(--fg);
  font-family:var(--serif); font-size:18px; line-height:1.72;
  font-variant-numeric:oldstyle-nums proportional-nums;
}
body.document .md > :first-child{margin-top:0}
body.document .md > :last-child{margin-bottom:0}
body.document .md p{margin:0 0 1.05em}
body.document .md h1,body.document .md h2,body.document .md h3,
body.document .md h4,body.document .md h5,body.document .md h6{
  font-family:var(--sans); margin:1.5em 0 .5em; line-height:1.3; letter-spacing:-.012em}
body.document .md h1{font-size:1.6em} body.document .md h2{font-size:1.28em}
body.document .md h3{font-size:1.18em}
body.document .md ul,body.document .md ol{margin:.4em 0 1.05em; padding-left:1.5em}
body.document .md li{margin:.2em 0}
body.document .md li::marker{color:var(--faint)}
body.document .md blockquote{
  margin:.8em 0; padding:.2em 0 .2em 1.1em; border-left:2px solid var(--line); color:var(--muted)}
body.document .md hr{border:0; border-top:1px solid var(--line); margin:1.6em 0}
body.document .md a{color:var(--accent); text-decoration-color:color-mix(in srgb,var(--accent) 45%,transparent);
  text-underline-offset:2px}
body.document .md strong{font-weight:650}
body.document .md table{
  margin:.6em 0 1.2em; border-collapse:collapse; font-family:var(--sans); font-size:14.5px; width:100%}
body.document .md th,body.document .md td{border:1px solid var(--line); padding:6px 10px; text-align:left; vertical-align:top}
body.document .md th{background:var(--raised); font-weight:600; color:var(--muted)}
body.document .md tbody tr:nth-child(even) td{background:var(--sunken)}
body.document .md code{font-family:var(--mono); font-size:.9em; font-weight:400; background:var(--sunken);
  padding:.12em .38em; border-radius:4px; border:1px solid var(--line-soft)}
body.document .md pre{background:var(--sunken); border:1px solid var(--line); border-radius:8px}
body.document .md pre code{background:none; border:0; padding:0; font-size:15px; line-height:26px; font-weight:400; letter-spacing:0}
body.document .blk.blank{height:10px}
body.document .blk.rule .bd{color:var(--line); letter-spacing:.2em}
body.document .blk.q .bd{border-left:2px solid var(--line); padding:2px 0 2px 14px; color:var(--muted); font-style:italic}
body.document .blk.li .bd{font-family:var(--serif); font-size:17.5px; margin:0 0 3px; padding-left:20px; position:relative; line-height:1.6}
body.document .blk.li .bd::before{content:"•"; position:absolute; left:2px; color:var(--faint)}
body.document .blk.li.task .bd::before{content:"☐"; color:var(--muted)}
body.document .blk.li.task.done .bd::before{content:"☑"; color:var(--add-fg)}
body.document .blk.tb .bd{margin:0 0 16px; border-collapse:collapse; font-size:12.5px; width:100%}
body.document .blk.tb .bd td{border:1px solid var(--line); padding:5px 9px; vertical-align:top}
body.document .blk.tb .bd tr:first-child td{background:var(--raised); font-weight:600; color:var(--muted)}
body.document .blk.tb .bd tr:nth-child(even):not(:first-child) td{background:var(--sunken)}
body.document .blk.code{margin:0 0 16px}
body.document .blk.code pre{margin:0; padding:12px 14px; background:var(--sunken); border:1px solid var(--line);
  border-radius:var(--r-sm); overflow-x:auto; font:400 15px/26px var(--mono);
  letter-spacing:.005em; white-space:pre}
body.document .blk.code .lang{display:inline-block; margin-bottom:4px; font:13px/1.6 var(--sans);
  text-transform:uppercase; letter-spacing:.08em; color:var(--faint)}
body.document .doc code{font-family:var(--mono); font-size:.9em; background:var(--sunken); padding:1px 5px;
  border-radius:4px; color:var(--fg)}
body.document .doc b{font-weight:700} body.document .doc i{font-style:italic} body.document .doc s{opacity:.7}
.diagram{margin:0 0 16px; padding:14px; background:var(--sunken); border:1px solid var(--line);
  border-radius:8px; overflow-x:auto; text-align:center}
.diagram.drawn svg{max-width:100%; height:auto}
.diagram.undrawn{white-space:pre; text-align:left; font-family:var(--mono); font-size:12.5px; color:var(--muted)}
.docpath{font-family:var(--mono); font-size:13px; color:var(--muted); margin-top:6px; word-break:break-all}
/* the outline: every heading, with the one you are reading marked */
#outline{padding:10px 8px 20px; border-right:1px solid var(--line); background:var(--surface); overflow:auto; min-height:0}
#outline .group{padding:6px 8px 3px}
#outline a{display:block; padding:5px 8px; border-radius:5px; color:var(--muted); text-decoration:none;
  font-size:13.5px; line-height:1.4; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
#outline a:hover{background:var(--raised); color:var(--fg)}
#outline a.lv1{font-weight:700; color:var(--fg)}
#outline a.lv2{padding-left:16px} #outline a.lv3{padding-left:26px; font-size:13px}
#outline a.lv4,#outline a.lv5,#outline a.lv6{padding-left:36px; font-size:13px; color:var(--faint)}
#outline a.here{background:var(--accent-soft); color:var(--accent)}
/* Code tokens. One palette, for the engine the page actually uses, tuned to
   the same dark background as the diff so highlighted and plain code sit
   together without a seam. */
.hljs-comment,.hljs-quote{color:#8b96a8; font-style:italic}
.hljs-keyword,.hljs-selector-tag,.hljs-literal,.hljs-doctag{color:#c792ea}
.hljs-string,.hljs-regexp,.hljs-addition{color:#a5d6a7}
.hljs-number,.hljs-symbol,.hljs-bullet{color:#f0b072}
.hljs-title,.hljs-title.class_,.hljs-title.function_,.hljs-section{color:#82aaff}
.hljs-type,.hljs-class .hljs-title,.hljs-built_in,.hljs-params{color:#ffcb6b}
.hljs-variable,.hljs-template-variable,.hljs-attribute,.hljs-attr,.hljs-property{color:#e6edf3}
.hljs-meta,.hljs-punctuation,.hljs-operator{color:#9aa7bd}
.hljs-name,.hljs-tag{color:#ff7b72}
.hljs-emphasis{font-style:italic} .hljs-strong{font-weight:600}
.hljs-link{text-decoration:underline}
@media(max-width:1100px){
  main,body.document main{grid-template-columns:minmax(120px,19%) minmax(0,1fr) minmax(160px,23%)}
  body.comments-collapsed main,body.document.comments-collapsed main{grid-template-columns:minmax(120px,19%) minmax(0,1fr)}
  #toolbar{flex-wrap:wrap}
  #toolbar .hint{display:none}
  footer{grid-template-columns:minmax(0,1fr)}
}
[hidden]{display:none !important}
</style>
</head>
<body>
<header>
  <div class="top">
    <div class="title">
      <h1 id="review-title">Review changes</h1>
      <div class="chips">
        <span class="chip" id="chip-files"></span>
        <span class="chip add" id="chip-add"></span>
        <span class="chip del" id="chip-del"></span>
      </div>
    </div>
    <button id="help-open" class="tiny ghost" title="Keyboard shortcuts">? shortcuts</button>
  </div>
  <p id="task-summary"></p>
  <div class="meta"><code id="review-id"></code></div>
  <ul id="repos"></ul>
  <details id="review-brief">
    <summary>Review brief</summary>
    <div id="criterion"></div>
  </details>
</header>
<div id="toolbar">
  <div id="review-tabs" role="tablist" aria-label="Review view">
    <button id="tab-diff" class="tiny" role="tab" aria-selected="true" aria-controls="diff">Diff</button>
    <button id="tab-guided" class="tiny" role="tab" aria-selected="false" aria-controls="diff" tabindex="-1">Guided</button>
  </div>
  <input id="file-filter" type="search" placeholder="Filter files&hellip;" aria-label="Filter files by path" spellcheck="false">
  <button id="expand-all" class="tiny">Expand all</button>
  <button id="collapse-all" class="tiny">Collapse all</button>
  <div class="diff-view-controls" role="group" aria-label="Diff layout">
    <button id="view-inline" class="tiny" aria-pressed="true">Inline</button>
    <button id="view-split" class="tiny" aria-pressed="false">Side-by-side</button>
  </div>
  <button id="wrap-lines" class="tiny" aria-pressed="true">Wrap lines</button>
  <button id="comments-toggle" class="tiny" aria-controls="threads-panel" aria-expanded="true">Hide comments (0)</button>
  <span class="spacer"></span>
  <span class="hint">Click a line or drag a range to comment &middot; <kbd>?</kbd> for shortcuts</span>
</div>
<main>
  <nav id="outline" hidden></nav>
  <aside id="files-panel">
    <div class="panel-head"><h2>Files</h2><span class="chip" id="file-total"></span></div>
    <ul id="files"></ul>
  </aside>
  <section id="review-pane" aria-label="Review content">
    <div id="current-file" hidden>
      <span id="current-file-path" tabindex="0"></span>
      <span id="current-file-position"></span>
      <div id="change-navigation" role="group" aria-label="Change navigation">
        <button id="previous-change" class="tiny" disabled>Previous change</button>
        <span id="change-position">0 changes</span>
        <button id="next-change" class="tiny" disabled>Next change</button>
      </div>
    </div>
    <section id="diff"></section>
  </section>
  <aside id="threads-panel">
    <div class="panel-head">
      <h2>Comments</h2>
      <span>
        <button id="next-thread" class="tiny ghost" title="Jump to the next comment (N)">Next</button>
        <button id="discard" class="tiny ghost" hidden>Discard all</button>
      </span>
    </div>
    <ul id="threads"></ul>
  </aside>
</main>
<div id="composer" hidden>
  <div class="where" id="composer-where"></div>
  <textarea id="composer-text" rows="3" placeholder="Describe the problem on the selected lines. &#9166; saves, Esc cancels."></textarea>
  <div class="acts">
    <button id="composer-cancel">Cancel</button>
    <button id="composer-save" class="primary">Add comment</button>
  </div>
</div>
<footer>
  <div>
    <label for="review-comment">Overall comment (optional)</label>
    <textarea id="review-comment" rows="2" placeholder="Sent with your decision, for the whole change rather than one line."></textarea>
  </div>
  <div>
    <div class="actions">
      <span id="counts"></span>
      <button id="cancel" class="danger">Cancel <kbd>&#8984;C</kbd></button>
      <button id="planning">Return to planning <kbd>&#8984;P</kbd></button>
      <button id="changes">Request changes <kbd>&#8984;R</kbd></button>
      <button id="approve" class="primary">Approve <kbd>&#8984;A</kbd></button>
    </div>
    <div id="banner" hidden>
      <span id="banner-text"></span>
      <button id="banner-resolve" class="tiny">Keep as non-blocking nits</button>
    </div>
  </div>
  <div id="message" role="status" aria-live="polite"></div>
</footer>
<div id="backdrop" hidden>
  <div id="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
    <h2 id="dialog-title"></h2>
    <p class="body" id="dialog-body"></p>
    <div class="acts" id="dialog-acts"></div>
  </div>
</div>
<div id="help" hidden>
  <div class="card" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
    <h2>Shortcuts</h2>
    <table>
      <tr><td><kbd>&#8984;A</kbd></td><td>Approve the change</td></tr>
      <tr><td><kbd>&#8984;R</kbd></td><td>Request changes and send the comments back</td></tr>
      <tr><td><kbd>&#8984;P</kbd></td><td>Return to planning</td></tr>
      <tr><td><kbd>&#8984;C</kbd></td><td>Cancel the review</td></tr>
      <tr><td><kbd>J</kbd> <kbd>K</kbd></td><td>Next / previous file</td></tr>
      <tr><td><kbd>N</kbd></td><td>Jump to the next comment</td></tr>
      <tr><td><kbd>Tab</kbd></td><td>Focus the code pane for line selection</td></tr>
      <tr><td><kbd>↑</kbd> <kbd>↓</kbd></td><td>Select the previous / next source line in the focused code pane</td></tr>
      <tr><td><kbd>Shift ↑</kbd> <kbd>Shift ↓</kbd></td><td>Extend / shrink a continuous same-side range</td></tr>
      <tr><td><kbd>←</kbd> <kbd>→</kbd></td><td>Choose Before / After when that source side exists</td></tr>
      <tr><td><kbd>Enter</kbd></td><td>Write a comment on the selected lines</td></tr>
      <tr><td><kbd>/</kbd></td><td>Filter files</td></tr>
      <tr><td><kbd>?</kbd></td><td>This panel</td></tr>
      <tr><td><kbd>Esc</kbd></td><td>Close a box, or clear the selection</td></tr>
    </table>
  </div>
</div>
<div id="overlay" hidden>Decision sent. You can close this window.</div>
<script type="application/json" id="boot">__HTML_REVIEW_BOOT__</script>
<script src="vendor/markdown-it.min.js"></script>
<script src="vendor/markdown-it-task-lists.min.js"></script>
<script src="vendor/markdown-it-footnote.min.js"></script>
<script src="vendor/highlight.min.js"></script>
<script src="vendor/mermaid.min.js"></script>
<script>
__HTML_DIFF_VIEW__
</script>
<script>
"use strict";
const boot = JSON.parse(document.getElementById("boot").textContent);
const el = (id) => document.getElementById(id);

// markdown-it renders the inside of a block; the block boundaries and their
// source ranges are decided server side and are never second-guessed here.
const md = (() => {
  if (!window.markdownit) return null;
  const engine = window.markdownit({html: false, linkify: true, typographer: true, breaks: false});
  // Task lists and footnotes are plugins, not core: the two a specification
  // actually uses, so the page is not quietly worse than the markdown written.
  for (const plugin of [window.markdownitTaskLists, window.markdownitFootnote]) {
    try { if (plugin) engine.use(plugin); } catch (error) { /* keep rendering */ }
  }
  return engine;
})();
// The vendored engines already declare their own globals, so they are read
// through `window` and never shadowed by a `const` of the same name.
const state = {
  data: null,
  files: [],
  currentFile: -1,
  changeStops: [],
  currentChange: -1,
  changeLocation: null,
  commentsCollapsed: false,
  diffView: "inline",
  reviewView: "diff",
  reviewScroll: {},
  reviewedChapters: new Set(),
  wrapLines: true,
  dragging: false,
  threads: [],
  nextThreadId: 1,
  armed: false,
  blocks: [],
  selection: null,
  painted: [],
  expanded: new Set(),
  filter: "",
  threadCursor: -1,
  dialog: null,
  submitted: false,
};

// ---------------------------------------------------------------- transport

async function loadReview() {
  const response = await fetch(boot.url + boot.reviewUrl, {cache: "no-store", credentials: "omit"});
  if (!response.ok) throw new Error("the review payload could not be read (" + response.status + ")");
  return response.json();
}

function say(text, kind) {
  el("message").textContent = text || "";
  el("message").className = kind || "";
}

function unresolvedThreads() { return state.threads.filter((t) => !t.resolved); }
function resolvedThreads() { return state.threads.filter((t) => t.resolved); }
function reviewText() { return el("review-comment").value.trim(); }

function sideNumber(row, side) { return side === "old" ? row.old_line : row.new_line; }

async function sendDecision(decision) {
  const annotations = [];
  if (decision !== "cancelled") {
    // Approval carries only resolved threads, as non-blocking nits. Feedback
    // carries every thread: an unresolved comment is the work the author still
    // has to do, which is the whole point of sending it back.
    for (const thread of state.threads) {
      if (decision === "approve" && !thread.resolved) continue;
      annotations.push({text: thread.text, target: thread.target});
    }
    const review = el("review-comment").value.trim();
    if (review) annotations.push({text: review, target: {scope: "review"}});
  }
  const payload = {decision: decision, annotations: annotations};
  try {
    const response = await fetch(boot.url + boot.decisionUrl, {
      method: "POST",
      body: JSON.stringify(payload),
      cache: "no-store",
      credentials: "omit",
    });
    if (!response.ok) {
      let detail = response.status + " " + response.statusText;
      try { detail = (await response.json()).error || detail; } catch (ignored) {}
      say(detail, "error");
      return false;
    }
  } catch (error) {
    say("The decision could not be delivered: " + error, "error");
    return false;
  }
  state.submitted = true;
  el("overlay").hidden = false;
  return true;
}

function visibleFiles() {
  const needle = state.filter.trim().toLowerCase();
  const files = needle ? state.files.filter((file) => file.path.toLowerCase().includes(needle)) : state.files;
  if (state.reviewView !== "guided" || !state.data?.guide) return files;
  const shown = new Set(files);
  return state.data.guide.chapters.flatMap(chapter => chapter.file_indices.map(index => state.files[index])).filter(file => shown.has(file));
}

function openCountFor(file) {
  return unresolvedThreads().filter(
    (t) => t.target.path === file.path && t.target.repository === file.repository).length;
}

function statusClass(status) {
  if (status === "added" || status === "untracked") return "add";
  if (status === "deleted" || status === "renamed") return "del";
  return "";
}

// Nerd Font private-use code points, keyed by file extension. Every one of
// these was rendered and checked against the patched fonts on this machine, and
// an unknown extension falls back to the plain-file glyph. They are written as
// code points rather than literal glyphs so the mapping cannot be mangled by an
// editor or a copy through a terminal.
const G = (code) => String.fromCharCode(code);
const PLAIN_FILE_GLYPH = G(0xf15b);
const FILE_GLYPHS = {
  py: G(0xe606), pyi: G(0xe606), js: G(0xe74e), jsx: G(0xe74e), mjs: G(0xe74e), cjs: G(0xe74e),
  ts: G(0xe628), tsx: G(0xe628), rs: G(0xe7a8), go: G(0xe627), md: G(0xe73e), mdx: G(0xe73e),
  json: G(0xe60b), yaml: G(0xe6a8), yml: G(0xe6a8), toml: G(0xe6a8), sh: G(0xf489), bash: G(0xf489),
  zsh: G(0xf489), sql: G(0xf1c0), html: G(0xf13b), css: G(0xe749), scss: G(0xf603), vue: G(0xfd42),
  rb: G(0xe739), c: G(0xe61e), h: G(0xf0fd), cpp: G(0xe61d), hpp: G(0xe61d),
  txt: G(0xf15c), lock: G(0xf023), lockfile: G(0xf023), pdf: G(0xf1c1), png: G(0xf1c5), jpg: G(0xf1c5),
  jpeg: G(0xf1c5), gif: G(0xf1c6), svg: G(0xf1c5), zip: G(0xf410), tar: G(0xf410), gz: G(0xf410),
  mod: G(0xe624), sum: G(0xe624), dockerfile: G(0xf308), makefile: G(0xf085),
};

function fileGlyph(path) {
  const name = path.split("/").pop().toLowerCase();
  if (name === "dockerfile") return FILE_GLYPHS.dockerfile;
  if (name === "makefile") return FILE_GLYPHS.makefile;
  const dot = name.lastIndexOf(".");
  const ext = dot > 0 ? name.slice(dot + 1) : name;
  return FILE_GLYPHS[ext] || PLAIN_FILE_GLYPH;
}

function statusTone(status) {
  if (status === "added" || status === "untracked") return "add";
  if (status === "deleted") return "del";
  if (status === "renamed") return "moved";
  return "mod";
}

function fileIcon(file) {
  const icon = document.createElement("span");
  icon.className = "ficon " + statusTone(file.status);
  icon.textContent = fileGlyph(file.path);
  return icon;
}

function render() {
  if (boot.mode === "document") return renderDocument();
  const data = state.data;
  renderBrief(data.criterion);
  el("review-id").textContent = "review " + data.review_id.slice(0, 12);
  el("chip-files").innerHTML = "<b>" + data.totals.files + "</b> file" + (data.totals.files === 1 ? "" : "s");
  el("chip-add").innerHTML = "<b>+" + data.totals.added + "</b> added";
  el("chip-del").innerHTML = "<b>-" + data.totals.removed + "</b> removed";
  const repos = el("repos");
  repos.textContent = "";
  for (const repository of data.repositories) {
    const item = document.createElement("li");
    item.className = "chip repo";
    const scope = repository.paths ? " [" + repository.paths.join(", ") + "]" : "";
    item.textContent = repository.root + scope + "   +" + repository.added + " / -" + repository.removed;
    repos.appendChild(item);
  }
  state.files = [];
  for (const repository of data.repositories) {
    for (const file of repository.files) {
      state.files.push({
        repository: file.repository, path: file.path, old_path: file.old_path,
        status: file.status, binary: file.binary, added: file.added,
        removed: file.removed, lines: file.lines,
        // language and text drive diff highlighting; without them every row
        // falls back to plain text even though the payload carried them.
        language: file.language, text: file.text,
      });
    }
  }
  if (!state.expanded.size) state.files.forEach((file, index) => state.expanded.add(index));
  renderFiles();
  renderDiff();
  renderThreads();
  renderFooter();
}

function reviewSummary(criterion) {
  const firstLine = criterion.split(NEWLINE).find((line) => line.trim()) || "";
  const compact = firstLine.trim().replace(/\\s+/g, " ");
  return compact.length > 180 ? compact.slice(0, 177).trimEnd() + "\u2026" : compact;
}

function renderBrief(criterion) {
  el("task-summary").textContent = reviewSummary(criterion);
  el("criterion").textContent = criterion;
}

function pathLabel(path) {
  const label = document.createElement("span");
  label.className = "path";
  const separator = path.lastIndexOf("/");
  if (separator >= 0) {
    const directory = document.createElement("span");
    directory.className = "directory";
    directory.textContent = path.slice(0, separator + 1);
    label.appendChild(directory);
  }
  const name = document.createElement("strong");
  name.textContent = path.slice(separator + 1);
  label.appendChild(name);
  return label;
}

function renderFiles() {
  const list = el("files");
  list.textContent = "";
  const shown = visibleFiles();
  el("file-total").textContent = state.filter.trim()
    ? shown.length + " / " + state.files.length
    : String(state.files.length);
  if (!state.files.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "No changes in scope.";
    list.appendChild(empty);
    return;
  }
  if (!shown.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "No file matches that filter.";
    list.appendChild(empty);
    return;
  }
  shown.forEach((file) => {
    const index = state.files.indexOf(file);
    const item = document.createElement("li");
    item.tabIndex = 0;
    item.dataset.file = String(index);
    const name = document.createElement("span");
    name.className = "fname";
    name.appendChild(fileIcon(file));
    const path = pathLabel(file.path);
    name.appendChild(path);
    const counts = document.createElement("span");
    counts.className = "counts";
    const numbers = document.createElement("span");
    numbers.textContent = file.status + "  +" + file.added + " / -" + file.removed;
    counts.appendChild(numbers);
    const open = openCountFor(file);
    if (open) {
      const badge = document.createElement("span");
      badge.className = "open";
      badge.textContent = open + " to fix";
      counts.appendChild(badge);
    }
    item.append(name, counts);
    const go = () => {
      state.expanded.add(index);
      renderDiff();
      const anchor = el("diff").querySelector('.file[data-file="' + index + '"]');
      if (anchor) anchor.scrollIntoView({block: "start"});
    };
    item.addEventListener("click", go);
    item.addEventListener("keydown", (event) => { if (event.key === "Enter") go(); });
    list.appendChild(item);
  });
  trackFile();
}

function trackFile() {
  if (boot.mode === "document") return;
  const host = el("diff");
  const blocks = Array.from(host.querySelectorAll(".file"));
  const top = host.getBoundingClientRect().top;
  const location = state.changeLocation;
  const destination = location && Math.abs(host.scrollTop - location.scrollTop) < 1 && blocks.find((block) => Number(block.dataset.file) === location.fileIndex);
  const current = destination || blocks.find((block) => block.getBoundingClientRect().bottom > top + 1) || blocks[blocks.length - 1];
  state.currentFile = current ? Number(current.dataset.file) : -1;
  el("current-file").hidden = !current;
  const file = state.files[state.currentFile];
  const label = el("current-file-path");
  if (label.dataset.file !== String(state.currentFile)) {
    label.replaceChildren(...(file ? [pathLabel(file.path)] : []));
    label.dataset.file = String(state.currentFile);
    label.scrollLeft = 0;
  }
  el("current-file-path").title = file ? file.repository + "/" + file.path : "";
  el("current-file-position").textContent = current ? "File " + (blocks.indexOf(current) + 1) + " of " + blocks.length : "";
  for (const item of el("files").children) {
    const active = !!current && item.dataset.file === String(state.currentFile);
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "true"); else item.removeAttribute("aria-current");
  }
  trackChanges();
}

function collectChangeStops() {
  const stops = [];
  for (const file of visibleFiles()) {
    const fileIndex = state.files.indexOf(file);
    const rows = [];
    file.lines.forEach((line, row) => {
      if (line.type === "meta" && line.text.startsWith("@@ ")) rows.push(row);
    });
    for (const row of rows.length ? rows : [null]) stops.push({fileIndex, row});
  }
  return stops;
}

function changeElement(stop) {
  if (stop.row !== null) return el("diff").querySelector('[data-file="' + stop.fileIndex + '"][data-row="' + stop.row + '"]');
  const file = el("diff").querySelector('.file[data-file="' + stop.fileIndex + '"]');
  return file ? file.firstElementChild : null;
}

function trackChanges() {
  const stops = state.changeStops;
  const top = el("diff").getBoundingClientRect().top;
  let current = -1;
  stops.forEach((stop, index) => {
    if (stop.fileIndex !== state.currentFile) return;
    const node = changeElement(stop);
    const margin = node ? parseFloat(getComputedStyle(node).scrollMarginTop) || 0 : 0;
    if (current === -1 || (node && node.getBoundingClientRect().top <= top + margin + 1)) current = index;
  });
  const location = state.changeLocation;
  if (location && Math.abs(el("diff").scrollTop - location.scrollTop) < 1) {
    const destination = stops.findIndex((stop) => stop.fileIndex === location.fileIndex && stop.row === location.row);
    if (destination >= 0) current = destination;
  } else state.changeLocation = null;
  state.currentChange = current;
  el("change-position").textContent = stops.length ? "Change " + (current + 1) + " of " + stops.length : "0 changes";
  el("previous-change").disabled = current <= 0;
  el("next-change").disabled = !stops.length || (current === stops.length - 1 && !!changeElement(stops[current]));
}

function stepChange(step) {
  if (boot.mode === "document" || state.submitted || state.dialog || !el("help").hidden) return;
  trackFile();
  const current = state.currentChange;
  const index = current < 0 ? 0 : step > 0 && !changeElement(state.changeStops[current]) ? current : current + step;
  const stop = state.changeStops[index];
  if (!stop) return;
  const truncated = stop.row !== null && boot.maxLines > 0 && stop.row >= boot.maxLines;
  if (!state.expanded.has(stop.fileIndex) || truncated) {
    state.expanded.add(stop.fileIndex);
    if (truncated) boot.maxLines = 0;
    renderDiff();
  }
  const node = changeElement(stop);
  if (node) {
    node.scrollIntoView({block: "start", inline: "nearest", behavior: "instant"});
    state.changeLocation = {...stop, scrollTop: el("diff").scrollTop};
  }
  trackFile();
}

// ---------------------------------------------------------------- diff tokens
//
// A diff shows fragments of a file, so tokenizing each row on its own gets
// multi-line strings and block comments wrong. Instead the whole new-side file
// is tokenized once and the resulting markup is split per line, re-opening any
// span that continues onto the next line. Removed lines have no pre-image on
// disk, so they are shown as plain text.

const tokenCache = new Map();

function tokenLines(file) {
  if (tokenCache.has(file.path)) return tokenCache.get(file.path);
  let perLine = null;
  const engine = window.hljs;
  if (engine && file.language && file.text !== undefined && engine.getLanguage(file.language)) {
    try {
      const whole = engine.highlight(file.text, {language: file.language, ignoreIllegals: true}).value;
      perLine = splitTokenHtml(whole);
    } catch (error) { perLine = null; }
  }
  tokenCache.set(file.path, perLine);
  return perLine;
}

// highlight.js emits a flat run of spans and keeps the file's real newlines, so
// a line boundary closes whatever is still open and re-opens it on the next
// line. A stack handles the general case and costs nothing: the depth is zero or
// one in practice.
const NEWLINE = String.fromCharCode(10);

function splitTokenHtml(html) {
  const lines = [];
  const stack = [];
  const openTags = () => stack.map((name) => '<span class="' + name + '">').join("");
  const closeTags = () => "</span>".repeat(stack.length);
  let buffer = "";
  const endLine = () => {
    lines.push(buffer + closeTags());
    buffer = openTags();
  };
  let index = 0;
  while (index < html.length) {
    const next = html.indexOf("<", index);
    if (next === -1) {
      const rest = html.slice(index);
      const pieces = rest.split(NEWLINE);
      for (let i = 0; i < pieces.length; i++) {
        buffer += pieces[i];
        if (i < pieces.length - 1) endLine();
      }
      break;
    }
    // Plain text before the next tag may itself contain a line break.
    const text = html.slice(index, next);
    const pieces = text.split(NEWLINE);
    for (let i = 0; i < pieces.length; i++) {
      buffer += pieces[i];
      if (i < pieces.length - 1) endLine();
    }
    const end = html.indexOf(">", next);
    if (end === -1) { buffer += html.slice(next); break; }
    const tag = html.slice(next, end + 1);
    if (tag.charAt(1) === "/") {
      stack.pop();
      buffer += tag;
    } else if (tag === "<br>" || tag === "<br/>" || tag === "<br />") {
      endLine();
    } else {
      const match = /class="([^"]*)"/.exec(tag);
      stack.push(match ? match[1] : "");
      buffer += tag;
    }
    index = end + 1;
  }
  lines.push(buffer + closeTags());
  return lines;
}

function lineTokens(file, line, side) {
  const perLine = tokenLines(file);
  if (side !== "old" && perLine && line && line > 0) {
    if (line - 1 < perLine.length) return perLine[line - 1];
  }
  return null;
}

function markCodeChanges(code, ranges) {
  const nodes = [];
  const visit = (parent) => {
    for (const child of parent.childNodes) {
      if (child.nodeType === 3) nodes.push(child);
      else visit(child);
    }
  };
  visit(code);
  let offset = 0;
  for (const node of nodes) {
    const text = node.data;
    const end = offset + text.length;
    const pieces = [];
    let cursor = 0;
    for (const [start, stop] of ranges) {
      const left = Math.max(offset, start);
      const right = Math.min(end, stop);
      if (left >= right) continue;
      if (left - offset > cursor) pieces.push(document.createTextNode(text.slice(cursor, left - offset)));
      const mark = document.createElement("mark");
      mark.className = "word-change";
      mark.textContent = text.slice(left - offset, right - offset);
      pieces.push(mark);
      cursor = right - offset;
    }
    if (pieces.length) {
      if (cursor < text.length) pieces.push(document.createTextNode(text.slice(cursor)));
      node.replaceWith(...pieces);
    }
    offset = end;
  }
}

function makeRow(fileIndex, line, index, changes) {
  const row = document.createElement("div");
  row.className = "row " + line.type;
  row.dataset.file = String(fileIndex);
  row.dataset.row = String(index);
  const oldNumber = document.createElement("span");
  oldNumber.className = "ln";
  oldNumber.dataset.side = "old";
  oldNumber.textContent = line.old_line === null ? "" : String(line.old_line);
  const newNumber = document.createElement("span");
  newNumber.className = "ln";
  newNumber.dataset.side = "new";
  newNumber.textContent = line.new_line === null ? "" : String(line.new_line);
  const sign = document.createElement("span");
  sign.className = "sign";
  sign.textContent = line.type === "add" ? "+" : line.type === "remove" ? "-" : " ";
  const code = document.createElement("span");
  code.className = "code";
  const file = state.files[fileIndex];
  const tokens = file ? lineTokens(file, sideNumber(line, line.type === "remove" ? "old" : "new"),
                                     line.type === "remove" ? "old" : "new") : null;
  if (tokens !== null && tokens !== undefined) {
    code.innerHTML = tokens === "" ? " " : tokens;
  } else {
    code.textContent = line.text === "" ? " " : line.text;
  }
  if (changes && changes.length && code.textContent === line.text) markCodeChanges(code, changes);
  row.append(oldNumber, newNumber, sign, code);
  if (line.type === "context" || line.type === "add" || line.type === "remove") {
    row.addEventListener("mousedown", (event) => onRowPress(event, fileIndex, index, line));
  }
  return row;
}

function makeSideCell(fileIndex, index, side, changes) {
  const row = document.createElement("div");
  if (index === null) {
    row.className = "row blank";
    row.setAttribute("aria-hidden", "true");
    return row;
  }
  const file = state.files[fileIndex];
  const line = file.lines[index];
  row.className = "row " + line.type;
  row.dataset.file = String(fileIndex);
  row.dataset.row = String(index);
  row.dataset.side = side;
  const number = document.createElement("span");
  number.className = "ln";
  number.dataset.side = side;
  number.textContent = String(sideNumber(line, side));
  const sign = document.createElement("span");
  sign.className = "sign";
  sign.textContent = line.type === "add" ? "+" : line.type === "remove" ? "-" : " ";
  const code = document.createElement("span");
  code.className = "code";
  const tokens = lineTokens(file, line.new_line, side === "old" && line.type === "remove" ? "old" : "new");
  if (tokens !== null && tokens !== undefined) code.innerHTML = tokens || " ";
  else code.textContent = line.text || " ";
  if (changes && changes.length && code.textContent === line.text) markCodeChanges(code, changes);
  row.append(number, sign, code);
  row.addEventListener("mousedown", (event) => onRowPress(event, fileIndex, index, line, side));
  return row;
}

function diffRow(fileIndex, index, side) {
  const suffix = state.diffView === "split" ? '[data-side="' + side + '"]' : "";
  return el("diff").querySelector('[data-file="' + fileIndex + '"][data-row="' + index + '"]' + suffix);
}

function readingPosition() {
  const host = el("diff");
  const top = host.getBoundingClientRect().top;
  const current = Array.from(host.querySelectorAll(".row[data-row]")).find(row => {
    const line = state.files[Number(row.dataset.file)].lines[Number(row.dataset.row)];
    return (line.old_line !== null || line.new_line !== null) && row.getBoundingClientRect().bottom > top;
  });
  return current ? {...current.dataset} : null;
}

function restoreReadingPosition(position) {
  if (position) {
    const line = state.files[Number(position.file)].lines[Number(position.row)];
    const side = position.side || (line.new_line !== null ? "new" : "old");
    const row = diffRow(Number(position.file), Number(position.row), side);
    if (row) row.scrollIntoView({block: "start", inline: "nearest"});
  }
  trackFile();
}

function setDiffView(view) {
  if (boot.mode === "document" || state.diffView === view) return;
  const position = readingPosition();
  state.diffView = view;
  state.selection = null;
  state.dragging = false;
  el("view-inline").setAttribute("aria-pressed", view === "inline" ? "true" : "false");
  el("view-split").setAttribute("aria-pressed", view === "split" ? "true" : "false");
  renderDiff();
  restoreReadingPosition(position);
}

function setWrapLines(wrap) {
  if (boot.mode === "document" || state.wrapLines === wrap) return;
  const position = readingPosition();
  state.wrapLines = wrap;
  el("wrap-lines").setAttribute("aria-pressed", wrap ? "true" : "false");
  for (const file of el("diff").querySelectorAll(".file")) file.classList.toggle("nowrap", !wrap);
  if (wrap) el("diff").scrollLeft = 0;
  restoreReadingPosition(position);
}

function onDiffKey(event) {
  if (boot.mode === "document" || state.submitted || state.dialog || !el("help").hidden || !el("composer").hidden ||
      event.target !== el("diff") || event.ctrlKey || event.metaKey || event.altKey ||
      !["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
  event.preventDefault();
  const rows = Array.from(el("diff").querySelectorAll(".row[data-row]"));
  let current = state.selection;
  const selected = current && diffRow(current.fileIndex, current.to, current.side);
  const top = el("diff").getBoundingClientRect().top;
  const available = rows.filter(row => {
    const line = state.files[Number(row.dataset.file)].lines[Number(row.dataset.row)];
    return line.old_line !== null || line.new_line !== null;
  });
  const anchor = selected || available.find(row => row.getBoundingClientRect().bottom > top) || available[available.length - 1];
  if (!anchor) return;
  const fileIndex = Number(anchor.dataset.file);
  const file = state.files[fileIndex];
  const limit = boot.maxLines > 0 ? Math.min(file.lines.length, boot.maxLines) : file.lines.length;
  const lines = file.lines.slice(0, limit);
  if (!selected) {
    const index = Number(anchor.dataset.row);
    const side = event.key === "ArrowLeft" && file.lines[index].old_line !== null ? "old" :
      file.lines[index].new_line !== null ? "new" : "old";
    current = {side, from: index, to: index};
  } else current = ReviewDiff.moveSelection(lines, current, event.key, event.shiftKey);
  if (!current) return;
  state.selection = {fileIndex, ...current};
  state.dragging = false;
  state.armed = true;
  paintSelection();
  const target = selectionTarget();
  if (target) {
    diffRow(fileIndex, current.to, current.side).scrollIntoView({block: "nearest", inline: "nearest"});
    say(target.path + " · " + (target.side === "old" ? "Before" : "After") + " lines " +
        target.start_line + "–" + target.end_line + ". Enter to comment.");
  }
}

function onSelectionEnter(event) {
  if (event.key !== "Enter" || !state.selection) return false;
  if (boot.mode !== "document" && (state.submitted || state.dialog || !el("help").hidden || !el("composer").hidden ||
      event.target !== el("diff") || event.ctrlKey || event.metaKey || event.altKey)) return false;
  event.preventDefault();
  showComposer();
  return true;
}

function setReviewView(view) {
  if (boot.mode === "document" || state.submitted || state.dialog || !["diff", "guided"].includes(view) || state.reviewView === view) return;
  state.reviewScroll ||= {};
  state.reviewScroll[state.reviewView] = el("diff").scrollTop;
  state.reviewView = view;
  state.dragging = false;
  for (const name of ["diff", "guided"]) {
    const tab = el("tab-" + name);
    tab.setAttribute("aria-selected", name === view ? "true" : "false");
    tab.tabIndex = name === view ? 0 : -1;
  }
  renderFiles();
  renderDiff();
  el("diff").scrollTop = state.reviewScroll[view] || 0;
  trackFile();
}

function onReviewTabKey(event) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key) || state.submitted || state.dialog) return;
  event.preventDefault();
  const view = event.key === "Home" ? "diff" : event.key === "End" ? "guided" : state.reviewView === "diff" ? "guided" : "diff";
  setReviewView(view);
  el("tab-" + view).focus();
}

function renderGuideOverview(host) {
  const guide = state.data.guide;
  const overview = document.createElement("section");
  overview.className = "guide-overview";
  const title = document.createElement("h2");
  title.textContent = "Overview";
  const note = document.createElement("p");
  note.className = "guide-note";
  note.textContent = guide.authored ? "Agent-authored explanation · Check the actual diff; this is not verified behavior." : "Directory grouping · No authored explanation";
  const summary = document.createElement("p");
  summary.textContent = guide.summary;
  overview.append(title, note, summary);
  if (guide.authored) {
    const comparison = document.createElement("div");
    comparison.className = "guide-comparison";
    for (const side of ["before", "after"]) {
      const card = document.createElement("section");
      card.className = "guide-side " + side;
      const heading = document.createElement("h3");
      heading.textContent = side === "before" ? "Before" : "After";
      const description = document.createElement("p");
      description.textContent = guide[side];
      card.append(heading, description);
      if (guide.flow) {
        const flow = document.createElement("ol");
        flow.className = "guide-flow";
        flow.setAttribute("aria-label", heading.textContent + " flow");
        for (const text of guide.flow[side]) {
          const label = document.createElement("li");
          label.textContent = text;
          flow.appendChild(label);
        }
        card.appendChild(flow);
      }
      comparison.appendChild(card);
    }
    overview.appendChild(comparison);
  }
  host.appendChild(overview);
}

function renderGuidedDiff(host) {
  renderGuideOverview(host);
  const guide = state.data.guide;
  const shown = new Set(visibleFiles());
  guide.chapters.forEach((chapter, chapterIndex) => {
    const files = chapter.file_indices.map(index => state.files[index]).filter(file => shown.has(file));
    if (!files.length) return;
    const section = document.createElement("section");
    section.className = "guide-chapter";
    const context = document.createElement("div");
    context.className = "guide-context";
    const position = document.createElement("p");
    position.className = "guide-position";
    position.textContent = "Chapter " + (chapterIndex + 1) + " / " + guide.chapters.length;
    const title = document.createElement("h2");
    title.textContent = chapter.title;
    const summary = document.createElement("p");
    summary.textContent = chapter.summary;
    const progress = document.createElement("label");
    progress.className = "guide-progress";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.reviewedChapters.has(chapterIndex);
    checkbox.disabled = state.submitted;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.reviewedChapters.add(chapterIndex); else state.reviewedChapters.delete(chapterIndex);
    });
    const label = document.createElement("span");
    label.textContent = "Reviewed chapter (reading progress only)";
    progress.append(checkbox, label);
    const list = document.createElement("div");
    list.className = "guide-files";
    const code = document.createElement("div");
    code.className = "guide-code";
    for (const file of files) {
      const index = state.files.indexOf(file);
      const link = document.createElement("button");
      link.className = "tiny ghost";
      link.textContent = file.path + "  +" + file.added + " / -" + file.removed;
      link.addEventListener("click", () => {
        state.expanded.add(index);
        renderDiff();
        el("diff").querySelector('.file[data-file="' + index + '"]').scrollIntoView({block: "start"});
        el("diff").focus({preventScroll: true});
      });
      list.appendChild(link);
      code.appendChild(renderFileDiff(file));
    }
    context.append(position, title, summary, progress, list);
    section.append(context, code);
    host.appendChild(section);
  });
}

function renderDiff() {
  state.changeLocation = null;
  state.changeStops = collectChangeStops();
  const host = el("diff");
  host.textContent = "";
  host.className = state.reviewView === "guided" ? "guided" : "";
  host.tabIndex = 0;
  host.setAttribute("role", "tabpanel");
  host.setAttribute("aria-labelledby", state.reviewView === "guided" ? "tab-guided" : "tab-diff");
  host.setAttribute("aria-label", "Code diff. Arrow keys select lines; Shift extends a range; Enter comments.");
  if (!state.files.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.style.padding = "16px";
    empty.textContent = "This review has no changes in scope.";
    host.appendChild(empty);
    trackFile();
    return;
  }
  if (state.reviewView === "guided") renderGuidedDiff(host);
  else visibleFiles().forEach(file => host.appendChild(renderFileDiff(file)));
  if (!visibleFiles().length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No file matches that filter.";
    host.appendChild(empty);
  }
  markThreadedRows();
  paintSelection();
  trackFile();
}

function renderFileDiff(file) {
    const fileIndex = state.files.indexOf(file);
    const open = state.expanded.has(fileIndex);
    const block = document.createElement("article");
    block.className = "file" + (state.diffView === "split" ? " split" : "") + (state.wrapLines ? "" : " nowrap");
    block.dataset.file = String(fileIndex);

    const heading = document.createElement("h3");
    const toggle = document.createElement("button");
    toggle.className = "chev";
    toggle.textContent = open ? "\u25be" : "\u25b8";
    toggle.title = open ? "Collapse this file" : "Expand this file";
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.addEventListener("click", () => {
      if (open) state.expanded.delete(fileIndex); else state.expanded.add(fileIndex);
      renderDiff();
    });
    const path = pathLabel(file.path);
    const badge = document.createElement("span");
    badge.className = "badge " + statusClass(file.status);
    badge.textContent = file.status;
    const counts = document.createElement("span");
    counts.className = "counts";
    counts.textContent = "+" + file.added + " / -" + file.removed;
    heading.append(toggle, fileIcon(file), path, badge, counts);
    if (file.old_path) {
      const from = document.createElement("span");
      from.className = "counts";
      from.textContent = "from " + file.old_path;
      heading.appendChild(from);
    }
    block.appendChild(heading);

    if (open) {
      const rows = document.createElement("div");
      rows.className = "rows";
      const limit = boot.maxLines > 0 ? Math.min(file.lines.length, boot.maxLines) : file.lines.length;
      const pairs = ReviewDiff.pairLines(file.lines.slice(0, limit));
      const changes = new Map();
      for (const pair of pairs) {
        if (pair.old == null || pair.new == null || file.lines[pair.old].type !== "remove" || file.lines[pair.new].type !== "add") continue;
        const ranges = ReviewDiff.wordRanges(file.lines[pair.old].text, file.lines[pair.new].text);
        if (ranges) { changes.set(pair.old, ranges.old); changes.set(pair.new, ranges.new); }
      }
      if (state.diffView === "split") {
        const labels = document.createElement("div");
        labels.className = "split-labels";
        for (const text of ["Before", "After"]) {
          const label = document.createElement("span");
          label.textContent = text;
          labels.appendChild(label);
        }
        rows.appendChild(labels);
        for (const pair of pairs) {
          if (pair.meta !== undefined) rows.appendChild(makeRow(fileIndex, file.lines[pair.meta], pair.meta));
          else {
            const row = document.createElement("div");
            row.className = "split-row";
            row.append(makeSideCell(fileIndex, pair.old, "old", changes.get(pair.old)), makeSideCell(fileIndex, pair.new, "new", changes.get(pair.new)));
            rows.appendChild(row);
          }
        }
      } else {
        for (let row = 0; row < limit; row++) rows.appendChild(makeRow(fileIndex, file.lines[row], row, changes.get(row)));
      }
      if (file.binary) {
        const note = document.createElement("div");
        note.className = "row meta";
        const code = document.createElement("span");
        code.className = "code";
        code.textContent = "Binary file: no lines to comment on.";
        note.appendChild(code);
        rows.appendChild(note);
      }
      if (file.lines.length > limit) {
        const more = document.createElement("div");
        more.className = "row meta";
        more.style.gridTemplateColumns = "1fr";
        const button = document.createElement("button");
        button.className = "link";
        button.textContent = "\u2026 " + (file.lines.length - limit) + " more line(s) not rendered";
        button.addEventListener("click", () => { boot.maxLines = 0; renderDiff(); });
        more.appendChild(button);
        rows.appendChild(more);
      }
      block.appendChild(rows);
    }
    return block;
}

// A commented line carries a dot in the gutter, so the diff itself shows where
// the work is instead of making the reader hunt through the side panel.
function markThreadedRows() {
  for (const thread of state.threads) {
    if (thread.target.scope !== "line") continue;
    const fileIndex = state.files.findIndex(
      (file) => file.path === thread.target.path && file.repository === thread.target.repository);
    if (fileIndex < 0) continue;
    const file = state.files[fileIndex];
    const rowIndex = file.lines.findIndex(
      (line) => line.type !== "meta" && lineNumberFor(line, thread.target.side) === thread.target.start_line);
    if (rowIndex < 0) continue;
    const row = diffRow(fileIndex, rowIndex, thread.target.side || "new");
    if (!row) continue;
    row.classList.add("threaded");
    if (thread.resolved) row.classList.add("resolved-thread");
  }
}

function lineNumberFor(line, side) {
  if (!side || side === "new") return line.new_line;
  return line.old_line;
}

// ----------------------------------------------------------- document mode

// The document renders as blocks. Every block remembers the source range it
// came from, and a comment carries exactly that range, so "line 42" means one
// specific place in the file no matter how the document is drawn.
const BLOCK_CLASS = {
  heading: "h", paragraph: "p", text: "p", blank: "blank", rule: "rule",
  quote: "q", list: "li", table: "tb", code: "code",
};

function renderDocument() {
  const data = state.data;
  document.body.classList.add("document");
  el("review-title").textContent = "Review document";
  renderBrief(data.criterion);
  el("review-id").textContent = data.name || data.path;
  const line = document.createElement("div");
  line.className = "docpath";
  line.textContent = data.path;
  el("repos").textContent = "";
  el("repos").appendChild(line);

  const host = el("diff");
  host.className = "doc";
  host.textContent = "";
  state.blocks = data.blocks || [];
  for (const block of state.blocks) host.appendChild(renderBlock(block));
  state.files = [];
  renderOutline();
  renderThreads();
  renderFooter();
  markDocumentThreadedRows();
  drawDiagrams();
}

function renderBlock(block) {
  const node = document.createElement("section");
  node.className = "blk " + (BLOCK_CLASS[block.kind] || "p");
  if (block.kind === "heading") node.classList.add("h" + block.level);
  if (block.kind === "list" && block.checked !== undefined) {
    node.classList.add("task");
    if (block.checked) node.classList.add("done");
  }
  node.dataset.start = String(block.start);
  node.dataset.end = String(block.end);

  const anchor = document.createElement("span");
  anchor.className = "at";
  anchor.textContent = String(block.start);
  anchor.title = "lines " + block.start + "-" + block.end;
  const body = document.createElement("div");
  // The markdown class is what the document typography hangs off: every rule
  // for prose, tables and lists is scoped to it, not to the block shell.
  body.className = block.kind === "code" || block.kind === "blank" || block.kind === "rule" ? "bd" : "bd md";
  body.innerHTML = blockBody(block);
  node.append(anchor, body);
  if (block.kind !== "blank" && block.kind !== "rule") {
    node.addEventListener("mousedown", (event) => onDocumentPress(event, block));
  }
  return node;
}


// Footnotes are the one construct that spans blocks: the reference sits in a
// paragraph, the definition in another. markdown-it only renders a footnote
// list for footnotes something referenced, so the definition text travels with
// the reference that needs it, and the bare definitions render as nothing.
function documentFootnotes() {
  if (state.footnotes === undefined) {
    const found = {};
    for (const block of state.blocks || []) {
      if (block.kind !== "text" || !block.source) continue;
      const lines = block.source.split(NEWLINE);
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.indexOf("[^") !== 0) continue;
        const close = line.indexOf("]");
        if (close < 3 || line.charAt(close + 1) !== ":") continue;
        const id = line.slice(2, close);
        if (found[id] !== undefined) continue;
        const parts = [line];
        while (i + 1 < lines.length && lines[i + 1].length && lines[i + 1].indexOf("[^") !== 0) {
          parts.push(lines[i + 1].trim());
          i += 1;
        }
        found[id] = parts.join(NEWLINE);
      }
    }
    state.footnotes = found;
  }
  return state.footnotes;
}

function footnoteRefs(text) {
  const ids = [];
  let at = text.indexOf("[^");
  while (at !== -1) {
    const end = text.indexOf("]", at);
    if (end === -1) break;
    const id = text.slice(at + 2, end);
    if (id && id.indexOf(":") === -1 && ids.indexOf(id) === -1) ids.push(id);
    at = text.indexOf("[^", end);
  }
  return ids;
}

function isFootnoteDefinitionBlock(block) {
  if (block.kind !== "text" || !block.source) return false;
  const text = block.source.trim();
  if (text.indexOf("[^") !== 0) return false;
  const close = text.indexOf("]");
  return close > 2 && text.charAt(close + 1) === ":";
}

function renderBlockMarkdown(block) {
  const source = block.source;
  if (isFootnoteDefinitionBlock(block)) return "";
  const footnotes = documentFootnotes();
  if (!Object.keys(footnotes).length) return md.render(source);
  const refs = footnoteRefs(source).filter((id) => footnotes[id] !== undefined);
  if (!refs.length) return md.render(source);
  const carried = refs.map((id) => footnotes[id]).join(NEWLINE);
  return md.render(source + NEWLINE + NEWLINE + carried);
}

function blockBody(block) {
  if (block.kind === "blank") return "";
  if (block.kind === "rule") return '<hr>';
  if (block.kind === "code") return codeBlockHtml(block);
  if (block.source !== undefined && md) return renderBlockMarkdown(block);
  if (block.kind === "table") return tableHtml(block);
  return block.html.replace(/\\n/g, "<br>");
}

// The block's source still carries its fence lines; the body is between them.
let mermaidReady = false;
let mermaidId = 0;

const DIAGRAM_KEYWORDS = ["graph", "flowchart", "sequenceDiagram", "classDiagram",
  "stateDiagram", "stateDiagram-v2", "erDiagram", "journey", "gantt", "pie",
  "gitGraph", "mindmap", "timeline", "quadrantChart", "requirementDiagram", "C4Context"];

function prepareMermaid() {
  if (mermaidReady || !window.mermaid) return mermaidReady;
  try {
    window.mermaid.initialize({
      startOnLoad: false, securityLevel: "strict", theme: "dark",
      themeVariables: { fontFamily: "Inter, sans-serif", primaryColor: "#1a1e28",
        primaryTextColor: "#e7ecf4", primaryBorderColor: "#3a4256", lineColor: "#8b95a5",
        textColor: "#c9d3e0" },
      flowchart: { htmlLabels: false },
    });
  } catch (error) { return false; }
  mermaidReady = true;
  return true;
}

// Mermaid only draws what it recognises. No regex: the page lives inside a
// non-raw Python string, where a backslash written for the browser arrives as
// a control character.
function isDiagramSource(source) {
  const body = String(source || "").trim();
  if (!body) return false;
  const first = body.split(NEWLINE)[0].trim();
  return DIAGRAM_KEYWORDS.some((word) => {
    if (first === word) return true;
    for (const tail of [" ", "/", "{", ":"]) {
      if (first.indexOf(word + tail) === 0) return true;
    }
    return false;
  });
}

async function drawDiagrams() {
  if (!prepareMermaid()) return;
  const nodes = [...document.querySelectorAll(".diagram")];
  for (const node of nodes) {
    const source = node.textContent;
    try {
      const drawn = await window.mermaid.render("m" + node.dataset.mermaid, source);
      node.innerHTML = drawn.svg;
      node.classList.add("drawn");
    } catch (error) {
      node.classList.add("undrawn");
    }
  }
}

function fenceBody(block) {
  const lines = (block.source || "").split("\\n");
  if (!lines.length) return "";
  const opening = lines[0].trim();
  if (opening.charAt(0) !== "`" && opening.charAt(0) !== "~") return lines.join("\\n");
  const marker = opening.charAt(0);
  let width = 0;
  while (width < opening.length && opening.charAt(width) === marker) width++;
  const body = lines.slice(1);
  while (body.length && body[body.length - 1].trim().indexOf(marker.repeat(width)) !== 0) body.pop();
  if (body.length) body.pop();
  return body.join("\\n");
}

function codeBlockHtml(block) {
  const body = fenceBody(block);
  const language = (block.language || "").toLowerCase();
  if (language === "mermaid" && isDiagramSource(body)) {
    return '<div class="diagram" data-mermaid="' + mermaidId++ + '">' + escapeHtml(body) + "</div>";
  }
  let code = escapeHtml(body);
  const engine = window.hljs;
  if (engine && language && language !== "text" && engine.getLanguage(language)) {
    try { code = engine.highlight(body, {language: language, ignoreIllegals: true}).value; }
    catch (error) { /* an engine failure must never cost a review */ }
  }
  const label = language && language !== "text" ? '<span class="lang">' + escapeHtml(language) + "</span>" : "";
  return label + "<pre><code>" + code + "</code></pre>";
}

function escapeHtml(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function tableHtml(block) {
  const lines = block.html.split("\\n").filter((row) => row.length);
  const cells = (row) => row.replace(/^[|]/, "").replace(/[|]$/, "").split("|").map((cell) => cell.trim());
  const isDivider = (row) => /^[\\s:|-]+$/.test(row.replace(/[|]/g, ""));
  const head = lines.length && !isDivider(lines[0]) ? lines.shift() : null;
  const body = lines.filter((row) => !isDivider(row));
  const out = ["<table>"];
  if (head) out.push("<tr>" + cells(head).map((c) => "<td>" + c + "</td>").join("") + "</tr>");
  for (const row of body) out.push("<tr>" + cells(row).map((c) => "<td>" + c + "</td>").join("") + "</tr>");
  out.push("</table>");
  return out.join("");
}

function renderOutline() {
  const nav = el("outline");
  nav.hidden = !state.blocks.length;
  nav.textContent = "";
  const headings = state.blocks.filter((block) => block.kind === "heading");
  if (!headings.length) { nav.hidden = true; return; }
  const label = document.createElement("div");
  label.className = "group";
  label.textContent = "Outline";
  nav.appendChild(label);
  for (const block of headings) {
    const link = document.createElement("a");
    link.className = "lv" + block.level;
    link.href = "#";
    link.dataset.start = String(block.start);
    link.textContent = block.html.replace(/<[^>]*>/g, "").trim() || "Section";
    link.addEventListener("click", (event) => {
      event.preventDefault();
      jumpToRange(block.start, block.end);
    });
    nav.appendChild(link);
  }
}

// The outline marks the heading the viewport is inside, so you always know
// where you are in a long specification.
function trackOutline() {
  if (boot.mode !== "document" || !state.blocks || !state.blocks.length) return;
  const links = el("outline").querySelectorAll("a");
  if (!links.length) return;
  const headings = Array.from(links);
  // The heading you are reading is the last one above the middle of the
  // viewport. A threshold tied to the header height is fragile: the moment a
  // heading sits just below it, the mark lags a whole section.
  const limit = window.innerHeight / 2;
  let current = null;
  for (const link of headings) {
    const block = state.blocks.find((b) => b.kind === "heading" && b.start === Number(link.dataset.start));
    if (!block) continue;
    const node = el("diff").querySelector('[data-start="' + block.start + '"]');
    if (node && node.getBoundingClientRect().top <= limit) current = link;
  }
  for (const link of headings) link.classList.toggle("here", link === current);
}

function jumpToRange(start, end) {
  const node = el("diff").querySelector('[data-start="' + start + '"]');
  if (!node) return;
  node.scrollIntoView({block: "center"});
  node.classList.remove("flash");
  void node.offsetWidth;
  node.classList.add("flash");
}

function onDocumentPress(event, block) {
  if (state.submitted) return;
  const current = state.selection;
  if (event.shiftKey && current && current.mode === "document" && current.fileIndex === block.start) {
    current.to = block.end;
  } else if (event.shiftKey && current && current.mode === "document") {
    // Shift extends from the anchor, so a drag across blocks stays one range.
    current.to = block.end;
  } else {
    state.selection = {mode: "document", fileIndex: block.start, side: "new", from: block.start, to: block.end};
  }
  hideComposer();
  paintSelection();
}

function paintSelection() {
  for (const row of state.painted) row.classList.remove("sel");
  state.painted = [];
  const selection = state.selection;
  if (!selection) return;
  if (selection.mode === "document") {
    const from = Math.min(selection.from, selection.to);
    const to = Math.max(selection.from, selection.to);
    for (const node of el("diff").querySelectorAll(".blk")) {
      const start = Number(node.dataset.start);
      const end = Number(node.dataset.end);
      if (end >= from && start <= to) { node.classList.add("sel"); state.painted.push(node); }
    }
    return;
  }
  const block = document.querySelector('.file[data-file="' + selection.fileIndex + '"]');
  if (!block) return;
  const from = Math.min(selection.from, selection.to);
  const to = Math.max(selection.from, selection.to);
  for (const row of block.querySelectorAll(".row[data-row]")) {
    const index = Number(row.dataset.row);
    if (index < from || index > to || (row.dataset.side && row.dataset.side !== selection.side)) continue;
    if (sideNumber(state.files[selection.fileIndex].lines[index], selection.side) === null) continue;
    row.classList.add("sel");
    state.painted.push(row);
  }
}

function markDocumentThreadedRows() {
  for (const thread of state.threads) {
    if (thread.target.scope !== "line") continue;
    const wanted = thread.target.start_line;
    const block = (state.blocks || []).find((item) => wanted >= item.start && wanted <= item.end);
    if (!block) continue;
    const node = el("diff").querySelector('[data-start="' + block.start + '"]');
    if (!node) continue;
    node.classList.add("threaded");
    if (thread.resolved) node.classList.add("resolved-thread");
  }
}

function threadLocation(target) {
  if (target.scope === "review") return "whole review";
  return target.path + ":" + target.start_line +
    (target.end_line === target.start_line ? "" : "-" + target.end_line) +
    (target.side ? " (" + target.side + ")" : "");
}

function jumpToThread(thread) {
  setCommentsCollapsed(false);
  if (thread.target.scope !== "line") return;
  if (boot.mode === "document") {
    const wanted = thread.target.start_line;
    const block = (state.blocks || []).find(
      (item) => wanted >= item.start && wanted <= item.end);
    if (block) jumpToRange(block.start, block.end);
    return;
  }
  const fileIndex = state.files.findIndex(
    (file) => file.path === thread.target.path && file.repository === thread.target.repository);
  if (fileIndex < 0) return;
  if (!visibleFiles().includes(state.files[fileIndex])) {
    state.filter = "";
    el("file-filter").value = "";
    renderFiles();
  }
  state.expanded.add(fileIndex);
  renderDiff();
  const file = state.files[fileIndex];
  const rowIndex = file.lines.findIndex(
    (line) => line.type !== "meta" && lineNumberFor(line, thread.target.side) === thread.target.start_line);
  if (rowIndex < 0) return;
  const row = diffRow(fileIndex, rowIndex, thread.target.side || "new");
  if (!row) return;
  row.scrollIntoView({block: "center"});
  row.classList.remove("flash");
  void row.offsetWidth;
  row.classList.add("flash");
}

function renderThreads() {
  renderCommentsToggle();
  const list = el("threads");
  list.textContent = "";
  if (!state.threads.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.innerHTML = "No comments yet.<br><br>Click a line, or drag across a range, then write your note. " +
      "Comments you leave open are what the coding agent receives when you choose <b>Request changes</b>.";
    list.appendChild(empty);
    return;
  }
  const open = unresolvedThreads();
  const done = resolvedThreads();
  const addGroup = (label) => {
    const head = document.createElement("li");
    head.className = "group";
    head.textContent = label;
    list.appendChild(head);
  };
  const addThread = (thread) => {
    const item = document.createElement("li");
    item.className = "thread" + (thread.resolved ? " resolved" : "");
    item.tabIndex = 0;
    const where = document.createElement("div");
    where.className = "where";
    where.textContent = threadLocation(thread.target);
    const text = document.createElement("div");
    text.className = "text";
    text.textContent = thread.text;
    const acts = document.createElement("div");
    acts.className = "acts";
    const toggle = document.createElement("button");
    toggle.className = "tiny";
    toggle.textContent = thread.resolved ? "Reopen" : "Resolve";
    toggle.addEventListener("click", () => { thread.resolved = !thread.resolved; refreshThreads(); });
    const remove = document.createElement("button");
    remove.className = "tiny";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => {
      state.threads = state.threads.filter((other) => other.id !== thread.id);
      refreshThreads();
    });
    acts.append(toggle, remove);
    item.append(where, text, acts);
    item.addEventListener("click", (event) => {
      if (event.target.tagName === "BUTTON") return;
      jumpToThread(thread);
    });
    list.appendChild(item);
  };
  if (open.length) { addGroup("To fix (" + open.length + ")"); open.forEach(addThread); }
  if (done.length) { addGroup("Resolved (" + done.length + ")"); done.forEach(addThread); }
}

function renderCommentsToggle() {
  const toggle = el("comments-toggle");
  toggle.textContent = (state.commentsCollapsed ? "Show" : "Hide") + " comments (" + state.threads.length + ")";
  toggle.setAttribute("aria-expanded", state.commentsCollapsed ? "false" : "true");
}

function setCommentsCollapsed(collapsed) {
  state.commentsCollapsed = collapsed;
  document.body.classList.toggle("comments-collapsed", collapsed);
  el("threads-panel").hidden = collapsed;
  renderCommentsToggle();
  trackOutline();
  trackFile();
}

function renderFooter() {
  const unresolved = unresolvedThreads().length;
  const resolved = resolvedThreads().length;
  const review = reviewText() ? 1 : 0;
  el("counts").textContent = unresolved + " to fix, " + resolved + " resolved, " + review + " review";
  el("discard").hidden = unresolved === 0;
  el("banner").hidden = unresolved === 0;
  el("banner-text").textContent = unresolved
    ? unresolved + " comment(s) to send back. They block approval until you resolve, delete, or keep them as nits."
    : "";
  // Feedback is never blocked: the open comments are the point of it.
  el("changes").disabled = false;
  el("approve").disabled = false;
  el("planning").disabled = false;
}

// ----------------------------------------------------------------- selection

function onRowPress(event, fileIndex, index, line, explicitSide) {
  if (state.submitted || (event.button !== undefined && event.button !== 0)) return;
  const sideCell = event.target.classList.contains("ln") ? event.target.dataset.side : null;
  const side = explicitSide || sideCell || (line.new_line !== null ? "new" : "old");
  if (sideNumber(line, side) === null) return;
  const current = state.selection;
  if (event.shiftKey && current && current.fileIndex === fileIndex && current.side === side) {
    current.to = index;
  } else {
    state.selection = {fileIndex: fileIndex, side: side, from: index, to: index};
  }
  state.dragging = true;
  hideComposer();
  paintSelection();
}

function extendDiffSelection(event) {
  if (!state.dragging || !(event.buttons & 1) || !state.selection || state.submitted) return;
  const row = event.target.closest(".row[data-row]");
  if (!row || Number(row.dataset.file) !== state.selection.fileIndex) return;
  const index = Number(row.dataset.row);
  const line = state.files[state.selection.fileIndex].lines[index];
  const sideCell = event.target.closest("[data-side]");
  const side = sideCell ? sideCell.dataset.side : (line.new_line !== null ? "new" : "old");
  if (side !== state.selection.side || sideNumber(line, side) === null) return;
  state.selection.to = index;
  paintSelection();
}

function selectionTarget() {
  const selection = state.selection;
  if (!selection) return null;
  if (selection.mode === "document") {
    // A document has no old side: the selection is the source range of the
    // block, or of the blocks a shift-drag covered.
    return {
      scope: "line",
      path: state.data.path,
      start_line: Math.min(selection.from, selection.to),
      end_line: Math.max(selection.from, selection.to),
    };
  }
  const file = state.files[selection.fileIndex];
  const range = ReviewDiff.rangeFor(file.lines, selection.side, selection.from, selection.to);
  if (!range) return null;
  return {
    scope: "line",
    repository: file.repository,
    path: file.path,
    side: selection.side,
    ...range,
  };
}

function showComposer() {
  const target = selectionTarget();
  if (!target) {
    say("Select existing lines on one side within a continuous range.", "warn");
    return;
  }
  state.pendingTarget = target;
  el("composer-where").textContent = target.path + ":" + target.start_line +
    (target.end_line === target.start_line ? "" : "-" + target.end_line) +
    (target.side ? " (" + target.side + " side)" : "");
  el("composer-text").value = "";
  el("composer").hidden = false;
  el("composer-text").focus();
  say("");
}

function hideComposer() {
  state.pendingTarget = null;
  el("composer").hidden = true;
}

// Every panel that counts or lists comments reads the same thread set, so one
// call after any change to it keeps the counts honest.
function refreshThreads() {
  renderThreads();
  renderFiles();
  renderFooter();
  if (boot.mode === "document") markDocumentThreadedRows(); else markThreadedRows();
}

function saveComment() {
  const text = el("composer-text").value.trim();
  if (!text) { say("A comment needs text.", "warn"); return; }
  if (!state.pendingTarget) { hideComposer(); return; }
  state.threads.push({id: state.nextThreadId++, resolved: false, text: text, target: state.pendingTarget});
  hideComposer();
  state.selection = null;
  paintSelection();
  refreshThreads();
  say("Comment added. It is sent with the decision once resolved.", "");
}

// -------------------------------------------------------------------- dialog

function openDialog(title, body, actions) {
  state.dialog = actions;
  el("dialog-title").textContent = title;
  el("dialog-body").textContent = body;
  const acts = el("dialog-acts");
  acts.textContent = "";
  let first = null;
  for (const action of actions) {
    const button = document.createElement("button");
    if (action.primary) button.className = "primary";
    button.textContent = action.label;
    button.addEventListener("click", () => { closeDialog(); action.run(); });
    acts.appendChild(button);
    if (action.primary && !first) first = button;
  }
  el("backdrop").hidden = false;
  (first || acts.querySelector("button")).focus();
}

function closeDialog() {
  state.dialog = null;
  el("backdrop").hidden = true;
}

function approve() {
  if (state.submitted) return;
  const unresolved = unresolvedThreads();
  if (unresolved.length) {
    openDialog(
      unresolved.length + " unresolved comment(s) block approval",
      "Resolve or delete each comment first, or keep them as non-blocking nits: they will be sent with an approval instead of holding it back.",
      [
        {label: "Back", run: () => {}},
        {label: "Keep as nits and approve", primary: true, run: () => { unresolved.forEach((t) => { t.resolved = true; }); confirmApprove(); }},
      ]);
    return;
  }
  confirmApprove();
}

function confirmApprove() {
  const carried = resolvedThreads().length + (reviewText() ? 1 : 0);
  if (!carried) { sendDecision("approve"); return; }
  openDialog(
    "Approve with " + carried + " comment(s)?",
    "The comments are sent as non-blocking nits. The review is still approved.",
    [
      {label: "Back", run: () => {}},
      {label: "Approve anyway", primary: true, run: () => { sendDecision("approve"); }},
    ]);
}

function requestChanges() {
  if (state.submitted) return;
  // Unresolved comments ARE the feedback the author has to act on, so they
  // never block sending it. Only approval is gated by them.
  if (!state.threads.length && !reviewText()) {
    say("Add a review comment or a line comment before sending feedback.", "warn");
    return;
  }
  sendDecision("request-changes");
}

function returnToPlanning() {
  if (state.submitted) return;
  sendDecision("return-to-planning");
}

function cancelReview() {
  if (state.submitted) return;
  const threads = state.threads.length;
  const review = reviewText() ? 1 : 0;
  if (!threads && !review) { sendDecision("cancelled"); return; }
  openDialog(
    "Cancel the review?",
    threads + " comment(s) and " + review + " review comment(s) will be discarded. Nothing is approved.",
    [
      {label: "Back", run: () => {}},
      {label: "Cancel the review", primary: true, run: () => { sendDecision("cancelled"); }},
    ]);
}

// --------------------------------------------------------------------- wiring

el("diff").addEventListener("mousedown", (event) => {
  if (state.submitted || boot.mode === "document") return;
  if (event.target.closest(".row") && !event.target.closest(".row[data-row]")) {
    state.selection = null;
    state.dragging = false;
    hideComposer();
    paintSelection();
  }
});

// Releasing the mouse ends a comment: a click or a dragged range both mean
// "I want to say something about this", so the box opens straight away instead
// of making the reader remember a second key.
el("diff").addEventListener("scroll", () => { trackOutline(); trackFile(); }, {passive: true});
window.addEventListener("resize", () => { trackOutline(); trackFile(); });
el("review-brief").addEventListener("toggle", () => { trackOutline(); trackFile(); });
el("diff").addEventListener("mouseup", () => {
  if (state.submitted || !state.selection) return;
  if (boot.mode !== "document" && !state.dragging) return;
  state.dragging = false;
  showComposer();
});
el("diff").addEventListener("mousemove", extendDiffSelection);
el("diff").addEventListener("keydown", onDiffKey);
document.addEventListener("mouseup", () => { state.dragging = false; });
window.addEventListener("blur", () => { state.dragging = false; });

// Arming: the diff arms the keyboard layer, any button parks it again.
el("diff").addEventListener("mousedown", () => { state.armed = true; });
document.addEventListener("click", (event) => {
  if (event.target.closest("button")) state.armed = false;
});

el("approve").addEventListener("click", approve);
el("changes").addEventListener("click", requestChanges);
el("planning").addEventListener("click", returnToPlanning);
el("cancel").addEventListener("click", cancelReview);

el("file-filter").addEventListener("input", (event) => {
  state.filter = event.target.value;
  renderFiles();
  renderDiff();
});
el("expand-all").addEventListener("click", () => {
  visibleFiles().forEach((file) => state.expanded.add(state.files.indexOf(file)));
  renderDiff();
});
el("collapse-all").addEventListener("click", () => {
  state.expanded.clear();
  renderDiff();
});
el("comments-toggle").addEventListener("click", () => setCommentsCollapsed(!state.commentsCollapsed));
for (const view of ["diff", "guided"]) {
  el("tab-" + view).addEventListener("click", () => setReviewView(view));
  el("tab-" + view).addEventListener("keydown", onReviewTabKey);
}
el("view-inline").addEventListener("click", () => setDiffView("inline"));
el("view-split").addEventListener("click", () => setDiffView("split"));
el("wrap-lines").addEventListener("click", () => setWrapLines(!state.wrapLines));
el("previous-change").addEventListener("click", () => stepChange(-1));
el("next-change").addEventListener("click", () => stepChange(1));
el("next-thread").addEventListener("click", () => cycleThread(1));
el("help-open").addEventListener("click", () => { el("help").hidden = false; });
el("help").addEventListener("click", () => { el("help").hidden = true; });

function cycleThread(step) {
  if (!state.threads.length) { say("No comments yet.", ""); return; }
  state.threadCursor = ((state.threadCursor === undefined ? -1 : state.threadCursor) + step + state.threads.length) % state.threads.length;
  const thread = state.threads[state.threadCursor];
  jumpToThread(thread);
  say("Comment " + (state.threadCursor + 1) + " of " + state.threads.length + ": " + threadLocation(thread.target));
}

function stepFile(step) {
  const shown = visibleFiles();
  if (!shown.length) return;
  const anchors = shown.map((file) => state.files.indexOf(file));
  trackFile();
  const current = anchors.indexOf(state.currentFile);
  const next = current === -1 ? 0 : (current + step + shown.length) % shown.length;
  const index = anchors[next];
  state.expanded.add(index);
  renderDiff();
  const box = el("diff").querySelector('.file[data-file="' + index + '"]');
  if (box) box.scrollIntoView({block: "start"});
  renderFiles();
}

el("discard").addEventListener("click", () => {
  state.threads = state.threads.filter((t) => t.resolved);
  refreshThreads();
  say("Unresolved comments discarded.", "");
});
el("banner-resolve").addEventListener("click", () => {
  unresolvedThreads().forEach((t) => { t.resolved = true; });
  refreshThreads();
  say("Unresolved comments kept as non-blocking nits.", "");
});
el("composer-save").addEventListener("click", saveComment);
el("composer-cancel").addEventListener("click", () => { hideComposer(); });
el("composer-text").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); saveComment(); }
  if (event.key === "Escape") { event.preventDefault(); hideComposer(); }
});
el("review-comment").addEventListener("input", renderFooter);

document.addEventListener("keydown", (event) => {
  const typing = /^(INPUT|TEXTAREA)$/.test(event.target.tagName);
  if (state.dialog) {
    if (event.key === "Escape") { event.preventDefault(); closeDialog(); return; }
    if (event.key === "Tab") {
      const buttons = Array.from(el("dialog-acts").querySelectorAll("button"));
      if (!buttons.length) return;
      const index = buttons.indexOf(document.activeElement);
      event.preventDefault();
      buttons[(index + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length].focus();
    }
    return;
  }
  if (event.key === "Escape") {
    state.dragging = false;
    if (!el("help").hidden) { el("help").hidden = true; return; }
    if (!el("composer").hidden) { hideComposer(); return; }
    if (state.selection) { state.selection = null; paintSelection(); return; }
  }
  if (typing) return;
  if (onSelectionEnter(event)) return;
  if (event.key === "?") { event.preventDefault(); el("help").hidden = !el("help").hidden; return; }
  // A decision sends an irreversible verdict to the coding agent, so it needs
  // a modifier as well as the right key: a stray letter must never be able to
  // approve or cancel a change. Deliberate means deliberate, so this runs
  // before the focus guards that protect the bare keys below.
  if (event.metaKey || event.ctrlKey || event.altKey) {
    const decision = {a: approve, r: requestChanges, p: returnToPlanning, c: cancelReview};
    const chosen = decision[event.key.toLowerCase()];
    if (chosen) { event.preventDefault(); chosen(); }
    return;
  }
  if (event.target.tagName === "BUTTON" || !el("help").hidden) return;
  if (event.key === "/") { event.preventDefault(); el("file-filter").focus(); return; }
  if (!state.armed) return;
  const nav = {n: () => cycleThread(1), j: () => stepFile(1), k: () => stepFile(-1)};
  const action = nav[event.key.toLowerCase()];
  if (action) { event.preventDefault(); action(); }
});

window.addEventListener("pagehide", () => {
  // A closed window is a withdrawn review, but a reload also ends the page: the
  // server withdraws the review only if this is still the newest page.
  if (state.submitted) return;
  state.submitted = true;
  try {
    navigator.sendBeacon(boot.url + "api/closing?page=" + boot.page);
  } catch (ignored) {}
});

loadReview().then((data) => {
  state.data = data;
  // Open every file: a reviewer should see the whole change, not hunt for it.
  state.expanded = new Set([]);
  render();
  document.body.dataset.ready = "1";
}).catch((error) => {
  say(error.message || String(error), "error");
});
</script>
</body>
</html>
"""


def render_page(token: str, mode: str = "diff", page: int = 0) -> bytes:
    """The one self-contained page, with its own token and mode baked into the
    boot JSON. A document review loads the same page and renders a document."""
    boot = json.dumps(
        {
            "url": f"/{token}/",
            "page": page,
            "maxLines": MAX_RENDERED_LINES_PER_FILE,
            "mode": mode,
            "reviewUrl": "api/review" if mode == "diff" else "api/doc",
            "decisionUrl": "api/decision" if mode == "diff" else "api/doc-decision",
        },
        separators=(",", ":"),
    )
    logic = (Path(__file__).resolve().parents[1] / "assets" / "review-diff.js").read_text(encoding="utf-8")
    return PAGE_TEMPLATE.replace("__HTML_REVIEW_BOOT__", boot).replace("__HTML_DIFF_VIEW__", logic).encode("utf-8")


# --------------------------------------------------------------------------
# server
# --------------------------------------------------------------------------


class ReviewHandler(BaseHTTPRequestHandler):
    """Serves the page, the review payload, and the decision, behind the token."""

    protocol_version = "HTTP/1.1"
    server_version = "html-review"
    sys_version = ""

    @property
    def session(self) -> "ReviewSession":
        return self.server.session  # type: ignore[attr-defined]

    def log_message(self, *args: Any) -> None:
        """Silence the default request log: it would print the token and paths."""

    def route(self) -> "str | None":
        # A token that does not match is a probe, not a user: only count the
        # requests that prove somebody actually opened the page.
        path = urllib.parse.urlsplit(self.path).path
        parts = [part for part in path.split("/") if part]
        if parts and secrets.compare_digest(parts[0], self.session.token):
            self.session._requests += 1
        if not parts or not secrets.compare_digest(parts[0], self.session.token):
            return None
        rest = parts[1:]
        if not rest:
            return "page"
        if rest == ["api", "review"]:
            return "review"
        if rest == ["api", "decision"]:
            return "decision"
        if rest == ["api", "doc"]:
            return "doc"
        if rest == ["api", "doc-decision"]:
            return "doc-decision"
        if rest == ["api", "closing"]:
            return "closing"
        # The code font is bundled with the reviewer and served from this same
        # origin, so the page needs no external resource and works offline.
        if len(rest) == 2 and rest[0] == "font" and rest[1] in FONT_FILES:
            return "font"
        if len(rest) == 2 and rest[0] == "vendor" and rest[1] in VENDOR_FILES:
            return "vendor"
        return None

    def respond(self, status: int, body: bytes = b"", content_type: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        if status != 204:  # a 204 carries no body, so it carries no length either
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def fail(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.respond(status, body, "application/json; charset=utf-8")

    def read_body(self) -> "bytes | None":
        length = self.headers.get("Content-Length")
        if length is None:
            self.fail(411, "a decision needs a Content-Length")
            return None
        try:
            size = int(length)
        except ValueError:
            self.fail(400, "an unusable Content-Length")
            return None
        if size < 0 or size > MAX_BODY_BYTES:
            self.fail(413, "the decision is too large")
            return None
        return self.rfile.read(size) if size else b""

    def do_GET(self) -> None:
        route = self.route()
        if route == "page":
            page = self.session.next_page()
            self.respond(200, render_page(self.session.token, self.session.mode, page), "text/html; charset=utf-8")
            return
        if route == "review":
            self.respond(
                200,
                json.dumps(self.session.payload, separators=(",", ":")).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if route == "doc":
            self.respond(
                200,
                json.dumps(self.session.payload, separators=(",", ":")).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if route == "font":
            name = urllib.parse.urlsplit(self.path).path.split("/")[-1]
            self.respond(200, FONT_FILES[name].read_bytes(), "font/woff2")
            return
        if route == "vendor":
            name = urllib.parse.urlsplit(self.path).path.split("/")[-1]
            self.respond(200, (ASSET_VENDOR / name).read_bytes(), VENDOR_FILES[name])
            return
        if route is None:
            self.fail(404, "not found")
            return
        self.fail(405, f"{route} needs POST")

    def do_POST(self) -> None:
        route = self.route()
        if route in ("page", "review", "doc", "font", "vendor"):
            self.fail(405, f"{route} needs POST")
            return
        if route == "closing":
            page = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("page", [""])[0]
            if not page.isascii() or not page.isdigit() or len(page) > 9 or int(page) < 1:
                self.fail(400, "a closing report needs the number of the page that is closing")
                return
            self.session.begin_close(int(page))
            self.respond(204)
            return
        if route not in ("decision", "doc-decision"):
            self.fail(404, "not found")
            return
        body = self.read_body()
        if body is None:
            return
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.fail(400, "the decision is not valid JSON")
            return
        try:
            if route == "doc-decision":
                result = parse_document_decision(decoded, self.session.request, self.session.index)
            else:
                result = parse_decision(decoded, self.session.request, self.session.index)
        except DecisionError as error:
            self.fail(400, str(error))
            return
        self.respond(204)
        self.session.submit(result)



def publish_url(path: "str | None", url: str, stream: "Any" = None) -> None:
    """Publishes the page URL so a caller that cannot see stderr can still open it."""
    if not path:
        return
    out = sys.stderr if stream is None else stream
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(url + "\n")
    except OSError as error:
        # A review must not fail because a convenience file could not be written.
        out.write(f"{PRODUCER}: unable to publish the review URL to {path} ({error})\n")
        out.flush()


def withdraw_url(path: "str | None") -> None:
    """Removes the published URL: the token dies with the server."""
    if not path:
        return
    try:
        os.unlink(path)
    except OSError:
        pass


class ReviewSession:
    """One review: a bound server, the token that gates it, and its result."""

    def __init__(
        self,
        request: Any,
        payload: dict[str, Any],
        *,
        token: "str | None" = None,
        open_browser: bool = True,
        host: str = HOST,
        lifetime_seconds: float = LIFETIME_SECONDS,
        idle_seconds: float = IDLE_SECONDS,
        close_grace_seconds: float = CLOSE_GRACE_SECONDS,
        mode: str = "diff",
    ) -> None:
        self.request = request
        self.payload = payload
        self.mode = mode
        # A diff indexes (repository, path, side); a document indexes plain line
        # numbers, because a specification has no repository and no old side.
        self.index = document_line_index(payload) if mode == "document" else line_index(payload)
        self.token = token if token is not None else secrets.token_urlsafe(24)
        self.open_browser = open_browser
        self._decided = threading.Event()
        self._result: "dict[str, Any] | None" = None
        self._lock = threading.Lock()
        self._closed = False
        self._serving = False
        self._httpd = ThreadingHTTPServer((host, 0), ReviewHandler)
        self._httpd.daemon_threads = True
        self._httpd.session = self  # type: ignore[attr-defined]
        self._requests = 0
        self._reason: "str | None" = None
        self.lifetime_seconds = lifetime_seconds
        self.idle_seconds = idle_seconds
        self.close_grace_seconds = close_grace_seconds
        self._closing: "threading.Timer | None" = None
        self._page = 0

    @property
    def host(self) -> str:
        return str(self._httpd.server_address[0])

    @property
    def port(self) -> int:
        return int(self._httpd.server_address[1])

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.token}/"

    def start(self) -> "ReviewSession":
        """Serves in the background so a caller can talk to the server itself."""
        if self._serving:
            return self
        self._serving = True
        thread = threading.Thread(target=self._httpd.serve_forever, name="html-review", daemon=True)
        thread.start()
        return self

    def submit(self, result: dict[str, Any]) -> None:
        with self._lock:
            if self._result is not None:
                return
            self._result = result
        self._decided.set()
        # shutdown() blocks until serve_forever() returns, so it must not run in
        # the handler thread that serve_forever() is currently waiting on.
        threading.Thread(target=self._httpd.shutdown, name="html-review-stop", daemon=True).start()

    def stop(self) -> None:
        """Ends the review with no decision: withdrawn, never approved."""
        self.submit(cancelled_result(self.request))

    def next_page(self) -> int:
        """Numbers a page being served; a newer page cancels a pending close."""
        with self._lock:
            self._page += 1
            page = self._page
        self.cancel_close()
        return page

    def begin_close(self, page: int) -> None:
        """A page is closing: withdraw the review unless a newer page exists or
        is requested within the grace period."""
        with self._lock:
            if self._result is not None or self._closing is not None or page != self._page:
                return
            self._closing = threading.Timer(self.close_grace_seconds, self.stop)
            self._closing.daemon = True
            self._closing.start()

    def cancel_close(self) -> None:
        with self._lock:
            closing, self._closing = self._closing, None
        if closing is not None:
            closing.cancel()

    def result(self, timeout: "float | None" = None) -> "dict[str, Any] | None":
        if not self._decided.wait(timeout):
            return None
        with self._lock:
            return self._result

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.cancel_close()
        self._httpd.shutdown()
        self._httpd.server_close()

    def watch_lifetime(self, *, poll: float = 0.5) -> threading.Thread:
        """Ends the review when nobody is left to receive it.

        A client killed with SIGKILL, a crash, or a closed laptop cannot clean
        this process up, and without a bound it would hold its port and wait
        for a decision that can no longer be recorded. Three conditions end it:
        the parent is gone, the wall-clock budget is spent, or the page was
        never opened.
        """
        original_parent = os.getppid()
        started = time.monotonic()

        def gone() -> bool:
            return os.getppid() != original_parent

        def poll_loop() -> None:
            while not self._decided.wait(poll):
                if gone():
                    self.expire("the client process ended")
                    return
                if time.monotonic() - started >= self.lifetime_seconds:
                    self.expire("the review lifetime expired")
                    return
                if self.idle_seconds and time.monotonic() - started >= self.idle_seconds and self._requests == 0:
                    self.expire("the review page was never opened")
                    return

        thread = threading.Thread(target=poll_loop, name="html-review-watchdog", daemon=True)
        thread.start()
        return thread

    def expire(self, reason: str) -> None:
        """Withdraws the review. An expired review is never an approval."""
        if self._reason is None:
            self._reason = reason
        self.stop()

    def serve_and_wait(
        self,
        stream: "Any" = None,
        url_file: "str | None" = None,
    ) -> dict[str, Any]:
        """Opens the page, serves until a decision arrives, and returns it."""
        out = sys.stderr if stream is None else stream
        self.start()
        out.write(f"{PRODUCER}: review page {self.url}\n")
        out.flush()
        publish_url(url_file, self.url, out)
        # Bounded from the moment the page is published, so a client that dies
        # uncatchably cannot leave this process holding its port forever.
        self.watch_lifetime()
        try:
            if self.open_browser:
                try:
                    webbrowser.open(self.url, new=1)
                except Exception as error:  # a headless box must not fail the gate
                    out.write(f"{PRODUCER}: unable to open a browser ({error}); open the URL above\n")
                    out.flush()
            self._decided.wait()
            result = self.result()
        finally:
            withdraw_url(url_file)
        self.close()
        # Nothing decided is a withdrawn review, never an approval.
        return result if result is not None else cancelled_result(self.request)


def start_review_server(
    request: task_review.ReviewRequest,
    *,
    git: GitRunner = task_review.run_git,
    open_browser: bool = True,
    token: "str | None" = None,
    host: str = HOST,
) -> ReviewSession:
    """Builds the payload, binds an ephemeral port, and serves in the background.

    Tests drive the returned session directly instead of opening a browser.
    """
    payload = build_payload(request, git)
    return ReviewSession(request, payload, token=token, open_browser=open_browser, host=host).start()


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------


def browser_enabled(environ: "dict[str, str]") -> bool:
    value = environ.get(NO_BROWSER_ENV, "").strip().lower()
    return value in ("", "0", "false", "no", "off")


def positive_seconds(environ: "dict[str, str]", name: str, default: float) -> float:
    """Reads a lifetime bound, treating junk as absent rather than guessing."""
    raw = environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def emit(result: dict[str, Any], stream: "Any" = None) -> None:
    out = sys.stdout if stream is None else stream
    out.write(json.dumps(result, separators=(",", ":")) + "\n")
    out.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PRODUCER,
        description="Review one task-review request in a local browser page and print one result line.",
    )
    parser.add_argument(
        "--review",
        nargs="?",
        const="",
        default=None,
        metavar="JSON",
        help="a complete ReviewRequest JSON document; with no value the request is read from stdin",
    )
    parser.add_argument(
        "--review-doc",
        nargs="?",
        const="",
        default=None,
        metavar="JSON",
        help="a complete DocumentRequest JSON document for a specification or plan",
    )
    return parser


def main(
    argv: "Sequence[str] | None" = None,
    environ: "dict[str, str] | None" = None,
    *,
    git: GitRunner = task_review.run_git,
    open_browser: "bool | None" = None,
    stream: "Any" = None,
) -> int:
    environment = dict(os.environ) if environ is None else environ
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.review is None and args.review_doc is None:
        parser.print_usage(sys.stderr)
        sys.stderr.write(
            f"{PRODUCER}: a review request is required: --review JSON or --review-doc JSON\n"
        )
        return EXIT_ERROR
    try:
        if args.review_doc is not None:
            request = parse_document_request(read_request_text(args.review_doc))
            session = ReviewSession(
                request,
                build_document_payload(request),
                open_browser=browser_enabled(environment) if open_browser is None else open_browser,
                lifetime_seconds=positive_seconds(environment, LIFETIME_ENV, LIFETIME_SECONDS),
                idle_seconds=positive_seconds(environment, IDLE_ENV, IDLE_SECONDS),
                mode="document",
            )
        else:
            request = parse_request(read_request_text(args.review))
            session = ReviewSession(
                request,
                build_payload(request, git),
                open_browser=browser_enabled(environment) if open_browser is None else open_browser,
                lifetime_seconds=positive_seconds(environment, LIFETIME_ENV, LIFETIME_SECONDS),
                idle_seconds=positive_seconds(environment, IDLE_ENV, IDLE_SECONDS),
            )
    except (task_review.TaskReviewError, OSError) as error:
        sys.stderr.write(f"{PRODUCER}: {error}\n")
        return EXIT_ERROR
    emit(session.serve_and_wait(stream, url_file=environment.get(URL_FILE_ENV)))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
