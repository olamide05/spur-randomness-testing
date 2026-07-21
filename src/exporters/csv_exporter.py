"""CSV exporter."""
from pathlib import Path
from typing import Optional


def export_csv(summary, output_path: Optional[Path] = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "report.csv"

    passed = sum(1 for t in summary.tests if t.status == "Pass")
    failed = sum(1 for t in summary.tests if t.status == "Fail")
    not_run = sum(1 for t in summary.tests if t.status == "Not Run")

    lines = [
        "NIST STS 2.1.2 Test Results",
        "",
        f"Generator,{summary.generator}",
        f"Total Tests,{len(summary.tests)}",
        f"Tests Passed,{passed}",
        f"Tests Failed,{failed}",
        f"Tests Not Run,{not_run}",
        f"Overall Result,{'PASS' if summary.overall_passed else 'FAIL'}",
        "",
        "Test Name,Status,P-Value,Proportion,Pass Rate,Mean P-Value,Min P-Value,Max P-Value,Notes",
    ]

    for t in summary.tests:
        pval = f"{t.p_value:.6f}" if t.p_value else "N/A"
        prop = f"{t.proportion:.4f}" if t.proportion else "N/A"
        mean_p = f"{t.mean_p_value:.6f}" if t.mean_p_value else "N/A"
        min_p = f"{t.min_p_value:.6f}" if t.min_p_value else "N/A"
        max_p = f"{t.max_p_value:.6f}" if t.max_p_value else "N/A"
        lines.append(f"{t.name},{t.status},{pval},{prop},{t.pass_rate},{mean_p},{min_p},{max_p},{t.notes}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return output_path