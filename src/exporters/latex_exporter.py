from pathlib import Path
from typing import Optional

from ..parser.result_parser import ExperimentSummary


class LatexExporter:
    @staticmethod
    def export(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            output_path = Path(summary.experiment_directory) / "report.tex"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(LatexExporter.to_string(summary))

        return output_path

    @staticmethod
    def to_string(summary: ExperimentSummary) -> str:
        lines = [
            "\\documentclass{article}",
            "\\usepackage{booktabs}",
            "\\usepackage{longtable}",
            "\\usepackage{xcolor}",
            "\\definecolor{passgreen}{RGB}{0,128,0}",
            "\\definecolor{failred}{RGB}{200,0,0}",
            "",
            "\\begin{document}",
            "",
            "\\section*{NIST STS Test Results}",
            f"\\textbf{{Generator:}} {summary.generator or 'Unknown'} \\\\",
            f"\\textbf{{Stream Length:}} {summary.stream_length:,} bits \\\\",
            f"\\textbf{{Number of Streams:}} {summary.number_of_streams} \\\\",
            "",
        ]

        if summary.overall_passed is not None:
            status = "PASS" if summary.overall_passed else "FAIL"
            color = "passgreen" if summary.overall_passed else "failred"
            lines.append(f"\\textbf{{\\textcolor{{{color}}}{{Overall Result: {status}}}}}")
            lines.append("")

        lines.extend([
            "\\begin{longtable}{llcc}",
            "\\toprule",
            "\\textbf{Test} & \\textbf{Passed} & \\textbf{P-value} & \\textbf{Proportion} \\\\",
            "\\midrule",
            "\\endfirsthead",
            "\\toprule",
            "\\textbf{Test} & \\textbf{Passed} & \\textbf{P-value} & \\textbf{Proportion} \\\\",
            "\\midrule",
            "\\endhead",
            "\\bottomrule",
            "\\endfoot",
            "",
        ])

        for test in summary.tests:
            name = test.name.replace("_", " ").title()
            passed = "\\textcolor{passgreen}{\\textbf{Yes}}" if test.passed is True else \
                     "\\textcolor{failred}{\\textbf{No}}" if test.passed is False else "N/A"
            pval = f"{test.p_value:.6f}" if test.p_value is not None else "N/A"
            prop = f"{test.proportion:.4f}" if test.proportion is not None else "N/A"
            lines.append(f"{name} & {passed} & {pval} & {prop} \\\\")

        lines.extend(["", "\\end{longtable}", "", "\\end{document}"])
        return "\n".join(lines)


def export_latex(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
    return LatexExporter.export(summary, output_path)