import hashlib
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


class NISTRunner:
    DEFAULTS = {
        "block_frequency": {"block_length": 128},
        "non_overlapping_template": {"block_length": 9},
        "overlapping_template": {"block_length": 9},
        "approximate_entropy": {"block_length": 10},
        "serial": {"block_length": 16},
        "linear_complexity": {"block_length": 500},
    }

    TEST_ORDER = [
        "frequency", "block_frequency", "cumulative_sums", "runs",
        "longest_run", "rank", "fft", "non_overlapping_template",
        "overlapping_template", "universal", "approximate_entropy",
        "random_excursions", "random_excursions_variant", "serial",
        "linear_complexity",
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

    def _prepare_input_file(self) -> str:
        """Return the path to hand to assess's stdin, guaranteeing it's
        reachable from sts_dir (assess runs with cwd=sts_dir).

        assess reads this value with an unbounded C `scanf("%s", file)`
        into a fixed 200-byte buffer (sts-2.1.2/src/utilities.c), so this
        deliberately returns a short sts_dir-relative name rather than a
        long absolute path -- both to actually find the file (a bare
        filename only resolves if it's already inside sts_dir) and to
        stay well clear of that buffer.
        """
        abs_input = self.config.input_file.resolve()
        abs_sts = self.sts_dir

        try:
            return str(abs_input.relative_to(abs_sts))
        except ValueError:
            suffix = "".join(ch for ch in abs_input.suffix if ch.isalnum())[:10]
            safe_suffix = f".{suffix}" if suffix else ".bin"
            digest = hashlib.sha256(str(abs_input).encode()).hexdigest()[:16]
            dest = abs_sts / f"input_{digest}{safe_suffix}"
            if not dest.exists() or dest.stat().st_mtime < abs_input.stat().st_mtime:
                shutil.copy2(abs_input, dest)
            return dest.name

    def _get_param(self, test_name: str, param_name: str, default):
        test_cfg = self.config.tests.get(test_name)
        if test_cfg is None:
            return default
        return test_cfg.parameters.get(param_name, default)

    def _requires_custom_input(self) -> bool:
        """Whether STS needs its per-test selection/parameter dialogue.

        Selecting "all tests" in STS ignores disabled tests. It is therefore
        only safe when every test is enabled and every block length is still
        its STS default.
        """
        for test_name in self.TEST_ORDER:
            test_cfg = self.config.tests.get(test_name)
            if test_cfg is not None and not test_cfg.enabled:
                return True
        for test_name, defaults in self.DEFAULTS.items():
            for param_name, default_val in defaults.items():
                actual = self._get_param(test_name, param_name, default_val)
                if actual != default_val:
                    return True
        return False

    def _build_input_all_tests(self, mode: int, input_name: str) -> str:
        lines = [
            "0",
            input_name,
            "1",
            "0",
            str(self.config.number_of_streams),
            str(mode),
        ]
        return "\n".join(lines) + "\n"

    def _build_input_custom(self, mode: int, input_name: str) -> str:
        lines = [
            "0",
            input_name,
            "0",
        ]

        for test_name in self.TEST_ORDER:
            test_cfg = self.config.tests.get(test_name)
            enabled = test_cfg.enabled if test_cfg is not None and hasattr(test_cfg, "enabled") else True
            lines.append("1" if enabled else "0")

        # STS numbers this menu from only the enabled parameterized tests.
        # Build it dynamically; fixed IDs apply the wrong value as soon as a
        # preceding test is unchecked.
        menu_index = 0
        for test_name, defaults in self.DEFAULTS.items():
            test_cfg = self.config.tests.get(test_name)
            enabled = test_cfg.enabled if test_cfg is not None else True
            if enabled:
                menu_index += 1
                block_len = self._get_param(test_name, "block_length", defaults["block_length"])
                lines.extend([str(menu_index), str(block_len)])

        lines.append("0")
        lines.append(str(self.config.number_of_streams))
        lines.append(str(mode))

        return "\n".join(lines) + "\n"

    def _build_input(self, mode: int, input_name: str) -> str:
        if self._requires_custom_input():
            return self._build_input_custom(mode, input_name)
        return self._build_input_all_tests(mode, input_name)

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

        placeholder = algo_dir / "create-dir-script"
        if not placeholder.exists():
            placeholder.touch()

    def _clean_old_results(self):
        sts_dir = self.sts_dir
        for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
            p = sts_dir / name
            if p.exists():
                p.unlink()

        algo_dir = sts_dir / "experiments" / "AlgorithmTesting"
        if algo_dir.exists():
            for item in algo_dir.iterdir():
                if item.is_dir():
                    for f in item.iterdir():
                        if f.is_file():
                            f.unlink()
                elif item.is_file() and item.name != "create-dir-script":
                    item.unlink()

    def _copy_results(self, dest: Path):
        sts_dir = self.sts_dir
        for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
            src = sts_dir / name
            if src.exists():
                shutil.copy2(src, dest / name)

        algo_dir = sts_dir / "experiments" / "AlgorithmTesting"
        if algo_dir.exists():
            for item in algo_dir.iterdir():
                if item.is_file() and item.name != "create-dir-script":
                    shutil.copy2(item, dest / item.name)
                elif item.is_dir():
                    dst = dest / item.name
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)

    def run(self) -> Path:
        mode = self._detect_mode(self.config.input_file)
        input_name = self._prepare_input_file()

        exp_name = self.config.input_file.stem
        self.exp_dir = Path("experiments") / f"{exp_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.exp_dir.mkdir(parents=True, exist_ok=True)

        self._setup_directories()
        self._clean_old_results()

        cmd = ["./assess", str(self.config.stream_length)]
        inp = self._build_input(mode, input_name)

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