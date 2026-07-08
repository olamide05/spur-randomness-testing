"""JSON Exporter module."""
import json
from pathlib import Path
from typing import Optional

from ..parser.result_parser import ExperimentSummary


class JSONExporter:
    @staticmethod
    def export(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            output_path = Path(summary.experiment_directory) / "report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "framework": "NIST STS 2.1.2",
            "metadata": {
                "generator": summary.generator,
                "experiment_directory": summary.experiment_directory,
                "stream_length": summary.stream_length,
                "number_of_streams": summary.number_of_streams,
                "overall_passed": summary.overall_passed,
                "total_tests": len(summary.tests),
                "tests_passed": sum(1 for t in summary.tests if t.status == "Pass"),
                "tests_failed": sum(1 for t in summary.tests if t.status == "Fail"),
                "tests_not_run": sum(1 for t in summary.tests if t.status == "Not Run"),
            },
            "tests": [t.to_dict() for t in summary.tests],
            "raw": {
                "final_report": summary.raw_final_report,
                "stats": summary.raw_stats,
                "results": summary.raw_results,
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return output_path

    @staticmethod
    def to_string(summary: ExperimentSummary) -> str:
        return json.dumps(summary.to_dict(), indent=2, ensure_ascii=False, default=str)


def export_json(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
    return JSONExporter.export(summary, output_path)