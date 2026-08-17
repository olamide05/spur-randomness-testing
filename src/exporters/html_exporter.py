"""HTML dashboard exporter."""
import html
from pathlib import Path

_PASS = "#1F6E4A"
_PASS_BG = "#E7F2EC"
_FAIL = "#A6362B"
_FAIL_BG = "#F3E5E2"
_SKIP = "#8B948E"
_SKIP_BG = "#EEF0EE"
_INK = "#161D1A"
_INK_SOFT = "#4B564F"
_PAPER = "#F6F7F5"
_LINE = "#DCE1DC"

_CHIP_LIMIT = 24  # above this, switch from discrete chips to a proportion bar


def _display_name(name: str) -> str:
    return name.replace("_", " ").title()


def _bit_bar(passed: int, total: int) -> str:
    """Visualize passed/total: discrete chips for small N, a single
    proportion bar once N is too large to show individually (e.g.
    non_overlapping_template pools 148 sub-templates x N streams)."""
    if total <= 0:
        return '<div class="bar bar-empty">not run</div>'

    failed = total - passed
    if total <= _CHIP_LIMIT:
        chips = "<span class=\"chip chip-pass\"></span>" * passed
        chips += "<span class=\"chip chip-fail\"></span>" * failed
        return f'<div class="bar">{chips}</div>'

    pct = passed / total * 100
    return (
        '<div class="bar bar-solid">'
        f'<div class="bar-pass" style="width:{pct:.2f}%"></div>'
        f'<div class="bar-fail" style="width:{100 - pct:.2f}%"></div>'
        "</div>"
    )


def _config_panel(config) -> str:
    """Render the optional run configuration supplied by the web UI."""
    if config is None:
        return ""

    enabled_tests = []
    for name, test_config in getattr(config, "tests", {}).items():
        enabled = (
            test_config.get("enabled", True)
            if isinstance(test_config, dict)
            else getattr(test_config, "enabled", True)
        )
        if enabled:
            enabled_tests.append(name.replace("_", " ").title())

    stream_length = getattr(config, "stream_length", "—")
    number_of_streams = getattr(config, "number_of_streams", "—")
    tests = ", ".join(enabled_tests) if enabled_tests else "None"
    return f"""<details class=\"config\">
  <summary>Run configuration</summary>
  <dl>
    <dt>Stream length</dt><dd>{html.escape(str(stream_length))} bits</dd>
    <dt>Streams</dt><dd>{html.escape(str(number_of_streams))}</dd>
    <dt>Enabled tests</dt><dd>{html.escape(tests)}</dd>
  </dl>
</details>"""


