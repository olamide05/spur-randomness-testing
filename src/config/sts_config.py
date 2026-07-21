"""NIST STS Configuration with auto file type detection."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any


@dataclass
class STSConfig:
    """Configuration that auto-detects ASCII vs Binary."""
    sts_path: Path
    input_file: Path
    generator: str
    stream_length: int = 1_000_000
    number_of_streams: int = 100
    input_mode: Optional[int] = None  # None = auto-detect
    run_all_tests: bool = True
    selected_tests: List[int] = field(default_factory=list)
    experiments_directory: Optional[Path] = None
    tests: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        self.sts_path = Path(self.sts_path).resolve()
        self.input_file = Path(self.input_file).resolve()

        if self.experiments_directory is None:
            self.experiments_directory = Path("experiments").resolve()
        else:
            self.experiments_directory = Path(self.experiments_directory).resolve()

        # Auto-detect input mode if not specified
        if self.input_mode is None:
            self.input_mode = self._detect_mode()

        if self.stream_length < 100_000:
            raise ValueError("stream_length must be >= 100,000")
        if self.number_of_streams < 1:
            raise ValueError("number_of_streams must be >= 1")
        if self.input_mode not in (0, 1):
            raise ValueError("input_mode must be 0 (ASCII) or 1 (Binary)")

    def _detect_mode(self) -> int:
        """Auto-detect if file is ASCII or binary."""
        with open(self.input_file, "rb") as f:
            data = f.read(1000)

        if not data:
            raise ValueError("Input file is empty")

        # ASCII files only contain '0', '1', whitespace
        ascii_chars = {ord("0"), ord("1"), ord(" "), ord("\n"), ord("\r"), ord("\t")}

        for byte in data:
            if byte not in ascii_chars:
                return 1  # Binary

        return 0  # ASCII

    def get_file_info(self) -> dict:
        """Get file info for display."""
        size = self.input_file.stat().st_size
        if self.input_mode == 0:
            total_bits = size
            mode_name = "ASCII"
        else:
            total_bits = size * 8
            mode_name = "Binary"

        return {
            "path": str(self.input_file),
            "size_bytes": size,
            "total_bits": total_bits,
            "input_mode": self.input_mode,
            "mode_name": mode_name,
        }

    def get_test_param(self, name: str, key: str, default: Any = None) -> Any:
        return self.tests.get(name, {}).get(key, default)

    def is_test_enabled(self, name: str) -> bool:
        return self.tests.get(name, {}).get("enabled", True)

    def get_assess_executable(self) -> Path:
        return self.sts_path / "assess"

    def get_experiment_path(self) -> Path:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() else "_" for c in self.generator)
        return self.experiments_directory / f"{safe}_{self.stream_length}_{self.number_of_streams}_{ts}"

    @classmethod
    def from_json(cls, path: Path) -> "STSConfig":
        with open(path) as f:
            data = json.load(f)

        return cls(
            sts_path=Path(data["sts_path"]),
            input_file=Path(data["input_file"]),
            generator=data["generator"],
            stream_length=data.get("stream_length", 1_000_000),
            number_of_streams=data.get("number_of_streams", 100),
            input_mode=data.get("input_mode"),  # None = auto-detect
            run_all_tests=data.get("run_all_tests", True),
            selected_tests=data.get("selected_tests", []),
            experiments_directory=Path(data["experiments_directory"]) if "experiments_directory" in data else None,
            tests=data.get("tests", {}),
        )