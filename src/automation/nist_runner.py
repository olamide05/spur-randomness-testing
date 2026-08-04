import subprocess
import shutil
from pathlib import Path
from datetime import datetime


class NISTRunner:
    # NIST defaults for each parameter-adjustable test
    DEFAULTS = {
        "block_frequency": {"block_length": 128},
        "non_overlapping_template": {"block_length": 9},
        "overlapping_template": {"block_length": 9},
        "approximate_entropy": {"block_length": 10},
        "serial": {"block_length": 16},
        "linear_complexity": {"block_length": 500},
    }

    # Test order for the 15 NIST tests (1-15)
    TEST_ORDER = [
        "frequency",           # 1
        "block_frequency",     # 2
        "cumulative_sums",     # 3
        "runs",                # 4
        "longest_run",         # 5
        "rank",                # 6
        "fft",                 # 7
        "non_overlapping_template",  # 8
        "overlapping_template",      # 9
        "universal",           # 10
        "approximate_entropy", # 11
        "random_excursions",   # 12
        "random_excursions_variant", # 13
        "serial",              # 14
        "linear_complexity",   # 15
    ]

    def __init__(self, config):
        self.config = config
        self.sts_dir = config.sts_path.resolve()
        self.exp_dir = None

    def _detect_mode(self, file_path: Path) -> int:
        if self.config.input_mode is not None:
            return self.config.input_mode
        with open(file_path, "rb") as f:
            sample = f.read(1000)
        text = sample.decode("ascii", errors="ignore")
        valid = set("01 \n\r\t")
        if all(c in valid for c in text) and len(text) > 100:
            return 0
        return 1

    def _relative_input(self) -> str:
        abs_input = self.config.input_file.resolve()
        abs_sts = self.sts_dir.resolve()
        try:
            return str(abs_input.relative_to(abs_sts))
        except ValueError:
            return str(abs_input.name)

    def _get_param(self, test_name: str, param_name: str, default):
        test_cfg = self.config.tests.get(test_name)
        if test_cfg is None:
            return default
        return test_cfg.parameters.get(param_name, default)

    def _has_custom_params(self) -> bool:
        """Check if any test parameter differs from NIST default."""
        for test_name, defaults in self.DEFAULTS.items():
            for param_name, default_val in defaults.items():
                actual = self._get_param(test_name, param_name, default_val)
                if actual != default_val:
                    return True
        return False

    def _build_input_all_tests(self, mode: int) -> str:
        """Path A: Run all tests with default parameters."""
        lines = [
            "0",                           # Input File
            self._relative_input(),        # file path
            "1",                           # run ALL tests
            "0",                           # continue (accept defaults)
            str(self.config.number_of_streams),
            str(mode),
        ]
        return "\n".join(lines) + "\n"

    def _build_input_custom(self, mode: int) -> str:
        """Path B: Custom test selection with adjustable parameters."""
        lines = [
            "0",                           # Input File
            self._relative_input(),        # file path
            "0",                           # custom test selection
        ]

        # Enable/disable each of the 15 tests
        for test_name in self.TEST_ORDER:
            test_cfg = self.config.tests.get(test_name)
            if test_cfg is not None and hasattr(test_cfg, "enabled"):
                enabled = test_cfg.enabled
            else:
                enabled = True
            lines.append("1" if enabled else "0")

        # Parameter adjustments
        # [1] Block Frequency
        block_len = self._get_param("block_frequency", "block_length", 128)
        lines.extend(["1", str(block_len)])

        # [2] NonOverlapping Template
        non_overlap_len = self._get_param("non_overlapping_template", "block_length", 9)
        lines.extend(["2", str(non_overlap_len)])

        # [3] Overlapping Template
        overlap_len = self._get_param("overlapping_template", "block_length", 9)
        lines.extend(["3", str(overlap_len)])

        # [4] Approximate Entropy
        approx_len = self._get_param("approximate_entropy", "block_length", 10)
        lines.extend(["4", str(approx_len)])

        # [5] Serial
        serial_len = self._get_param("serial", "block_length", 16)
        lines.extend(["5", str(serial_len)])

        # [6] Linear Complexity
        linear_len = self._get_param("linear_complexity", "block_length", 500)
        lines.extend(["6", str(linear_len)])

        lines.append("0")  # done adjusting
        lines.append(str(self.config.number_of_streams))
        lines.append(str(mode))

        return "\n".join(lines) + "\n"

    def _build_input(self, mode: int) -> str:
        if self._has_custom_params():
            return self._build_input_custom(mode)
        return self._build_input_all_tests(mode)

    def _setup_directories(self):
        sts_dir = self.sts_dir
        algo_dir = sts_dir / "experiments" / "AlgorithmTesting"
        algo_dir.mkdir(parents=True, exist_ok=True)

        test_names = [
            "Frequency", "BlockFrequency", "CumulativeSums", "Runs",
            "LongestRun", "Rank", "FFT", "NonOverlappingTemplate",
            "OverlappingTemplate", "Universal", "ApproximateEntropy",
            "RandomExcursions", "RandomExcursionsVariant", "Serial", "LinearComplexity"
        ]
        for name in test_names:
            (algo_dir / name).mkdir(exist_ok=True)
            for f in (algo_dir / name).iterdir():
                if f.is_file():
                    f.unlink()

    def _clean_old_results(self):
        sts_dir = self.sts_dir
        for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
            p = sts_dir / name
            if p.exists():
                p.unlink()

    def _copy_results(self, dest: Path):
        sts_dir = self.sts_dir
        for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
            src = sts_dir / name
            if src.exists():
                shutil.copy2(src, dest / name)

        algo_dir = sts_dir / "experiments" / "AlgorithmTesting"
        if algo_dir.exists():
            for item in algo_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dest / item.name)
                elif item.is_dir():
                    dst = dest / item.name
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)

    def run(self) -> Path:
        mode = self._detect_mode(self.config.input_file)

        self.exp_dir = Path("experiments") / f"{self.config.generator}_{self.config.stream_length}_{self.config.number_of_streams}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.exp_dir.mkdir(parents=True, exist_ok=True)

        self._setup_directories()
        self._clean_old_results()

        cmd = ["./assess", str(self.config.stream_length)]
        inp = self._build_input(mode)

        result = subprocess.run(
            cmd,
            input=inp,
            cwd=self.sts_dir,
            capture_output=True,
            text=True,
            timeout=600
        )

        self._copy_results(self.exp_dir)

        report = self.sts_dir / "experiments" / "AlgorithmTesting" / "finalAnalysisReport.txt"
        if not report.exists() or report.stat().st_size < 100:
            raise RuntimeError(f"assess failed. stdout: {result.stdout[-500:]}")

        return self.exp_dir