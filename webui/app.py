"""Flask front end for bitstream, C, and SystemVerilog STS assessments.

Source modes first produce a validated bitstream and then use the same
NISTRunner / ResultParser / exporter path as uploaded files. One input returns
a dashboard; multiple uploaded files use the parallel comparison path.

Setup and run:
    make install
    make serve
"""

from __future__ import annotations

import json
import multiprocessing
import re
import os
import shutil
import sys
import tempfile
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from flask import (
    Flask,
    Response,
    abort,
    after_this_request,
    make_response,
    render_template,
    request,
    send_file,
)
from werkzeug.utils import secure_filename

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)  # The runner/exporters use repository-relative paths.

from src.automation.nist_runner import NISTRunner  # noqa: E402
from src.core import BatchReporter  # noqa: E402
from src.exporters import export_csv, export_html, export_json, export_latex  # noqa: E402
from src.generators.source_runner import (  # noqa: E402
    C_TEMPLATE,
    SV_CORE_TEMPLATE,
    SV_TB_TEMPLATE,
    GenerationError,
    generate_from_c,
    generate_from_cpp,
    generate_from_systemverilog,
)
from src.generators.examples import (  # noqa: E402
    available_library_examples,
    extra_compile_flags,
    library_example_by_id,
    sv_example_by_id,
    SV_EXAMPLES,
)

STS_PATH = REPO_ROOT / "sts" / "sts-2.1.2"
UPLOAD_DIR = REPO_ROOT / "webui" / "uploads"
INPUT_UPLOAD_DIR = UPLOAD_DIR / "inputs"
GENERATED_DIR = UPLOAD_DIR / "generated"
REPORT_DIR = UPLOAD_DIR / "reports"
ACTIVE_DIR = UPLOAD_DIR / "active"
REPORT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
REPORT_DOWNLOADS = {
    "json": ("report.json", "JSON"),
    "csv": ("report.csv", "CSV"),
    "latex": ("report.tex", "LaTeX"),
}
for directory in (
    UPLOAD_DIR, INPUT_UPLOAD_DIR, GENERATED_DIR, REPORT_DIR, ACTIVE_DIR
):
    directory.mkdir(parents=True, exist_ok=True)

