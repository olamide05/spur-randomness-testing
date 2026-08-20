"""
Spur web UI -- a minimal Flask front end over the existing NISTRunner /
ResultParser / exporter pipeline. One generator = a normal run and you get
the dashboard. More than one = a parallel batch run (uses the "cores"
field) and you get the comparison view instead. Both reuse the exact same
backend code the CLI (run.py) uses -- this is just a form in front of it.

The "Advanced" section exposes exactly what NISTRunner supports: enabling/
disabling any of the 15 tests, and overriding block length on the 6 tests
that take one. Whatever was actually used is shown back on the results
page in a "Run configuration" panel, collapsed by default.

Setup:
    pip install flask
    python webui/app.py
    open http://127.0.0.1:5000

Assumes the fixed result_parser.py / nist_runner.py / exporters / batch_reporter.py
are already in place.
"""
import html
import multiprocessing
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, request, Response

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)  # NISTRunner + exporters use paths relative to the repo root

from src.automation.nist_runner import NISTRunner  # noqa: E402  (TEST_ORDER / DEFAULTS to build + parse the form)
from src.exporters import export_html, export_json, export_csv, export_latex  # noqa: E402
from src.core import BatchReporter  # noqa: E402

STS_PATH = REPO_ROOT / "sts" / "sts-2.1.2"
UPLOAD_DIR = REPO_ROOT / "webui" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CPU_COUNT = multiprocessing.cpu_count()

TEST_LABELS = {name: name.replace("_", " ").title() for name in NISTRunner.TEST_ORDER}
PARAM_TESTS = list(NISTRunner.DEFAULTS.keys())  # the 6 tests that take a block-length parameter

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB


def _link_or_copy(source, destination):
    """Hard-link immutable STS assets, falling back to a regular copy."""
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _run_one(args):
    """Run one generator's config end-to-end and return its ExperimentSummary.
    Self-contained (re-imports inside the function) so it's safe to hand to
    a multiprocessing worker on spawn-based platforms (macOS/Windows), not
    just fork-based ones (Linux)."""
    file_path, generator, stream_length, number_of_streams, tests_cfg, isolated = args
    sys.path.insert(0, str(REPO_ROOT))
    os.chdir(REPO_ROOT)
    from src.config.sts_config import STSConfig as _STSConfig, TestConfig as _TestConfig
    from src.automation.nist_runner import NISTRunner as _NISTRunner
    from src.parser.result_parser import ResultParser as _ResultParser

    tests = {
        name: _TestConfig(enabled=t["enabled"], parameters=t.get("parameters", {}))
        for name, t in (tests_cfg or {}).items()
    }

    temp_dir = None
    sts_path = STS_PATH
    if isolated:
        temp_dir = tempfile.TemporaryDirectory(prefix="sts_web_worker_", dir=REPO_ROOT)
        sts_path = Path(temp_dir.name) / "sts"
        shutil.copytree(
            STS_PATH,
            sts_path,
            copy_function=_link_or_copy,
            ignore=shutil.ignore_patterns("experiments", "finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"),
        )

    config = _STSConfig(
        sts_path=sts_path,
        input_file=Path(file_path),
        generator=generator,
        stream_length=stream_length,
        number_of_streams=number_of_streams,
        tests=tests,
    )
    try:
        exp_dir = _NISTRunner(config).run()
        return _ResultParser(exp_dir, generator=generator).parse()
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def _test_checkboxes() -> str:
    return "".join(
        f'<label class="chk"><input type="checkbox" name="enable_{name}" checked> {label}</label>'
        for name, label in TEST_LABELS.items()
    )


def _param_inputs() -> str:
    items = []
    for name in PARAM_TESTS:
        default = NISTRunner.DEFAULTS[name]["block_length"]
        items.append(f"""<div>
      <label for="param_{name}">{TEST_LABELS[name]} &mdash; block length</label>
      <input type="number" id="param_{name}" name="param_{name}" value="{default}" min="1">
    </div>""")
    return "".join(items)


