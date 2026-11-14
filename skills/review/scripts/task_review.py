#!/usr/bin/env python3
"""Runtime-agnostic pre-commit task review client for the RDG review protocol.

Every coding runtime (Pi, Claude Code, Codex, Antigravity, omp) shells out to
this module so exactly one implementation owns request validation, state
fingerprinting, launcher invocation, and the approval ledger.

The client fails closed. Any error, malformed launcher output, mismatched
review id, or change to the working tree during the human review yields no
approval and a non-approval exit code. An approval is only ever handed out when
the launcher approved the exact byte state this client re-verified afterwards.

Commands:

    task_review.py review  (--criterion TEXT --repo ROOT [--paths a,b] | --json REQUEST)
    task_review.py verify  (--repo ROOT [--paths a,b] | --json REQUEST)
    task_review.py status  [--repo ROOT]
    task_review.py consume --repo ROOT
    task_review.py revoke  [--repo ROOT]

stdout carries exactly one JSON object per run; human-readable text goes to
stderr so a caller can parse the result without filtering noise.
"""
from __future__ import annotations

import argparse
import codecs
import contextlib
import datetime
import hashlib
import json
import os
import posixpath
import re
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Sequence

PROTOCOL_VERSION = "1"
PRODUCER = "task_review.py"
LEDGER_NAME = "task-review-approval.jsonl"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DECISIONS = ("approve", "request-changes", "return-to-planning", "cancelled")
APPROVING_DECISION = "approve"
REVIEWER_ENV = "TASK_REVIEW_REVIEWER"
LAUNCHER_ENV = "RDG_CONTROL_COMMAND"
HTML_REVIEWER = "html"
RDG_REVIEWER = "rdg"
DEFAULT_REVIEWER = HTML_REVIEWER
TIMEOUT_ENV = "TASK_REVIEW_TIMEOUT"
DEFAULT_TIMEOUT_SECONDS = 1800
MAX_GUIDE_BYTES = 48 * 1024

EXIT_OK = 0
EXIT_NOT_APPROVED = 1
EXIT_ERROR = 2

# Review outcomes mapped onto ledger states. Only an approval is ever positive.
DECISION_STATES = {
    "approve": "approved",
    "request-changes": "rejected",
    "return-to-planning": "rejected",
    "cancelled": "cancelled",
}

GitRunner = Callable[..., bytes]
Launcher = Callable[[str, str, "int | None"], bytes]


class TaskReviewError(Exception):
    """Any condition that must fail the review closed with exit code 2."""


class UsageError(TaskReviewError):
    """Bad command line or unusable environment configuration."""


class GitError(TaskReviewError):
    """A git invocation failed or returned something unusable."""


class LauncherError(TaskReviewError):
    """The reviewer could not be run, or failed."""


class ResultError(TaskReviewError):
    """The launcher result violated the review protocol."""


class DocumentError(TaskReviewError):
    """A document request or document review was unusable."""


# --------------------------------------------------------------------------
# process boundaries (injectable)
# --------------------------------------------------------------------------


def run_git(root: str, args: Sequence[str], *, allowed_codes: Sequence[int] = (0,)) -> bytes:
    """Runs git in ``root`` and returns raw stdout.

    Output is captured so git chatter can never reach this client's stdout, and
    callers get a message instead of a CalledProcessError.
    """
    command = ["git", "-C", root, *args]
    try:
        completed = subprocess.run(command, capture_output=True)
    except OSError as error:
        raise GitError(f"unable to run git in {root}: {error}") from None
    if completed.returncode not in allowed_codes:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {args[0]} failed in {root}: {detail or f'exit code {completed.returncode}'}")
    return completed.stdout


def resolve_launcher_command(launcher: str) -> list[str]:
    """Turns a reviewer name or launcher path into argv.

    A bare name selects a known reviewer; anything else is a path or a command
    line. RDG_CONTROL_COMMAND stays honored for callers that already set it.
    """
    if launcher == HTML_REVIEWER:
        return [sys.executable, str(Path(__file__).resolve().parent / "html_review.py")]
    if launcher == RDG_REVIEWER:
        return ["rdg"]
    if os.path.isfile(launcher):
        return [launcher]
    parts = shlex.split(launcher)
    if not parts:
        raise UsageError(f"{REVIEWER_ENV} is empty")
    return parts


def resolve_reviewer(environ: "os._Environ[str] | dict[str, str]") -> str:
    """Reviewer precedence: TASK_REVIEW_REVIEWER, then RDG_CONTROL_COMMAND, then
    the bundled HTML reviewer."""
    for name in (REVIEWER_ENV, LAUNCHER_ENV):
        value = environ.get(name, "").strip()
        if value:
            return value
    return DEFAULT_REVIEWER


def run_reviewer(
    launcher: str, flag: str, request_json: str, timeout: "int | None", timed_out: str,
    *, recovery: "ReviewRecovery | None" = None,
) -> bytes:
    command = [*resolve_launcher_command(launcher), flag, request_json]
    environment = None
    if recovery is not None:
        environment = {**os.environ, "HTML_REVIEW_URL_FILE": str(recovery.directory / "browser-url.txt")}
    with tempfile.TemporaryFile() as output:
        process = None
        interrupted = False
        diagnostics: list[bytes] = []
        relay_errors: list[Exception] = []

        def interrupt(signum: int, frame: Any) -> None:
            nonlocal interrupted
            if interrupted:
                return
            interrupted = True
            # Defer interruption until Popen returns an owned process handle.
            if process is not None:
                raise KeyboardInterrupt

        def stop() -> None:
            if process is None:
                return
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()

        def relay() -> None:
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            try:
                while chunk := process.stderr.read1(65536):
                    diagnostics.append(chunk)
                    sys.stderr.write(decoder.decode(chunk))
                    sys.stderr.flush()
                sys.stderr.write(decoder.decode(b"", final=True))
                sys.stderr.flush()
            except Exception as error:
                relay_errors.append(error)
                stop()

        reader = threading.Thread(target=relay, name="task-review-stderr")
        previous_handlers: dict[int, Any] = {}
        try:
            if threading.current_thread() is threading.main_thread():
                for signum in (signal.SIGTERM, signal.SIGINT):
                    previous_handlers[signum] = signal.getsignal(signum)
                    signal.signal(signum, interrupt)
            try:
                process = subprocess.Popen(
                    command, stdout=output, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                    env=environment, start_new_session=os.name == "posix",
                )
            except OSError as error:
                raise LauncherError(f"unable to run the reviewer: {error}") from None
            if interrupted:
                raise KeyboardInterrupt
            if recovery is not None:
                recovery.reviewer_started(process.pid, command)
            reader.start()
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise LauncherError(timed_out) from None
        except KeyboardInterrupt:
            raise LauncherError("the review was interrupted; no approval was returned") from None
        finally:
            interrupted = True
            if process is not None:
                stop()
                process.wait()
                if reader.ident is not None:
                    reader.join()
                process.stderr.close()
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
        if relay_errors:
            raise LauncherError(f"unable to forward reviewer diagnostics: {relay_errors[0]}")
        if process.returncode != 0:
            stderr = b"".join(diagnostics).decode("utf-8", "replace")
            raise LauncherError(stderr.strip() or f"the reviewer exited with code {process.returncode}")
        output.seek(0)
        return output.read()


