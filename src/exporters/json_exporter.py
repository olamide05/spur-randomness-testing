import json
from pathlib import Path


def export_json(summary, output_path: Path = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "report.json"
    
    data = {
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
    }
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    return output_path