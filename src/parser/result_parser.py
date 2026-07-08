import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from statistics import mean


@dataclass
class TestResult:
    name: str
    passed: Optional[bool] = None
    p_value: Optional[float] = None
    proportion: Optional[float] = None
    p_values: List[float] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "p_value": self.p_value,
            "proportion": self.proportion,
            "p_values": self.p_values,
            "mean_p_value": mean(self.p_values) if self.p_values else None,
            "min_p_value": min(self.p_values) if self.p_values else None,
            "max_p_value": max(self.p_values) if self.p_values else None,
            "notes": self.notes,
        }


@dataclass
class ExperimentSummary:
    experiment_directory: str
    generator: str = ""
    stream_length: int = 0
    number_of_streams: int = 0
    tests: List[TestResult] = field(default_factory=list)
    overall_passed: Optional[bool] = None
    raw_final_report: str = ""
    raw_stats: str = ""
    raw_results: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": "NIST STS 2.1.2",
            "experiment_directory": self.experiment_directory,
            "generator": self.generator,
            "stream_length": self.stream_length,
            "number_of_streams": self.number_of_streams,
            "overall_passed": self.overall_passed,
            "tests": [t.to_dict() for t in self.tests],
        }


class ResultParser:
    TEST_NAME_MAP = {
        "Frequency": "frequency",
        "BlockFrequency": "block_frequency",
        "CumulativeSums": "cumulative_sums",
        "Runs": "runs",
        "LongestRun": "longest_run",
        "Rank": "rank",
        "FFT": "fft",
        "NonOverlappingTemplate": "non_overlapping_template",
        "OverlappingTemplate": "overlapping_template",
        "Universal": "universal",
        "ApproximateEntropy": "approximate_entropy",
        "RandomExcursions": "random_excursions",
        "RandomExcursionsVariant": "random_excursions_variant",
        "Serial": "serial",
        "LinearComplexity": "linear_complexity",
    }

    def __init__(self, experiment_directory: Path):
        self.experiment_directory = Path(experiment_directory)
        if not self.experiment_directory.exists():
            raise FileNotFoundError(f"Not found: {experiment_directory}")

    def parse(self) -> ExperimentSummary:
        summary = ExperimentSummary(experiment_directory=str(self.experiment_directory))

        summary.raw_final_report = self._read("finalAnalysisReport.txt")
        summary.raw_stats = self._read("stats.txt")
        summary.raw_results = self._read("results.txt")

        return self.merge(
            summary,
            self.parse_final_report(),
            self.parse_stats(),
            self.parse_results()
        )

    def _read(self, filename: str) -> str:
        path = self.experiment_directory / filename
        if not path.exists():
            return ""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except (IOError, OSError):
            return ""

    def parse_final_report(self) -> Dict[str, Any]:
        content = self._read("finalAnalysisReport.txt")
        if not content:
            return {}

        data = {"generator": "", "tests": []}

        match = re.search(r'generator is (.+)', content)
        if match:
            data["generator"] = match.group(1).strip()

        lines = content.split('\n')
        in_table = False

        for line in lines:
            if "P-VALUE" in line and "STATISTICAL TEST" in line:
                in_table = True
                continue
            if in_table and line.strip():
                test = self._parse_line(line)
                if test:
                    data["tests"].append(test)

        return data

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        pattern = r'(?:\s+\d+){10}\s+([\d.]+)\s+(\d+)/(\d+)\s+(.+)'
        match = re.search(pattern, line)

        if match:
            passed = int(match.group(2))
            total = int(match.group(3))
            prop = passed / total if total > 0 else 0
            name = match.group(4).strip()

            return {
                "name": self.TEST_NAME_MAP.get(name, name.lower()),
                "p_value": float(match.group(1)),
                "proportion": prop,
                "passed": prop >= 0.96,
                "raw_name": name,
            }
        return None

    def parse_stats(self) -> Dict[str, List[float]]:
        content = self._read("stats.txt")
        if not content:
            return {}

        data = {}
        current = None

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line in self.TEST_NAME_MAP:
                current = line
                data[current] = []
            elif current and self._is_float(line):
                data[current].append(float(line))

        return data

    def parse_results(self) -> Dict[str, List[bool]]:
        content = self._read("results.txt")
        if not content:
            return {}

        data = {}
        current = None

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line in self.TEST_NAME_MAP:
                current = line
                data[current] = []
            elif current and line in ('0', '1'):
                data[current].append(line == '1')

        return data

    def _is_float(self, s: str) -> bool:
        try:
            float(s)
            return True
        except ValueError:
            return False

    def merge(self, summary: ExperimentSummary, report: Dict, stats: Dict, results: Dict) -> ExperimentSummary:
        if report.get("generator"):
            summary.generator = report["generator"]

        tests = []
        for td in report.get("tests", []):
            tr = TestResult(
                name=td.get("name", "unknown"),
                passed=td.get("passed"),
                p_value=td.get("p_value"),
                proportion=td.get("proportion"),
            )

            raw = td.get("raw_name", tr.name)
            if raw in stats:
                tr.p_values = stats[raw]
                if not tr.p_value and tr.p_values:
                    tr.p_value = mean(tr.p_values)

            if raw in results:
                passes = results[raw]
                if tr.proportion is None and passes:
                    tr.proportion = sum(passes) / len(passes)
                if tr.passed is None and passes:
                    tr.passed = tr.proportion >= 0.96

            tests.append(tr)

        summary.tests = tests
        if tests:
            summary.overall_passed = all(t.passed for t in tests if t.passed is not None)

        parts = self.experiment_directory.name.split('_')
        if len(parts) >= 3:
            try:
                summary.stream_length = int(parts[-3])
                summary.number_of_streams = int(parts[-2])
            except ValueError:
                pass

        return summary