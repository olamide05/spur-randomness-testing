"""HTML Dashboard exporter."""
from pathlib import Path


def export_html(summary, output_path: Path = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "dashboard.html"
    
    labels = []
    passed = []
    colors = []
    
    for test in summary.tests:
        labels.append(test.name)
        if test.total > 0:
            passed.append(test.passed)
            colors.append("#22c55e" if test.status == "pass" else "#ef4444")
        else:
            passed.append(0)
            colors.append("#9ca3af")
    
    rows = ""
    for test in summary.tests:
        icon = "✅" if test.status == "pass" else "❌" if test.status == "fail" else "➖"
        rows += f"<tr><td>{test.name}</td><td>{icon}</td><td>{test.passed}/{test.total}</td></tr>"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>NIST STS Results - {summary.generator}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 1000px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
.card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
h1 {{ margin: 0 0 8px 0; }}
.status {{ font-size: 24px; font-weight: bold; padding: 12px 24px; border-radius: 8px; display: inline-block; }}
.status.pass {{ background: #dcfce7; color: #166534; }}
.status.fail {{ background: #fee2e2; color: #991b1b; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
th {{ background: #f9fafb; font-weight: 600; }}
.chart-container {{ height: 300px; }}
</style>
</head>
<body>
<div class="card">
<h1>NIST STS Results</h1>
<p>Generator: <strong>{summary.generator}</strong></p>
<p>Directory: {summary.experiment_directory.name}</p>
<div class="status {'pass' if summary.overall_status == 'pass' else 'fail'}">{summary.overall_status.upper()}</div>
</div>
<div class="card">
<div class="chart-container"><canvas id="chart"></canvas></div>
</div>
<div class="card">
<table>
<tr><th>Test</th><th>Status</th><th>Passed</th></tr>
{rows}
</table>
</div>
<script>
new Chart(document.getElementById('chart'), {{
  type: 'bar',
  data: {{
    labels: {labels},
    datasets: [{{ label: 'Passed', data: {passed}, backgroundColor: {colors} }}]
  }},
  options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
}});
</script>
</body>
</html>"""
    
    with open(output_path, "w") as f:
        f.write(html)
    return output_path