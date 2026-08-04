"""LaTeX exporter."""
from pathlib import Path


def export_latex(summary, output_path: Path = None) -> Path:
    if output_path is None:
        output_path = summary.experiment_directory / "report.tex"
    
    rows = ""
    for t in summary.tests:
        status = t.status.upper()
        rows += f"{t.name} & {status} & {t.passed}/{t.total} \\\\\n"
    
    header = r"""\documentclass{article}
\usepackage{booktabs}
\begin{document}
\section*{NIST STS Results: """ + summary.generator + r"""}
\begin{tabular}{lcc}
\toprule
Test & Status & Passed \\
\midrule
"""
    
    footer = r"""\bottomrule
\end{tabular}
\end{document}
"""
    
    with open(output_path, "w") as f:
        f.write(header + rows + footer)
    return output_path