CPU_COUNT = multiprocessing.cpu_count()
TEST_LABELS = {
    name: name.replace("_", " ").title() for name in NISTRunner.TEST_ORDER
}
PARAM_DEFAULTS = {
    name: config["block_length"] for name, config in NISTRunner.DEFAULTS.items()
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024


def _link_or_copy(source: Path, destination: Path) -> None:
    """Hard-link immutable STS assets, falling back to a regular copy."""
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _run_one(args):
    """Run one configuration and return its parsed experiment summary.

    Imports are repeated inside the function so multiprocessing remains safe
    on spawn-based platforms as well as Linux/fork.
    """
    (
        file_path,
        generator,
        stream_length,
        number_of_streams,
        tests_cfg,
        input_mode,
        archive_meta,
    ) = args
    sys.path.insert(0, str(REPO_ROOT))
    os.chdir(REPO_ROOT)

    from src.automation.nist_runner import NISTRunner as _NISTRunner
    from src.config.sts_config import STSConfig as _STSConfig
    from src.config.sts_config import TestConfig as _TestConfig
    from src.core.archive_writer import archive_run as _archive_run
    from src.parser.result_parser import ResultParser as _ResultParser

    tests = {
        name: _TestConfig(
            enabled=test["enabled"], parameters=test.get("parameters", {})
        )
        for name, test in (tests_cfg or {}).items()
    }

    with tempfile.TemporaryDirectory(
        prefix="sts_web_worker_", dir=REPO_ROOT
    ) as temp_name:
        sts_path = Path(temp_name) / "sts"
        shutil.copytree(
            STS_PATH,
            sts_path,
            copy_function=_link_or_copy,
            ignore=shutil.ignore_patterns(
                "experiments",
                "finalAnalysisReport.txt",
                "stats.txt",
                "results.txt",
                "freq.txt",
            ),
        )

        config = _STSConfig(
            sts_path=sts_path,
            input_file=Path(file_path),
            generator=generator,
            stream_length=stream_length,
            number_of_streams=number_of_streams,
            input_mode=input_mode,
            tests=tests,
        )
        experiment_dir = _NISTRunner(config).run()
        summary = _ResultParser(
            experiment_dir, generator=generator, number_of_streams=number_of_streams
        ).parse()

        run_config = SimpleNamespace(
            stream_length=stream_length,
            number_of_streams=number_of_streams,
            tests=tests_cfg,
        )
        meta = dict(archive_meta)
        kind = meta.pop("kind")
        _archive_run(
            kind,
            generator=generator,
            experiment_dir=experiment_dir,
            summary=summary,
            run_config=run_config,
            bitstream_path=Path(file_path),
            **meta,
        )
        return summary


def _safe_generator_name(value: str, fallback: str) -> str:
    """Return a short label that is safe in reports and artifact names."""
    cleaned = secure_filename((value or "").strip())
    return (cleaned or fallback)[:100]


def _save_uploaded_input(upload) -> tuple[Path, str]:
    original_name = Path(upload.filename).name
    safe_name = secure_filename(original_name)
    if not safe_name:
        raise GenerationError("An uploaded input has an invalid filename.")
    destination = INPUT_UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
    upload.save(destination)
    label = _safe_generator_name(Path(original_name).stem, "uploaded_input")
    return destination, label


def _source_text(
    editor_field: str, upload_field: str, starter: str, label: str
) -> str:
    """Read editor text, with upload fallback when JavaScript is unavailable."""
    editor_source = request.form.get(editor_field, "")
    upload = request.files.get(upload_field)
    if upload and upload.filename and editor_source.strip() == starter.strip():
        data = upload.stream.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise GenerationError(f"{label} source exceeds the 2 MiB limit.")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GenerationError(f"{label} source must be UTF-8 text.") from exc
    return editor_source


def _library_examples_json() -> str:
    payload = [
        {
            "id": ex.id,
            "title": ex.title,
            "generator_name": ex.generator_name,
            "output_format": ex.output_format,
            "source": ex.source,
        }
        for ex in available_library_examples()
    ]
    return json.dumps(payload).replace("</", "<\\/")


def _template_context() -> dict:
    return {
        "c_template": C_TEMPLATE,
        "sv_core_template": SV_CORE_TEMPLATE,
        "sv_tb_template": SV_TB_TEMPLATE,
        "test_labels": TEST_LABELS,
        "param_defaults": PARAM_DEFAULTS,
        "cpu_count": CPU_COUNT,
        "default_cores": max(1, CPU_COUNT - 1),
        "library_examples": available_library_examples(),
        "library_examples_json": _library_examples_json(),
        "sv_examples": SV_EXAMPLES,
    }


def _example_prefill(example_id: str) -> dict:
    """Fields to override in the main form's context when `?example=<id>` is
    given -- looked up server-side, never trusting the id beyond a lookup."""
    if not example_id:
        return {}

    library = library_example_by_id(example_id)
    if library is not None:
        return {
            "selected_mode": "c",
            "c_template": library.source,
            "selected_language": "cpp",
            "selected_library": library.id,
            "selected_generator_name": library.generator_name,
            "selected_output_format": library.output_format,
        }

    sv_example = sv_example_by_id(example_id)
    if sv_example is not None:
        return {
            "selected_mode": "systemverilog",
            "sv_core_template": sv_example.core_source,
            "selected_generator_name": sv_example.generator_name,
        }

    return {}


def _error_page(message: str) -> Response:
    return make_response(render_template("error.html", message=message), 400)


def _parse_run_settings():
    try:
        stream_length = int(request.form.get("stream_length", 1000000))
        number_of_streams = int(request.form.get("number_of_streams", 100))
        cores = max(1, int(request.form.get("cores", 1)))
    except ValueError as exc:
        raise GenerationError(
            "Stream length, number of streams, and cores must be whole numbers."
        ) from exc
    if stream_length < 1 or number_of_streams < 1:
        raise GenerationError(
            "Stream length and number of streams must both be at least 1."
        )
    return stream_length, number_of_streams, cores


def _parse_tests() -> dict:
    tests = {}
    for name in NISTRunner.TEST_ORDER:
        enabled = request.form.get(f"enable_{name}") == "on"
        parameters = {}
        if name in NISTRunner.DEFAULTS:
            default_length = NISTRunner.DEFAULTS[name]["block_length"]
            raw = request.form.get(f"param_{name}", "").strip()
            try:
                parameters["block_length"] = int(raw) if raw else default_length
            except ValueError as exc:
                raise GenerationError(
                    f"Block length for {TEST_LABELS[name]} must be a whole number."
                ) from exc
            if parameters["block_length"] < 1:
                raise GenerationError(
                    f"Block length for {TEST_LABELS[name]} must be at least 1."
                )
            if (
                name == "non_overlapping_template"
                and not 2 <= parameters["block_length"] <= 21
            ):
                raise GenerationError(
                    "Non Overlapping Template block length must be between 2 "
                    "and 21 (the template files bundled with STS)."
                )
        tests[name] = {"enabled": enabled, "parameters": parameters}

    if not any(test["enabled"] for test in tests.values()):
        raise GenerationError("At least one test needs to stay enabled.")
    return tests


def _file_jobs(stream_length: int, streams: int, tests: dict) -> list:
    uploads = [item for item in request.files.getlist("input_files") if item.filename]
    if not uploads:
        raise GenerationError("Choose at least one input file.")
    jobs = []
    for upload in uploads:
        destination, generator = _save_uploaded_input(upload)
        jobs.append(
            (
                str(destination),
                generator,
                stream_length,
                streams,
                tests,
                None,
                {"kind": "upload", "original_filename": Path(upload.filename).name},
            )
        )
    return jobs


def _c_job(stream_length: int, streams: int, tests: dict) -> tuple:
    source = _source_text("c_source", "c_file", C_TEMPLATE, "C")
    generator = _safe_generator_name(
        request.form.get("generator_name", ""), "c_generator"
    )
    output_format = request.form.get("output_format", "binary")
    language = request.form.get("language", "c")
    library_id = request.form.get("library", "none")

    library = None
    if library_id != "none":
        library = library_example_by_id(library_id)
        if library is None:
            raise GenerationError(f"Library '{library_id}' is not available on this host.")
        language = "cpp"

    artifact_dir = GENERATED_DIR / uuid.uuid4().hex
    artifact_dir.mkdir(parents=True)
    extension = ".txt" if output_format == "ascii" else ".bin"

    if language == "cpp":
        source_path = artifact_dir / "generator.cpp"
        source_path.write_text(source, encoding="utf-8")
        extra_flags = extra_compile_flags(library) if library else ()
        generated = generate_from_cpp(
            source,
            artifact_dir / f"bitstream{extension}",
            stream_length * streams,
            output_format=output_format,
            extra_flags=extra_flags,
        )
    else:
        source_path = artifact_dir / "generator.c"
        source_path.write_text(source, encoding="utf-8")
        generated = generate_from_c(
            source,
            artifact_dir / f"bitstream{extension}",
            stream_length * streams,
            output_format=output_format,
        )

    return (
        str(generated.path),
        generator,
        stream_length,
        streams,
        tests,
        generated.input_mode,
        {"kind": "c", "c_source_path": source_path},
    )


def _systemverilog_job(stream_length: int, streams: int, tests: dict) -> tuple:
    core_source = _source_text(
        "sv_core_source", "sv_core_file", SV_CORE_TEMPLATE, "SystemVerilog core"
    )
    testbench_source = _source_text(
        "sv_tb_source",
        "sv_tb_file",
        SV_TB_TEMPLATE,
        "SystemVerilog testbench",
    )
    generator = _safe_generator_name(
        request.form.get("generator_name", ""), "sv_generator"
    )
    top_module = request.form.get("top_module", "tb").strip()
    output_format = request.form.get("output_format", "binary")
    artifact_dir = GENERATED_DIR / uuid.uuid4().hex
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "core.sv").write_text(core_source, encoding="utf-8")
    (artifact_dir / "testbench.sv").write_text(
        testbench_source, encoding="utf-8"
    )
    extension = ".txt" if output_format == "ascii" else ".bin"
    binary_path = artifact_dir / "testbench_binary"
    generated = generate_from_systemverilog(
        core_source,
        testbench_source,
        top_module,
        artifact_dir / f"bitstream{extension}",
        stream_length * streams,
        output_format=output_format,
        binary_destination=binary_path,
    )
    return (
        str(generated.path),
        generator,
        stream_length,
        streams,
        tests,
        generated.input_mode,
        {
            "kind": "sv",
            "sv_core_path": artifact_dir / "core.sv",
            "sv_binary_path": binary_path,
        },
    )


