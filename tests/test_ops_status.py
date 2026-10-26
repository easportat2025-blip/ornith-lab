import ops_status


def test_build_snapshot_shape():
    snap = ops_status.build_snapshot()
    assert "utc" in snap
    assert "git" in snap
    assert "queue" in snap
    assert "secrets" in snap
    assert all(isinstance(v, bool) for v in snap["secrets"].values())


def test_render_is_secret_free():
    snap = ops_status.build_snapshot()
    text = ops_status.render(snap)
    assert "Ornith Lab ops status" in text
    assert "Secrets:" in text
    assert "missing=" in text
