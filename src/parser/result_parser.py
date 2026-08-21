import math
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
    flagged: bool = False


@dataclass
class ExperimentSummary:
    generator: str
    experiment_directory: Path
    overall_status: str = "unknown"
    tests: List[TestResult] = field(default_factory=list)


class ResultParser:
    DETAIL_DIR_NAMES = {
        "frequency": "Frequency",
        "block_frequency": "BlockFrequency",
        "cumulative_sums": "CumulativeSums",
        "runs": "Runs",
        "longest_run": "LongestRun",
        "rank": "Rank",
        "fft": "FFT",
        "non_overlapping_template": "NonOverlappingTemplate",
        "overlapping_template": "OverlappingTemplate",
        "universal": "Universal",
        "approximate_entropy": "ApproximateEntropy",
        "random_excursions": "RandomExcursions",
        "random_excursions_variant": "RandomExcursionsVariant",
        "serial": "Serial",
        "linear_complexity": "LinearComplexity",
    }

    def __init__(
        self,
        experiment_directory: Path,
        generator: str = "",
        number_of_streams: int = 1,
    ):
        self.experiment_directory = Path(experiment_directory)
        self.generator = generator
        self.number_of_streams = number_of_streams

    def parse(self) -> ExperimentSummary:
        summary = ExperimentSummary(
            generator=self.generator,
            experiment_directory=self.experiment_directory,
            tests=[]
        )

        if self.number_of_streams == 1:
            summary.tests = self._parse_single_stream()
        else:
            summary.tests = self._parse_report()

        evaluated = [t for t in summary.tests if t.total > 0]
        if evaluated:
            passed_count = sum(1 for t in evaluated if t.status == "pass")
            summary.overall_status = "pass" if passed_count == len(evaluated) else "fail"

        return summary

    def _parse_single_stream(self) -> List[TestResult]:
        """A single sequence makes STS's own proportion table meaningless
        (it would just be a trivial 0/1 or 1/1), so pass/fail is instead the
        raw p-value from each test's own result folder, read directly."""
        tests = []
        for name, dir_name in self.DETAIL_DIR_NAMES.items():
            p_values = self._read_raw_p_values(dir_name)
            if not p_values:
                tests.append(TestResult(name=name, passed=0, total=0, status="skipped"))
                continue

            worst_p = min(p_values)
            passed = worst_p > 0.01
            tests.append(TestResult(
                name=name,
                passed=1 if passed else 0,
                total=1,
                p_value=worst_p,
                proportion=1.0 if passed else 0.0,
                status="pass" if passed else "fail",
            ))
        return tests

    def _parse_report(self) -> List[TestResult]:
        report = self.experiment_directory / "finalAnalysisReport.txt"
        if not report.exists():
            raise FileNotFoundError(f"Report not found: {report}")

        report_data: Dict[str, list] = {}
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

                name, p_val, passed, total, flagged = parsed
                report_data.setdefault(name, []).append(
                    {"p_value": p_val, "passed": passed, "total": total, "flagged": flagged}
                )

        tests = []
        for name, rows in report_data.items():
            flagged_rows = [r for r in rows if r["flagged"]]
            if flagged_rows:
                worst = flagged_rows[0]
            else:
                worst = min(rows, key=lambda r: (r["passed"] / r["total"]) if r["total"] else 0)

            test = TestResult(name=name, passed=worst["passed"], total=worst["total"])
            test.flagged = bool(flagged_rows)
            test.p_value = worst["p_value"]

            if test.total > 0:
                test.proportion = test.passed / test.total
                if test.flagged:
                    test.status = "fail"
                else:
                    low, high = self._acceptable_range(test.total)
                    test.status = "pass" if low <= test.passed <= high else "fail"
            else:
                test.status = "skipped"

            tests.append(test)
        return tests

    @staticmethod
    def _acceptable_range(sample_size: int) -> tuple:
        if sample_size <= 0:
            return 0, 0
        alpha = 0.01
        p_hat = 1.0 - alpha
        delta = 3.0 * math.sqrt((p_hat * alpha) / sample_size)
        return (p_hat - delta) * sample_size, (p_hat + delta) * sample_size

    def _parse_report_line(self, line: str) -> Optional[tuple]:
        raw_parts = line.strip().split()
        flagged = "*" in raw_parts
        parts = [p for p in raw_parts if p != "*"]
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

        return name, p_val, passed, total, flagged

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

    def _read_raw_p_values(self, dir_name: str) -> List[float]:
        """Read the p-values STS wrote for one test, straight from its own
        results.txt (format: 'index\\tp_value' per line, one line per
        sub-variant when a test has them, e.g. per template)."""
        results_file = self.experiment_directory / dir_name / "results.txt"
        if not results_file.exists():
            return []

        p_values = []
        with open(results_file) as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                try:
                    p_values.append(float(parts[-1]))
                except ValueError:
                    continue
        return p_values