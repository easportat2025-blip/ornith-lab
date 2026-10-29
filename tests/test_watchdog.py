import pytest

import kaggle_watchdog_ci as w


@pytest.fixture(autouse=True)
def _clear_dataset_cache():
    w._DATASET_READY_CACHE.clear()


def test_kernel_status_running(monkeypatch):
    monkeypatch.setattr(
        w, "run", lambda *a, **k: (0, "KernelWorkerStatus.RUNNING", ""))
    assert w.kernel_status("x/y") == "RUNNING"


def test_kernel_status_missing(monkeypatch):
    monkeypatch.setattr(
        w, "run", lambda *a, **k: (1, "", "404 Not Found"))
    assert w.kernel_status("x/y") == "MISSING"


def test_kernel_status_unknown(monkeypatch):
    monkeypatch.setattr(
        w, "run", lambda *a, **k: (1, "", "boom"))
    assert w.kernel_status("x/y") == "UNKNOWN"


def test_kernel_status_private_missing(monkeypatch):
    monkeypatch.setattr(
        w, "run", lambda *a, **k: (
            1, "", "Cannot access kernel 'dieniw/x' "
                   "(Permission 'kernels.get' was denied)."))
    assert w.kernel_status("dieniw/x") == "MISSING"


def test_load_json_default(tmp_path):
    assert w.load_json(str(tmp_path / "missing.json"), {"a": 1}) == {"a": 1}


def test_load_json_reads_utf8(tmp_path):
    p = tmp_path / "q.json"
    p.write_text('{"a": "xin chào"}', encoding="utf-8")
    assert w.load_json(str(p), {})["a"] == "xin chào"


def test_wants_download_defaults():
    assert w.wants_download({"kind": "eval"}, {"kind": "eval"}) is True
    assert w.wants_download({"kind": "train"}, {"kind": "train"}) is False
    assert w.wants_download({"download_results": True},
                            {"kind": "train"}) is True
    assert w.wants_download({"download_results": False},
                            {"kind": "eval"}) is False


def test_default_result_pattern_covers_b18_b19():
    import re
    assert re.search(w.DEFAULT_RESULT_PATTERN, "b18_result.json", re.I)
    assert re.search(w.DEFAULT_RESULT_PATTERN, "b19_result.json", re.I)
    assert re.search(w.DEFAULT_RESULT_PATTERN, "b17_result.json", re.I)
    assert not re.search(w.DEFAULT_RESULT_PATTERN,
                         "adapter_model.safetensors", re.I)


def test_dataset_ready_requires_adapter_file(monkeypatch):
    monkeypatch.setattr(
        w, "run", lambda *a, **k: (
            0, "name size\nadapter_config.json 123\nadapter_model.safetensors 456",
            ""))
    assert w.dataset_ready("dieniw/ornith-gui-lora-v26") is True


def test_dataset_ready_false_while_processing(monkeypatch):
    monkeypatch.setattr(
        w, "run", lambda *a, **k: (1, "", "404 Not Found"))
    assert w.dataset_ready("dieniw/ornith-gui-lora-v26") is False


def test_dataset_ready_retries_429(monkeypatch):
    calls = {"n": 0}
    sleeps = []

    def fake_run(args, timeout=180):
        calls["n"] += 1
        if calls["n"] < 3:
            return 1, "", "429 Too Many Requests"
        return 0, "adapter_model.safetensors 1", ""

    monkeypatch.setattr(w, "run", fake_run)
    monkeypatch.setattr(w.time, "sleep", lambda s: sleeps.append(s))
    assert w.dataset_ready("dieniw/ornith-gui-lora-v26") is True
    assert calls["n"] == 3
    assert sleeps == [15, 30]


def test_dataset_ready_caches_success(monkeypatch):
    calls = {"n": 0}

    def fake_run(args, timeout=180):
        calls["n"] += 1
        return 0, "adapter_config.json 1", ""

    monkeypatch.setattr(w, "run", fake_run)
    assert w.dataset_ready("dieniw/ornith-gui-lora-v26") is True
    assert w.dataset_ready("dieniw/ornith-gui-lora-v26") is True
    assert calls["n"] == 1


def test_target_block_waits_for_after_kernel():
    by_ref = {"dieniw/ornith-gui-sft-v26": {"status": "RUNNING"}}
    item = {"after": "dieniw/ornith-gui-sft-v26"}
    assert w.target_block(item, by_ref).startswith("after:")
    by_ref["dieniw/ornith-gui-sft-v26"]["status"] = "COMPLETE"
    assert w.target_block(item, by_ref) == ""


def test_target_block_waits_for_adapter(monkeypatch):
    monkeypatch.setattr(w, "dataset_ready", lambda ref: False)
    item = {"after": "dieniw/ornith-gui-sft-v26",
            "requires": "dieniw/ornith-gui-lora-v26"}
    by_ref = {"dieniw/ornith-gui-sft-v26": {"status": "COMPLETE"}}
    assert w.target_block(item, by_ref) == "requires:dieniw/ornith-gui-lora-v26"
    monkeypatch.setattr(w, "dataset_ready", lambda ref: True)
    assert w.target_block(item, by_ref) == ""


def test_download_results_uses_safe_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(w, "RESULTS", str(tmp_path))
    calls = {}

    def fake_run(args, timeout=180):
        calls["args"] = args
        return 0, "", ""

    monkeypatch.setattr(w, "run", fake_run)
    rc, _blob, kept = w.download_results("dieniw/ornith-gui-bench-b17-v22")
    assert rc == 0
    assert kept == []
    assert "--file-pattern" in calls["args"]
    assert any("dieniw__ornith-gui-bench-b17-v22" in str(x)
               for x in calls["args"])
