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
    Path("/Users/dshanklin/repos-personal/conduit/scripts/conduit"),
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


def launch_cockpit_entry(
    cockpit: dict[str, Any],
    mode: str | None = None,
    *,
    launch_target: dict[str, Any] | None = None,
    build_claude_cmd=None,
) -> None:
    cockpit = enrich_cockpit_entry(cockpit)
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