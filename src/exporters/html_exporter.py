"""HTML Dashboard exporter."""
from pathlib import Path
from typing import Optional
from datetime import datetime


def export_html(summary, output_path: Optional[Path] = None) -> Path:
    exp_dir = Path(summary.experiment_directory)

    if output_path is None:
        output_path = exp_dir / "dashboard.html"

    total = len(summary.tests)
    passed = sum(1 for t in summary.tests if t.status == "Pass")
    failed = sum(1 for t in summary.tests if t.status == "Fail")
    not_run = sum(1 for t in summary.tests if t.status == "Not Run")

    rows = []
    for t in summary.tests:
        pval = f"{t.p_value:.6f}" if t.p_value else "N/A"
        mean_p = f"{t.mean_p_value:.6f}" if t.mean_p_value else "N/A"
        color = "#d4edda" if t.status == "Pass" else "#f8d7da" if t.status == "Fail" else "#e2e3e5"
        badge = "bg-success" if t.status == "Pass" else "bg-danger" if t.status == "Fail" else "bg-secondary"
        rows.append(f"""
        <tr style="background-color: {color}">
            <td><strong>{t.name}</strong></td>
            <td><span class="badge {badge}">{t.status}</span></td>
            <td>{t.pass_rate}</td>
            <td>{pval}</td>
            <td>{mean_p}</td>
            <td>{t.notes or ""}</td>
        </tr>
        """)

    labels = [t.name for t in summary.tests]
    pvalues = [t.p_value if t.p_value else 0 for t in summary.tests]
    statuses = [t.status for t in summary.tests]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NIST STS Results - {summary.generator}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f5f7fa; color: #333; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
header {{ background: linear-gradient(135deg, #1e3a5f, #2d5a87); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
.card {{ background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid; }}
.card.pass {{ border-color: #28a745; }}
.card.fail {{ border-color: #dc3545; }}
.card.info {{ border-color: #17a2b8; }}
.card h3 {{ font-size: 0.875rem; text-transform: uppercase; color: #6c757d; margin-bottom: 0.5rem; }}
.card .value {{ font-size: 2.5rem; font-weight: 700; color: #1e3a5f; }}
.overall {{ font-size: 3rem; text-align: center; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
.overall.pass {{ background: #d4edda; color: #155724; }}
.overall.fail {{ background: #f8d7da; color: #721c24; }}
table {{ width: 100%; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-collapse: collapse; }}
th {{ background: #1e3a5f; color: white; padding: 1rem; text-align: left; }}
td {{ padding: 1rem; border-bottom: 1px solid #e9ecef; }}
.badge {{ padding: 0.35em 0.65em; border-radius: 6px; font-size: 0.875rem; font-weight: 600; }}
.bg-success {{ background: #d4edda; color: #155724; }}
.bg-danger {{ background: #f8d7da; color: #721c24; }}
.bg-secondary {{ background: #e2e3e5; color: #383d41; }}
.chart {{ background: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; }}
.footer {{ text-align: center; color: #6c757d; margin-top: 2rem; font-size: 0.875rem; }}
</style>
</head>
<body>
<div class="container">
<header>
<h1>NIST STS 2.1.2 Results</h1>
<p>Generator: <strong>{summary.generator}</strong> | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
</header>

<div class="overall {'pass' if summary.overall_passed else 'fail'}">
{'PASS' if summary.overall_passed else 'FAIL'}
</div>

<div class="grid">
<div class="card info"><h3>Total</h3><div class="value">{total}</div></div>
<div class="card pass"><h3>Passed</h3><div class="value">{passed}</div></div>
<div class="card fail"><h3>Failed</h3><div class="value">{failed}</div></div>
<div class="card info"><h3>Not Run</h3><div class="value">{not_run}</div></div>
</div>

<div class="chart">
<h2 style="margin-bottom:1rem">P-Values</h2>
<canvas id="chart" height="80"></canvas>
</div>

<h2 style="margin-bottom:1rem">Results</h2>
<table>
<thead><tr><th>Test</th><th>Status</th><th>Pass Rate</th><th>P-Value</th><th>Mean P</th><th>Notes</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>

<div class="footer"><p>SPUR NIST STS Framework</p></div>
</div>

<script>
const colors = {str(statuses)}.map(s => s === 'Pass' ? '#28a745' : s === 'Fail' ? '#dc3545' : '#6c757d');
new Chart(document.getElementById('chart'), {{
type: 'bar',
data: {{ labels: {str(labels)}, datasets: [{{ label: 'P-Value', data: {str(pvalues)}, backgroundColor: colors, borderWidth: 0 }}] }},
options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true, max: 1 }} }}, plugins: {{ legend: {{ display: false }} }} }}
}});
</script>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)
    return output_path