def export_html(summary, output_path: Path = None, config=None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "dashboard.html"

    gen = html.escape(str(summary.generator) or "unlabelled")
    exp_name = html.escape(summary.experiment_directory.name)
    overall = summary.overall_status
    overall_label = {"pass": "PASS", "fail": "FAIL"}.get(overall, "UNKNOWN")

    evaluated = [t for t in summary.tests if t.total > 0]
    passed_n = sum(1 for t in evaluated if t.status == "pass")

    # Failing tests surface first -- that's the information that matters most.
    order = {"fail": 0, "unknown": 0, "pass": 1, "skipped": 2}
    tests = sorted(summary.tests, key=lambda t: order.get(t.status, 1))

    rows = []
    for t in tests:
        name = html.escape(_display_name(t.name))
        badge_class = {"pass": "pass", "fail": "fail"}.get(t.status, "skip")
        badge_label = {"pass": "PASS", "fail": "FAIL", "skipped": "SKIP"}.get(t.status, "\u2014")
        p_val = f"{t.p_value:.6f}" if t.p_value is not None else "\u2014"
        count = f"{t.passed}/{t.total}" if t.total else "\u2014"

        rows.append(f"""<div class="row">
  <div class="row-name">{name}</div>
  {_bit_bar(t.passed, t.total)}
  <div class="row-count">{count}</div>
  <div class="row-p">p={p_val}</div>
  <div class="badge {badge_class}">{badge_label}</div>
</div>""")

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STS Report \u2014 {gen}</title>
<style>
  :root {{
    --paper: {_PAPER}; --ink: {_INK}; --ink-soft: {_INK_SOFT}; --line: {_LINE};
    --pass: {_PASS}; --pass-bg: {_PASS_BG}; --fail: {_FAIL}; --fail-bg: {_FAIL_BG};
    --skip: {_SKIP}; --skip-bg: {_SKIP_BG};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    padding: 32px 16px 64px;
  }}
  .report {{ max-width: 780px; margin: 0 auto; }}
  .eyebrow {{
    font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--ink-soft); margin: 0 0 6px;
  }}
  .masthead {{
    display: flex; justify-content: space-between; align-items: flex-end;
    gap: 16px; border-bottom: 2px solid var(--ink); padding-bottom: 20px; margin-bottom: 4px;
    flex-wrap: wrap;
  }}
  h1 {{ font-size: 26px; margin: 0; font-weight: 700; letter-spacing: -0.01em; }}
  .meta {{ color: var(--ink-soft); font-size: 12px; margin-top: 6px; }}
  .stamp {{
    font-size: 20px; font-weight: 700; letter-spacing: 0.08em;
    padding: 10px 18px; border: 2px solid currentColor; line-height: 1;
  }}
  .stamp.pass {{ color: var(--pass); }}
  .stamp.fail {{ color: var(--fail); }}
  .stamp.unknown {{ color: var(--skip); }}
  .tally {{
    display: flex; gap: 24px; padding: 16px 0 20px; color: var(--ink-soft); font-size: 12px;
    border-bottom: 1px solid var(--line);
  }}
  .tally b {{ color: var(--ink); font-size: 14px; }}
  details.config {{ border: 1px solid var(--line); margin: 16px 0 4px; }}
  details.config summary {{ cursor: pointer; font-size: 12px; font-weight: 700; padding: 10px 12px; }}
  details.config dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; padding: 0 12px 12px; font-size: 12px; }}
  details.config dt {{ color: var(--ink-soft); }}
  details.config dd {{ margin: 0; }}
  .row {{
    display: flex; align-items: center; gap: 16px;
    padding: 11px 0; border-bottom: 1px solid var(--line);
    font-size: 13px;
  }}
  .row-name {{ width: 200px; flex: 0 0 auto; color: var(--ink); }}
  .row-count {{ width: 78px; flex: 0 0 auto; color: var(--ink-soft); text-align: right; }}
  .row-p {{ width: 104px; flex: 0 0 auto; color: var(--ink-soft); text-align: right; }}
  .bar {{ flex: 1 1 auto; display: flex; align-items: center; gap: 3px; flex-wrap: wrap; min-width: 60px; margin-right: 6px; }}
  .chip {{ width: 9px; height: 9px; flex: 0 0 auto; }}
  .chip-pass {{ background: var(--pass); }}
  .chip-fail {{ background: var(--fail); }}
  .bar-solid {{ display: flex; width: 100%; height: 9px; overflow: hidden; }}
  .bar-pass {{ background: var(--pass); height: 100%; }}
  .bar-fail {{ background: var(--fail); height: 100%; }}
  .bar-empty {{ color: var(--skip); font-size: 12px; }}
  .badge {{
    width: 56px; flex: 0 0 auto; text-align: center; font-size: 11px; font-weight: 700;
    letter-spacing: 0.06em; padding: 4px 0; border-radius: 3px;
  }}
  .badge.pass {{ color: var(--pass); background: var(--pass-bg); }}
  .badge.fail {{ color: var(--fail); background: var(--fail-bg); }}
  .badge.skip {{ color: var(--skip); background: var(--skip-bg); }}
  footer {{ margin-top: 28px; font-size: 11px; color: var(--ink-soft); }}
  @media (max-width: 560px) {{
    .row {{ flex-wrap: wrap; gap: 4px 12px; padding: 14px 0; }}
    .row-name {{ width: 100%; font-weight: 600; }}
    .bar {{ order: 3; width: 100%; margin-top: 4px; }}
    .row-count, .row-p {{ width: auto; text-align: left; }}
  }}
</style>
</head>
<body>
<div class="report">
  <div class="masthead">
    <div>
      <p class="eyebrow">NIST SP 800-22 &middot; STS Report</p>
      <h1>{gen}</h1>
      <p class="meta">{exp_name}</p>
    </div>
    <div class="stamp {overall}">{overall_label}</div>
  </div>
  <div class="tally">
    <span><b>{passed_n}</b> / {len(evaluated)} tests passed</span>
  </div>
  {_config_panel(config)}
  {"".join(rows)}
  <footer>Generated by the randomness-testing-framework &middot; thresholds per NIST SP 800-22</footer>
</div>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html_doc)
    return output_path