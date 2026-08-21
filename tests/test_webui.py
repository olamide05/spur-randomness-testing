from webui.app import app


def test_form_exposes_split_pane_and_all_assessment_modes():
    response = app.test_client().get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="runner-shell"' in page
    assert 'class="controls-panel"' in page
    assert 'class="editor-panel"' in page
    assert 'href="/history"' in page
    assert 'value="files"' in page
    assert 'value="c"' in page
    assert 'value="systemverilog"' in page
    assert "generator OUTPUT_PATH REQUESTED_BITS" in page
    assert "+OUTPUT=&lt;path&gt;" in page
    assert 'name="stream_length" value="1000000"' in page
    assert 'name="number_of_streams" value="100"' in page
    assert 'value="binary" selected' in page
    assert "12.5 MB packed binary" in page


def test_runner_uses_monaco_and_hidden_source_fields():
    page = app.test_client().get("/").get_data(as_text=True)

    assert 'id="source-editor"' in page
    assert 'type="hidden" id="c_source"' in page
    assert 'type="hidden" id="sv_core_source"' in page
    assert 'type="hidden" id="sv_tb_source"' in page
    assert "<textarea" not in page
    assert "vendor/monaco/vs/loader.js" in page
    assert "vendor/ace" not in page


def test_monaco_configuration_and_submission_sync_are_present():
    client = app.test_client()
    script = client.get("/static/app.js").get_data(as_text=True)

    assert 'theme: "vs-dark"' in script
    assert "minimap: { enabled: true }" in script
    assert "automaticLayout: true" in script
    assert 'register({ id: "systemverilog" })' in script
    assert "form.addEventListener(\"submit\"" in script
    assert "model.getValue()" in script
    assert "setModelLanguage" in script


def test_index_is_available():
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"C generator" in response.data
    assert b"SystemVerilog" in response.data


def test_editor_assets_are_served_locally():
    client = app.test_client()

    assert client.get("/static/app.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/history.js").status_code == 200
    assert client.get("/static/vendor/monaco/LICENSE").status_code == 200
    assert client.get("/static/vendor/monaco/vs/loader.js").status_code == 200
    assert client.get("/static/vendor/monaco/vs/editor/editor.main.js").status_code == 200
    assert (
        client.get(
            "/static/vendor/monaco/vs/base/worker/workerMain.js"
        ).status_code
        == 200
    )


def test_run_requires_a_file_in_files_mode():
    client = app.test_client()
    response = client.post(
        "/run",
        data={
            "input_kind": "files",
            "stream_length": "1000",
            "number_of_streams": "1",
            "cores": "1",
            "enable_frequency": "on",
        },
    )

    assert response.status_code == 400
    assert b"Choose at least one input file" in response.data


def test_history_lists_saved_reports_and_serves_artifacts(tmp_path, monkeypatch):
    from importlib import import_module
    import json

    webui_app = import_module("webui.app")
    run_id = "a" * 32
    report_dir = tmp_path / run_id
    report_dir.mkdir()
    (report_dir / "dashboard.html").write_text("<h1>Saved dashboard</h1>")
    (report_dir / "report.csv").write_text("test,status\nfrequency,pass\n")
    (report_dir / "report.json").write_text(
        json.dumps(
            {
                "generator": "history_rng",
                "overall_status": "pass",
                "tests": [
                    {"name": "frequency", "status": "pass"},
                    {"name": "runs", "status": "fail"},
                    {"name": "universal", "status": "skipped"},
                ],
            }
        )
    )
    monkeypatch.setattr(webui_app, "REPORT_DIR", tmp_path)

    client = app.test_client()
    page = client.get("/history")

    assert page.status_code == 200
    assert b"history_rng" in page.data
    assert b"No assessments are running right now" in page.data
    assert b'http-equiv="refresh"' not in page.data
    assert b"1/2 completed tests passed" in page.data
    assert f"/history/{run_id}/html".encode() in page.data
    assert client.get(f"/history/{run_id}/html").data == b"<h1>Saved dashboard</h1>"

    csv_response = client.get(f"/history/{run_id}/csv")
    assert csv_response.status_code == 200
    assert "attachment" in csv_response.headers["Content-Disposition"]


def test_history_report_routes_reject_unknown_paths(tmp_path, monkeypatch):
    from importlib import import_module

    webui_app = import_module("webui.app")
    monkeypatch.setattr(webui_app, "REPORT_DIR", tmp_path)
    client = app.test_client()

    assert client.get("/history/not-a-report/html").status_code == 404
    assert client.get(f"/history/{'a' * 32}/unknown").status_code == 404


def test_history_shows_active_assessment(tmp_path, monkeypatch):
    from importlib import import_module
    import json
    import time

    webui_app = import_module("webui.app")
    report_dir = tmp_path / "reports"
    active_dir = tmp_path / "active"
    report_dir.mkdir()
    active_dir.mkdir()
    run_id = "b" * 32
    (active_dir / f"{run_id}.json").write_text(
        json.dumps(
            {
                "id": run_id,
                "input_kind": "c",
                "phase": "Running NIST STS",
                "started_at": time.time() - 65,
                "updated_at": time.time(),
                "generators": ["pcg32", "splitmix64"],
                "instance_count": 2,
                "stages": [
                    {
                        "key": "generator",
                        "label": "C/C++ execution",
                        "started_at": time.time() - 65,
                        "finished_at": time.time() - 40,
                    },
                    {
                        "key": "nist",
                        "label": "NIST STS",
                        "started_at": time.time() - 40,
                        "finished_at": None,
                    },
                ],
            }
        )
    )
    monkeypatch.setattr(webui_app, "REPORT_DIR", report_dir)
    monkeypatch.setattr(webui_app, "ACTIVE_DIR", active_dir)

    page = app.test_client().get("/history")

    assert page.status_code == 200
    assert b"Currently running" in page.data
    assert b"pcg32, splitmix64" in page.data
    assert b"Running NIST STS" in page.data
    assert b"2 instances" in page.data
    assert b"Total execution" in page.data
    assert b"C/C++ execution" in page.data
    assert b"NIST STS" in page.data
    assert b"stage-complete" in page.data
    assert b"stage-running" in page.data
    assert b"active-progress" in page.data
    assert b"processing-spinner" not in page.data
    assert b'http-equiv="refresh"' in page.data

    timer_script = app.test_client().get("/static/history.js")
    assert timer_script.status_code == 200
    assert b"setInterval(updateClocks, 1000)" in timer_script.data
