import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


@dataclass
class TestConfig:
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class STSConfig:
    sts_path: Path
    input_file: Path
    generator: str
    stream_length: int
    number_of_streams: int
    input_mode: Optional[int] = None
    tests: Dict[str, TestConfig] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str) -> "STSConfig":
        with open(path) as f:
            data = json.load(f)

        tests = {}
        for name, cfg in data.get("tests", {}).items():
            tests[name] = TestConfig(
                enabled=cfg.get("enabled", True),
                parameters={k: v for k, v in cfg.items() if k != "enabled"}
            )

        return cls(
            sts_path=Path(data["sts_path"]),
            input_file=Path(data["input_file"]),
            generator=data["generator"],
            stream_length=data["stream_length"],
            number_of_streams=data["number_of_streams"],
            input_mode=data.get("input_mode"),
            tests=tests
        )

    def to_json(self, path: str):
        data = {
            "sts_path": str(self.sts_path),
            "input_file": str(self.input_file),
            "generator": self.generator,
            "stream_length": self.stream_length,
            "number_of_streams": self.number_of_streams,
            "input_mode": self.input_mode,
            "tests": {}
        }
        for name, cfg in self.tests.items():
            data["tests"][name] = {"enabled": cfg.enabled, **cfg.parameters}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)