PAGE_STYLE = """
  :root {
    --paper: #F6F7F5; --ink: #161D1A; --ink-soft: #4B564F; --line: #DCE1DC;
    --pass: #1F6E4A; --pass-bg: #E7F2EC; --fail: #A6362B; --fail-bg: #F3E5E2;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    padding: 32px 16px 64px;
  }
  .wrap { max-width: 640px; margin: 0 auto; }
  .eyebrow { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft); margin: 0 0 6px; }
  h1 { font-size: 28px; margin: 0 0 20px; font-weight: 700; letter-spacing: -0.01em;
       border-bottom: 2px solid var(--ink); padding-bottom: 20px; }
  label { display: block; font-size: 12px; color: var(--ink-soft); margin: 18px 0 6px; }
  input[type=file], input[type=number], input[type=text] {
    width: 100%; padding: 9px 10px; font: inherit; font-size: 13px; color: var(--ink);
    background: white; border: 1px solid var(--line); border-radius: 3px;
  }
  .row { display: flex; gap: 14px; }
  .row > div { flex: 1; }
  .hint { font-size: 11px; color: var(--ink-soft); margin-top: 6px; line-height: 1.5; }
  button {
    margin-top: 26px; width: 100%; font: inherit; font-weight: 700; letter-spacing: 0.06em;
    font-size: 14px; padding: 13px; background: var(--ink); color: var(--paper);
    border: 2px solid var(--ink); border-radius: 3px; cursor: pointer;
  }
  button:hover { background: var(--paper); color: var(--ink); }
  .error { background: var(--fail-bg); color: var(--fail); border: 1px solid var(--fail);
            padding: 12px 14px; border-radius: 3px; margin-bottom: 20px; font-size: 13px; }
  a { color: var(--ink); }
  details.adv { border: 1px solid var(--line); border-radius: 3px; margin: 22px 0 4px; background: white; }
  details.adv summary { cursor: pointer; padding: 12px 14px; font-weight: 700; font-size: 13px; color: var(--ink); }
  details.adv[open] summary { border-bottom: 1px solid var(--line); }
  .adv-label { font-size: 11px; color: var(--ink-soft); margin: 14px 14px 6px; text-transform: uppercase; letter-spacing: 0.06em; }
  .test-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; padding: 0 14px 14px; }
  .chk { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ink); margin: 0; }
  .chk input { width: auto; margin: 0; }
  .param-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 14px; padding: 0 14px 16px; }
  .param-grid label { margin: 10px 0 4px; }
"""

FORM_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spur &mdash; STS Test Runner</title>
<style>{PAGE_STYLE}</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">NIST SP 800-22 &middot; Spur</p>
  <h1>STS Test Runner</h1>
  <form action="/run" method="post" enctype="multipart/form-data">
    <label for="input_files">Input file(s)</label>
    <input type="file" id="input_files" name="input_files" multiple required>
    <p class="hint">One file &rarr; single dashboard. Multiple files &rarr; parallel batch run + comparison view. Each file's name (minus extension) becomes its generator label. The same test selection and parameters below apply to every file.</p>
    <p id="file-count" class="hint" aria-live="polite">No files selected.</p>

    <div class="row">
      <div>
        <label for="stream_length">Stream length (bits)</label>
        <input type="number" id="stream_length" name="stream_length" value="100000" min="100" required>
      </div>
      <div>
        <label for="number_of_streams">Number of streams</label>
        <input type="number" id="number_of_streams" name="number_of_streams" value="10" min="1" required>
      </div>
    </div>

    <label for="cores">CPU cores to use for batch runs</label>
    <input type="number" id="cores" name="cores" value="{max(1, CPU_COUNT - 1)}" min="1" max="{CPU_COUNT}">
    <p class="hint">This machine has {CPU_COUNT} CPU core{'s' if CPU_COUNT != 1 else ''}. Only matters with more than one input file &mdash; each generator's run is CPU-bound (it shells out to the real <code>assess</code> binary), so more cores means more of them run at once instead of queueing. A single file always just uses one.</p>

    <details class="adv">
      <summary>Advanced: custom test parameters</summary>
      <p class="hint" style="padding:0 14px; margin-top:12px;">Unchecked tests are skipped entirely. Block lengths only apply to the six tests that use them &mdash; values shown are STS's own defaults.</p>
      <p class="adv-label">Tests to run</p>
      <div class="test-grid">{_test_checkboxes()}</div>
      <p class="adv-label">Block lengths</p>
      <div class="param-grid">{_param_inputs()}</div>
    </details>

    <button type="submit">Run</button>
  </form>
