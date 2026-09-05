"""Harness aliases, binary launch, and CLI --harness parsing."""

import subprocess
import sys
from io import StringIO

import pytest

from ai_cockpit.harness import (
    CANONICAL_HARNESSES,
    HARNESS_BINARIES,
    HarnessError,
    build_binary_harness_argv,
    launch_binary_harness,
    parse_harness_args,
    pick_harness_menu,
    resolve_harness,
)


@pytest.mark.parametrize(
    "raw,canonical",
    [
        (None, "claude-code"),
        ("", "claude-code"),
        ("claude", "claude-code"),
        ("claude-code", "claude-code"),
        ("grok", "grok"),
        ("codex", "codex"),
        ("cursor", "cursor-agent"),
        ("cursor-agent", "cursor-agent"),
        ("eidos", "eidos-harness"),
        ("eidos-harness", "eidos-harness"),
        ("hermes", "hermes"),
        ("none", "none"),
        ("dsh", "deepseek"),
        ("deepseek", "deepseek"),
    ],
)
def test_resolve_harness_aliases(raw, canonical):
    assert resolve_harness(raw) == canonical


def test_unknown_harness():
    with pytest.raises(HarnessError, match="Unknown harness"):
        resolve_harness("chatgpt")


def test_harness_binaries_cover_non_deepseek():
    for name in ("claude-code", "grok", "codex", "cursor-agent", "eidos-harness", "hermes"):
        assert name in HARNESS_BINARIES
    assert "deepseek" not in HARNESS_BINARIES
    assert "none" not in HARNESS_BINARIES
    assert set(CANONICAL_HARNESSES) == {
        "claude-code",
        "grok",
        "codex",
        "cursor-agent",
        "eidos-harness",
        "hermes",
        "deepseek",
        "none",
    }


def test_build_binary_argv():
    assert build_binary_harness_argv("grok") == ["grok"]
    assert build_binary_harness_argv("codex", ["--yolo"]) == ["codex", "--yolo"]
    assert build_binary_harness_argv("none") == []
    with pytest.raises(HarnessError, match="Paseo"):
        build_binary_harness_argv("deepseek")
    with pytest.raises(HarnessError, match="Paseo"):
        build_binary_harness_argv("dsh")


def test_launch_binary_harness_missing():
    with pytest.raises(HarnessError, match="not found on PATH"):
        launch_binary_harness("grok", "/tmp", which=lambda _: None)


def test_launch_binary_harness_exec():
    seen = {}

    def execvp(file, argv):
        seen["file"] = file
        seen["argv"] = argv

    def chdir(path):
        seen["cwd"] = path

    launch_binary_harness(
        "hermes",
        "/tmp/cockpit",
        which=lambda name: f"/usr/bin/{name}",
        execvp=execvp,
        chdir=chdir,
    )
    assert seen["file"] == "hermes"
    assert seen["argv"] == ["hermes"]
    assert seen["cwd"] == "/tmp/cockpit"


def test_launch_none_is_noop():
    assert launch_binary_harness("none", "/tmp") == []


def test_parse_harness_args_flag_and_equals():
    harness, rest = parse_harness_args(["my-cockpit", "--harness", "dsh", "-a"])
    assert harness == "dsh"
    assert rest == ["my-cockpit", "-a"]

    harness, rest = parse_harness_args(["--harness=grok", "ops"])
    assert harness == "grok"
    assert rest == ["ops"]

    harness, rest = parse_harness_args(["-H", "none", "ops"])
    assert harness == "none"
    assert rest == ["ops"]


def test_parse_harness_args_env(monkeypatch):
    monkeypatch.setenv("COCKPIT_HARNESS", "hermes")
    harness, rest = parse_harness_args(["ops"])
    assert harness == "hermes"
    assert rest == ["ops"]


def test_parse_harness_args_missing_value():
    with pytest.raises(HarnessError, match="Usage"):
        parse_harness_args(["ops", "--harness"])


def test_pick_harness_menu_number_and_default():
    out = StringIO()
    assert pick_harness_menu(stdin=StringIO("7\n"), stdout=out) == "deepseek"
    assert "DeepSeek" in out.getvalue()
    assert pick_harness_menu(stdin=StringIO("\n"), stdout=StringIO()) == "claude-code"
    assert pick_harness_menu(stdin=StringIO("dsh\n"), stdout=StringIO()) == "deepseek"


def test_launch_cockpit_routes_deepseek_and_binaries(monkeypatch):
    from ai_cockpit.cli import launch_cockpit

    seen = {}
    monkeypatch.setattr(
        "ai_cockpit.cli.launch_deepseek_via_paseo",
        lambda path: seen.setdefault("dsh", path),
    )
    monkeypatch.setattr(
        "ai_cockpit.cli.launch_binary_harness",
        lambda name, path: seen.setdefault("bin", (name, path)),
    )
    monkeypatch.setattr(
        "ai_cockpit.cli.launch_cockpit_entry",
        lambda *a, **k: seen.setdefault("claude", True),
    )

    cockpit = {"name": "Ops", "slug": "ops", "path": "/tmp/ops"}
    launch_cockpit(cockpit, harness="dsh")
    assert seen["dsh"] == "/tmp/ops"

    launch_cockpit(cockpit, harness="grok")
    assert seen["bin"] == ("grok", "/tmp/ops")

    launch_cockpit(cockpit, harness="none")
    launch_cockpit(cockpit, harness="claude-code")
    assert seen.get("claude") is True


def test_cli_help_mentions_paseo_deepseek():
    r = subprocess.run(
        [sys.executable, "-m", "ai_cockpit.cli", "help"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    text = r.stdout.lower()
    assert "deepseek" in text
    assert "paseo" in text
    assert "--harness" in text
    assert "dsh" in text
    assert "claude-code" in text
    assert "can-i-close" in text
