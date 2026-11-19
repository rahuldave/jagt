"""The records of the agentic targets: a result of a fresh agent becomes a record that the commit gate reads.

Three commands write a record in `records/` of the shared log folder:

- `record_result.py hook` reads the input of a `SubagentStop` hook on stdin. The hooks of Claude Code and of Codex
  run it when a fresh agent stops. The record has `"source": "hook"`. The hook never stops the fresh agent.
- `record_result.py record TARGET FILE` reads the result from FILE, for a harness without that hook. `just record`
  runs it. The record has `"source": "agent"`. Under Claude Code the hook writes the record, so the command stops.
  Under Codex the result must be the last message of a turn of a fresh agent whose parent is the thread that runs
  the command, so an agent cannot write the result itself.
- `record_result.py skip TARGET REASON` lets the worktree tree through without the record of TARGET. `just
  record-skip` runs it, after the agent hooks asked the person. The record has `"source": "skip"`.

A result counts only when `jagt result lint --expect-target TARGET --expect-nonce NONCE` accepts it. The nonce names
the packet file in `packets/`, which gives the target, the input tree and the worktree. The output tree is the
worktree tree of that worktree now, after the changes of the fresh agent.

Usage: record_result.py hook | record TARGET FILE | skip TARGET REASON
"""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from typing import Iterator, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agentic_target  # noqa: E402
from agentic_target import Stop, git, plain_env, prepare_log, shared_log, worktree_diff  # noqa: E402

import yaml  # noqa: E402

NONCE = re.compile(r"^nonce:[ \t]*['\"]?([a-f][0-9a-f]{31})['\"]?[ \t]*$", re.M)
START, END = "<<<AGENT_RESULT v1>>>", "<<<END_AGENT_RESULT>>>"
# The variables of Claude Code, whose SubagentStop hook writes the records.
CLAUDE_VARIABLES = ("CLAUDE_CODE_SESSION_ID", "CLAUDECODE")


