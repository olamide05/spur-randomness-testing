from dataclasses import dataclass, field
from typing import Dict, List
from pathlib import Path


@dataclass
class STSConfig:
    sts_path: Path
    input_file: Path
    generator: str
    stream_length: int
    number_of_streams: int
    input_mode: int = 0
    run_all_tests: bool = True
    selected_tests: List[int] = field(default_factory=list)
    test_parameters: Dict[str, Dict] = field(default_factory=dict)
    experiments_directory: Path = field(default_factory=lambda: Path("experiments"))

    def __post_init__(self):
        self.sts_path = Path(self.sts_path).resolve()
        self.input_file = Path(self.input_file).resolve()
        self.experiments_directory = Path(self.experiments_directory).resolve()

        if self.input_mode not in (0, 1):
            raise ValueError("input_mode must be 0 or 1")
        if self.stream_length < 100000:
            raise ValueError("stream_length must be >= 100000")
        if self.number_of_streams < 1:
            raise ValueError("number_of_streams must be >= 1")
        if not self.run_all_tests and not self.selected_tests:
            raise ValueError("selected_tests required when run_all_tests=False")

        invalid = set(self.selected_tests) - set(range(1, 16))
        if invalid:
            raise ValueError(f"Invalid test indices: {invalid}")

    def get_assess_executable(self) -> Path:
        return self.sts_path / "assess"

    def get_experiment_path(self) -> Path:
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{self.generator}_{self.stream_length}_{self.number_of_streams}_{ts}"
        return self.experiments_directory / name