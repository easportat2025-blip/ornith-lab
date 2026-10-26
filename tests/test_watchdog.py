import kaggle_watchdog_ci as w


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
