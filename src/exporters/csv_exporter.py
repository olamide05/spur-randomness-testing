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
            
            writer.writerow(["NIST STS 2.1.2 Test Results"])
            writer.writerow([])
            
            writer.writerow(["Generator", summary.generator])
            writer.writerow(["Stream Length", f"{summary.stream_length:,}"])
            writer.writerow(["Number of Streams", summary.number_of_streams])
            writer.writerow(["Total Tests", len(summary.tests)])
            writer.writerow(["Tests Passed", sum(1 for t in summary.tests if t.status == "Pass")])
            writer.writerow(["Tests Failed", sum(1 for t in summary.tests if t.status == "Fail")])
            writer.writerow(["Tests Not Run", sum(1 for t in summary.tests if t.status == "Not Run")])
            writer.writerow(["Overall Result", "PASS" if summary.overall_passed else "FAIL" if summary.overall_passed is not None else "N/A"])
            writer.writerow([])
            
            writer.writerow([
                "Test Name",
                "Status",
                "P-Value",
                "Proportion",
                "Pass Rate",
                "Mean P-Value",
                "Min P-Value", 
                "Max P-Value",
                "Notes"
            ])
            
            for test in summary.tests:
                if test.status == "Not Run":
                    pval = "N/A"
                    prop = "N/A"
                    mean_p = "N/A"
                    min_p = "N/A"
                    max_p = "N/A"
                else:
                    pval = f"{test.p_value:.6f}" if test.p_value is not None else "----"
                    prop = f"{test.proportion:.4f}" if test.proportion is not None else "----"
                    mean_p = f"{mean(test.p_values):.6f}" if test.p_values else "----"
                    min_p = f"{min(test.p_values):.6f}" if test.p_values else "----"
                    max_p = f"{max(test.p_values):.6f}" if test.p_values else "----"
                
                writer.writerow([
                    test.name.replace("_", " ").title(),
                    test.status,
                    pval,
                    prop,
                    test.pass_rate,
                    mean_p,
                    min_p,
                    max_p,
                    test.notes
                ])

        return output_path


def export_csv(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
    return CSVExporter.export(summary, output_path)