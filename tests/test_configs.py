import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_parse():
    files = sorted((ROOT / ".github/workflows").glob("*.yml"))
    assert files, "no workflows found"
    for p in files:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict), p


def test_dependabot_parses():
    p = ROOT / ".github/dependabot.yml"
    assert isinstance(yaml.safe_load(p.read_text(encoding="utf-8")), dict)


def test_configs_parse():
    for p in sorted((ROOT / "configs").glob("*.json")):
        assert isinstance(json.loads(p.read_text(encoding="utf-8")), dict)


def test_queue_targets_have_ref_and_path():
    q = json.loads((ROOT / "configs/kaggle_queue.json").read_text(encoding="utf-8"))
    assert isinstance(q.get("targets"), list)
    for t in q["targets"]:
        assert t.get("ref")
        assert t.get("path")


def test_devcontainer_parses():
    p = ROOT / ".devcontainer/devcontainer.json"
    assert isinstance(json.loads(p.read_text(encoding="utf-8")), dict)
