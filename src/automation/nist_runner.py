"""NIST STS Runner."""
import subprocess
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.config.sts_config import STSConfig


@dataclass
class RunResult:
    experiment_directory: Path
    stdout: str
    stderr: str
    return_code: int
    success: bool


class NISTRunner:
    TEST_NAMES = [
        "Frequency", "BlockFrequency", "CumulativeSums", "Runs",
        "LongestRun", "Rank", "FFT", "NonOverlappingTemplate",
        "OverlappingTemplate", "Universal", "ApproximateEntropy",
        "RandomExcursions", "RandomExcursionsVariant", "Serial", "LinearComplexity"
    ]

    def __init__(self, config: STSConfig):
        self.config = config
        self._validate()

    def _validate(self):
        assess = self.config.get_assess_executable()
        if not assess.exists():
            raise FileNotFoundError(f"assess not found at {assess}. Build: cd {self.config.sts_path} && make")
        if not self.config.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.config.input_file}")

    def _setup_directories(self):
        """Ensure experiments/AlgorithmTesting/ exists with proper subdirectories.
        Clean old files but keep directory structure."""
        sts_dir = self.config.sts_path.resolve()
        algo_dir = sts_dir / "experiments" / "AlgorithmTesting"

        # Create if missing
        algo_dir.mkdir(parents=True, exist_ok=True)

        for name in self.TEST_NAMES:
            test_dir = algo_dir / name
            test_dir.mkdir(exist_ok=True)
            # Clear old files inside each test directory
            for f in test_dir.iterdir():
                if f.is_file():
                    f.unlink()

    def _relative_input(self) -> str:
        try:
            return str(self.config.input_file.relative_to(self.config.sts_path))
        except ValueError:
            return str(self.config.input_file)

    def build_input(self) -> str:
        lines = [
            "0",
            self._relative_input(),
            "1" if self.config.run_all_tests else "0",
        ]

        if not self.config.run_all_tests:
            for i in range(1, 16):
                lines.append("1" if i in self.config.selected_tests else "0")

        tests = self.config.tests

        if self._needs_param(2):
            lines.append(str(tests.get("block_frequency", {}).get("block_length", 128)))
            lines.append("0")

        if self._needs_param(8):
            lines.append(str(tests.get("non_overlapping_template", {}).get("template_length", 9)))
            lines.append(str(tests.get("non_overlapping_template", {}).get("num_templates", 148)))
            lines.append("0")

        if self._needs_param(9):
            lines.append(str(tests.get("overlapping_template", {}).get("template_length", 9)))
            lines.append("0")

        if self._needs_param(11):
            lines.append(str(tests.get("approximate_entropy", {}).get("block_length", 10)))
            lines.append("0")

        if self._needs_param(14):
            lines.append(str(tests.get("serial", {}).get("block_length", 16)))
            lines.append("0")

        if self._needs_param(15):
            lines.append(str(tests.get("linear_complexity", {}).get("block_length", 500)))
            lines.append("0")

        lines.append(str(self.config.number_of_streams))
        lines.append(str(self.config.input_mode))

        return "\n".join(lines) + "\n"

    def _needs_param(self, idx: int) -> bool:
        if self.config.run_all_tests:
            return True
        return idx in self.config.selected_tests

    def run(self, timeout: int = 3600) -> RunResult:
        exp_dir = self.config.get_experiment_path()
        exp_dir.mkdir(parents=True, exist_ok=True)

        self._setup_directories()

        # Clear old top-level result files
        sts_dir = self.config.sts_path.resolve()
        for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
            p = sts_dir / name
            if p.exists():
                p.unlink()

        assess = self.config.get_assess_executable().resolve()
        input_data = self.build_input()
        cwd = str(sts_dir)

        try:
            result = subprocess.run(
                [str(assess), str(self.config.stream_length)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            self._copy_results(exp_dir)

            success = (
                "Statistical Testing Complete" in result.stdout
                or (exp_dir / "finalAnalysisReport.txt").exists()
            )

            return RunResult(exp_dir, result.stdout, result.stderr, result.returncode, success)

        except subprocess.TimeoutExpired:
            return RunResult(exp_dir, "", f"Timeout after {timeout}s", -1, False)
        except Exception as e:
            return RunResult(exp_dir, "", str(e), -1, False)

    def _copy_results(self, exp_dir: Path):
        sts_dir = self.config.sts_path.resolve()
        for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
            src = sts_dir / name
            if src.exists():
                shutil.copy2(src, exp_dir / name)

        algo_dir = sts_dir / "experiments" / "AlgorithmTesting"
        if algo_dir.exists():
            for item in algo_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, exp_dir / item.name)
                elif item.is_dir():
                    dst = exp_dir / item.name
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)