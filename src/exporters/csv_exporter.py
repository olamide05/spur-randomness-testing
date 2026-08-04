"""CSV exporter."""
from pathlib import Path


def export_csv(summary, output_path: Path = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "report.csv"
    
    lines = ["test,status,passed,total,p_value,proportion"]
    for t in summary.tests:
        lines.append(f"{t.name},{t.status},{t.passed},{t.total},{t.p_value or ''},{t.proportion or ''}")
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return output_path