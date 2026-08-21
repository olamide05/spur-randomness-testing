"""Persist a durable record of every simulation run.

Folder naming convention: DDMMYY_<identifier>[_<md5_first5>]/, one subfolder
per simulation, nested under the top-level ARCHIVE_ROOT.
"""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from werkzeug.utils import secure_filename

from src.exporters.html_exporter import export_html

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_ROOT = REPO_ROOT / "nist_algorithm_testing"


def _md5_first5(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:5]


def _folder_name(
    kind: str,
    date_str: str,
    generator: str,
    original_filename: Optional[str],
    bitstream_path: Path,
) -> str:
    if kind == "upload":
        safe_name = secure_filename(Path(original_filename or generator).stem) or generator
        return f"{date_str}_{safe_name}_{_md5_first5(bitstream_path)}"

    tag = {"c": "C", "sv": "SV"}[kind]
    base = f"{date_str}_{tag}_{secure_filename(generator) or generator}"
    if not (ARCHIVE_ROOT / base).exists():
        return base
    return f"{base}_{_md5_first5(bitstream_path)}"


def archive_run(
    kind: str,
    *,
    generator: str,
    experiment_dir: Path,
    summary,
    run_config,
    bitstream_path: Path,
    original_filename: Optional[str] = None,
    c_source_path: Optional[Path] = None,
    sv_core_path: Optional[Path] = None,
    sv_binary_path: Optional[Path] = None,
) -> Path:
    """Archive one simulation run under ARCHIVE_ROOT and return its folder."""
    if kind not in ("upload", "c", "sv"):
        raise ValueError(f"Unknown archive kind: {kind}")

    experiment_dir = Path(experiment_dir)
    bitstream_path = Path(bitstream_path)
    date_str = datetime.now().strftime("%d%m%y")

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    folder = ARCHIVE_ROOT / _folder_name(
        kind, date_str, generator, original_filename, bitstream_path
    )
    folder.mkdir(parents=True, exist_ok=True)

    if kind == "upload":
        dest_name = secure_filename(Path(original_filename or bitstream_path.name).name)
        shutil.copy2(bitstream_path, folder / (dest_name or bitstream_path.name))
    elif kind == "c":
        c_source_path = Path(c_source_path)
        shutil.copy2(c_source_path, folder / c_source_path.name)
        shutil.copy2(bitstream_path, folder / bitstream_path.name)
    else:
        shutil.copy2(sv_core_path, folder / "core.sv")
        shutil.copy2(sv_binary_path, folder / "testbench_binary")
        shutil.copy2(bitstream_path, folder / bitstream_path.name)

    export_html(summary, folder / "report.html", config=run_config)
    shutil.make_archive(
        str(folder / "algorithm_testing_results"), "zip", root_dir=experiment_dir
    )

    return folder
