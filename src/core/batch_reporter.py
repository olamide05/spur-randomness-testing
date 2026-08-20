import html
import json
from src.exporters.html_exporter import _config_panel as _single_config_panel
from pathlib import Path
from typing import List
from dataclasses import dataclass


@dataclass
class BatchReporter:
    summaries: List
    config: object = None

    def _collect_tests(self) -> List[str]:
        """Get all unique test names across all runs."""
        tests = set()
        for s in self.summaries:
            for t in s.tests:
                tests.add(t.name)
        return sorted(tests)

    def _get_test_result(self, summary, test_name: str):
        """Get a specific test result from a summary."""
        for t in summary.tests:
            if t.name == test_name:
                return t
        return None

    def generate_md(self, output_path: Path):
        """Generate Markdown comparison table."""
        tests = self._collect_tests()

        lines = [
            "# NIST STS Batch Comparison",
            "",
            "| Generator | Overall | " + " | ".join(t.replace("_", " ").title() for t in tests) + " |",
            "|" + "-" * 10 + "|" + "-" * 8 + "|" + "|".join("-" * 12 for _ in tests) + "|",
        ]

        for summary in self.summaries:
            overall = "PASS" if summary.overall_status == "pass" else "FAIL" if summary.overall_status == "fail" else "N/A"
            row = f"| {summary.generator:8s} | {overall:6s} |"

            for test_name in tests:
                t = self._get_test_result(summary, test_name)
                if t and t.total > 0:
                    status = f"{t.passed}/{t.total}"
                elif t:
                    status = "SKIP"
                else:
                    status = "N/A"
                row += f" {status:10s} |"

            lines.append(row)

        with open(output_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def generate_json(self, output_path: Path):
        """Generate JSON comparison."""
        data = []
        for summary in self.summaries:
            data.append({
                "generator": summary.generator,
                "overall_status": summary.overall_status,
                "experiment_directory": str(summary.experiment_directory),
                "tests": [
                    {
                        "name": t.name,
                        "status": t.status,
                        "passed": t.passed,
                        "total": t.total,
                        "p_value": t.p_value,
                        "proportion": t.proportion
                    }
                    for t in summary.tests
                ]
            })

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def _config_panel(self) -> str:
        return _single_config_panel(self.config)

    def generate_html(self, output_path: Path):
        """Generate an HTML comparison dashboard across all runs in the batch."""
        tests = self._collect_tests()

        header_cols = "".join(
            f'<th>{html.escape(t.replace("_", " ").title())}</th>'
            for t in tests
        )

        rows = []
        for summary in self.summaries:
            overall = summary.overall_status
            overall_label = {"pass": "PASS", "fail": "FAIL"}.get(overall, "N/A")

            cells = ""
            for test_name in tests:
                t = self._get_test_result(summary, test_name)
                if t and t.total > 0:
                    cls = "pass" if t.status == "pass" else "fail"
                    text = f"{t.passed}/{t.total}"
                elif t:
                    cls, text = "skip", "SKIP"
                else:
                    cls, text = "skip", "\u2014"
                cells += f'<td class="{cls}"><span class="dot"></span>{text}</td>'

            rows.append(
                f'<tr><td class="gen">{html.escape(str(summary.generator))}</td>'
                f'<td class="overall {overall}">{overall_label}</td>{cells}</tr>'
            )

        passed_n = sum(1 for s in self.summaries if s.overall_status == "pass")

        cards = []
        for summary in self.summaries:
            evaluated = [test for test in summary.tests if test.total > 0]
            passed = sum(1 for test in evaluated if test.status == "pass")
            test_rows = "".join(
                f"<li><span>{html.escape(test.name.replace(chr(95), chr(32)).title())}</span><b>{html.escape(test.status.upper())} · {test.passed}/{test.total}</b></li>"
                for test in summary.tests
            )
            cards.append(
                f'''<section class="summary-card">
  <h2>{html.escape(str(summary.generator))}</h2>
  <p><b>{passed}</b> / {len(evaluated)} evaluated tests passed</p>
  <details><summary>View this file's test results</summary><ul>{test_rows}</ul></details>
</section>'''
            )

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STS Batch Comparison</title>
<style>
  :root {{
    --paper: #F6F7F5; --ink: #161D1A; --ink-soft: #4B564F; --line: #DCE1DC;
    --pass: #1F6E4A; --pass-bg: #E7F2EC; --fail: #A6362B; --fail-bg: #F3E5E2;
    --skip: #8B948E; --skip-bg: #EEF0EE;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    padding: 32px 16px 64px;
  }}
  .report {{ max-width: 1100px; margin: 0 auto; }}
  .eyebrow {{
    font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--ink-soft); margin: 0 0 6px;
  }}
  h1 {{ font-size: 26px; margin: 0 0 6px; font-weight: 700; letter-spacing: -0.01em; }}
  .meta {{
    color: var(--ink-soft); font-size: 12px; border-bottom: 2px solid var(--ink);
    padding-bottom: 20px; margin-bottom: 20px;
  }}
  .meta b {{ color: var(--ink); }}
  details.config {{ border: 1px solid var(--line); margin: 0 0 20px; }}
  details.config summary {{ cursor: pointer; font-size: 12px; font-weight: 700; padding: 10px 12px; }}
  details.config dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; padding: 0 12px 12px; font-size: 12px; }}
  details.config dt {{ color: var(--ink-soft); }}
  details.config dd {{ margin: 0; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin: 0 0 20px; }}
  .summary-card {{ border: 1px solid var(--line); background: white; padding: 14px; }}
  .summary-card h2 {{ font-size: 15px; margin: 0; overflow-wrap: anywhere; }}
  .summary-card p {{ color: var(--ink-soft); font-size: 12px; margin: 8px 0; }}
  .summary-card p b {{ color: var(--ink); }}
  .summary-card summary {{ cursor: pointer; font-size: 12px; }}
  .summary-card ul {{ list-style: none; margin: 10px 0 0; padding: 0; font-size: 11px; }}
  .summary-card li {{ display: flex; justify-content: space-between; gap: 8px; border-top: 1px solid var(--line); padding: 5px 0; }}
  .summary-card li span {{ min-width: 0; overflow-wrap: anywhere; }}
  .summary-card li b {{ flex: 0 0 auto; white-space: nowrap; }}
  @media (max-width: 560px) {{
    .summary-card li {{ align-items: flex-start; flex-wrap: wrap; }}
    .summary-card li span {{ flex-basis: 100%; }}
    .summary-card li b {{ margin-left: 0; }}
  }}
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12px; table-layout: fixed; }}
  th, td {{ padding: 9px 10px; text-align: right; border-bottom: 1px solid var(--line); white-space: nowrap; }}
  th {{ width: 92px; text-align: right; font-weight: 600; color: var(--ink-soft); background: var(--paper);
       white-space: normal; line-height: 1.3; vertical-align: bottom;
       position: sticky; top: 0; border-bottom: 2px solid var(--ink); }}
  th:first-child, td:first-child {{ width: 130px; text-align: left; position: sticky; left: 0; background: var(--paper); }}
  th:nth-child(2), td:nth-child(2) {{ width: 70px; }}
  .gen {{ font-weight: 700; }}
  .overall {{ font-weight: 700; letter-spacing: 0.04em; }}
  .overall.pass {{ color: var(--pass); }}
  .overall.fail {{ color: var(--fail); }}
  td.pass, td.fail, td.skip {{ font-variant-numeric: tabular-nums; }}
  .dot {{ display: inline-block; width: 7px; height: 7px; margin-right: 6px; vertical-align: middle; }}
  .pass .dot {{ background: var(--pass); }}
  .fail .dot {{ background: var(--fail); }}
  .skip .dot {{ background: var(--skip); }}
  tr:hover td {{ background: #EEF1EE; }}
  tr:hover td:first-child {{ background: #EEF1EE; }}
  footer {{ margin-top: 20px; font-size: 11px; color: var(--ink-soft); }}
</style>
</head>
<body>
<div class="report">
  <p class="eyebrow">NIST SP 800-22 &middot; Batch Comparison</p>
  <h1>{len(self.summaries)} generators &middot; {len(tests)} tests</h1>
  <p class="meta"><b>{passed_n}</b> / {len(self.summaries)} generators passed every evaluated test</p>
  {self._config_panel()}
  <div class="summary-grid">{"".join(cards)}</div>
  <div class="table-wrap">
  <table>
  <thead><tr><th>Generator</th><th>Overall</th>{header_cols}</tr></thead>
  <tbody>
  {"".join(rows)}
  </tbody>
  </table>
  </div>
  <footer>Generated by the randomness-testing-framework &middot; thresholds per NIST SP 800-22</footer>
</div>
</body>
</html>"""

        with open(output_path, "w") as f:
            f.write(html_doc)