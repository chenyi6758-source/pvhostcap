import json

from pvhostcap.cli import main, run


def test_cli_writes_json_and_html_report(tmp_path):
    payload = run("lv", tmp_path, locational=False, mitigations=False)

    json_path = tmp_path / "lv-hosting-capacity.json"
    html_path = tmp_path / "lv-hosting-capacity.html"
    assert json.loads(json_path.read_text()) == payload
    assert "<html" in html_path.read_text()
    assert "System hosting capacity" in html_path.read_text()


def test_cli_main_accepts_flags(tmp_path):
    assert main(["--feeder", "mv", "--output-dir", str(tmp_path), "--no-locational", "--no-mitigations"]) == 0
    assert (tmp_path / "mv-hosting-capacity.json").exists()