def launch_review(launcher: str, request_json: str, timeout: "int | None") -> bytes:
    return run_reviewer(launcher, "--review", request_json, timeout, "the review timed out before a human decided")


def launch_document(launcher: str, request_json: str, timeout: "int | None") -> bytes:
    """A document review speaks the same contract on a different flag, so a
    reviewer that only speaks diffs fails loudly instead of silently reviewing
    the wrong thing."""
    return run_reviewer(
        launcher, "--review-doc", request_json, timeout, "the document review timed out before a human decided"
    )


def resolve_timeout(environ: "dict[str, str]") -> "int | None":
    raw = environ.get(TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        seconds = int(raw)
    except ValueError:
        raise UsageError(f"{TIMEOUT_ENV} must be a whole number of seconds: {raw!r}") from None
    if seconds < 0:
        raise UsageError(f"{TIMEOUT_ENV} must not be negative: {raw!r}")
    return None if seconds == 0 else seconds


# --------------------------------------------------------------------------
# request model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Repository:
    root: str
    paths: "list[str] | None" = None

    def payload(self) -> dict[str, Any]:
        if self.paths is None:
            return {"root": self.root}
        return {"root": self.root, "paths": list(self.paths)}


@dataclass(frozen=True)
class ReviewRequest:
    """A diff review: one or more repository scopes, judged against a criterion."""

    version: str
    review_id: str
    criterion: str
    repositories: tuple[Repository, ...]
    guide: "dict[str, Any] | None" = None

    def payload(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "review_id": self.review_id,
            "criterion": self.criterion,
            "repositories": [repository.payload() for repository in self.repositories],
        }
        if self.guide is not None:
            payload["guide"] = self.guide
        return payload

    def to_json(self) -> str:
        return json.dumps(self.payload(), separators=(",", ":"))


@dataclass(frozen=True)
class DocumentRequest:
    """A document review: one markdown file, judged against a criterion.

    A specification or a plan is a file, not a diff, so there is no repository
    and no old side. Comments still anchor to real lines, which is what makes an
    approval mean "I read this exact text".
    """

    version: str
    review_id: str
    criterion: str
    path: str
    kind: str = "document"

    def payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "review_id": self.review_id,
            "criterion": self.criterion,
            "path": self.path,
            "kind": self.kind,
        }

    def to_json(self) -> str:
        return json.dumps(self.payload(), separators=(",", ":"))


def normalize_root(value: Any) -> str:
    """Validates a repository root and canonicalises it with realpath.

    RDG matches repositories by canonical path, so a symlinked root such as
    ``/tmp/x`` would be rejected by the launcher; resolving symlinks here keeps
    the request canonical and the error local.
    """
    if not isinstance(value, str) or not value:
        raise ResultError("each repository needs a non-empty root path")
    if not os.path.isabs(value):
        raise ResultError(f"repository root must be absolute: {value!r}")
    if any(part in (".", "..") for part in value.split("/")):
        raise ResultError(f"repository root must not contain '.' or '..': {value!r}")
    return os.path.realpath(value)


