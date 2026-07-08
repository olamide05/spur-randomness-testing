from pathlib import Path
from typing import List, Optional
import shutil


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_experiment_dirs(base_dir: Path, pattern: str = "*") -> List[Path]:
    if not base_dir.exists():
        return []
    return sorted([d for d in base_dir.glob(pattern) if d.is_dir()])


def get_latest_experiment(base_dir: Path) -> Optional[Path]:
    dirs = find_experiment_dirs(base_dir)
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def get_sts_result_files(experiment_dir: Path) -> dict:
    return {
        "final_report": experiment_dir / "finalAnalysisReport.txt",
        "stats": experiment_dir / "stats.txt",
        "results": experiment_dir / "results.txt",
        "freq": experiment_dir / "freq.txt",
        "matrix": experiment_dir / "matrix.txt",
    }