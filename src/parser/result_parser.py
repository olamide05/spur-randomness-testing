"""Result Parser."""
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
from statistics import mean


@dataclass
class TestResult:
    name: str
    status: str
    p_value: Optional[float]
    proportion: Optional[float]
    pass_rate: str
    mean_p_value: Optional[float]
    min_p_value: Optional[float]
    max_p_value: Optional[float]
    notes: str = ""


@dataclass
class ExperimentSummary:
    generator: str
    framework: str
    tests: List[TestResult]
    overall_passed: bool
    experiment_directory: Path


class ResultParser:
    def __init__(self, experiment_directory: Path, generator: str = ""):
        self.experiment_directory = Path(experiment_directory)
        self.generator = generator
        self.framework = "NIST STS 2.1.2"

    def parse(self) -> ExperimentSummary:
        report = self._read_file("finalAnalysisReport.txt")
        stats = self._parse_stats()
        results = self._parse_results()
        tests = self._parse_report(report, stats, results)
        overall = all(t.status == "Pass" for t in tests) if tests else False
        return ExperimentSummary(
            generator=self.generator,
            framework=self.framework,
            tests=tests,
            overall_passed=overall,
            experiment_directory=self.experiment_directory,
        )

    def _read_file(self, filename: str) -> str:
        path = self.experiment_directory / filename
        return path.read_text() if path.exists() else ""

    def _parse_stats(self) -> Dict[str, List[float]]:
        text = self._read_file("stats.txt")
        data = {}
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            name = lines[i]
            i += 1
            values = []
            while i < len(lines):
                try:
                    values.append(float(lines[i]))
                    i += 1
                except ValueError:
                    break
            if values:
                data[name] = values
        return data

    def _parse_results(self) -> Dict[str, List[int]]:
        text = self._read_file("results.txt")
        data = {}
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            name = lines[i]
            i += 1
            values = []
            while i < len(lines):
                try:
                    values.append(int(lines[i]))
                    i += 1
                except ValueError:
                    break
            if values:
                data[name] = values
        return data

    def _parse_report(self, report: str, stats: Dict, results: Dict) -> List[TestResult]:
        tests = []
        aggregated = {}
        seen = set()

        for line in report.splitlines():
            parsed = self._parse_line(line)
            if not parsed:
                continue

            name, pval_str, prop_str, starred = parsed

            # Skip lines where name is just "*" (malformed)
            if not name or name == "*":
                continue

            if name == "NonOverlappingTemplate":
                if name not in aggregated:
                    aggregated[name] = {"pvals": [], "passed": 0, "total": 0}
                if pval_str and pval_str not in ("----", "------"):
                    try:
                        aggregated[name]["pvals"].append(float(pval_str))
                    except:
                        pass
                if prop_str and "/" in prop_str:
                    try:
                        passed, total = map(int, prop_str.split("/"))
                        aggregated[name]["passed"] += passed
                        aggregated[name]["total"] += total
                    except:
                        pass
                continue

            if name in seen:
                continue
            seen.add(name)

            test = self._create_result(name, pval_str, prop_str, starred, stats, results)
            tests.append(test)

        if "NonOverlappingTemplate" in aggregated:
            agg = aggregated["NonOverlappingTemplate"]
            pval = mean(agg["pvals"]) if agg["pvals"] else None
            proportion = agg["passed"] / agg["total"] if agg["total"] > 0 else None
            pass_rate = f"{agg['passed']}/{agg['total']}"
            status = "Pass" if proportion and proportion >= 0.96 else "Fail" if proportion else "Not Run"
            pvals = stats.get("NonOverlappingTemplate", [])
            tests.append(TestResult(
                name="non_overlapping_template",
                status=status,
                p_value=pval,
                proportion=proportion,
                pass_rate=pass_rate,
                mean_p_value=mean(pvals) if pvals else None,
                min_p_value=min(pvals) if pvals else None,
                max_p_value=max(pvals) if pvals else None,
            ))

        return tests

    def _parse_line(self, line: str):
        # Match NIST report line
        # The * failure marker appears before the test name
        pattern = r'^\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+([\d.]+|----|------)\s+([\d/]+|------)\s+(.*)$'
        match = re.match(pattern, line)
        if match:
            rest = match.group(3).strip()
            # Check if rest starts with * (failure marker)
            starred = False
            if rest.startswith("*"):
                starred = True
                rest = rest[1:].strip()
            return (rest, match.group(1), match.group(2), starred)
        return None

    def _create_result(self, name: str, pval_str: str, prop_str: str, starred: bool,
                      stats: Dict, results: Dict) -> TestResult:
        p_value = None
        if pval_str and pval_str not in ("----", "------"):
            try:
                p_value = float(pval_str)
            except:
                pass

        proportion = None
        pass_rate = prop_str if prop_str not in ("------", "") else "0/0"
        if "/" in pass_rate:
            try:
                passed, total = map(int, pass_rate.split("/"))
                if total > 0:
                    proportion = passed / total
            except:
                pass

        if pass_rate == "0/0" or prop_str in ("------", ""):
            status = "Not Run"
        elif proportion and proportion >= 0.96:
            status = "Pass"
        else:
            status = "Fail"

        notes = "* FAILED" if starred else ""

        stat_values = stats.get(name, [])
        normalized = name.lower().replace(" ", "_").replace("-", "_")

        return TestResult(
            name=normalized,
            status=status,
            p_value=p_value,
            proportion=proportion,
            pass_rate=pass_rate,
            mean_p_value=mean(stat_values) if stat_values else None,
            min_p_value=min(stat_values) if stat_values else None,
            max_p_value=max(stat_values) if stat_values else None,
            notes=notes,
        )