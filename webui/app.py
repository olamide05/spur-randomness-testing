"""Flask front end for bitstream, C, and SystemVerilog STS assessments.

Source modes first produce a validated bitstream and then use the same
NISTRunner / ResultParser / exporter path as uploaded files. One input returns
a dashboard; multiple uploaded files use the parallel comparison path.

Setup and run:
    make install
    make serve
"""

from __future__ import annotations

import multiprocessing
import os
import shutil
import sys
import tempfile
import traceback
import uuid
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, Response, make_response, render_template, request
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
    generate_from_systemverilog,
)

STS_PATH = REPO_ROOT / "sts" / "sts-2.1.2"
UPLOAD_DIR = REPO_ROOT / "webui" / "uploads"
INPUT_UPLOAD_DIR = UPLOAD_DIR / "inputs"
GENERATED_DIR = UPLOAD_DIR / "generated"
REPORT_DIR = UPLOAD_DIR / "reports"
for directory in (UPLOAD_DIR, INPUT_UPLOAD_DIR, GENERATED_DIR, REPORT_DIR):
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
    ) = args
    sys.path.insert(0, str(REPO_ROOT))
    os.chdir(REPO_ROOT)

    from src.automation.nist_runner import NISTRunner as _NISTRunner
    from src.config.sts_config import STSConfig as _STSConfig
    from src.config.sts_config import TestConfig as _TestConfig
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
        return _ResultParser(experiment_dir, generator=generator).parse()


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


def _template_context() -> dict:
    return {
        "c_template": C_TEMPLATE,
        "sv_core_template": SV_CORE_TEMPLATE,
        "sv_tb_template": SV_TB_TEMPLATE,
        "test_labels": TEST_LABELS,
        "param_defaults": PARAM_DEFAULTS,
        "cpu_count": CPU_COUNT,
        "default_cores": max(1, CPU_COUNT - 1),
    }


def _error_page(message: str) -> Response:
    return make_response(render_template("error.html", message=message), 400)


def _parse_run_settings():
    try:
        stream_length = int(request.form.get("stream_length", 100000))
        number_of_streams = int(request.form.get("number_of_streams", 10))
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
            )
        )
    return jobs


def _c_job(stream_length: int, streams: int, tests: dict) -> tuple:
    source = _source_text("c_source", "c_file", C_TEMPLATE, "C")
    generator = _safe_generator_name(
        request.form.get("generator_name", ""), "c_generator"
    )
    output_format = request.form.get("output_format", "ascii")
    artifact_dir = GENERATED_DIR / uuid.uuid4().hex
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "generator.c").write_text(source, encoding="utf-8")
    extension = ".txt" if output_format == "ascii" else ".bin"
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
    output_format = request.form.get("output_format", "ascii")
    artifact_dir = GENERATED_DIR / uuid.uuid4().hex
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "core.sv").write_text(core_source, encoding="utf-8")
    (artifact_dir / "testbench.sv").write_text(
        testbench_source, encoding="utf-8"
    )
    extension = ".txt" if output_format == "ascii" else ".bin"
    generated = generate_from_systemverilog(
        core_source,
        testbench_source,
        top_module,
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
    )


@app.get("/")
def index():
    return render_template("index.html", **_template_context())


@app.post("/run")
def run():
    input_kind = request.form.get("input_kind", "files")
    if input_kind not in {"files", "c", "systemverilog"}:
        return _error_page("Choose a valid assessment input type.")

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
            output_path = report_dir / "dashboard.html"
            export_html(summary, output_path, config=display_config)
            export_json(summary, report_dir / "report.json")
            export_csv(summary, report_dir / "report.csv")
            export_latex(summary, report_dir / "report.tex")
        else:
            workers = min(cores, len(jobs), CPU_COUNT)
            with multiprocessing.Pool(processes=workers) as pool:
                summaries = pool.map(_run_one, jobs)
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