def result_block(text: str) -> dict:
    """The mapping of the one AGENT_RESULT v1 block in TEXT."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == START]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise Stop("the text needs exactly one AGENT_RESULT v1 block")
    try:
        block = yaml.safe_load("\n".join(lines[starts[0] + 1:ends[0]]))
    except yaml.YAMLError as error:
        raise Stop(f"the AGENT_RESULT v1 block is not YAML: {error}")
    if not isinstance(block, dict):
        raise Stop("the AGENT_RESULT v1 block is not a mapping")
    return block


def nonce_of(text: str) -> str:
    found = set(NONCE.findall(text))
    if len(found) != 1:
        raise Stop("the result needs exactly one nonce")
    return found.pop()


def is_tree(value: object) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def packet_of(log: Path, nonce: str) -> dict:
    try:
        packet = json.loads((log / "packets" / f"{nonce}.json").read_text())
    except (OSError, ValueError) as error:
        raise Stop(f"no packet file for the nonce {nonce}: {error}")
    if not (isinstance(packet, dict) and packet.get("version") == 1 and packet.get("nonce") == nonce
            and isinstance(packet.get("target"), str) and is_tree(packet.get("input_tree"))
            and isinstance(packet.get("worktree"), str)):
        raise Stop(f"the packet file of the nonce {nonce} is not a packet file of version 1")
    return packet


def lint(text: str, target: str, nonce: str) -> None:
    """Stop unless jagt accepts the result for the target and the nonce."""
    try:
        run = subprocess.run(["jagt", "result", "lint", "--expect-count", "1", "--expect-target", target,
                              "--expect-nonce", nonce, "-"], input=text, capture_output=True, text=True)
    except OSError as error:
        raise Stop(f"cannot run jagt: {error.strerror}")
    if run.returncode != 0:
        raise Stop(f"jagt result lint refused the result: {(run.stderr or run.stdout).strip()}")


def findings_of(block: dict) -> List[dict]:
    """The findings of the result. A result that puts them beside `outputs`, or that gives no list, gives no record,
    since the gate would not see them."""
    if "findings" in block:
        raise Stop("the findings must be in outputs.findings, not beside outputs")
    outputs = block.get("outputs")
    findings = outputs.get("findings") if isinstance(outputs, dict) else None
    if findings is None:
        return []
    if not isinstance(findings, list):
        raise Stop("outputs.findings must be a list")
    return findings


def write_record(root: Path, record: dict, name: str, once: bool = False) -> Path:
    """Write the record as records/NAME.json of the shared log folder. It writes a temporary file and then links or
    renames it, so the gate never reads half a record. The folders are opened as in agentic_target.py, with no link
    followed. With ONCE, a record of that name must not exist yet: one result of a packet gives one record."""
    try:
        # YAML gives values that JSON has not, such as a date. The record keeps them as text.
        text = json.dumps(record, indent=2, default=str) + "\n"
    except (TypeError, ValueError) as error:
        raise Stop(f"the result has a value that a record cannot hold: {error}")
    log, fd = prepare_log(root, "records")
    temp, final = f".{name}.{os.getpid()}.{secrets.token_hex(8)}.tmp", f"{name}.json"
    path = log / "records" / final
    try:
        try:
            out = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
            with os.fdopen(out, "w") as handle:
                handle.write(text)
            if not once:
                os.replace(temp, final, src_dir_fd=fd, dst_dir_fd=fd)
                return path
            try:
                os.link(temp, final, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except OSError as error:
                if error.errno not in (errno.EPERM, errno.ENOTSUP, errno.EXDEV, errno.EOPNOTSUPP):
                    raise
                # A file system with no hard links: write the record in place, as a new file. A half file would
                # block each later try, so a failed write removes it.
                out = os.open(final, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
                try:
                    with os.fdopen(out, "w") as handle:
                        handle.write(text)
                except BaseException:
                    os.unlink(final, dir_fd=fd)
                    raise
        except FileExistsError:
            raise Stop(f"{path} exists already: the result of a packet gives one record")
        except OSError as error:
            raise Stop(f"cannot write {path}: {error.strerror}")
        finally:
            try:
                os.unlink(temp, dir_fd=fd)
            except OSError:
                pass
    finally:
        os.close(fd)
    return path


def same_repository(root: Path, worktree: Path) -> bool:
    def common(path: Path) -> Path:
        return (path / git(["rev-parse", "--git-common-dir"], path, plain_env()).strip()).resolve()
    return common(root) == common(worktree)


def record_from(text: str, root: Path, source: str, model: Optional[str], target: Optional[str] = None) -> Path:
    """Write the record of the result in TEXT. TARGET, when given, must be the target of the packet."""
    nonce = nonce_of(text)
    packet = packet_of(shared_log(root), nonce)
    if target is not None and packet["target"] != target:
        raise Stop(f"the nonce {nonce} belongs to a packet of {packet['target']}, not of {target}")
    lint(text, packet["target"], nonce)
    block = result_block(text)
    worktree = Path(packet["worktree"])
    if not worktree.is_dir():
        raise Stop(f"the worktree of the packet, {worktree}, is gone")
    if not same_repository(root, worktree):
        raise Stop(f"the worktree of the packet, {worktree}, is not a worktree of this repository")
    _, output_tree, _ = worktree_diff(worktree)
    record = {"version": 1, "target": packet["target"], "status": block.get("status"),
              "input_tree": packet["input_tree"], "output_tree": output_tree, "findings": findings_of(block),
              "source": source, "model": model or "unknown", "nonce": nonce}
    return write_record(root, record, nonce, once=True)


def entries(path: Optional[str]) -> Iterator[dict]:
    """The JSON lines of a transcript, last first. It only reads the file."""
    if not path:
        return
    try:
        lines = Path(path).expanduser().read_text(errors="replace").splitlines()
    except OSError:
        return
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            yield entry


def transcript_model(path: Optional[str]) -> Optional[str]:
    """The model of the last answer in a transcript of Claude Code or Codex, or None."""
    for entry in entries(path):
        for holder in (entry.get("message"), entry.get("payload")):
            model = holder.get("model") if isinstance(holder, dict) else None
            if isinstance(model, str) and model and not model.startswith("<"):
                return model
    return None


def handback_message(path: Optional[str]) -> Optional[str]:
    """The message of the last SubagentHandback call in the transcript of a fresh agent of Claude Code, or None. A
    fresh agent that reports through that tool ends with a short closing text, and its result is in the call."""
    for entry in entries(path):
        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for part in reversed(content if isinstance(content, list) else []):
            if isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "SubagentHandback":
                text = part.get("input", {}).get("message") if isinstance(part.get("input"), dict) else None
                if isinstance(text, str):
                    return text
    return None


def hook(stdin: bytes) -> int:
    """The SubagentStop hook. It never blocks the fresh agent: a result that gives no record only prints why."""
    try:
        event = json.loads(stdin.decode(errors="replace"))
        if not isinstance(event, dict):
            return 0
        transcript = event.get("agent_transcript_path")
        transcript = transcript if isinstance(transcript, str) else None
        message = event.get("last_assistant_message")
        if not isinstance(message, str) or START not in message:
            message = handback_message(transcript)
        if not isinstance(message, str) or START not in message:
            return 0
        cwd = event.get("cwd")
        cwd = Path(cwd if isinstance(cwd, str) and cwd else os.getcwd())
        root = Path(git(["rev-parse", "--show-toplevel"], cwd, plain_env()).strip())
        path = record_from(message, root, "hook", transcript_model(transcript))
        print(f"record: wrote {path}", file=sys.stderr)
    except ValueError:
        return 0
    except Stop as stop:
        print(f"record: no record of this result: {stop}", file=sys.stderr)
    except Exception as error:  # The hook never stops the fresh agent, also on a fault of its own.
        print(f"record: no record of this result: {error!r}", file=sys.stderr)
    return 0


def codex_sessions() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "sessions"


def mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def fresh_child(meta: object, thread: str) -> bool:
    """True for the session_meta of a fresh agent that the Codex thread THREAD spawned. A forked agent is not fresh:
    its transcript holds the turns of its parent, so the parent could pass its own answer as the result."""
    if not isinstance(meta, dict) or meta.get("parent_thread_id") != thread or meta.get("forked_from_id"):
        return False
    source = meta.get("source")
    spawn = source.get("subagent", {}).get("thread_spawn") if isinstance(source, dict) else None
    spawn_parent = spawn.get("parent_thread_id") if isinstance(spawn, dict) else None
    return spawn_parent in (None, thread)


def codex_result(thread: str, nonce: str) -> Tuple[str, Optional[str]]:
    """The last message of a turn of a fresh agent of the Codex thread THREAD that holds NONCE, and the model of the
    fresh agent. It reads the JSONL transcripts in the sessions folder of Codex, and no SQLite file."""
    for path in sorted(codex_sessions().glob("**/*.jsonl"), key=mtime, reverse=True):
        try:
            with path.open(errors="replace") as handle:
                first = json.loads(handle.readline() or "null")
        except (OSError, ValueError):
            continue
        meta = first.get("payload") if isinstance(first, dict) and first.get("type") == "session_meta" else None
        if not fresh_child(meta, thread):
            continue
        lines = list(entries(str(path)))
        if sum(1 for entry in lines if entry.get("type") == "session_meta") != 1:
            continue
        for entry in lines:
            payload = entry.get("payload")
            if not (isinstance(payload, dict) and payload.get("type") == "task_complete"):
                continue
            message = payload.get("last_agent_message")
            if isinstance(message, str) and nonce in NONCE.findall(message):
                return message, transcript_model(str(path))
    raise Stop(f"no fresh agent of this Codex thread gave a result with the nonce {nonce}")


def has_record_hook(root: Path) -> bool:
    """True when a setting of Claude Code or of Codex runs the SubagentStop hook of the records: in this checkout, in
    the main checkout, or for the person. A harness reads the settings of the checkout that it runs in, and a branch
    can add the hook before it reaches the main checkout."""
    home = Path.home()
    folders = [root.resolve(), shared_log(root).parent.parent]
    files = [folder / name for folder in folders
             for name in (".claude/settings.json", ".claude/settings.local.json", ".codex/hooks.json",
                          ".codex/config.toml")]
    files += [home / ".claude/settings.json", home / ".codex/hooks.json", home / ".codex/config.toml"]
    if os.environ.get("CODEX_HOME"):
        files += [Path(os.environ["CODEX_HOME"]) / name for name in ("hooks.json", "config.toml")]
    for path in files:
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if path.suffix == ".toml":
            # Python 3.9 has no TOML reader. The name of the hook script is enough in a file that holds settings.
            if "record-result.sh" in text and "SubagentStop" in text:
                return True
            continue
        try:
            settings = json.loads(text)
        except ValueError:
            continue
        hooks = settings.get("hooks") if isinstance(settings, dict) else None
        if isinstance(hooks, dict) and "record-result.sh" in json.dumps(hooks.get("SubagentStop", [])):
            return True
    return False


def record(root: Path, target: str, file: str) -> Path:
    if any(os.environ.get(name) for name in CLAUDE_VARIABLES):
        raise Stop("in Claude Code the SubagentStop hook writes the record; give the packet to a fresh agent instead")
    try:
        text = Path(file).read_text(errors="replace")
    except OSError as error:
        raise Stop(f"cannot read {file}: {error.strerror}")
    thread = os.environ.get("CODEX_THREAD_ID")
    if thread:
        # The result in FILE could come from the agent itself. The record takes the result from the transcript.
        text, model = codex_result(thread, nonce_of(text))
        return record_from(text, root, "agent", model, target)
    # The variables of a harness can be cleared, so they cannot say that no harness runs. A repository with the
    # record hook has a harness that writes the records, and the file of an agent is not proof of a fresh agent.
    if has_record_hook(root):
        raise Stop("this repository writes the records through the SubagentStop hook of Claude Code or Codex; give "
                   "the packet to a fresh agent there. In Codex, run just record in the thread that ran the fresh "
                   "agent")
    return record_from(text, root, "agent", None, target)


def skip(root: Path, target: str, reason: str) -> Path:
    if target not in agentic_target.TARGETS:
        raise Stop(f"{target} is not an agentic target; the targets are " + ", ".join(agentic_target.TARGETS))
    if not reason.strip():
        raise Stop("a skip needs a reason")
    _, tree, _ = worktree_diff(root)
    record = {"version": 1, "target": target, "status": "success", "input_tree": tree, "output_tree": tree,
              "findings": [], "source": "skip", "reason": reason.strip()}
    return write_record(root, record, f"skip-{target}-{tree}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["hook"]:
        return hook(sys.stdin.buffer.read())
    try:
        root = Path(git(["rev-parse", "--show-toplevel"], Path.cwd(), plain_env()).strip())
        if len(argv) == 3 and argv[0] == "record":
            print(f"record: wrote {record(root, argv[1], argv[2])}")
            return 0
        if len(argv) >= 3 and argv[0] == "skip":
            print(f"record: wrote {skip(root, argv[1], ' '.join(argv[2:]))}")
            return 0
    except Stop as stop:
        print(f"record: {stop}", file=sys.stderr)
        return 1
    print("usage: record_result.py hook | record TARGET FILE | skip TARGET REASON", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
