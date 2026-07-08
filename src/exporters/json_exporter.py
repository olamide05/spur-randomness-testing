import json
from pathlib import Path
from typing import Optional

from ..parser.result_parser import ExperimentSummary


class JSONExporter:
    @staticmethod
    def export(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            output_path = Path(summary.experiment_directory) / "report.json"

        data = summary.to_dict()
        data["raw"] = {
            "final_report": summary.raw_final_report,
            "stats": summary.raw_stats,
            "results": summary.raw_results,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return output_path

    @staticmethod
    def to_string(summary: ExperimentSummary) -> str:
        return json.dumps(summary.to_dict(), indent=2, ensure_ascii=False, default=str)


def export_json(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
    return JSONExporter.export(summary, output_path)