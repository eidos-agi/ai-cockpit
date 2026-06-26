"""Tests for flight deck launch router."""

from ai_cockpit.launch import (
    GREENMARK_LAUNCH_TARGETS,
    build_remote_shell_command,
    enrich_cockpit_entry,
    enrich_registry,
    is_local_target,
    remote_targets,
)


def test_greenmark_enrichment():
    c = {"slug": "greenmark-cockpit", "name": "Greenmark", "path": "/tmp/gm"}
    out = enrich_cockpit_entry(c)
    assert len(out["launch_targets"]) == 2
    assert out["launch_targets"][1]["machine_id"] == "rentamac-cyprus-01"


def test_remote_targets_filters_local():
    c = enrich_cockpit_entry({"slug": "greenmark-cockpit", "path": "/tmp"})
    remotes = remote_targets(c)
    assert len(remotes) == 1
    assert remotes[0]["substrate"] == "greenmark_cyprus"


def test_is_local_target():
    assert is_local_target({"machine_id": "daniel-laptop-01", "remote_path": None})
    assert not is_local_target(
        {"machine_id": "rentamac-cyprus-01", "remote_path": "/remote/path"}
    )


def test_build_remote_shell_command():
    cmd = build_remote_shell_command("/Users/rentamac/repos/greenmark-cockpit", "grok")
    assert "git pull --ff-only" in cmd
    assert "exec grok" in cmd
    assert "/Users/rentamac/repos/greenmark-cockpit" in cmd


def test_enrich_registry_preserves_other_cockpits():
    reg = enrich_registry({
        "cockpits": [
            {"slug": "software-engineer", "path": "/a"},
            {"slug": "greenmark-cockpit", "path": "/b"},
        ]
    })
    gm = next(c for c in reg["cockpits"] if c["slug"] == "greenmark-cockpit")
    se = next(c for c in reg["cockpits"] if c["slug"] == "software-engineer")
    assert "launch_targets" in gm
    assert "launch_targets" not in se