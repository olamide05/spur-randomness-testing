"""LaTeX exporter."""
from pathlib import Path
from typing import Optional


def export_latex(summary, output_path: Optional[Path] = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "report.tex"

    passed = sum(1 for t in summary.tests if t.status == "Pass")
    failed = sum(1 for t in summary.tests if t.status == "Fail")
    not_run = sum(1 for t in summary.tests if t.status == "Not Run")

    rows = []
    for t in summary.tests:
        color = "green" if t.status == "Pass" else "red" if t.status == "Fail" else "gray"
        pval = f"{t.p_value:.4f}" if t.p_value else "N/A"
        row = "\\textcolor{" + color + "}{" + t.name + "} & " + t.status + " & " + pval + " & " + t.pass_rate + " \\\\"
        rows.append(row)

    overall_color = "green" if summary.overall_passed else "red"
    overall_text = "PASS" if summary.overall_passed else "FAIL"

    latex = (
        "\\documentclass{article}\n"
        "\\usepackage{xcolor}\n"
        "\\usepackage{longtable}\n"
        "\\begin{document}\n"
        "\\section*{NIST STS 2.1.2 Results: " + summary.generator + "}\n"
        "\\textbf{Overall:} \\textcolor{" + overall_color + "}{" + overall_text + "}\n\n"
        "\\begin{tabular}{|l|l|l|l|}\n"
        "\\hline\n"
        "Test & Status & P-Value & Pass Rate \\\\\n"
        "\\hline\n"
        + "\n".join(rows) + "\n"
        "\\hline\n"
        "\\end{tabular}\n"
        "\\end{document}\n"
    )

    with open(output_path, "w") as f:
        f.write(latex)

    return output_path