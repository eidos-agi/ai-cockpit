"""Flight deck launch router — hat × substrate × instrument."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

LOCAL_MACHINE_IDS = frozenset({"daniel-laptop-01", "local", "laptop"})

CONDUIT_SEARCH = [
    Path.home() / "repos-personal" / "conduit" / "scripts" / "conduit",
    Path.home() / "repos-personal" / "conduit" / "scripts" / "conduit.py",
]

GREENMARK_LAUNCH_TARGETS = [
    {
        "substrate": "local",
        "machine_id": "daniel-laptop-01",
        "remote_path": None,
        "runtime_default": "claude",
        "label": "Local",
    },
    {
        "substrate": "greenmark_cyprus",
        "machine_id": "rentamac-cyprus-01",
        "remote_path": "/Users/rentamac/repos-greenmark-waste-solutions/greenmark-cockpit",
        "runtime_default": "grok",
        "label": "Cyprus",
        "trust": "rented",
    },
]


def find_conduit_script() -> Path | None:
    for candidate in CONDUIT_SEARCH:
        if candidate.is_file():
            return candidate
    found = shutil.which("conduit")
    if found:
        return Path(found)
    return None


def get_launch_targets(cockpit: dict[str, Any]) -> list[dict[str, Any]]:
    return list(cockpit.get("launch_targets") or [])


def is_local_target(target: dict[str, Any]) -> bool:
    machine = (target.get("machine_id") or "").lower()
    substrate = (target.get("substrate") or "").lower()
    if machine in LOCAL_MACHINE_IDS:
        return True
    if substrate in LOCAL_MACHINE_IDS:
        return True
    if target.get("remote_path") in (None, ""):
        return True
    return False


def remote_targets(cockpit: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for t in get_launch_targets(cockpit) if not is_local_target(t)]


def enrich_cockpit_entry(cockpit: dict[str, Any]) -> dict[str, Any]:
    """Apply known launch_targets defaults (Greenmark v1)."""
    if cockpit.get("slug") == "greenmark-cockpit" and not cockpit.get("launch_targets"):
        cockpit = {**cockpit, "launch_targets": [dict(t) for t in GREENMARK_LAUNCH_TARGETS]}
    return cockpit


def enrich_registry(reg: dict[str, Any]) -> dict[str, Any]:
    reg = dict(reg)
    reg["cockpits"] = [enrich_cockpit_entry(c) for c in reg.get("cockpits", [])]
    return reg


def conduit_doctor(machine_id: str, *, conduit: Path | None = None) -> bool:
    script = conduit or find_conduit_script()
    if not script:
        return False
    proc = subprocess.run(
        [str(script), "doctor", machine_id],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def build_remote_shell_command(remote_path: str, runtime: str) -> str:
    runtime = (runtime or "grok").lower()
    if runtime == "grok":
        agent = "grok"
    elif runtime == "claude":
        agent = "claude"
    else:
        agent = runtime
    quoted = shlex.quote(remote_path)
    return f"cd {quoted} && git pull --ff-only && exec {agent}"


def build_remote_launch_argv(
    cockpit: dict[str, Any],
    target: dict[str, Any],
    *,
    conduit: Path | None = None,
) -> list[str]:
    script = conduit or find_conduit_script()
    if not script:
        raise RuntimeError("conduit not found — install repos-personal/conduit")

    machine_id = target["machine_id"]
    remote_path = target.get("remote_path")
    if not remote_path:
        raise RuntimeError(f"remote target missing remote_path: {target.get('substrate')}")

    runtime = target.get("runtime_default", "grok")
    remote_shell = build_remote_shell_command(remote_path, runtime)
    return [
        str(script),
        "run",
        "--target",
        machine_id,
        "--",
        "bash",
        "-lc",
        remote_shell,
    ]


def describe_launch(
    cockpit: dict[str, Any],
    target: dict[str, Any] | None = None,
    *,
    local_cmd: list[str] | None = None,
) -> str:
    if target and not is_local_target(target):
        argv = build_remote_launch_argv(cockpit, target)
        return " ".join(shlex.quote(a) for a in argv)
    if local_cmd:
        return " ".join(shlex.quote(a) for a in local_cmd)
    return f"claude (local) in {cockpit.get('path', '')}"


def launch_remote(
    cockpit: dict[str, Any],
    target: dict[str, Any],
    *,
    conduit: Path | None = None,
) -> None:
    script = conduit or find_conduit_script()
    if not script:
        print("  \033[31mconduit not found\033[0m")
        print("  \033[90mExpected: ~/repos-personal/conduit/scripts/conduit\033[0m")
        sys.exit(1)

    machine_id = target["machine_id"]
    label = target.get("label") or target.get("substrate") or machine_id
    runtime = target.get("runtime_default", "grok")

    print(f"\n  \033[36m→\033[0m Remote launch \033[1m{cockpit['name']}\033[0m")
    print(f"  \033[90m{label} · {machine_id} · {runtime}\033[0m")
    print(f"  \033[90m{target.get('remote_path')}\033[0m")
    print(f"  \033[33mStep 1/3:\033[0m conduit doctor {machine_id}")

    if not conduit_doctor(machine_id, conduit=script):
        print(f"  \033[31mDoctor failed for {machine_id} — aborting launch\033[0m")
        sys.exit(1)

    print(f"  \033[33mStep 2/3:\033[0m git pull --ff-only on remote")
    print(f"  \033[33mStep 3/3:\033[0m attach {runtime} (interactive)\n")

    argv = build_remote_launch_argv(cockpit, target, conduit=script)
    os.execvp(argv[0], argv)


def launch_local_claude(cockpit: dict[str, Any], mode: str | None, build_claude_cmd) -> None:
    """Delegate to existing Claude launcher (build_claude_cmd from cli)."""
    path = cockpit["path"]
    if not Path(path).exists():
        print(f"  \033[31mPath missing:\033[0m {path}")
        sys.exit(1)

    cmd, startup_cmd = build_claude_cmd(cockpit, mode)

    print(f"\n  \033[36m→\033[0m Opening \033[1m{cockpit['name']}\033[0m")
    print(f"  \033[90m{path}\033[0m")
    if mode:
        print(f"  \033[33mMode: {mode}\033[0m")
    else:
        print(f"  \033[90mAuto mode: unlocked (Shift+Tab)\033[0m")
    if startup_cmd:
        print(f"  \033[90mStartup: {startup_cmd}\033[0m")
    print()

    os.chdir(path)
    os.execvp("claude", cmd)


REMOTE_PATH_EXPORT = 'export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"'


def is_local_host(host: str) -> bool:
    return (host or "").lower() in LOCAL_MACHINE_IDS


def launch_mux_remote(cockpit: dict[str, Any], mode: str | None = None) -> None:
    """Mux cockpit chat: a claude chat in a tmux session on the right machine,
    registered into the right plane.

    Two flavors per plane (the manager/worker split):
      manager — chat lives IN the directmux plane on the manager machine and
                steers the target plane via its forwarding CLI (e.g. `gmux`).
      session — chat lives on the plane's own host, registered into that
                plane, driving it with the host-local CLI (e.g. `greenmux`).
    """
    r = cockpit["remote"]
    host = r["host"]
    mux = r["mux"]
    cli = r.get("cli", mux)                      # CLI the chat drives the plane with
    container = r.get("container", mux)          # plane the chat itself lives in
    container_cli = r.get("container_cli", cli)  # CLI used to register the chat
    session = r.get("session", f"cockpit-{mux}")
    how = r.get("how", "")
    if r.get("manager"):
        default_prompt = (
            f"You are the {mux} MANAGER chat, living inside the {container} plane on the "
            f"manager machine. You steer the {mux} plane remotely: `{cli} <verb>` here "
            f"forwards to its host. "
            + (f"Plane notes:\n{how}\n\n" if how else "")
            + f"Start now: run `{cli} ls` to show the {mux} fleet and summarize it. "
            f"Then await orders."
        )
    else:
        default_prompt = (
            f"You are the {mux} cockpit chat — the supervisor console living on the {mux} "
            f"plane's own machine. Drive it with `{cli} <verb>` (ls, capture, send, run, ask, ...). "
            + (f"Plane notes:\n{how}\n\n" if how else "")
            + f"Start now: run `{cli} ls` to show the fleet and summarize what each agent "
            f"is doing. If the plane is not running, start it and report. Then await orders."
        )
    prompt = r.get("prompt") or default_prompt
    perm = "--dangerously-skip-permissions" if mode == "yolo" else "--permission-mode auto"
    inner = f"{REMOTE_PATH_EXPORT}; claude {perm} {shlex.quote(prompt)}"
    # Create detached, register into the container plane (best-effort), then attach.
    # If the session already exists, new-session fails quietly and we reattach.
    tmux_cmd = (
        f"{REMOTE_PATH_EXPORT}; "
        f"tmux new-session -d -s {shlex.quote(session)} {shlex.quote(inner)} 2>/dev/null; "
        f"{shlex.quote(container_cli)} register {shlex.quote(session)} {shlex.quote(session)} "
        f"-d {shlex.quote(f'cockpit chat: {cockpit['name']}')} >/dev/null 2>&1; "
        f"exec tmux attach -t {shlex.quote(session)}"
    )
    where = f"locally ({host})" if is_local_host(host) else f"on \033[1m{host}\033[0m"
    print(f"\n  \033[36m⇄\033[0m Opening \033[1m{cockpit['name']}\033[0m {where}")
    print(f"  \033[90mtmux: {session} · lives in {container} · drives {mux} via {cli}\033[0m\n")
    if is_local_host(host):
        os.execvp("/bin/sh", ["sh", "-c", tmux_cmd])
    else:
        os.execvp("ssh", ["ssh", "-t", host, tmux_cmd])


def launch_cockpit_entry(
    cockpit: dict[str, Any],
    mode: str | None = None,
    *,
    launch_target: dict[str, Any] | None = None,
    build_claude_cmd=None,
) -> None:
    cockpit = enrich_cockpit_entry(cockpit)
    if cockpit.get("remote"):
        launch_mux_remote(cockpit, mode)
        return
    if launch_target and not is_local_target(launch_target):
        launch_remote(cockpit, launch_target)
        return
    if build_claude_cmd is None:
        raise RuntimeError("build_claude_cmd required for local launch")
    launch_local_claude(cockpit, mode, build_claude_cmd)


def registry_hygiene_report(reg: dict[str, Any]) -> list[str]:
    """Plan 2: surface registry lies."""
    lines: list[str] = []
    for c in reg.get("cockpits", []):
        if c.get("remote"):
            continue  # remote mux cockpits have no local path
        path = c.get("path", "")
        if not path:
            lines.append(f"  \033[31m✗\033[0m {c.get('slug', '?')}: empty path")
            continue
        p = Path(path)
        if not p.exists():
            lines.append(f"  \033[31m✗\033[0m {c.get('slug', '?')}: path missing — {path}")
        elif ".disabled" in path:
            lines.append(f"  \033[33m!\033[0m {c.get('slug', '?')}: disabled path — {path}")
    exe = shutil.which("cockpit") or sys.argv[0]
    lines.append(f"  \033[90mcockpit binary:\033[0m {exe}")
    conduit = find_conduit_script()
    if conduit:
        lines.append(f"  \033[32m✓\033[0m conduit: {conduit}")
    else:
        lines.append("  \033[31m✗\033[0m conduit: not found")
    return lines