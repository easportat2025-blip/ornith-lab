import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def load_workflow(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def triggers(wf):
    # PyYAML follows YAML 1.1 and may parse the key `on` as boolean True.
    return wf.get("on") or wf.get(True) or {}


def step_text(wf):
    parts = []
    for job in (wf.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            parts.append(str(step.get("run") or ""))
            parts.append(str((step.get("with") or {}).get("script") or ""))
    return "\n".join(parts)


def test_ops_tick_contract():
    wf = load_workflow("ops-tick.yml")
    t = triggers(wf)
    assert "kaggle-watchdog" in t["workflow_run"]["workflows"]
    assert "delay_seconds" in t["workflow_dispatch"]["inputs"]
    assert wf["permissions"]["actions"] == "write"
    text = step_text(wf)
    assert "configs/ops.json" in text
    assert "kaggle-watchdog.yml" in text
    assert "ops-heartbeat.yml" in text
    assert "ops-tick.yml" in text
    assert "listWorkflowRuns" in text
    assert "next_delay" in text
    assert "using safe defaults" in text


def test_watchdog_contract():
    wf = load_workflow("kaggle-watchdog.yml")
    t = triggers(wf)
    assert "auto_push" in t["workflow_dispatch"]["inputs"]
    assert "configs/ops.json" in t["push"]["paths"]
    assert wf["permissions"]["contents"] == "write"
    assert wf["permissions"]["issues"] == "write"


def test_ops_health_contract():
    wf = load_workflow("ops-health.yml")
    t = triggers(wf)
    assert "schedule" in t
    assert "workflow_dispatch" in t
    assert wf["permissions"]["actions"] == "write"
    assert wf["permissions"]["issues"] == "write"
    text = step_text(wf)
    assert "scripts/ops_health.py" in text
    assert "--redispatch" in text
    assert "[ops] loop health" in text


def test_ops_config_contract():
    cfg = json.loads((ROOT / "configs" / "ops.json").read_text(encoding="utf-8"))
    assert cfg["loop"]["enabled"] is True
    assert cfg["loop"]["delay_seconds"] == 600
    assert cfg["loop"]["stale_after_minutes"] > cfg["loop"]["delay_seconds"] / 60
    assert cfg["features"]["auto_push"] is True
    assert cfg["features"]["download_results"] is True
    assert cfg["features"]["heartbeat"] is True
    assert cfg["upgrade"]["mode"] is False


def test_hf_sync_reads_config():
    wf = load_workflow("hf-sync.yml")
    text = step_text(wf)
    assert "requirements-hf.txt" in (WORKFLOWS / "hf-sync.yml").read_text(
        encoding="utf-8")
    assert "configs/ops.json" in text
    assert "hf_sync" in text


def test_workflow_names_unique():
    names = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        wf = yaml.safe_load(path.read_text(encoding="utf-8"))
        names.append(wf.get("name"))
    assert len(names) == len(set(names))
