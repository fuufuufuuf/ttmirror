"""Small wrapper around `codex exec --json` for this automation project."""

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Callable, List, Optional


CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_MODEL = os.environ.get("CODEX_MODEL", "")
CODEX_SANDBOX = os.environ.get("CODEX_SANDBOX", "workspace-write")
CODEX_APPROVAL_POLICY = os.environ.get("CODEX_APPROVAL_POLICY", "never")


@dataclass
class CodexRunResult:
    returncode: int
    text: str = ""
    stderr: str = ""
    messages: List[str] = field(default_factory=list)


def build_codex_command(
    *,
    model: Optional[str] = None,
    sandbox: str = CODEX_SANDBOX,
    approval_policy: str = CODEX_APPROVAL_POLICY,
) -> List[str]:
    cmd = [
        CODEX_BIN,
        "exec",
        "--json",
        "--sandbox",
        sandbox,
        "-c",
        f"approval_policy='{approval_policy}'",
    ]
    selected_model = CODEX_MODEL if model is None else model
    if selected_model:
        cmd.extend(["-m", selected_model])
    cmd.append("-")
    return cmd


def _json_events(output: str):
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            # Codex can print startup warnings in the same stream. They are useful
            # for humans but should not break automation parsing.
            continue


def _item_text(item: dict) -> str:
    if item.get("type") == "agent_message":
        return item.get("text", "") or ""
    return ""


def _summarize_item(item: dict) -> str:
    if item.get("status") and item.get("status") != "in_progress":
        return ""
    item_type = item.get("type", "")
    if item_type == "command_execution":
        command = item.get("command") or item.get("cmd") or ""
        if command:
            return f"-> Bash({command})"
    if item_type in ("mcp_tool_call", "tool_call"):
        name = (
            item.get("tool")
            or item.get("tool_name")
            or item.get("name")
            or item.get("recipient")
            or item_type
        )
        server = item.get("server")
        if server and name:
            name = f"{server}.{name}"
        args = item.get("arguments") or item.get("input") or {}
        return f"-> {name}({json.dumps(args, ensure_ascii=False)[:500]})"
    return ""


def run_codex_text(
    prompt: str,
    *,
    cwd: str,
    model: Optional[str] = None,
    sandbox: str = "read-only",
    timeout: int = 60,
) -> CodexRunResult:
    cmd = build_codex_command(model=model, sandbox=sandbox)
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as e:
        return CodexRunResult(
            returncode=124,
            stderr=str(e),
        )

    messages: List[str] = []
    for event in _json_events(proc.stdout):
        item = event.get("item") or {}
        text = _item_text(item)
        if text:
            messages.append(text)

    return CodexRunResult(
        returncode=proc.returncode,
        text="\n".join(messages).strip(),
        stderr=proc.stderr,
        messages=messages,
    )


def stream_codex(
    prompt: str,
    *,
    cwd: str,
    model: Optional[str] = None,
    sandbox: str = CODEX_SANDBOX,
    print_func: Callable[..., None] = print,
    on_text: Optional[Callable[[str], None]] = None,
) -> CodexRunResult:
    cmd = build_codex_command(model=model, sandbox=sandbox)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        bufsize=1,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(prompt)
    proc.stdin.close()

    messages: List[str] = []
    for raw_line in proc.stdout:
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        item = event.get("item") or {}
        text = _item_text(item)
        if text:
            messages.append(text)
            print_func(f"  {text}", flush=True)
            if on_text:
                on_text(text)
            continue

        summary = _summarize_item(item)
        if summary:
            print_func(f"  {summary}", flush=True)

    proc.wait()
    return CodexRunResult(
        returncode=proc.returncode,
        text="\n".join(messages).strip(),
        messages=messages,
    )
