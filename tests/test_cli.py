"""Tests for the cockpit CLI."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_cockpit import __version__
from ai_cockpit.cli import (
    _check_cockpit_workspace,
    detect_capabilities,
    detect_schema_version,
    get_scan_dirs,
    load_config,
    load_registry,
    save_config,
    save_registry,
    slugify,
)


# ─── Unit Tests ──────────────────────────────────────────


def test_version_exists():
    assert __version__
    assert "." in __version__


def test_slugify():
    assert slugify("My Cockpit") == "my-cockpit"
    assert slugify("some_thing") == "some-thing"
    assert slugify("already-slug") == "already-slug"


def test_load_config_missing(tmp_path):
    with patch("ai_cockpit.cli.CONFIG_PATH", tmp_path / "nope.json"):
        cfg = load_config()
    assert cfg == {}


def test_save_and_load_config(tmp_path):
    config_path = tmp_path / "config.json"
    with patch("ai_cockpit.cli.CONFIG_PATH", config_path):
        save_config({"scan_dirs": ["/tmp/repos"]})
        cfg = load_config()
    assert cfg["scan_dirs"] == ["/tmp/repos"]


def test_load_registry_missing(tmp_path):
    with patch("ai_cockpit.cli.REGISTRY_PATH", tmp_path / "nope.json"):
        reg = load_registry()
    assert reg == {"cockpits": []}


def test_save_and_load_registry(tmp_path):
    reg_path = tmp_path / "registry.json"
    with patch("ai_cockpit.cli.REGISTRY_PATH", reg_path):
        save_registry({"cockpits": [{"name": "test", "slug": "test", "path": "/tmp/test"}]})
        reg = load_registry()
    assert len(reg["cockpits"]) == 1
    assert reg["cockpits"][0]["slug"] == "test"


def test_get_scan_dirs_empty(tmp_path):
    with patch("ai_cockpit.cli.CONFIG_PATH", tmp_path / "nope.json"):
        dirs = get_scan_dirs()
    assert dirs == []


def test_get_scan_dirs_configured(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"scan_dirs": ["~/repos", "/opt/cockpits"]}))
    with patch("ai_cockpit.cli.CONFIG_PATH", config_path):
        dirs = get_scan_dirs()
    assert len(dirs) == 2
    assert all(isinstance(d, Path) for d in dirs)


# ─── Capability Detection ────────────────────────────────


def test_detect_capabilities_missing(tmp_path):
    caps = detect_capabilities(tmp_path / "nonexistent")
    assert caps["exists"] is False


def test_detect_capabilities_minimal(tmp_path):
    (tmp_path / "state.json").write_text('{"cockpit": {"name": "test"}}')
    caps = detect_capabilities(tmp_path)
    assert caps["exists"] is True
    assert caps["state_json"] is True
    assert caps["claude_md"] is False


def test_detect_capabilities_full(tmp_path):
    from ai_cockpit.cli import CORE_SKILLS
    (tmp_path / "state.json").write_text('{"cockpit": {"name": "test"}}')
    (tmp_path / "CLAUDE.md").write_text("# Test")
    (tmp_path / ".mcp.json").write_text("{}")
    skills_dir = tmp_path / ".claude" / "skills"
    for skill in CORE_SKILLS:
        (skills_dir / skill).mkdir(parents=True, exist_ok=True)
        (skills_dir / skill / "skill.md").write_text(f"# {skill}")
    (tmp_path / ".visionlog").mkdir()
    (tmp_path / ".research").mkdir()
    (tmp_path / ".ike").mkdir()
    caps = detect_capabilities(tmp_path)
    assert caps["core_skills_complete"] is True
    assert caps["has_trilogy"] is True
    assert caps["claude_md"] is True


def test_detect_schema_version_v0(tmp_path):
    (tmp_path / "state.json").write_text('{"cockpit": {"name": "test"}}')
    ver, caps = detect_schema_version(tmp_path)
    assert ver == 0


def test_detect_schema_version_missing(tmp_path):
    ver, caps = detect_schema_version(tmp_path / "nope")
    assert ver == -1


# ─── Workspace Contract ──────────────────────────────────


def test_workspace_check_clean_repo(tmp_path):
    # Init a clean git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True)
    clears, warns, blocks = _check_cockpit_workspace(str(tmp_path))
    assert "Working tree clean" in clears
    assert not blocks


def test_workspace_check_dirty_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / "dirty.txt").write_text("hello")
    clears, warns, blocks = _check_cockpit_workspace(str(tmp_path))
    assert any("untracked" in w for w in warns)


def test_workspace_check_uncommitted(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, capture_output=True)
    clears, warns, blocks = _check_cockpit_workspace(str(tmp_path))
    assert any("uncommitted" in b for b in blocks)


def test_workspace_check_not_git(tmp_path):
    clears, warns, blocks = _check_cockpit_workspace(str(tmp_path))
    assert any("Not a git repo" in w for w in warns)


# ─── CLI Integration ─────────────────────────────────────


def test_cli_help():
    r = subprocess.run([sys.executable, "-m", "ai_cockpit.cli", "help"], capture_output=True, text=True)
    assert "cockpit" in r.stdout.lower()
    assert "can-i-close" in r.stdout


def test_cli_version():
    r = subprocess.run([sys.executable, "-m", "ai_cockpit.cli", "version"], capture_output=True, text=True)
    assert __version__ in r.stdout


def test_cli_can_i_close_help():
    r = subprocess.run([sys.executable, "-m", "ai_cockpit.cli", "can-i-close", "--help"], capture_output=True, text=True)
    assert "workspace contract" in r.stdout.lower()


def test_cli_touch_and_go_help():
    r = subprocess.run([sys.executable, "-m", "ai_cockpit.cli", "touch-and-go", "--help"], capture_output=True, text=True)
    assert "checkpoint" in r.stdout.lower()


def test_cli_new_help():
    r = subprocess.run([sys.executable, "-m", "ai_cockpit.cli", "new"], capture_output=True, text=True)
    assert "create a new cockpit" in r.stdout.lower()


def test_cli_marketplace():
    r = subprocess.run([sys.executable, "-m", "ai_cockpit.cli", "marketplace"], capture_output=True, text=True)
    assert "eidos-marketplace" in r.stdout