def normalize_paths(value: Any) -> "list[str] | None":
    """Validates an optional scope of normalised repository-relative paths."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise ResultError("repository paths must be a list of strings")
    if not value:
        raise ResultError("repository paths must not be empty when present")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ResultError("each repository path must be a non-empty string")
        candidate = item.replace("\\", "/")
        if candidate.startswith("/") or re.match(r"^[A-Za-z]:/", candidate):
            raise ResultError(f"repository path must be relative: {item!r}")
        if any(part in ("", ".", "..") for part in candidate.split("/")):
            raise ResultError(f"repository path must be normalised without '.', '..' or '//': {item!r}")
        if posixpath.normpath(candidate) != candidate:
            raise ResultError(f"repository path must be normalised: {item!r}")
        normalized.append(candidate)
    return normalized


def normalize_repository(value: Any) -> Repository:
    if not isinstance(value, dict):
        raise ResultError("each repository must be an object")
    if "root" not in value:
        raise ResultError("each repository needs a root path")
    unknown = set(value) - {"root", "paths"}
    if unknown:
        raise ResultError(f"unsupported repository keys: {', '.join(sorted(unknown))}")
    return Repository(root=normalize_root(value["root"]), paths=normalize_paths(value.get("paths")))


def normalize_guide(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResultError("guide must be an object")
    if len(json.dumps(value, ensure_ascii=True).encode("utf-8")) > MAX_GUIDE_BYTES:
        raise ResultError("guide exceeds the 48 KiB limit")
    required = {"version", "fingerprint", "summary", "before", "after", "chapters"}
    if not required <= value.keys() or set(value) - required - {"flow"}:
        raise ResultError("guide needs version, fingerprint, summary, before, after and chapters; only flow is optional")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ResultError("unsupported guide version")
    if not isinstance(value["fingerprint"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["fingerprint"]):
        raise ResultError("guide needs a scoped diff fingerprint")

    def text(item: Any, name: str, limit: int = 8000) -> str:
        if not isinstance(item, str) or not item.strip() or len(item) > limit:
            raise ResultError(f"guide {name} must be non-empty text of at most {limit} characters")
        return item

    normalized = {"version": 1, "fingerprint": value["fingerprint"]}
    for key in ("summary", "before", "after"):
        normalized[key] = text(value[key], key)
    if "flow" in value:
        flow = value["flow"]
        if not isinstance(flow, dict) or set(flow) != {"before", "after"}:
            raise ResultError("guide flow needs before and after label lists")
        normalized["flow"] = {}
        for side in ("before", "after"):
            labels = flow[side]
            if not isinstance(labels, list) or not 1 <= len(labels) <= 20:
                raise ResultError("guide flow needs 1–20 labels per side")
            normalized["flow"][side] = [text(label, "flow label", 200) for label in labels]
    chapters = value["chapters"]
    if not isinstance(chapters, list) or len(chapters) > 128:
        raise ResultError("guide chapters must be a list of at most 128 chapters")
    normalized["chapters"] = []
    seen = set()
    for chapter in chapters:
        if not isinstance(chapter, dict) or set(chapter) != {"title", "summary", "files"}:
            raise ResultError("each guide chapter needs title, summary and files")
        files = chapter["files"]
        if not isinstance(files, list) or not files:
            raise ResultError("each guide chapter needs at least one file")
        references = []
        for reference in files:
            if not isinstance(reference, dict) or set(reference) != {"repository", "path"}:
                raise ResultError("guide file references need repository and path")
            root = normalize_root(reference["repository"])
            path = normalize_paths([reference["path"]])[0]
            identity = (root, path)
            if identity in seen:
                raise ResultError(f"duplicate guide file reference: {path}")
            seen.add(identity)
            references.append({"repository": root, "path": path})
        normalized["chapters"].append({
            "title": text(chapter["title"], "chapter title", 200),
            "summary": text(chapter["summary"], "chapter summary"),
            "files": references,
        })
    if len(json.dumps(normalized).encode("utf-8")) > MAX_GUIDE_BYTES:
        raise ResultError("guide exceeds the 48 KiB limit")
    return normalized


def read_guide(path: str) -> dict[str, Any]:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_GUIDE_BYTES + 1)
        if len(raw) > MAX_GUIDE_BYTES:
            raise ResultError("guide exceeds the 48 KiB limit")
        return normalize_guide(json.loads(raw.decode("utf-8")))
    except (OSError, UnicodeError, ValueError) as error:
        raise UsageError(f"unable to read guide: {error}") from None


def validate_guide_snapshot(guide: dict[str, Any], snapshot: "Snapshot") -> None:
    if guide["fingerprint"] != snapshot.fingerprint:
        raise ResultError("guide is stale or has a different scope; regenerate it for the current scoped diff")
    available = {(repo.root, file.path) for repo in snapshot.repositories for file in repo.files}
    for chapter in guide["chapters"]:
        for reference in chapter["files"]:
            if (reference["repository"], reference["path"]) not in available:
                raise ResultError(f"guide references a file outside the captured diff: {reference['path']}")


def normalize_request(payload: Any, *, require_review_fields: bool = True) -> ReviewRequest:
    """Validates a decoded ReviewRequest against the protocol.

    ``require_review_fields`` is relaxed for verify and status, which only need
    the repository scopes, so a stored request can be reused there.
    """
    if not isinstance(payload, dict):
        raise ResultError("the review request must be a JSON object")
    if payload.get("version") != PROTOCOL_VERSION:
        raise ResultError(f"unsupported review protocol version: {payload.get('version')!r}")
    review_id = payload.get("review_id")
    criterion = payload.get("criterion")
    if require_review_fields:
        if not isinstance(review_id, str) or not review_id:
            raise ResultError("the review request needs a non-empty review_id")
        if not isinstance(criterion, str) or not criterion:
            raise ResultError("the review request needs a non-empty criterion")
    else:
        review_id = review_id if isinstance(review_id, str) else ""
        criterion = criterion if isinstance(criterion, str) else ""
    repositories = payload.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ResultError("the review request needs at least one repository")
    normalized = [normalize_repository(item) for item in repositories]
    seen: set[str] = set()
    for repository in normalized:
        if repository.root in seen:
            raise ResultError(f"duplicate repository root: {repository.root}")
        seen.add(repository.root)
    return ReviewRequest(
        version=PROTOCOL_VERSION,
        review_id=review_id,
        criterion=criterion,
        repositories=tuple(normalized),
        guide=normalize_guide(payload["guide"]) if "guide" in payload else None,
    )


def parse_request_json(text: str, *, require_review_fields: bool = True) -> ReviewRequest:
    try:
        payload = json.loads(text)
    except ValueError as error:
        raise ResultError(f"the review request is not valid JSON: {error}") from None
    return normalize_request(payload, require_review_fields=require_review_fields)


def scoped_repositories(roots: Sequence[str], paths: "list[str] | None") -> list[Repository]:
    return [Repository(root=normalize_root(root), paths=paths) for root in roots]


def build_request(criterion: str, repositories: Sequence[Repository]) -> ReviewRequest:
    return normalize_request(
        {
            "version": PROTOCOL_VERSION,
            "review_id": uuid.uuid4().hex,
            "criterion": criterion,
            "repositories": [repository.payload() for repository in repositories],
        }
    )


def check_worktree(root: str, git: GitRunner) -> None:
    """Confirms the root is a Git worktree, using the launcher's own wording."""
    try:
        inside = git(root, ["rev-parse", "--is-inside-work-tree"]).decode("utf-8", "replace").strip()
    except GitError:
        raise ResultError(f"repository is not open or is not a Git worktree: {root}") from None
    if inside != "true":
        raise ResultError(f"repository is not open or is not a Git worktree: {root}")


# --------------------------------------------------------------------------
# snapshot and fingerprint
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StatusEntry:
    kind: str
    path: str
    original_path: "str | None" = None
    mode_head: str = ""
    mode_index: str = ""
    mode_worktree: str = ""


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    old_path: "str | None"
    mode: str
    old_mode: str
    content_hash: str
    patch_hash: str


@dataclass(frozen=True)
class RepositorySnapshot:
    root: str
    baseline: str
    scope_paths: "list[str] | None"
    files: tuple[FileSnapshot, ...]
    fingerprint: str


@dataclass(frozen=True)
class Snapshot:
    repositories: tuple[RepositorySnapshot, ...]
    fingerprint: str


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_fixed_fields(record: str, separators: int) -> "list[str] | None":
    fields: list[str] = []
    start = 0
    for _ in range(separators):
        index = record.find(" ", start)
        if index < 0:
            return None
        fields.append(record[start:index])
        start = index + 1
    fields.append(record[start:])
    return fields


def parse_porcelain_v2(data: bytes) -> list[StatusEntry]:
    """Parses ``git status --porcelain=v2 -z`` records into ordered entries."""
    records = data.split(b"\0")
    entries: list[StatusEntry] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        text = record.decode("utf-8", "surrogateescape")
        if text.startswith("? "):
            entries.append(StatusEntry(kind="untracked", path=text[2:]))
        elif text.startswith("1 "):
            fields = split_fixed_fields(text, 8)
            if not fields or len(fields) != 9:
                raise GitError("invalid porcelain v2 ordinary record")
            entries.append(
                StatusEntry(
                    kind="tracked",
                    path=fields[8],
                    mode_head=fields[3],
                    mode_index=fields[4],
                    mode_worktree=fields[5],
                )
            )
        elif text.startswith("2 "):
            fields = split_fixed_fields(text, 9)
            if not fields or len(fields) != 10 or index >= len(records):
                raise GitError("invalid porcelain v2 rename record")
            original = records[index].decode("utf-8", "surrogateescape")
            index += 1
            entries.append(
                StatusEntry(
                    kind="rename",
                    path=fields[9],
                    original_path=original,
                    mode_head=fields[3],
                    mode_index=fields[4],
                    mode_worktree=fields[5],
                )
            )
        elif text.startswith("u "):
            fields = split_fixed_fields(text, 10)
            if not fields or len(fields) != 11:
                raise GitError("invalid porcelain v2 unmerged record")
            entries.append(
                StatusEntry(
                    kind="tracked",
                    path=fields[10],
                    mode_head=fields[3],
                    mode_index=fields[5],
                    mode_worktree=fields[6],
                )
            )
        # Header lines ("# branch.oid ...") and unknown records carry no state.
    return entries


