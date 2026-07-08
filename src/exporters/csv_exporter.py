"""CSV Exporter module."""
import csv
from pathlib import Path
from typing import Optional
from statistics import mean

from ..parser.result_parser import ExperimentSummary


class CSVExporter:
    @staticmethod
    def export(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            output_path = Path(summary.experiment_directory) / "report.csv"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Test", "Passed", "P-value", "Proportion", "Mean P", "Min P", "Max P", "Notes"])

            for test in summary.tests:
                writer.writerow([
                    test.name,
                    "Yes" if test.passed else "No" if test.passed is not None else "N/A",
                    f"{test.p_value:.6f}" if test.p_value is not None else "N/A",
                    f"{test.proportion:.4f}" if test.proportion is not None else "N/A",
                    f"{mean(test.p_values):.6f}" if test.p_values else "N/A",
                    f"{min(test.p_values):.6f}" if test.p_values else "N/A",
                    f"{max(test.p_values):.6f}" if test.p_values else "N/A",
                    test.notes
                ])

            writer.writerow([])
            writer.writerow([
                "Overall",
                "PASS" if summary.overall_passed else "FAIL" if summary.overall_passed is not None else "N/A",
                "", "", "", "", "", ""
            ])

        return output_path


def export_csv(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
    return CSVExporter.export(summary, output_path)