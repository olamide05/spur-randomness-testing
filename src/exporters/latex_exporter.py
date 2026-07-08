"""LaTeX Exporter module."""
from pathlib import Path
from typing import Optional
from statistics import mean

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
        lines = []
        
        lines.append(r"\documentclass{article}")
        lines.append(r"\usepackage{booktabs}")
        lines.append(r"\usepackage{longtable}")
        lines.append(r"\usepackage{xcolor}")
        lines.append(r"\usepackage{geometry}")
        lines.append(r"\geometry{margin=1in}")
        lines.append(r"\definecolor{passgreen}{RGB}{0,128,0}")
        lines.append(r"\definecolor{failred}{RGB}{200,0,0}")
        lines.append(r"\definecolor{notrungray}{RGB}{128,128,128}")
        lines.append("")
        lines.append(r"\begin{document}")
        lines.append("")
        
        lines.append(r"\begin{center}")
        lines.append(r"\LARGE\textbf{NIST Statistical Test Suite 2.1.2}")
        lines.append(r"\end{center}")
        lines.append("")
        
        lines.append(r"\begin{center}")
        lines.append(r"\begin{tabular}{ll}")
        lines.append(r"\toprule")
        lines.append(f"\\textbf{{Generator:}} & {summary.generator or 'Unknown'} \\\\")
        lines.append(f"\\textbf{{Stream Length:}} & {summary.stream_length:,} bits \\\\")
        lines.append(f"\\textbf{{Number of Streams:}} & {summary.number_of_streams} \\\\")
        lines.append(f"\\textbf{{Total Tests:}} & {len(summary.tests)} \\\\")
        passed = sum(1 for t in summary.tests if t.status == "Pass")
        failed = sum(1 for t in summary.tests if t.status == "Fail")
        not_run = sum(1 for t in summary.tests if t.status == "Not Run")
        lines.append(f"\\textbf{{Tests Passed:}} & {passed} \\\\")
        lines.append(f"\\textbf{{Tests Failed:}} & {failed} \\\\")
        lines.append(f"\\textbf{{Tests Not Run:}} & {not_run} \\\\")
        lines.append(r"\midrule")
        
        if summary.overall_passed is not None:
            status = "PASS" if summary.overall_passed else "FAIL"
            color = "passgreen" if summary.overall_passed else "failred"
            lines.append(f"\\textbf{{\\textcolor{{{color}}}{{Overall Result:}}}} & \\textcolor{{{color}}}{{\\textbf{{{status}}}}} \\\\")
        
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{center}")
        lines.append("")
        
        lines.append(r"\begin{longtable}{lcccc}")
        lines.append(r"\caption{NIST STS Test Results} \\")
        lines.append(r"\toprule")
        lines.append(r"\textbf{Test Name} & \textbf{Status} & \textbf{P-Value} & \textbf{Proportion} & \textbf{Mean P} \\")
        lines.append(r"\midrule")
        lines.append(r"\endfirsthead")
        lines.append(r"\toprule")
        lines.append(r"\textbf{Test Name} & \textbf{Status} & \textbf{P-Value} & \textbf{Proportion} & \textbf{Mean P} \\")
        lines.append(r"\midrule")
        lines.append(r"\endhead")
        lines.append(r"\bottomrule")
        lines.append(r"\endfoot")
        lines.append("")
        
        for test in summary.tests:
            name = test.name.replace("_", " ").title()
            
            if test.status == "Pass":
                status = r"\textcolor{passgreen}{\textbf{PASS}}"
            elif test.status == "Fail":
                status = r"\textcolor{failred}{\textbf{FAIL}}"
            elif test.status == "Not Run":
                status = r"\textcolor{notrungray}{\textit{Not Run}}"
            else:
                status = "N/A"
            
            if test.status == "Not Run":
                pval = "---"
                prop = "---"
                mean_p = "---"
            else:
                pval = f"{test.p_value:.6f}" if test.p_value is not None else "----"
                prop = f"{test.proportion:.4f}" if test.proportion is not None else "----"
                mean_p = f"{mean(test.p_values):.6f}" if test.p_values else "----"
            
            lines.append(f"{name} & {status} & {pval} & {prop} & {mean_p} \\\\")
        
        lines.append("")
        lines.append(r"\end{longtable}")
        lines.append("")
        lines.append(r"\end{document}")
        
        return "\n".join(lines)


def export_latex(summary: ExperimentSummary, output_path: Optional[Path] = None) -> Path:
    return LatexExporter.export(summary, output_path)