def matches_scope(path: str, scope_paths: "Sequence[str] | None") -> bool:
    if not scope_paths:
        return True
    return any(path == scope or path.startswith(f"{scope}/") for scope in scope_paths)


def mode_for_path(path: str) -> str:
    try:
        info = os.lstat(path)
    except OSError:
        return ""
    if stat.S_ISLNK(info.st_mode):
        return "120000"
    if stat.S_ISDIR(info.st_mode):
        return "040000"
    return "100755" if info.st_mode & 0o111 else "100644"


def hash_working_path(path: str) -> str:
    """Hashes a working-tree path, tagging the kind so they cannot collide."""
    try:
        info = os.lstat(path)
    except OSError:
        return ""
    digest = hashlib.sha256()
    if stat.S_ISLNK(info.st_mode):
        digest.update(b"symlink\0")
        digest.update(os.readlink(path).encode("utf-8", "surrogateescape"))
    elif stat.S_ISREG(info.st_mode):
        digest.update(b"file\0")
        try:
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError:
            return ""
    elif stat.S_ISDIR(info.st_mode):
        digest.update(b"directory\0")
        digest.update(mode_for_path(path).encode())
    else:
        digest.update(b"other\0")
        digest.update(mode_for_path(path).encode())
    return digest.hexdigest()


def entry_modes(entry: StatusEntry, absolute_path: str) -> "tuple[str, str]":
    if entry.kind == "untracked":
        return mode_for_path(absolute_path), ""
    mode = entry.mode_worktree
    if not mode or mode == "000000":
        mode = entry.mode_index if entry.mode_index and entry.mode_index != "000000" else entry.mode_head
    old_mode = entry.mode_head if entry.mode_head and entry.mode_head != "000000" else ""
    return mode, old_mode


