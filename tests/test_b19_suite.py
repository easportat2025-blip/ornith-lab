import importlib.util
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B19 = os.path.join(ROOT, "phase13-gui", "bench_b19")
TASKS = os.path.join(B19, "tasks")


def _load_checker():
    path = os.path.join(B19, "checker.py")
    spec = importlib.util.spec_from_file_location("b19_checker", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_b19_tasks_are_complete():
    data = json.load(open(os.path.join(TASKS, "tasks.json"), encoding="utf-8"))
    assert data["suite"] == "B19"
    tasks = data["tasks"]
    assert len(tasks) == 8
    checker = _load_checker()
    for task in tasks:
        assert task["variants"] == [0, 1, 2, 3, 4, 5]
        assert task["task_id"] in checker.CHECKS
        app = os.path.join(TASKS, task["app"])
        assert os.path.isfile(app), app
        assert os.path.getsize(app) > 500


def test_b19_dataset_and_kernel_metadata():
    ds = json.load(open(os.path.join(B19, "dataset-metadata.json"),
                        encoding="utf-8"))
    assert ds["id"] == "dieniw/ornith-gui-bench-b19"
    kdir = os.path.join(ROOT, "phase13-gui", "kernel_bench_b19")
    km = json.load(open(os.path.join(kdir, "kernel-metadata.json"),
                        encoding="utf-8"))
    assert km["id"] == "dieniw/ornith-gui-bench-b19-v26"
    assert km["machine_shape"] == "NvidiaRtxPro6000"
    assert "dieniw/ornith-gui-bench-b19" in km["dataset_sources"]
    assert "dieniw/ornith-gui-lora-v26" in km["dataset_sources"]
    assert os.path.isfile(os.path.join(kdir, km["code_file"]))


def test_b19_kernel_loads_flat_dataset(monkeypatch, tmp_path):
    """The Kaggle dataset is flat: tasks.json/checker.py/HTML at its root."""
    flat = tmp_path / "flat"
    flat.mkdir()
    for name in os.listdir(TASKS):
        src = os.path.join(TASKS, name)
        if os.path.isfile(src):
            shutil.copy2(src, flat / name)
    shutil.copy2(os.path.join(B19, "checker.py"), flat / "checker.py")

    spec = importlib.util.spec_from_file_location(
        "b19_kernel_flat_test",
        os.path.join(ROOT, "phase13-gui", "kernel_bench_b19",
                     "bench_b19_kernel.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    files = sorted(os.listdir(flat))

    def fake_walk(top, *args, **kwargs):
        return iter([(str(flat), [], files)])

    monkeypatch.setattr(mod.os, "walk", fake_walk)
    monkeypatch.delitem(sys.modules, "checker", raising=False)
    eps = mod.suite_load()
    assert len(eps) == 48
    assert all(os.path.isfile(ep["path"]) for ep in eps)
