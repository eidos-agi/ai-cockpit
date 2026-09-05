"""Harness launch router — Claude, Grok, Codex, Cursor, Eidos, Hermes, DeepSeek/Paseo.

DeepSeek is not a raw ``dsh`` binary. It goes through Paseo provider ``dsh``:

    paseo run --provider dsh --cwd <cockpit> [--background --quiet]
    paseo attach <agentId>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

DSH_PROVIDER_ID = "dsh"

# Canonical names a caller can pass after alias resolution.
CANONICAL_HARNESSES = (
    "claude-code",
    "grok",
    "codex",
    "cursor-agent",
    "eidos-harness",
    "hermes",
    "deepseek",
    "none",
)

HARNESS_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "grok": "grok",
    "codex": "codex",
    "cursor": "cursor-agent",
    "cursor-agent": "cursor-agent",
    "eidos": "eidos-harness",
    "eidos-harness": "eidos-harness",
    "hermes": "hermes",
    "deepseek": "deepseek",
    "dsh": "deepseek",
    "none": "none",
}

# Raw binaries only. DeepSeek is intentionally absent — it launches via Paseo.
HARNESS_BINARIES = {
    "claude-code": "claude",
    "grok": "grok",
    "codex": "codex",
    "cursor-agent": "cursor-agent",
    "eidos-harness": "eidos-harness",
    "hermes": "hermes",
}

HARNESS_LABELS = {
    "claude-code": "Claude Code",
    "grok": "Grok",
    "codex": "Codex",
    "cursor-agent": "Cursor Agent",
    "eidos-harness": "Eidos Harness",
    "hermes": "Hermes",
    "deepseek": "DeepSeek (Paseo provider dsh)",
    "none": "None (directory only)",
}

DSH_INSTALL_HINT = (
    "Install the DeepSeek Paseo provider:\n"
    "  npm install dsh-acp-paseo\n"
    "  ~/.local/lib/dsh-acp-paseo/node_modules/.bin/dsh-acp-paseo-install-provider\n"
    "Or globally:\n"
    "  npm install -g dsh-acp-paseo && dsh-acp-paseo-install-provider\n"
    "Then reload Paseo: paseo daemon reload"
)

PASEO_INSTALL_HINT = "Install Paseo CLI: npm install -g @getpaseo/cli"


class HarnessError(RuntimeError):
    """User-facing harness launch failure."""


def supported_harness_names() -> list[str]:
    names = list(CANONICAL_HARNESSES)
    aliases = sorted({k for k, v in HARNESS_ALIASES.items() if k != v})
    return names + aliases


def resolve_harness(name: str | None) -> str:
    """Map CLI aliases (dsh, claude, cursor, eidos) to a canonical harness id."""
    if name is None or str(name).strip() == "":
        return "claude-code"
    key = str(name).strip().lower()
    if key in HARNESS_ALIASES:
        return HARNESS_ALIASES[key]
    raise HarnessError(
        f"Unknown harness: {name}\n"
        f"  Supported: {', '.join(CANONICAL_HARNESSES)} (alias: dsh → deepseek)"
    )


def paseo_config_path() -> Path:
    home = os.environ.get("PASEO_HOME")
    if home:
        return Path(home) / "config.json"
    return Path.home() / ".paseo" / "config.json"


def _load_paseo_config(source: dict[str, Any] | str | Path | None) -> dict[str, Any] | None:
    if source is None:
        source = paseo_config_path()
    if isinstance(source, dict):
        return source
    path = Path(source)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _provider_map(config: dict[str, Any]) -> dict[str, Any]:
    agents = config.get("agents")
    if isinstance(agents, dict):
        providers = agents.get("providers")
        if isinstance(providers, dict):
            return providers
    providers = config.get("providers")
    return providers if isinstance(providers, dict) else {}


def _dsh_provider_in_paseo_config(
    config: dict[str, Any] | str | Path | None = None,
) -> bool:
    """True when ~/.paseo/config.json (or PASEO_HOME) defines an enabled ``dsh`` provider."""
    data = _load_paseo_config(config)
    if data is None:
        return False
    entry = _provider_map(data).get(DSH_PROVIDER_ID)
    if not isinstance(entry, dict):
        return False
    if entry.get("enabled") is False:
        return False
    return True


def check_paseo_dsh_ready(
    *,
    which: Callable[[str], str | None] | None = None,
    config: dict[str, Any] | str | Path | None = None,
) -> tuple[bool, str]:
    """Return (ok, error). Error is empty when ready."""
    which = which or shutil.which
    if not which("paseo"):
        return False, f"paseo not found on PATH. {PASEO_INSTALL_HINT}"
    if not _dsh_provider_in_paseo_config(config):
        return False, (
            f"Paseo provider '{DSH_PROVIDER_ID}' is not configured.\n{DSH_INSTALL_HINT}"
        )
    return True, ""


def build_paseo_dsh_run_argv(cwd: str | Path, *, task: str | None = None) -> list[str]:
    """``paseo run --provider dsh --cwd <cockpit>`` plus flags so we can attach."""
    argv = [
        "paseo",
        "run",
        "--provider",
        DSH_PROVIDER_ID,
        "--cwd",
        str(cwd),
        "--background",
        "--quiet",
    ]
    if task:
        argv.append(task)
    return argv


def parse_paseo_run_agent_id(output: str | None) -> str | None:
    """Extract an agent id from ``paseo run --background --quiet`` (or JSON) output."""
    text = (output or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        for key in ("id", "agentId", "agent_id"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        agent = data.get("agent")
        if isinstance(agent, str) and agent.strip():
            return agent.strip()
        if isinstance(agent, dict):
            val = agent.get("id")
            if isinstance(val, str) and val.strip():
                return val.strip()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.search(
            r"(?:agent(?:\s+id)?|id)\s*[:=]\s*([A-Za-z0-9_-]{4,})",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1)
        if re.fullmatch(r"[A-Za-z0-9_-]{4,}", line):
            return line
    return None


def launch_deepseek_via_paseo(
    cwd: str | Path,
    *,
    task: str | None = None,
    runner: Callable[..., Any] | None = None,
    attach: Callable[[list[str]], Any] | None = None,
    which: Callable[[str], str | None] | None = None,
    config: dict[str, Any] | str | Path | None = None,
) -> str:
    """Start a Paseo ``dsh`` agent in ``cwd`` and attach. Returns the agent id."""
    ok, err = check_paseo_dsh_ready(which=which, config=config)
    if not ok:
        raise HarnessError(err)

    run_argv = build_paseo_dsh_run_argv(cwd, task=task)
    run = runner or subprocess.run
    proc = run(run_argv, capture_output=True, text=True)
    stdout = getattr(proc, "stdout", "") or ""
    stderr = getattr(proc, "stderr", "") or ""
    if getattr(proc, "returncode", 1) != 0:
        detail = (stderr or stdout).strip() or f"exit {proc.returncode}"
        raise HarnessError(f"paseo run --provider {DSH_PROVIDER_ID} failed:\n{detail}")

    agent_id = parse_paseo_run_agent_id(stdout) or parse_paseo_run_agent_id(stderr)
    if not agent_id:
        raise HarnessError(
            "paseo run did not return an agent id.\n"
            "Expected `paseo run --provider dsh --cwd <cockpit> --background --quiet` "
            "to print the id so we can `paseo attach <agentId>`."
        )

    attach_argv = ["paseo", "attach", agent_id]
    if attach is not None:
        attach(attach_argv)
        return agent_id
    os.execvp(attach_argv[0], attach_argv)
    return agent_id  # pragma: no cover — execvp does not return


def build_binary_harness_argv(harness: str, extra_args: list[str] | None = None) -> list[str]:
    name = resolve_harness(harness)
    if name == "deepseek":
        raise HarnessError(
            "deepseek / dsh launches through Paseo provider 'dsh', not a raw dsh binary."
        )
    if name == "none":
        return []
    binary = HARNESS_BINARIES[name]
    return [binary, *(extra_args or [])]


def launch_binary_harness(
    harness: str,
    cwd: str | Path,
    *,
    extra_args: list[str] | None = None,
    which: Callable[[str], str | None] | None = None,
    execvp: Callable[[str, list[str]], Any] | None = None,
    chdir: Callable[[str], Any] | None = None,
) -> list[str]:
    """Exec a PATH binary for a non-DeepSeek harness. Returns the argv (tests / none)."""
    name = resolve_harness(harness)
    if name == "none":
        return []
    argv = build_binary_harness_argv(name, extra_args)
    binary = argv[0]
    locator = which or shutil.which
    if not locator(binary):
        raise HarnessError(f"{binary} not found on PATH (harness: {name})")
    (chdir or os.chdir)(str(cwd))
    (execvp or os.execvp)(binary, argv)
    return argv


def pick_harness_menu(
    *,
    stdin=None,
    stdout=None,
    default: str = "claude-code",
) -> str:
    """Numbered harness picker used by the TUI launch path (harness-first menu)."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    rows = [(i + 1, key, HARNESS_LABELS[key]) for i, key in enumerate(CANONICAL_HARNESSES)]
    stdout.write("\n  \033[1m\033[36mHARNESS\033[0m\n\n")
    for num, key, label in rows:
        marker = " ← default" if key == default else ""
        stdout.write(f"    {num}. {label}  \033[90m({key})\033[0m{marker}\n")
    stdout.write("\n  Choose harness [1]: ")
    stdout.flush()
    try:
        raw = stdin.readline()
    except EOFError:
        return default
    choice = (raw or "").strip()
    if not choice:
        return default
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(CANONICAL_HARNESSES):
            return CANONICAL_HARNESSES[idx - 1]
    return resolve_harness(choice)


def parse_harness_args(args: list[str]) -> tuple[str | None, list[str]]:
    """Pull ``--harness`` / ``-H`` out of argv leftovers. Returns (harness, remaining)."""
    harness: str | None = None
    remaining: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token in ("--harness", "-H"):
            i += 1
            if i >= len(args):
                raise HarnessError("Usage: cockpit <name> --harness <name>")
            harness = args[i]
        elif token.startswith("--harness="):
            harness = token.split("=", 1)[1]
        else:
            remaining.append(token)
        i += 1
    env = os.environ.get("COCKPIT_HARNESS")
    if harness is None and env:
        harness = env
    return harness, remaining
