"""DeepSeek / Paseo launch path — provider config, readiness, argv, attach."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_cockpit.harness import (
    DSH_INSTALL_HINT,
    DSH_PROVIDER_ID,
    HARNESS_BINARIES,
    PASEO_PROVIDER_LS_TIMEOUT_SEC,
    PASEO_RUN_TIMEOUT_SEC,
    HarnessError,
    _dsh_listed_in_provider_ls,
    _dsh_provider_in_paseo_config,
    build_paseo_dsh_run_argv,
    check_paseo_dsh_ready,
    launch_deepseek_via_paseo,
    parse_paseo_run_agent_id,
    paseo_provider_diagnostic_argv,
    resolve_harness,
    run_paseo_timed,
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


def _ok_which(name):
    return "/usr/bin/paseo" if name == "paseo" else None


def _ls_runner(stdout="dsh  DSH / DeepSeek Harness  Enabled\n"):
    calls = []

    def runner(argv, **kwargs):
        calls.append({"argv": list(argv), "timeout": kwargs.get("timeout")})
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def test_check_paseo_dsh_ready_ok():
    runner = _ls_runner()
    ok, err = check_paseo_dsh_ready(
        which=_ok_which,
        config=_dsh_config(),
        runner=runner,
    )
    assert ok is True
    assert err == ""
    assert runner.calls[0]["argv"][:3] == ["paseo", "provider", "ls"]
    assert runner.calls[0]["timeout"] == PASEO_PROVIDER_LS_TIMEOUT_SEC
    assert all("diagnostic" not in c["argv"] for c in runner.calls)


def test_check_paseo_dsh_ready_never_calls_diagnostic():
    """Mac: `paseo provider diagnostic dsh` hangs past 8s even when ls is fine."""
    runner = _ls_runner()
    check_paseo_dsh_ready(which=_ok_which, config=_dsh_config(), runner=runner)
    invoked = [c["argv"] for c in runner.calls]
    assert paseo_provider_diagnostic_argv() not in invoked
    assert not any("diagnostic" in argv for argv in invoked)


def test_check_paseo_dsh_ready_ls_timeout_nonfatal():
    def runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 5))

    ok, err = check_paseo_dsh_ready(
        which=_ok_which,
        config=_dsh_config(),
        runner=runner,
        ls_timeout=0.05,
    )
    assert ok is True
    assert err == ""


def test_run_paseo_timed_timeout_does_not_block():
    def runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 1))

    stdout, stderr, rc = run_paseo_timed(
        ["paseo", "provider", "diagnostic", "dsh"],
        timeout=0.05,
        runner=runner,
    )
    assert rc == "timeout"
    assert stdout == ""


def test_dsh_listed_in_provider_ls():
    assert _dsh_listed_in_provider_ls("dsh  DSH / DeepSeek Harness  Enabled") is True
    assert _dsh_listed_in_provider_ls('{"id": "dsh", "enabled": true}') is True
    assert _dsh_listed_in_provider_ls('[{"id": "claude"}]') is False
    assert _dsh_listed_in_provider_ls("dshanklin  Enabled") is False
    assert _dsh_listed_in_provider_ls("") is False


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
    assert parse_paseo_run_agent_id("started\n") is None


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


def test_launch_deepseek_via_paseo_run_timeout():
    def runner(argv, **kwargs):
        if argv[:3] == ["paseo", "provider", "ls"]:
            return SimpleNamespace(returncode=0, stdout="dsh  Enabled\n", stderr="")
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 30))

    with pytest.raises(HarnessError, match="timed out"):
        launch_deepseek_via_paseo(
            "/tmp/c",
            runner=runner,
            attach=lambda _: None,
            which=_ok_which,
            config=_dsh_config(),
        )
    assert PASEO_RUN_TIMEOUT_SEC >= 1