def git_blob_hash(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - git object format, not a security hash


def decode_text(data: bytes) -> "str | None":
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None

def split_patch_lines(text: str) -> "list[str]":
    """Splits patch or file text into lines the way git does: on newlines only.

    ``str.splitlines`` also breaks on form feed, vertical tab, U+2028 and the
    other Unicode line boundaries, which git copies into a patch as ordinary
    file content. One such character would split a line in two and shift every
    line number after it, so a comment would anchor to the wrong line.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def synthesize_added_patch(path: str, mode: str, data: bytes) -> bytes:
    """Builds the all-added patch an untracked file would produce.

    The index line carries the git blob hash, so binary content still changes
    the patch when the bytes change.
    """
    lines = [
        f"diff --git a/{path} b/{path}",
        f"new file mode {mode or '100644'}",
        f"index {'0' * 40}..{git_blob_hash(data)}",
        "--- /dev/null",
        f"+++ b/{path}",
    ]
    text = decode_text(data)
    if text is None:
        lines.append(f"Binary files /dev/null and b/{path} differ")
    else:
        body = split_patch_lines(text)
        lines.append(f"@@ -0,0 +1,{len(body)} @@")
        lines.extend(f"+{line}" for line in body)
    return ("\n".join(lines) + "\n").encode("utf-8")


def entry_patch(root: str, baseline: str, entry: StatusEntry, git: GitRunner) -> bytes:
    if entry.kind == "untracked":
        absolute = os.path.join(root, *entry.path.split("/"))
        try:
            with open(absolute, "rb") as handle:
                data = handle.read()
        except OSError:
            data = b""
        return synthesize_added_patch(entry.path, mode_for_path(absolute), data)
    return git(root, ["diff", "--no-ext-diff", "--no-textconv", "--find-renames", baseline, "--", entry.path])


def resolve_baseline(root: str, git: GitRunner) -> str:
    output = git(root, ["rev-parse", "--verify", "HEAD"], allowed_codes=(0, 1, 128)).decode("ascii", "replace")
    candidate = output.strip()
    if re.fullmatch(r"[0-9a-f]{40,64}", candidate):
        return candidate
    return EMPTY_TREE


def fingerprint_repository(
    root: str,
    baseline: str,
    scope_paths: "Sequence[str] | None",
    files: Sequence[FileSnapshot],
) -> str:
    digest = hashlib.sha256()
    digest.update(root.encode("utf-8"))
    digest.update(b"\0")
    digest.update(baseline.encode("ascii"))
    digest.update(b"\0")
    digest.update(("\0".join(scope_paths) if scope_paths else "*").encode("utf-8"))
    for file in files:
        for value in (
            file.path,
            file.old_path or "",
            file.mode or "",
            file.old_mode or "",
            file.content_hash or "",
            file.patch_hash,
        ):
            digest.update(b"\0")
            digest.update(value.encode("utf-8", "surrogateescape"))
    return digest.hexdigest()


def collect_repository(repository: Repository, git: GitRunner = run_git) -> RepositorySnapshot:
    root = repository.root
    baseline = resolve_baseline(root, git)
    entries = parse_porcelain_v2(git(root, ["status", "--porcelain=v2", "-z", "--untracked-files=all"]))
    selected = [entry for entry in entries if matches_scope(entry.path, repository.paths)]
    files: list[FileSnapshot] = []
    for entry in sorted(selected, key=lambda item: item.path):
        absolute = os.path.join(root, *entry.path.split("/"))
        patch = entry_patch(root, baseline, entry, git)
        mode, old_mode = entry_modes(entry, absolute)
        files.append(
            FileSnapshot(
                path=entry.path,
                old_path=entry.original_path,
                mode=mode,
                old_mode=old_mode,
                content_hash=hash_working_path(absolute),
                patch_hash=sha256_hex(patch),
            )
        )
    fingerprint = fingerprint_repository(root, baseline, repository.paths, files)
    return RepositorySnapshot(
        root=root,
        baseline=baseline,
        scope_paths=list(repository.paths) if repository.paths else None,
        files=tuple(files),
        fingerprint=fingerprint,
    )


def collect_snapshot(repositories: Sequence[Repository], git: GitRunner = run_git) -> Snapshot:
    snapshots = [collect_repository(repository, git) for repository in repositories]
    composite = sha256_hex(
        "\0".join(f"{snapshot.root}\0{snapshot.fingerprint}" for snapshot in snapshots).encode("utf-8")
    )
    return Snapshot(repositories=tuple(snapshots), fingerprint=composite)


# --------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------


def resolve_common_git_dir(root: str, git: GitRunner) -> str:
    output = git(root, ["rev-parse", "--path-format=absolute", "--git-common-dir"]).decode("utf-8", "replace")
    directory = output.strip()
    if not directory:
        raise GitError(f"unable to resolve the git directory for {root}")
    return directory


def ledger_path(root: str, git: GitRunner = run_git) -> str:
    return os.path.join(resolve_common_git_dir(root, git), LEDGER_NAME)


def is_git_worktree(directory: str, git: GitRunner) -> bool:
    try:
        inside = git(directory, ["rev-parse", "--is-inside-work-tree"]).decode("utf-8", "replace").strip()
    except GitError:
        return False
    return inside == "true"


def document_ledger_path(path: str, git: GitRunner = run_git) -> str:
    """The ledger for a document lives beside the repository that contains it.

    A specification or plan is usually uncommitted, so there is nothing in the
    index to key on; the containing repository's git dir is the stable anchor,
    and a document outside any repository keeps its own ledger next to it.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    if not is_git_worktree(directory, git):
        return os.path.join(directory, LEDGER_NAME)
    return ledger_path(directory, git)


def document_fingerprint(path: str, criterion: str) -> str:
    """Binds an approval to the exact bytes of the document that was read.

    The same property the diff gate has: edit one character of the plan after
    approving it, and the approval no longer counts.
    """
    try:
        with open(path, "rb") as handle:
            body = handle.read()
    except OSError as error:
        raise DocumentError(f"the document could not be read: {error}") from None
    digest = hashlib.sha256()
    digest.update(b"document\0")
    digest.update(os.path.abspath(path).encode("utf-8"))
    digest.update(b"\0")
    digest.update(hashlib.sha256(body).hexdigest().encode("ascii"))
    digest.update(b"\0")
    digest.update(criterion.encode("utf-8"))
    return digest.hexdigest()


def utc_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_entry(
    state: str,
    decision: str,
    fingerprint: str,
    criterion: str,
    repositories: Sequence[Repository],
    annotations: Sequence[Any] = (),
    error: "str | None" = None,
    document: "str | None" = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ts": utc_timestamp(),
        "producer": PRODUCER,
        "state": state,
        "decision": decision,
        "fingerprint": fingerprint,
        "criterion": criterion,
        "repositories": [repository.payload() for repository in repositories],
        "annotations": list(annotations),
    }
    if document is not None:
        # A document review names the file it judged instead of a repository
        # scope, so a reader of the ledger can tell the two apart at a glance.
        entry["document"] = document
    if error is not None:
        entry["error"] = error
    return entry


def make_document_entry(
    state: str,
    decision: str,
    fingerprint: str,
    criterion: str,
    path: str,
    annotations: Sequence[Any] = (),
    error: "str | None" = None,
) -> dict[str, Any]:
    entry = make_entry(state, decision, fingerprint, criterion, (), annotations=annotations, error=error)
    entry["document"] = path
    return entry


def append_entry(path: str, entry: dict[str, Any]) -> None:
    payload = (json.dumps(entry, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(descriptor, payload)
        finally:
            os.close(descriptor)
        os.chmod(path, 0o600)
    except OSError as error:
        raise TaskReviewError(f"unable to append to the approval ledger {path}: {error}") from None


def append_ledger(paths: Sequence[str], entry: dict[str, Any]) -> None:
    for path in paths:
        append_entry(path, entry)


def read_entries(path: str) -> list[dict[str, Any]]:
    """Returns every well-formed ledger line; a malformed line is skipped."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except FileNotFoundError:
        return []
    except OSError as error:
        raise TaskReviewError(f"unable to read the approval ledger {path}: {error}") from None
    entries: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except ValueError:
            continue
        if isinstance(value, dict):
            entries.append(value)
    return entries


def newest_entry(path: str) -> "dict[str, Any] | None":
    entries = read_entries(path)
    return entries[-1] if entries else None


def approval_state(entry: "dict[str, Any] | None", fingerprint: str) -> "tuple[bool, str]":
    """Decides whether a ledger entry approves exactly this state.

    The producer check runs first: another runtime's approval bookkeeping must
    never validate this client's decision.
    """
    if entry is None:
        return False, "no task review approval is recorded"
    if entry.get("producer") != PRODUCER:
        return False, f"the newest ledger entry was not written by {PRODUCER}"
    state = entry.get("state")
    if state != "approved":
        return False, f"the newest ledger entry is {state!r}"
    if entry.get("decision") != APPROVING_DECISION:
        return False, f"the newest ledger entry decided {entry.get('decision')!r}"
    if entry.get("fingerprint") != fingerprint:
        return False, "the working tree changed since the approval was recorded"
    return True, "the approval matches the current state"


# --------------------------------------------------------------------------
# result validation
# --------------------------------------------------------------------------


def is_positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1



def is_document_annotation(value: Any, path: str) -> bool:
    """A document comment: review-scoped, or anchored to real lines of the file.

    Same fail-closed spirit as a diff annotation, minus the git-specific fields:
    a document has no repository and no old side, and a comment may only name
    the file that was actually reviewed.
    """
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("text"), str):
        return False
    target = value.get("target")
    if not isinstance(target, dict):
        return False
    if target.get("scope") == "review":
        return True
    if target.get("scope") != "line":
        return False
    if target.get("repository") is not None or target.get("side") is not None:
        return False
    return (
        target.get("path") == path
        and is_positive_integer(target.get("start_line"))
        and is_positive_integer(target.get("end_line"))
        and target["end_line"] >= target["start_line"]
    )


def is_annotation(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("text"), str):
        return False
    target = value.get("target")
    if not isinstance(target, dict):
        return False
    if target.get("scope") == "review":
        return True
    if target.get("scope") != "line":
        return False
    return (
        isinstance(target.get("repository"), str)
        and isinstance(target.get("path"), str)
        and target.get("side") in ("old", "new")
        and is_positive_integer(target.get("start_line"))
        and is_positive_integer(target.get("end_line"))
        and target["end_line"] >= target["start_line"]
    )


def parse_review_result(
    stdout: bytes,
    review_id: str,
    validate: "Callable[[Any], bool] | None" = None,
) -> dict[str, Any]:
    """Validates the single JSON document the launcher prints.

    Any deviation fails closed: a result the client cannot fully understand is
    never treated as an approval. ``validate`` is the annotation rule for the
    kind of thing being reviewed -- a diff needs a repository and a side, a
    document needs neither.
    """
    check = validate or is_annotation
    try:
        text = stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise ResultError("the reviewer returned a non-UTF-8 result") from None
    try:
        payload = json.loads(text)
    except ValueError:
        raise ResultError("the reviewer returned a non-JSON result") from None
    if not isinstance(payload, dict):
        raise ResultError("the reviewer returned an invalid result")
    if payload.get("version") != PROTOCOL_VERSION:
        raise ResultError(f"the reviewer returned an unsupported protocol version: {payload.get('version')!r}")
    if payload.get("review_id") != review_id:
        raise ResultError("the reviewer returned a mismatched review id")
    decision = payload.get("decision")
    if decision not in DECISIONS:
        raise ResultError(f"the reviewer returned an unknown decision: {decision!r}")
    annotations = payload.get("annotations")
    if not isinstance(annotations, list) or not all(check(item) for item in annotations):
        raise ResultError("the reviewer returned malformed annotations")
    return {
        "version": PROTOCOL_VERSION,
        "review_id": review_id,
        "decision": decision,
        "annotations": annotations,
    }


def validate_decision_semantics(result: dict[str, Any]) -> None:
    annotations = result["annotations"]
    if result["decision"] == "request-changes" and not any(
        isinstance(item.get("text"), str) and item["text"].strip() for item in annotations
    ):
        raise ResultError("the reviewer requested changes without feedback")
    if result["decision"] == "cancelled" and annotations:
        raise ResultError("the reviewer returned annotations for a cancelled review")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stdout.flush()


def carried(entry: "dict[str, Any] | None", key: str, default: Any) -> Any:
    if entry is None:
        return default
    value = entry.get(key)
    return default if value in (None, "") else value


def ledger_paths(repositories: Sequence[Repository], git: GitRunner) -> list[str]:
    paths = []
    for repository in repositories:
        check_worktree(repository.root, git)
        paths.append(ledger_path(repository.root, git))
    return paths


class ReviewRecovery:
    def __init__(self, directory: str, request: "ReviewRequest | DocumentRequest"):
        self.directory = Path(directory).resolve()
        roots = [repository.root for repository in request.repositories] if isinstance(request, ReviewRequest) else [str(Path(request.path).parent)]
        if any(self.directory.is_relative_to(root) for root in roots):
            raise UsageError("the recovery directory must be outside the reviewed inputs")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if stat.S_IMODE(self.directory.stat().st_mode) & 0o077:
            raise UsageError("the recovery directory must be private (mode 0700)")
        if any(self.directory.iterdir()):
            raise UsageError("the recovery directory is not empty; recover the existing run before relaunching")
        self.request = request
        self.process = {
            "client_pid": os.getpid(), "parent_pid": os.getppid(),
            "review_id": request.review_id, "started_at": utc_timestamp(),
        }
        self.write_json("process.json", self.process, exclusive=True)
        self.write_json("request.json", request.payload())
        self.state("starting")

    def write_json(self, name: str, payload: dict[str, Any], *, exclusive: bool = False) -> None:
        destination = self.directory / name
        temporary = destination if exclusive else self.directory / f".{name}.{uuid.uuid4().hex}"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True)
                stream.write("\n")
            if not exclusive:
                os.replace(temporary, destination)
        finally:
            if not exclusive:
                temporary.unlink(missing_ok=True)

    def state(self, state: str, **fields: Any) -> None:
        self.write_json("state.json", {
            "review_id": self.request.review_id, "state": state,
            "updated_at": utc_timestamp(), **fields,
        })

    def reviewer_started(self, pid: int, command: list[str]) -> None:
        self.process.update(reviewer_pid=pid, reviewer_argv=command)
        self.write_json("process.json", self.process)

    def wrap_launch(self, launch: Launcher, flag: str) -> Launcher:
        if launch not in (launch_review, launch_document):
            return launch

        def invoke(launcher: str, request_json: str, timeout: "int | None") -> bytes:
            message = "the document review timed out before a human decided" if flag == "--review-doc" else "the review timed out before a human decided"
            return run_reviewer(launcher, flag, request_json, timeout, message, recovery=self)

        return invoke

    def finish(self, result: dict[str, Any], exit_code: int) -> None:
        self.write_json("result.json", result)
        self.state("finished", decision=result["decision"], exit_code=exit_code)

    def __enter__(self) -> "ReviewRecovery":
        descriptor = os.open(self.directory / "stderr.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.log = os.fdopen(descriptor, "w", encoding="utf-8")
        self.stderr = sys.stderr
        self.redirect = contextlib.redirect_stderr(self)
        self.redirect.__enter__()
        return self

    def write(self, text: str) -> int:
        self.log.write(text)
        return self.stderr.write(text)

    def flush(self) -> None:
        self.log.flush()
        self.stderr.flush()

    def __exit__(self, kind: Any, error: Any, traceback: Any) -> None:
        try:
            if error is not None:
                self.write(f"task_review: {error or 'review interrupted'}\n")
                self.state("error", exit_code=EXIT_ERROR, error=str(error) or "review interrupted")
        finally:
            self.redirect.__exit__(kind, error, traceback)
            self.log.close()


def review_snapshot(request: ReviewRequest, launcher: str, git: GitRunner) -> Snapshot:
    snapshot = collect_snapshot(request.repositories, git)
    if request.guide is not None:
        if launcher != HTML_REVIEWER:
            raise UsageError("guided reviews require TASK_REVIEW_REVIEWER=html")
        validate_guide_snapshot(request.guide, snapshot)
    return snapshot


def command_review(
    request: ReviewRequest,
    *,
    git: GitRunner,
    launch: Launcher,
    launcher: str,
    timeout: "int | None",
    recovery: "ReviewRecovery | None" = None,
) -> int:
    paths = ledger_paths(request.repositories, git)
    # Revoke any prior approval first: nothing counts as approved from here on
    # until this review completes and the reviewed state is re-verified.
    previous = newest_entry(paths[0])
    append_ledger(
        paths,
        make_entry(
            "superseded",
            carried(previous, "decision", "superseded"),
            carried(previous, "fingerprint", ""),
            request.criterion,
            request.repositories,
        ),
    )
    try:
        snapshot = review_snapshot(request, launcher, git)
        if recovery is not None:
            recovery.state("reviewing", fingerprint=snapshot.fingerprint)
        stdout = launch(launcher, request.to_json(), timeout)
        result = parse_review_result(stdout, request.review_id)
        validate_decision_semantics(result)
        if result["decision"] == APPROVING_DECISION:
            recaptured = collect_snapshot(request.repositories, git)
            if recaptured.fingerprint != snapshot.fingerprint:
                raise ResultError(
                    "the reviewed repository state changed while the human was deciding; "
                    "run the review again for the current state"
                )
        append_ledger(
            paths,
            make_entry(
                DECISION_STATES[result["decision"]],
                result["decision"],
                snapshot.fingerprint,
                request.criterion,
                request.repositories,
                annotations=result["annotations"],
            ),
        )
        code = EXIT_OK if result["decision"] == APPROVING_DECISION else EXIT_NOT_APPROVED
        if recovery is not None:
            recovery.finish(result, code)
        emit(result)
        return code
    except (TaskReviewError, OSError, KeyboardInterrupt) as error:
        append_ledger(
            paths,
            make_entry("error", "error", "", request.criterion, request.repositories, error=str(error)),
        )
        raise


def command_verify(repositories: Sequence[Repository], *, git: GitRunner) -> int:
    paths = ledger_paths(repositories, git)
    snapshot = collect_snapshot(repositories, git)
    entry: "dict[str, Any] | None" = None
    for path in paths:
        entry = newest_entry(path)
        approved, reason = approval_state(entry, snapshot.fingerprint)
        if not approved:
            emit(
                {
                    "approved": False,
                    "fingerprint": snapshot.fingerprint,
                    "state": (entry or {}).get("state"),
                    "reason": reason,
                }
            )
            return EXIT_NOT_APPROVED
    emit(
        {
            "approved": True,
            "fingerprint": snapshot.fingerprint,
            "state": (entry or {}).get("state"),
            "reason": "the approval matches the current state",
        }
    )
    return EXIT_OK


def command_status(repositories: Sequence[Repository], *, git: GitRunner) -> int:
    paths = ledger_paths(repositories, git)
    snapshot = collect_snapshot(repositories, git)
    reports = []
    approved = True
    first: "dict[str, Any] | None" = None
    for repository, path in zip(repositories, paths):
        entry = newest_entry(path)
        matches, entry_reason = approval_state(entry, snapshot.fingerprint)
        approved = approved and matches
        reports.append(
            {
                "root": repository.root,
                "ledger": path,
                "entry": entry,
                "state": (entry or {}).get("state"),
                "matches": matches,
                "reason": entry_reason,
            }
        )
        if first is None:
            first = entry
    reason = "the approval matches the current state"
    if not approved:
        reason = next(report["reason"] for report in reports if not report["matches"])
    emit(
        {
            "approved": approved,
            "fingerprint": snapshot.fingerprint,
            "recordedFingerprint": (first or {}).get("fingerprint"),
            "state": (first or {}).get("state"),
            "reason": reason,
            "entry": first,
            "repositories": reports,
        }
    )
    return EXIT_OK if approved else EXIT_NOT_APPROVED


def normalize_document(value: Any) -> str:
    """A document is a real file on this machine, not a scope in a repository."""
    if not isinstance(value, str) or not value.strip():
        raise DocumentError("a document review needs a document path")
    path = os.path.abspath(os.path.expanduser(value))
    if not os.path.isfile(path):
        raise DocumentError(f"the document does not exist: {value}")
    return path


def build_document_request(criterion: str, path: str) -> DocumentRequest:
    if not isinstance(criterion, str) or not criterion.strip():
        raise UsageError("a document review needs --criterion TEXT")
    return DocumentRequest(
        version=PROTOCOL_VERSION,
        review_id=uuid.uuid4().hex,
        criterion=criterion,
        path=path,
    )


def validate_document_annotations(result: dict[str, Any], path: str) -> None:
    for annotation in result["annotations"]:
        if not is_document_annotation(annotation, path):
            raise ResultError("a document comment named a line the document does not have")


def command_review_doc(
    request: DocumentRequest,
    *,
    git: GitRunner,
    launch: Launcher,
    launcher: str,
    timeout: "int | None",
    recovery: "ReviewRecovery | None" = None,
) -> int:
    """Reviews a specification or a plan with the same fail-closed guarantees as
    a diff review: the approval binds to the exact bytes that were read, and
    anything short of a clean approve leaves no approval behind."""
    ledger = document_ledger_path(request.path, git)
    previous = newest_entry(ledger)
    append_ledger(
        [ledger],
        make_document_entry(
            "superseded",
            carried(previous, "decision", "superseded"),
            carried(previous, "fingerprint", ""),
            request.criterion,
            request.path,
        ),
    )
    try:
        before = document_fingerprint(request.path, request.criterion)
        if recovery is not None:
            recovery.state("reviewing", fingerprint=before)
        stdout = launch(launcher, request.to_json(), timeout)
        result = parse_review_result(
            stdout,
            request.review_id,
            validate=lambda item: is_document_annotation(item, request.path),
        )
        validate_document_annotations(result, request.path)
        validate_decision_semantics(result)
        if result["decision"] == APPROVING_DECISION and document_fingerprint(
            request.path, request.criterion
        ) != before:
            raise ResultError(
                "the document changed while the human was deciding; "
                "run the review again for the current text"
            )
        append_ledger(
            [ledger],
            make_document_entry(
                DECISION_STATES[result["decision"]],
                result["decision"],
                before,
                request.criterion,
                request.path,
                annotations=result["annotations"],
            ),
        )
        code = EXIT_OK if result["decision"] == APPROVING_DECISION else EXIT_NOT_APPROVED
        if recovery is not None:
            recovery.finish(result, code)
        emit(result)
        return code
    except (TaskReviewError, OSError, KeyboardInterrupt) as error:
        append_ledger(
            [ledger],
            make_document_entry("error", "error", "", request.criterion, request.path, error=str(error)),
        )
        raise


def command_verify_doc(request: DocumentRequest, *, git: GitRunner) -> int:
    fingerprint = document_fingerprint(request.path, request.criterion)
    entry = newest_entry(document_ledger_path(request.path, git))
    approved, reason = approval_state(entry, fingerprint)
    emit(
        {
            "approved": approved,
            "fingerprint": fingerprint,
            "recordedFingerprint": (entry or {}).get("fingerprint"),
            "state": (entry or {}).get("state"),
            "document": request.path,
            "reason": reason,
        }
    )
    return EXIT_OK if approved else EXIT_NOT_APPROVED


def command_close_doc(request: DocumentRequest, state: str, *, git: GitRunner) -> int:
    """Retires a document approval once the next phase has used it."""
    ledger = document_ledger_path(request.path, git)
    entry = newest_entry(ledger)
    append_ledger(
        [ledger],
        make_document_entry(
            state,
            carried(entry, "decision", APPROVING_DECISION),
            document_fingerprint(request.path, request.criterion),
            request.criterion,
            request.path,
        ),
    )
    return EXIT_OK


def command_close(state: str, repositories: Sequence[Repository], *, git: GitRunner) -> int:
    """Records a terminal non-approval state (``consumed`` or ``superseded``)."""
    paths = ledger_paths(repositories, git)
    snapshot = collect_snapshot(repositories, git)
    previous = newest_entry(paths[0])
    append_ledger(
        paths,
        make_entry(
            state,
            carried(previous, "decision", state),
            carried(previous, "fingerprint", snapshot.fingerprint),
            carried(previous, "criterion", ""),
            repositories,
            annotations=carried(previous, "annotations", []),
        ),
    )
    emit(
        {
            "approved": False,
            "fingerprint": snapshot.fingerprint,
            "state": state,
            "reason": f"recorded {state} in the approval ledger",
        }
    )
    return EXIT_OK


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------


def add_repository_arguments(parser: argparse.ArgumentParser, *, paths: bool, required: bool) -> None:
    parser.add_argument("--repo", action="append", default=[], metavar="ROOT", required=required,
                        help="absolute path to a repository worktree root (repeatable)")
    if paths:
        parser.add_argument("--paths", default=None, metavar="A,B",
                            help="comma-separated repository-relative scope (single --repo only)")
    parser.add_argument("--json", default=None, metavar="REQUEST",
                        help="a complete ReviewRequest JSON document")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task_review.py",
        description="Run a pre-commit review through the configured reviewer and record a verifiable approval.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("review", "open a review and wait for a human decision"),
        ("preflight", "validate scope and guide without opening a review or changing approval"),
    ):
        review = commands.add_parser(name, help=help_text)
        review.add_argument("--criterion", required=False, metavar="TEXT")
        review.add_argument("--guide", metavar="PATH", help="local authored guide JSON for the HTML Guided tab")
        if name == "review":
            review.add_argument("--recovery-dir", metavar="PATH", help="new private directory outside reviewed inputs for client-owned recovery")
        add_repository_arguments(review, paths=True, required=False)

    verify = commands.add_parser("verify", help="approve only when a matching approval is recorded")
    add_repository_arguments(verify, paths=True, required=False)

    status = commands.add_parser("status", help="print the newest ledger entry and the fingerprint match")
    add_repository_arguments(status, paths=True, required=False)

    consume = commands.add_parser("consume", help="record that an approval was spent by a commit")
    add_repository_arguments(consume, paths=False, required=True)

    revoke = commands.add_parser("revoke", help="record that an approval no longer counts")
    add_repository_arguments(revoke, paths=False, required=False)

    review_doc = commands.add_parser(
        "review-doc", help="review a specification or plan in the browser and wait for a human decision"
    )
    review_doc.add_argument("--criterion", required=True, metavar="TEXT")
    review_doc.add_argument("--doc", required=True, metavar="PATH")
    review_doc.add_argument("--recovery-dir", metavar="PATH", help="new private directory outside reviewed inputs for client-owned recovery")

    verify_doc = commands.add_parser(
        "verify-doc", help="approve only when the exact document text was approved"
    )
    verify_doc.add_argument("--criterion", required=False, metavar="TEXT")
    verify_doc.add_argument("--doc", required=True, metavar="PATH")

    consume_doc = commands.add_parser(
        "consume-doc", help="record that a document approval was spent by the next phase"
    )
    consume_doc.add_argument("--criterion", required=False, metavar="TEXT")
    consume_doc.add_argument("--doc", required=True, metavar="PATH")
    return parser


def default_root() -> str:
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, cwd=os.getcwd())
    except OSError as error:
        raise TaskReviewError(f"unable to run git: {error}") from None
    if top.returncode != 0:
        raise UsageError("not inside a Git worktree: pass --repo ROOT")
    return top.stdout.decode("utf-8", "replace").strip()


def repositories_from_options(args: argparse.Namespace) -> list[Repository]:
    roots = list(args.repo) or [default_root()]
    raw_paths = getattr(args, "paths", None)
    if len(roots) > 1 and raw_paths is not None:
        raise UsageError("--paths is only allowed with exactly one --repo")
    paths = normalize_paths(raw_paths.split(",")) if raw_paths else None
    return scoped_repositories(roots, paths)


def require_no_json_with_flags(args: argparse.Namespace, *names: str) -> None:
    used = [name for name in names if getattr(args, name, None)]
    if args.json is not None and used:
        raise UsageError(f"--json cannot be combined with {' or '.join('--' + name for name in used)}")


def dispatch(
    args: argparse.Namespace,
    environ: "dict[str, str]",
    *,
    git: GitRunner,
    launch: Launcher,
    launch_doc: "Launcher | None" = None,
) -> int:
    if args.command in ("review-doc", "verify-doc", "consume-doc"):
        return dispatch_document(args, environ, git=git, launch=launch_doc or launch_document)
    if args.command in ("review", "preflight"):
        require_no_json_with_flags(args, "criterion", "repo", "paths", "guide")
        if args.json is not None:
            request = parse_request_json(args.json)
        else:
            if not args.criterion:
                raise UsageError("review needs --criterion TEXT or --json REQUEST")
            if not args.repo:
                raise UsageError("review needs --repo ROOT")
            request = build_request(args.criterion, repositories_from_options(args))
            if args.guide is not None:
                request = replace(request, guide=read_guide(args.guide))
        launcher = resolve_reviewer(environ)
        if args.command == "preflight":
            snapshot = review_snapshot(request, launcher, git)
            emit({"valid": True, "fingerprint": snapshot.fingerprint,
                  "repositories": [repository.payload() for repository in request.repositories]})
            return EXIT_OK
        recovery = ReviewRecovery(args.recovery_dir, request) if args.recovery_dir else None
        with recovery if recovery is not None else contextlib.nullcontext():
            return command_review(
                request, git=git,
                launch=recovery.wrap_launch(launch, "--review") if recovery is not None else launch,
                launcher=launcher, timeout=resolve_timeout(environ), recovery=recovery,
            )
    if args.json is not None:
        require_no_json_with_flags(args, "repo", "paths")
        repositories = list(parse_request_json(args.json, require_review_fields=False).repositories)
    else:
        repositories = repositories_from_options(args)
    if args.command == "verify":
        return command_verify(repositories, git=git)
    if args.command == "status":
        return command_status(repositories, git=git)
    if args.command == "consume":
        return command_close("consumed", repositories, git=git)
    return command_close("superseded", repositories, git=git)


def dispatch_document(
    args: argparse.Namespace,
    environ: "dict[str, str]",
    *,
    git: GitRunner,
    launch: Launcher,
) -> int:
    """A document review is a file and a criterion, never a repository scope."""
    path = normalize_document(args.doc)
    criterion = args.criterion
    if args.command == "review-doc":
        request = build_document_request(criterion, path)
        recovery = ReviewRecovery(args.recovery_dir, request) if args.recovery_dir else None
        with recovery if recovery is not None else contextlib.nullcontext():
            return command_review_doc(
                request, git=git,
                launch=recovery.wrap_launch(launch, "--review-doc") if recovery is not None else launch,
                launcher=resolve_reviewer(environ), timeout=resolve_timeout(environ), recovery=recovery,
            )
    # verify and consume need the same criterion the approval was recorded with,
    # because the criterion is part of the fingerprint. Take it from the ledger
    # when the caller did not repeat it.
    recorded = newest_entry(document_ledger_path(path, git))
    if not criterion:
        criterion = (recorded or {}).get("criterion", "")
    request = build_document_request(criterion or "document", path)
    if args.command == "verify-doc":
        return command_verify_doc(request, git=git)
    return command_close_doc(request, "consumed", git=git)


def main(
    argv: "Sequence[str] | None" = None,
    environ: "dict[str, str] | None" = None,
    *,
    git: GitRunner = run_git,
    launch: Launcher = launch_review,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        return dispatch(args, dict(os.environ) if environ is None else environ, git=git, launch=launch)
    except TaskReviewError as error:
        sys.stderr.write(f"task_review: {error}\n")
        return EXIT_ERROR
    except OSError as error:
        sys.stderr.write(f"task_review: {error}\n")
        return EXIT_ERROR
    except KeyboardInterrupt:
        sys.stderr.write("task_review: the review was interrupted; no approval was returned\n")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
