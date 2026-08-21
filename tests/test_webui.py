from webui.app import app


def test_form_exposes_all_three_assessment_modes():
    response = app.test_client().get("/")
    page = response.get_data(as_text=True)

    assert 'value="files"' in page
    assert 'value="c"' in page
    assert 'value="systemverilog"' in page
    assert "generator OUTPUT_PATH REQUESTED_BITS" in page
    assert "+OUTPUT=&lt;path&gt;" in page
    assert 'id="c-editor"' in page
    assert 'id="sv-core-editor"' in page
    assert "vendor/ace/ace.js" in page


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
    assert client.get("/static/vendor/ace/ace.js").status_code == 200
    assert client.get("/static/vendor/ace/mode-c_cpp.js").status_code == 200
    assert client.get("/static/vendor/ace/mode-verilog.js").status_code == 200


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
