"""JSON exporter."""
import json
from pathlib import Path
from typing import Optional


def export_json(summary, output_path: Optional[Path] = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "report.json"

    passed = sum(1 for t in summary.tests if t.status == "Pass")
    failed = sum(1 for t in summary.tests if t.status == "Fail")
    not_run = sum(1 for t in summary.tests if t.status == "Not Run")

    data = {
        "framework": summary.framework,
        "generator": summary.generator,
        "overall_passed": summary.overall_passed,
        "metadata": {
            "total_tests": len(summary.tests),
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_not_run": not_run,
        },
        "tests": [
            {
                "name": t.name,
                "status": t.status,
                "p_value": t.p_value,
                "proportion": t.proportion,
                "pass_rate": t.pass_rate,
                "mean_p_value": t.mean_p_value,
                "min_p_value": t.min_p_value,
                "max_p_value": t.max_p_value,
                "notes": t.notes,
            }
            for t in summary.tests
        ],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    return output_path