</div>
<script>
  const inputFiles = document.getElementById("input_files");
  const fileCount = document.getElementById("file-count");
  inputFiles.addEventListener("change", () => {{
    const count = inputFiles.files.length;
    fileCount.textContent = count === 1
      ? "1 file selected: a single dashboard will be generated."
      : count + " files selected: the batch report will show " + count + " file results.";
  }});
</script>
</body>
</html>"""


def _error_page(message: str) -> Response:
    body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Spur &mdash; Error</title><style>{PAGE_STYLE}</style></head>
<body><div class="wrap">
  <p class="eyebrow">NIST SP 800-22 &middot; Spur</p>
  <h1>STS Test Runner</h1>
  <div class="error">{html.escape(message)}</div>
  <p><a href="/">&larr; Back</a></p>
</div></body></html>"""
    return Response(body, status=400, mimetype="text/html")


@app.route("/", methods=["GET"])
def index():
    return FORM_PAGE


@app.route("/run", methods=["POST"])
def run():
    files = [f for f in request.files.getlist("input_files") if f.filename]
    if not files:
        return _error_page("Choose at least one input file.")

    try:
        stream_length = int(request.form.get("stream_length", 100000))
        number_of_streams = int(request.form.get("number_of_streams", 10))
        cores = max(1, int(request.form.get("cores", 1)))
    except ValueError:
        return _error_page("Stream length, number of streams, and cores must be whole numbers.")

    if stream_length < 1 or number_of_streams < 1:
        return _error_page("Stream length and number of streams must both be at least 1.")

    tests_cfg = {}
    for name in NISTRunner.TEST_ORDER:
        enabled = request.form.get(f"enable_{name}") == "on"
        params = {}
        if name in NISTRunner.DEFAULTS:
            default_len = NISTRunner.DEFAULTS[name]["block_length"]
            raw = request.form.get(f"param_{name}", "").strip()
            try:
                params["block_length"] = int(raw) if raw else default_len
            except ValueError:
                return _error_page(f"Block length for {TEST_LABELS[name]} must be a whole number.")
            if params["block_length"] < 1:
                return _error_page(f"Block length for {TEST_LABELS[name]} must be at least 1.")
            if name == "non_overlapping_template" and not 2 <= params["block_length"] <= 21:
                return _error_page("Non Overlapping Template block length must be between 2 and 21 (the template files bundled with STS).")
        tests_cfg[name] = {"enabled": enabled, "parameters": params}

    if not any(t["enabled"] for t in tests_cfg.values()):
        return _error_page("At least one test needs to stay enabled.")

    jobs = []
    for f in files:
        dest = UPLOAD_DIR / f.filename
        f.save(dest)
        generator = Path(f.filename).stem
        jobs.append((str(dest), generator, stream_length, number_of_streams, tests_cfg, len(files) > 1))

    # What actually produced this run, for the "Run configuration" panel on
    # the results page. A plain object, not a real STSConfig -- the
    # exporters only ever read .stream_length / .number_of_streams / .tests
    # off it (see html_exporter._config_panel), so nothing else is needed.
    display_config = SimpleNamespace(
        stream_length=stream_length, number_of_streams=number_of_streams, tests=tests_cfg,
    )

    try:
        if len(jobs) == 1:
            summary = _run_one(jobs[0])
            out_path = UPLOAD_DIR / "last_dashboard.html"
            export_html(summary, out_path, config=display_config)
            export_json(summary, UPLOAD_DIR / "last_report.json")
            export_csv(summary, UPLOAD_DIR / "last_report.csv")
            export_latex(summary, UPLOAD_DIR / "last_report.tex")
        else:
            workers = min(cores, len(jobs), CPU_COUNT)
            with multiprocessing.Pool(processes=workers) as pool:
                summaries = pool.map(_run_one, jobs)
            out_path = UPLOAD_DIR / "last_comparison.html"
            BatchReporter(summaries, config=display_config).generate_html(out_path)
    except Exception as e:
        traceback.print_exc()
        return _error_page(f"Run failed: {e}")

    return Response(out_path.read_text(), mimetype="text/html")


if __name__ == "__main__":
    print(f"Spur UI: STS suite at {STS_PATH}")
    print(f"Spur UI: up to {CPU_COUNT} CPU cores available for batch runs")
    app.run(debug=False, host="127.0.0.1", port=5000)