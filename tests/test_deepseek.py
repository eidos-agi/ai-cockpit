"""DeepSeek / Paseo launch path — provider config, readiness, argv, attach."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_cockpit.harness import (
    DSH_INSTALL_HINT,
    DSH_PROVIDER_ID,
    HARNESS_BINARIES,
    HarnessError,
    _dsh_provider_in_paseo_config,
    build_paseo_dsh_run_argv,
    check_paseo_dsh_ready,
    launch_deepseek_via_paseo,
    parse_paseo_run_agent_id,
    resolve_harness,
)


def _dsh_config(**overrides):
    entry = {
        "extends": "acp",
        "label": "DSH (DeepSeek Harness)",
        "enabled": True,
        **overrides,
    }
    return {"agents": {"providers": {"dsh": entry}}}


def test_dsh_alias_resolves_to_deepseek():
    assert resolve_harness("dsh") == "deepseek"
    assert resolve_harness("deepseek") == "deepseek"
    assert resolve_harness("DSH") == "deepseek"


def test_deepseek_not_in_harness_binaries():
    assert "deepseek" not in HARNESS_BINARIES
    assert "dsh" not in HARNESS_BINARIES
    assert DSH_PROVIDER_ID not in HARNESS_BINARIES


def test_dsh_provider_in_paseo_config_from_dict():
    assert _dsh_provider_in_paseo_config(_dsh_config()) is True
    assert _dsh_provider_in_paseo_config(_dsh_config(enabled=False)) is False
    assert _dsh_provider_in_paseo_config({"agents": {"providers": {}}}) is False
    assert _dsh_provider_in_paseo_config({}) is False


def test_dsh_provider_in_paseo_config_from_file(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(_dsh_config()))
    assert _dsh_provider_in_paseo_config(cfg) is True
    missing = tmp_path / "nope.json"
    assert _dsh_provider_in_paseo_config(missing) is False
    cfg.write_text("{not json")
    assert _dsh_provider_in_paseo_config(cfg) is False


def test_dsh_provider_respects_paseo_home(tmp_path, monkeypatch):
    monkeypatch.setenv("PASEO_HOME", str(tmp_path))
    (tmp_path / "config.json").write_text(json.dumps(_dsh_config()))
    assert _dsh_provider_in_paseo_config() is True


def test_check_paseo_dsh_ready_missing_binary():
    ok, err = check_paseo_dsh_ready(which=lambda _: None, config=_dsh_config())
    assert ok is False
    assert "paseo not found" in err
    assert "@getpaseo/cli" in err


def test_check_paseo_dsh_ready_missing_provider():
    ok, err = check_paseo_dsh_ready(
        which=lambda name: "/usr/bin/paseo" if name == "paseo" else None,
        config={"agents": {"providers": {}}},
    )
    assert ok is False
    assert "dsh" in err
    assert "npm install dsh-acp-paseo" in err
    assert "dsh-acp-paseo-install-provider" in err
    assert DSH_INSTALL_HINT.splitlines()[0] in err


def test_check_paseo_dsh_ready_ok():
    ok, err = check_paseo_dsh_ready(
        which=lambda name: "/usr/bin/paseo" if name == "paseo" else None,
        config=_dsh_config(),
    )
    assert ok is True
    assert err == ""


def test_build_paseo_dsh_run_argv():
    cwd = "/tmp/my-cockpit"
    argv = build_paseo_dsh_run_argv(cwd)
    assert argv[:6] == ["paseo", "run", "--provider", "dsh", "--cwd", cwd]
    assert "--background" in argv
    assert "--quiet" in argv
    # DeepSeek is Paseo-only — never a raw `dsh` exec
    assert argv[0] != "dsh"
    assert "dsh" not in argv[:2]


def test_parse_paseo_run_agent_id_formats():
    assert parse_paseo_run_agent_id("agt_abc123") == "agt_abc123"
    assert parse_paseo_run_agent_id('{"id": "abc123"}') == "abc123"
    assert parse_paseo_run_agent_id('{"agentId": "xyz-9"}') == "xyz-9"
    assert parse_paseo_run_agent_id("Started agent id: sess_1") == "sess_1"
    assert parse_paseo_run_agent_id("") is None
    assert parse_paseo_run_agent_id(None) is None


def test_launch_deepseek_via_paseo_success():
    captured = {}

    def runner(argv, **kwargs):
        captured["run"] = argv
        return SimpleNamespace(returncode=0, stdout="agent-42\n", stderr="")

    def attach(argv):
        captured["attach"] = argv

    agent_id = launch_deepseek_via_paseo(
        Path("/tmp/cockpit"),
        runner=runner,
        attach=attach,
        which=lambda name: "/bin/paseo" if name == "paseo" else None,
        config=_dsh_config(),
    )
    assert agent_id == "agent-42"
    assert captured["run"][:6] == [
        "paseo",
        "run",
        "--provider",
        "dsh",
        "--cwd",
        "/tmp/cockpit",
    ]
    assert captured["attach"] == ["paseo", "attach", "agent-42"]


def test_launch_deepseek_via_paseo_missing_paseo():
    with pytest.raises(HarnessError, match="paseo not found"):
        launch_deepseek_via_paseo(
            "/tmp/c",
            which=lambda _: None,
            config=_dsh_config(),
        )


def test_launch_deepseek_via_paseo_missing_provider():
    with pytest.raises(HarnessError, match="provider 'dsh'"):
        launch_deepseek_via_paseo(
            "/tmp/c",
            which=lambda name: "/bin/paseo" if name == "paseo" else None,
            config={"agents": {"providers": {}}},
        )


def test_launch_deepseek_via_paseo_run_failure():
    def runner(argv, **kwargs):
        return SimpleNamespace(returncode=2, stdout="", stderr="provider dsh unknown")

    with pytest.raises(HarnessError, match="paseo run"):
        launch_deepseek_via_paseo(
            "/tmp/c",
            runner=runner,
            attach=lambda _: None,
            which=lambda name: "/bin/paseo" if name == "paseo" else None,
            config=_dsh_config(),
        )


def test_launch_deepseek_via_paseo_no_agent_id():
    def runner(argv, **kwargs):
        return SimpleNamespace(returncode=0, stdout="started\n", stderr="")

    with pytest.raises(HarnessError, match="agent id"):
        launch_deepseek_via_paseo(
            "/tmp/c",
            runner=runner,
            attach=lambda _: None,
            which=lambda name: "/bin/paseo" if name == "paseo" else None,
            config=_dsh_config(),
        )
