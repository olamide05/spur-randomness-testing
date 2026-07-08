"""Result Parser module - handles REAL NIST STS output properly."""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from statistics import mean


@dataclass
class TestResult:
    name: str
    status: str = "unknown"
    passed: Optional[bool] = None
    p_value: Optional[float] = None
    proportion: Optional[float] = None
    pass_rate: str = ""
    p_values: List[float] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "passed": self.passed,
            "p_value": self.p_value,
            "proportion": self.proportion,
            "pass_rate": self.pass_rate,
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

    def __init__(self, experiment_directory: Path, generator: str = ""):
        self.experiment_directory = Path(experiment_directory)
        if not self.experiment_directory.exists():
            raise FileNotFoundError(f"Not found: {experiment_directory}")
        self.generator = generator

    def parse(self) -> ExperimentSummary:
        summary = ExperimentSummary(
            experiment_directory=str(self.experiment_directory),
            generator=self.generator
        )
        
        summary.raw_final_report = self._read("finalAnalysisReport.txt")
        summary.raw_stats = self._read("stats.txt")
        summary.raw_results = self._read("results.txt")
        
        stats_data = self.parse_stats()
        results_data = self.parse_results()
        report_data = self.parse_final_report()
        
        return self.merge(summary, report_data, stats_data, results_data)

    def _read(self, filename: str) -> str:
        path = self.experiment_directory / filename
        if not path.exists():
            return ""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except (IOError, OSError):
            return ""

    def parse_stats(self) -> Dict[str, List[float]]:
        content = self._read("stats.txt")
        if not content:
            return {}

        data = {}
        current_test = None
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            
            if line in self.TEST_NAME_MAP:
                current_test = line
                data[current_test] = []
            elif current_test and self._is_p_value(line):
                data[current_test].append(float(line))
        
        return data

    def parse_results(self) -> Dict[str, List[bool]]:
        content = self._read("results.txt")
        if not content:
            return {}

        data = {}
        current_test = None
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            
            if line in self.TEST_NAME_MAP:
                current_test = line
                data[current_test] = []
            elif current_test and line in ("0", "1"):
                data[current_test].append(line == "1")
        
        return data

    def parse_final_report(self) -> Dict[str, Any]:
        content = self._read("finalAnalysisReport.txt")
        if not content:
            return {}

        data = {"tests": []}
        
        lines = content.splitlines()
        in_table = False
        
        test_aggregates = {}
        
        for line in lines:
            if "P-VALUE" in line and "STATISTICAL TEST" in line:
                in_table = True
                continue
            if in_table and line.strip() and not line.startswith("-"):
                test = self._parse_report_line(line)
                if test:
                    name = test["name"]
                    if name not in test_aggregates:
                        test_aggregates[name] = {
                            "name": name,
                            "raw_name": test["raw_name"],
                            "p_value": test.get("p_value"),
                            "passed_count": 0,
                            "total_count": 0,
                            "starred": False,
                        }
                    tc = test_aggregates[name]
                    tc["passed_count"] += int(test["proportion"] * test.get("total_count", 0))
                    tc["total_count"] += test.get("total_count", 0)
                    if test.get("starred"):
                        tc["starred"] = True
        
        for name, agg in test_aggregates.items():
            total = agg["total_count"]
            passed = agg["passed_count"]
            proportion = passed / total if total > 0 else 0
            
            if total == 0:
                status = "Not Run"
                passed_flag = None
            elif proportion >= 0.96:
                status = "Pass"
                passed_flag = True
            else:
                status = "Fail"
                passed_flag = False
            
            data["tests"].append({
                "name": name,
                "status": status,
                "p_value": agg["p_value"],
                "proportion": proportion,
                "passed": passed_flag,
                "pass_rate": f"{passed}/{total}",
                "raw_name": agg["raw_name"],
                "starred": agg["starred"],
            })
        
        return data

    def _parse_report_line(self, line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line:
            return None

        prop_match = re.search(r'(\d+)/(\d+)\s+([*\s]*)\s*(\S+)$', line)
        if not prop_match:
            return None

        passed_count = int(prop_match.group(1))
        total_count = int(prop_match.group(2))
        star = prop_match.group(3).strip()
        test_name = prop_match.group(4).strip()

        if test_name not in self.TEST_NAME_MAP:
            for full_name in self.TEST_NAME_MAP:
                if full_name.startswith(test_name) or test_name.startswith(full_name[:5]):
                    test_name = full_name
                    break

        proportion = passed_count / total_count if total_count > 0 else 0

        p_value = None
        p_match = re.search(r'([\d.]+|----)\s+\d+/\d+', line)
        if p_match:
            p_str = p_match.group(1)
            if p_str != "----":
                try:
                    p_value = float(p_str)
                except ValueError:
                    p_value = None

        return {
            "name": self.TEST_NAME_MAP.get(test_name, test_name.lower()),
            "proportion": proportion,
            "p_value": p_value,
            "raw_name": test_name,
            "starred": bool(star),
            "total_count": total_count,
        }

    def _is_p_value(self, s: str) -> bool:
        try:
            val = float(s)
            return 0 <= val <= 1
        except ValueError:
            return False

    def merge(self, summary: ExperimentSummary, report: Dict, stats: Dict, results: Dict) -> ExperimentSummary:
        tests = []
        
        for td in report.get("tests", []):
            tr = TestResult(
                name=td.get("name", "unknown"),
                status=td.get("status", "unknown"),
                passed=td.get("passed"),
                p_value=td.get("p_value"),
                proportion=td.get("proportion"),
                pass_rate=td.get("pass_rate", ""),
                notes="* FAILED" if td.get("starred") else "",
            )

            raw = td.get("raw_name", tr.name)
            
            if raw in stats and stats[raw]:
                tr.p_values = stats[raw]
                if tr.p_value is None:
                    tr.p_value = mean(tr.p_values)
            
            if raw in results and results[raw]:
                passes = results[raw]
                if tr.proportion is None:
                    tr.proportion = sum(passes) / len(passes)
                if tr.passed is None:
                    tr.passed = tr.proportion >= 0.96
                    tr.status = "Pass" if tr.passed else "Fail"
                if not tr.pass_rate:
                    tr.pass_rate = f"{sum(passes)}/{len(passes)}"

            tests.append(tr)

        summary.tests = tests
        if tests:
            run_tests = [t for t in tests if t.status != "Not Run"]
            if run_tests:
                summary.overall_passed = all(t.passed for t in run_tests if t.passed is not None)

        dir_name = self.experiment_directory.name
        parts = dir_name.split("_")
        if len(parts) >= 4:
            try:
                for i, part in enumerate(parts):
                    if part.isdigit() and len(part) >= 4:
                        summary.stream_length = int(part)
                        if i + 1 < len(parts) and parts[i + 1].isdigit():
                            summary.number_of_streams = int(parts[i + 1])
                        break
            except (ValueError, IndexError):
                pass

        return summary