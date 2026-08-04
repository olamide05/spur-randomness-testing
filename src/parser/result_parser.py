import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class TestResult:
    name: str
    passed: int
    total: int
    p_value: Optional[float] = None
    proportion: Optional[float] = None
    status: str = "unknown"


@dataclass
class ExperimentSummary:
    generator: str
    experiment_directory: Path
    overall_status: str = "unknown"
    tests: List[TestResult] = field(default_factory=list)


class ResultParser:
    def __init__(self, experiment_directory: Path, generator: str = ""):
        self.experiment_directory = Path(experiment_directory)
        self.generator = generator

    def parse(self) -> ExperimentSummary:
        report = self.experiment_directory / "finalAnalysisReport.txt"
        if not report.exists():
            raise FileNotFoundError(f"Report not found: {report}")

        summary = ExperimentSummary(
            generator=self.generator,
            experiment_directory=self.experiment_directory,
            tests=[]
        )

        report_data: Dict[str, dict] = {}
        in_results = False

        with open(report) as f:
            for line in f:
                if "RESULTS FOR THE UNIFORMITY" in line:
                    in_results = True
                    continue
                if not in_results:
                    continue

                parsed = self._parse_report_line(line)
                if not parsed:
                    continue

                name, p_val, passed, total = parsed

                if name not in report_data:
                    report_data[name] = {
                        "p_values": [],
                        "passed": 0,
                        "total": 0
                    }

                report_data[name]["p_values"].append(p_val)
                report_data[name]["passed"] += passed
                report_data[name]["total"] += total

        for name, data in report_data.items():
            test = TestResult(
                name=name,
                passed=0,
                total=0,
                status="unknown"
            )

            detail_passed, detail_total = self._read_detail_file(name)
            if detail_total > 0:
                test.passed = detail_passed
                test.total = detail_total
            else:
                test.passed = data["passed"]
                test.total = data["total"]

            if test.total > 0:
                test.proportion = test.passed / test.total
                test.status = "pass" if test.proportion >= 0.96 else "fail"
            else:
                test.status = "skipped"

            p_vals = [p for p in data["p_values"] if p is not None]
            if p_vals:
                test.p_value = p_vals[0]

            summary.tests.append(test)

        evaluated = [t for t in summary.tests if t.total > 0]
        if evaluated:
            passed_count = sum(1 for t in evaluated if t.status == "pass")
            summary.overall_status = "pass" if passed_count == len(evaluated) else "fail"

        return summary

    def _parse_report_line(self, line: str) -> Optional[tuple]:
        parts = line.strip().split()
        if len(parts) < 3:
            return None

        p_val_str = parts[-3]
        prop_str = parts[-2]
        raw_name = parts[-1].replace("*", "").strip()

        name = self._normalize_name(raw_name.lower())

        p_val = None
        if p_val_str != "----":
            try:
                p_val = float(p_val_str)
            except ValueError:
                return None

        passed, total = 0, 0
        if prop_str != "------":
            try:
                p_str, t_str = prop_str.split("/")
                passed = int(p_str)
                total = int(t_str)
            except ValueError:
                return None

        return name, p_val, passed, total

    def _normalize_name(self, raw: str) -> str:
        mapping = {
            "nonoverlappingtemplate": "non_overlapping_template",
            "overlappingtemplate": "overlapping_template",
            "randomexcursionsvariant": "random_excursions_variant",
            "randomexcursions": "random_excursions",
            "approximateentropy": "approximate_entropy",
            "linearcomplexity": "linear_complexity",
            "blockfrequency": "block_frequency",
            "cumulativesums": "cumulative_sums",
            "longestrun": "longest_run",
            "frequency": "frequency",
            "runs": "runs",
            "rank": "rank",
            "fft": "fft",
            "universal": "universal",
            "serial": "serial",
        }
        return mapping.get(raw, raw)

    def _read_detail_file(self, name: str) -> tuple:
        dir_name = name.replace("_", "").title()
        if dir_name == "Cumulativesums":
            dir_name = "CumulativeSums"
        if dir_name == "Fft":
            dir_name = "FFT"

        test_dir = self.experiment_directory / dir_name
        if not test_dir.exists():
            return 0, 0

        results = list(test_dir.glob("results*.txt"))
        if not results:
            return 0, 0

        passed = 0
        total = 0
        for r in results:
            try:
                with open(r) as f:
                    for line in f:
                        if "SUCCESS" in line:
                            passed += 1
                            total += 1
                        elif "FAILURE" in line:
                            total += 1
            except Exception:
                continue

        return passed, total
