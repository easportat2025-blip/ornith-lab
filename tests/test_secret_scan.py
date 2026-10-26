import secret_scan


def test_detects_hf_token(tmp_path):
    token = "hf_" + ("A" * 30)
    p = tmp_path / "leak.txt"
    p.write_text("token = '%s'\n" % token, encoding="utf-8")
    hits = secret_scan.scan_file(str(p))
    assert any(name == "hf_token" for _, name in hits)


def test_detects_github_token(tmp_path):
    token = "ghp_" + ("B" * 36)
    p = tmp_path / "leak.txt"
    p.write_text("token = '%s'\n" % token, encoding="utf-8")
    hits = secret_scan.scan_file(str(p))
    assert any(name == "github_token" for _, name in hits)


def test_placeholder_allowed(tmp_path):
    p = tmp_path / "ok.txt"
    p.write_text("HF_TOKEN = os.environ['HF_TOKEN']  # example\n",
                 encoding="utf-8")
    assert secret_scan.scan_file(str(p)) == []


def test_private_key_pattern(tmp_path):
    marker = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    p = tmp_path / "key.txt"
    p.write_text(marker + "\n", encoding="utf-8")
    hits = secret_scan.scan_file(str(p))
    assert any(name == "private_key" for _, name in hits)