@app.get("/")
def index():
    context = _template_context()
    context.update(_example_prefill(request.args.get("example", "")))
    return render_template("index.html", **context)


@app.get("/examples")
def examples():
    return render_template("examples.html", **_template_context())


def _write_active_run(record: dict) -> None:
    """Atomically publish one active assessment for concurrent History reads."""
    record["updated_at"] = time.time()
    destination = ACTIVE_DIR / f"{record['id']}.json"
    temporary = ACTIVE_DIR / f".{record['id']}.tmp"
    temporary.write_text(json.dumps(record))
    os.replace(temporary, destination)


def _remove_active_run(run_id: str) -> None:
    try:
        (ACTIVE_DIR / f"{run_id}.json").unlink()
    except FileNotFoundError:
        pass


def _active_runs() -> list[dict]:
    """Read live assessments; ignore malformed or abandoned tracker files."""
    now = time.time()
    entries = []
    for path in ACTIVE_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text())
            started_at = float(record["started_at"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if now - float(record.get("updated_at", started_at)) > 12 * 60 * 60:
            continue
        record["started"] = datetime.fromtimestamp(started_at)
        record["elapsed_seconds"] = max(0, int(now - started_at))
        for stage in record.get("stages", []):
            stage_started = stage.get("started_at")
            stage_finished = stage.get("finished_at")
            if stage_started is None:
                stage["state"] = "waiting"
                stage["elapsed_seconds"] = 0
            else:
                stage_started = float(stage_started)
                stage["state"] = "complete" if stage_finished is not None else "running"
                stage_end = float(stage_finished) if stage_finished is not None else now
                stage["elapsed_seconds"] = max(0, int(stage_end - stage_started))
        entries.append(record)
    return sorted(entries, key=lambda entry: entry["started_at"])


def _history_entries() -> list[dict]:
    """Return completed WebUI reports newest first, tolerating partial runs."""
    entries = []
    for run_dir in REPORT_DIR.iterdir():
        if not run_dir.is_dir() or not REPORT_ID_RE.fullmatch(run_dir.name):
            continue

        html_path = next(
            (
                candidate
                for candidate in (
                    run_dir / "dashboard.html",
                    run_dir / "comparison.html",
                )
                if candidate.is_file()
            ),
            None,
        )
        if html_path is None:
            continue

        metadata = {}
        json_path = run_dir / "report.json"
        if json_path.is_file():
            try:
                metadata = json.loads(json_path.read_text())
            except (OSError, ValueError):
                metadata = {}

        tests = metadata.get("tests", [])
        completed_tests = [
            test for test in tests if test.get("status") != "skipped"
        ]
        passed_tests = sum(
            test.get("status") == "pass" for test in completed_tests
        )
        modified = html_path.stat().st_mtime
        status = str(
            metadata.get("overall_status")
            or ("comparison" if html_path.name == "comparison.html" else "complete")
        ).lower()
        if status not in {"pass", "fail", "comparison", "complete"}:
            status = "complete"
        entries.append(
            {
                "id": run_dir.name,
                "generator": metadata.get("generator") or "Batch comparison",
                "status": status,
                "created": datetime.fromtimestamp(modified),
                "passed_tests": passed_tests,
                "completed_tests": len(completed_tests),
                "downloads": [
                    {"key": key, "label": label}
                    for key, (filename, label) in REPORT_DOWNLOADS.items()
                    if (run_dir / filename).is_file()
                ],
            }
        )

    return sorted(entries, key=lambda entry: entry["created"], reverse=True)


@app.get("/history")
def history():
    return render_template(
        "history.html",
        active_runs=_active_runs(),
        reports=_history_entries(),
    )


def _report_artifact_path(run_id: str, artifact: str) -> Path:
    if not REPORT_ID_RE.fullmatch(run_id):
        abort(404)

    run_dir = REPORT_DIR / run_id
    if artifact == "html":
        for filename in ("dashboard.html", "comparison.html"):
            path = run_dir / filename
            if path.is_file():
                return path
        abort(404)

    download = REPORT_DOWNLOADS.get(artifact)
    if download is None:
        abort(404)
    path = run_dir / download[0]
    if not path.is_file():
        abort(404)
    return path


@app.get("/history/<run_id>/<artifact>")
def report_artifact(run_id: str, artifact: str):
    path = _report_artifact_path(run_id, artifact)
    return send_file(
        path,
        as_attachment=artifact != "html",
        download_name=path.name,
    )


@app.post("/run")
def run():
    input_kind = request.form.get("input_kind", "files")
    if input_kind not in {"files", "c", "systemverilog"}:
        return _error_page("Choose a valid assessment input type.")

    if input_kind == "files":
        initial_generators = [
            Path(upload.filename).stem
            for upload in request.files.getlist("input_files")
            if upload.filename
        ]
    else:
        initial_generators = [
            request.form.get("generator_name")
            or ("C generator" if input_kind == "c" else "SystemVerilog generator")
        ]

    started_at = time.time()
    execution_labels = {
        "files": "Input preparation",
        "c": "C/C++ execution",
        "systemverilog": "SystemVerilog execution",
    }
    preparation_phases = {
        "files": "Preparing bitstreams",
        "c": "Compiling and running C/C++",
        "systemverilog": "Compiling and running SystemVerilog",
    }
    active_run = {
        "id": uuid.uuid4().hex,
        "input_kind": input_kind,
        "phase": preparation_phases[input_kind],
        "started_at": started_at,
        "generators": initial_generators,
        "instance_count": max(1, len(initial_generators)),
        "stages": [
            {
                "key": "generator",
                "label": execution_labels[input_kind],
                "started_at": started_at,
                "finished_at": None,
            },
            {
                "key": "nist",
                "label": "NIST STS",
                "started_at": None,
                "finished_at": None,
            },
        ],
    }
    _write_active_run(active_run)

    @after_this_request
    def clear_active_run(response):
        _remove_active_run(active_run["id"])
        return response

    try:
        stream_length, streams, cores = _parse_run_settings()
        tests = _parse_tests()
        if input_kind == "files":
            jobs = _file_jobs(stream_length, streams, tests)
        elif input_kind == "c":
            jobs = [_c_job(stream_length, streams, tests)]
        else:
            jobs = [_systemverilog_job(stream_length, streams, tests)]
    except (GenerationError, OSError) as exc:
        return _error_page(f"Input preparation failed: {exc}")

    nist_started_at = time.time()
    active_run["stages"][0]["finished_at"] = nist_started_at
    active_run["stages"][1]["started_at"] = nist_started_at
    active_run.update(
        {
            "phase": "Running NIST STS",
            "generators": [job[1] for job in jobs],
            "instance_count": len(jobs),
        }
    )
    _write_active_run(active_run)

    display_config = SimpleNamespace(
        stream_length=stream_length,
        number_of_streams=streams,
        tests=tests,
    )
    report_dir = REPORT_DIR / uuid.uuid4().hex
    report_dir.mkdir(parents=True)
    try:
        if len(jobs) == 1:
            summary = _run_one(jobs[0])
            active_run["stages"][1]["finished_at"] = time.time()
            active_run["phase"] = "Exporting report"
            _write_active_run(active_run)
            output_path = report_dir / "dashboard.html"
            export_html(summary, output_path, config=display_config)
            export_json(summary, report_dir / "report.json")
            export_csv(summary, report_dir / "report.csv")
            export_latex(summary, report_dir / "report.tex")
        else:
            workers = min(cores, len(jobs), CPU_COUNT)
            with multiprocessing.Pool(processes=workers) as pool:
                summaries = pool.map(_run_one, jobs)
            active_run["stages"][1]["finished_at"] = time.time()
            active_run["phase"] = "Exporting comparison"
            _write_active_run(active_run)
            output_path = report_dir / "comparison.html"
            BatchReporter(summaries, config=display_config).generate_html(output_path)
    except Exception as exc:
        traceback.print_exc()
        return _error_page(f"Run failed: {exc}")

    return Response(output_path.read_text(), mimetype="text/html")


if __name__ == "__main__":
    print(f"Spur UI: STS suite at {STS_PATH}")
    print(f"Spur UI: up to {CPU_COUNT} CPU cores available for batch runs")
    host = os.environ.get("SPUR_HOST", "127.0.0.1")
    port = int(os.environ.get("SPUR_PORT", "5000"))
    app.run(debug=False, host=host, port=port)
