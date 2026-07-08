import subprocess
import shutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from ..config.sts_config import STSConfig
from ..utils.validation import validate_input_file, calculate_num_streams, ValidationResult
from ..utils.path_utils import ensure_directory, get_sts_result_files


@dataclass
class RunResult:
    experiment_directory: Path
    stdout: str
    stderr: str
    return_code: int
    success: bool


class NISTRunner:
    def __init__(self, config: STSConfig):
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        assess = self.config.get_assess_executable()
        if not assess.exists():
            raise FileNotFoundError(f"assess not found: {assess}")
        if not self.config.input_file.exists():
            raise FileNotFoundError(f"Input not found: {self.config.input_file}")

    def validate_input(self) -> ValidationResult:
        return validate_input_file(self.config.input_file, self.config.input_mode)

    def calculate_num_streams(self, bit_count: Optional[int] = None) -> int:
        if bit_count is None:
            result = self.validate_input()
            if not result:
                raise ValueError(f"Invalid input: {result.message}")
            bit_count = result.bit_count
        return calculate_num_streams(bit_count, self.config.stream_length)

    def build_sts_answers(self) -> str:
        answers = [
            str(self.config.input_file),
            str(self.config.input_mode),
            str(self.config.stream_length),
            "1" if self.config.run_all_tests else "0",
            str(self.config.number_of_streams),
        ]

        if not self.config.run_all_tests:
            for i in range(1, 16):
                answers.append("1" if i in self.config.selected_tests else "0")

        return "\n".join(answers) + "\n"

    def build_parameter_answers(self) -> str:
        answers = []
        params = self.config.test_parameters

        if self._should_answer(2):
            answers.append(str(params.get("block_frequency", {}).get("block_length", 128)))

        if self._should_answer(8):
            tmpl = params.get("non_overlapping_template", {})
            answers.append(str(tmpl.get("template_length", 9)))
            answers.append(str(tmpl.get("templates", 148)))

        if self._should_answer(9):
            answers.append(str(params.get("overlapping_template", {}).get("template_length", 9)))

        if self._should_answer(11):
            answers.append(str(params.get("approximate_entropy", {}).get("block_length", 10)))

        if self._should_answer(14):
            answers.append(str(params.get("serial", {}).get("block_length", 16)))

        if self._should_answer(15):
            answers.append(str(params.get("linear_complexity", {}).get("block_length", 500)))

        return "\n".join(answers) + "\n" if answers else ""

    def _should_answer(self, test_index: int) -> bool:
        if self.config.run_all_tests:
            return True
        return test_index in self.config.selected_tests

    def build_complete_input(self) -> str:
        sts = self.build_sts_answers()
        params = self.build_parameter_answers()
        return sts + params if params else sts

    def run(self, timeout: Optional[int] = 3600) -> RunResult:
        validation = self.validate_input()
        if not validation:
            return RunResult(Path(), "", f"Validation failed: {validation.message}", -1, False)

        exp_dir = self.config.get_experiment_path()
        ensure_directory(exp_dir)

        input_data = self.build_complete_input()
        assess_path = self.config.get_assess_executable()

        try:
            result = subprocess.run(
                [str(assess_path)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.config.sts_path)
            )

            self._copy_results(exp_dir)

            return RunResult(
                experiment_directory=exp_dir,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                success=result.returncode == 0
            )

        except subprocess.TimeoutExpired:
            return RunResult(exp_dir, "", f"Timeout after {timeout}s", -1, False)
        except Exception as e:
            return RunResult(exp_dir, "", str(e), -1, False)

    def _copy_results(self, exp_dir: Path) -> None:
        for name, src in get_sts_result_files(self.config.sts_path).items():
            if src.exists():
                shutil.copy2(src, exp_dir / src.name)