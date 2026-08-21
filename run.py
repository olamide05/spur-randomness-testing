import argparse
import json
import multiprocessing
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from types import SimpleNamespace

from src.config.sts_config import STSConfig, TestConfig
from src.automation.nist_runner import NISTRunner
from src.parser.result_parser import ResultParser, ExperimentSummary, TestResult
from src.exporters import export_json, export_csv, export_latex, export_html
from src.core.archive_writer import archive_run
from src.core.batch_reporter import BatchReporter


def _auto_calculate(file_path: Path) -> tuple:
    file_size = file_path.stat().st_size
    with open(file_path, "rb") as f:
        sample = f.read(1000)
    text = sample.decode("ascii", errors="ignore")
    valid = set("01 \n\r\t")
    is_ascii = all(c in valid for c in text) and len(text) > 100
    total_bits = file_size if is_ascii else file_size * 8
    
    stream_length = 100000
    number_of_streams = min(total_bits // stream_length, 10)
    
    if number_of_streams < 1:
        stream_length = max(1000, total_bits)
        number_of_streams = 1
    
    return stream_length, number_of_streams


def _build_config_from_inline(sts_path: Path, run_cfg: dict) -> STSConfig:
    input_file = Path(run_cfg["input_file"])
    
    stream_length = run_cfg.get("stream_length")
    number_of_streams = run_cfg.get("number_of_streams")
    
    if stream_length is None or number_of_streams is None:
        auto_len, auto_streams = _auto_calculate(input_file)
        stream_length = stream_length or auto_len
        number_of_streams = number_of_streams or auto_streams
    
    file_size = input_file.stat().st_size
    with open(input_file, "rb") as f:
        sample = f.read(1000)
    text = sample.decode("ascii", errors="ignore")
    valid = set("01 \n\r\t")
    is_ascii = all(c in valid for c in text) and len(text) > 100
    total_bits = file_size if is_ascii else file_size * 8
    needed = stream_length * number_of_streams
    
    if needed > total_bits:
        number_of_streams = max(1, total_bits // stream_length)
        print(f"  Warning: adjusted streams to {number_of_streams} (file has {total_bits:,} bits)")
    
    tests = {}
    test_overrides = run_cfg.get("tests", {})
    default_tests = [
        "frequency", "block_frequency", "cumulative_sums", "runs",
        "longest_run", "rank", "fft", "non_overlapping_template",
        "overlapping_template", "universal", "approximate_entropy",
        "random_excursions", "random_excursions_variant", "serial",
        "linear_complexity"
    ]
    for test_name in default_tests:
        override = test_overrides.get(test_name, {})
        tests[test_name] = TestConfig(
            enabled=override.get("enabled", True),
            parameters={k: v for k, v in override.items() if k != "enabled"}
        )
    
    return STSConfig(
        sts_path=sts_path,
        input_file=input_file,
        generator=run_cfg["name"],
        stream_length=stream_length,
        number_of_streams=number_of_streams,
        tests=tests
    )


def _run_worker(config_dict: dict) -> dict:
    """Run one test in an isolated temp directory for true parallelism."""
    original_sts_path = Path(config_dict["sts_path"]).resolve()
    input_file = Path(config_dict["input_file"]).resolve()
    original_input_name = input_file.name
    project_root = Path(config_dict["project_root"]).resolve()
    
    os.chdir(project_root)
    temp_dir = Path(tempfile.mkdtemp(prefix="sts_worker_"))
    
    try:
        # Copy entire STS tree to temp dir
        temp_sts = temp_dir / "sts"
        shutil.copytree(original_sts_path, temp_sts)
        
        # Copy input file into temp STS dir preserving relative path
        try:
            rel_path = input_file.relative_to(original_sts_path)
            dest = temp_sts / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_file, dest)
            input_file = dest
        except ValueError:
            dest = temp_sts / input_file.name
            shutil.copy2(input_file, dest)
            input_file = dest
        
        # Rebuild config pointing at temp dir and copied file
        tests = {}
        for k, v in config_dict["tests"].items():
            tests[k] = TestConfig(enabled=v["enabled"], parameters=v.get("parameters", {}))
        
        config = STSConfig(
            sts_path=temp_sts,
            input_file=input_file,
            generator=config_dict["generator"],
            stream_length=config_dict["stream_length"],
            number_of_streams=config_dict["number_of_streams"],
            tests=tests
        )
        
        runner = NISTRunner(config)
        exp_dir = runner.run()
        
        parser = ResultParser(exp_dir, generator=config.generator, number_of_streams=config.number_of_streams)
        summary = parser.parse()
        
        export_json(summary)
        export_csv(summary)
        export_latex(summary)
        export_html(summary)

        archive_run(
            "upload",
            generator=config.generator,
            experiment_dir=exp_dir,
            summary=summary,
            run_config=SimpleNamespace(
                stream_length=config.stream_length,
                number_of_streams=config.number_of_streams,
                tests=config_dict["tests"],
            ),
            bitstream_path=input_file,
            original_filename=original_input_name,
        )

        return {
            "generator": summary.generator,
            "overall_status": summary.overall_status,
            "experiment_directory": str(exp_dir),
            "tests": [
                {
                    "name": t.name,
                    "status": t.status,
                    "passed": t.passed,
                    "total": t.total,
                    "p_value": t.p_value,
                    "proportion": t.proportion
                }
                for t in summary.tests
            ]
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_single(config_path: str):
    config = STSConfig.from_json(config_path)
    config_dict = {
        "sts_path": str(config.sts_path),
        "input_file": str(config.input_file),
        "generator": config.generator,
        "stream_length": config.stream_length,
        "number_of_streams": config.number_of_streams,
        "tests": {k: {"enabled": v.enabled, "parameters": v.parameters} for k, v in config.tests.items()},
        "project_root": str(Path.cwd())
    }
    result = _run_worker(config_dict)
    
    print(f"\nOverall: {result['overall_status'].upper()}")
    print(f"Tests: {len(result['tests'])}")
    for t in result["tests"]:
        icon = "[OK]" if t["status"] == "pass" else "[XX]" if t["status"] == "fail" else "[--]"
        print(f"  {icon} {t['name']:30s} {t['passed']}/{t['total']}")
    print(f"\nDashboard: {result['experiment_directory']}/dashboard.html")


def run_quick(file_path: str, name: str, streams: int = None, length: int = None):
    input_file = Path(file_path)
    
    stream_length = length
    number_of_streams = streams
    if stream_length is None or number_of_streams is None:
        auto_len, auto_streams = _auto_calculate(input_file)
        stream_length = stream_length or auto_len
        number_of_streams = number_of_streams or auto_streams
    
    default_tests = [
        "frequency", "block_frequency", "cumulative_sums", "runs",
        "longest_run", "rank", "fft", "non_overlapping_template",
        "overlapping_template", "universal", "approximate_entropy",
        "random_excursions", "random_excursions_variant", "serial",
        "linear_complexity"
    ]
    
    config_dict = {
        "sts_path": "sts/sts-2.1.2",
        "input_file": str(input_file),
        "generator": name,
        "stream_length": stream_length,
        "number_of_streams": number_of_streams,
        "tests": {k: {"enabled": True, "parameters": {}} for k in default_tests},
        "project_root": str(Path.cwd())
    }
    result = _run_worker(config_dict)
    
    print(f"\nOverall: {result['overall_status'].upper()}")
    print(f"Tests: {len(result['tests'])}")
    for t in result["tests"]:
        icon = "[OK]" if t["status"] == "pass" else "[XX]" if t["status"] == "fail" else "[--]"
        print(f"  {icon} {t['name']:30s} {t['passed']}/{t['total']}")
    print(f"\nDashboard: {result['experiment_directory']}/dashboard.html")


def run_batch(batch_path: str):
    with open(batch_path) as f:
        batch = json.load(f)
    
    sts_path = Path(batch.get("sts_path", "sts/sts-2.1.2"))
    project_root = str(Path.cwd())
    
    config_dicts = []
    for run_cfg in batch["runs"]:
        config = _build_config_from_inline(sts_path, run_cfg)
        config_dicts.append({
            "sts_path": str(config.sts_path),
            "input_file": str(config.input_file),
            "generator": config.generator,
            "stream_length": config.stream_length,
            "number_of_streams": config.number_of_streams,
            "tests": {k: {"enabled": v.enabled, "parameters": v.parameters} for k, v in config.tests.items()},
            "project_root": project_root
        })
    
    num_workers = min(len(config_dicts), multiprocessing.cpu_count())
    print(f"Batch mode: {len(config_dicts)} runs")
    print(f"Running in parallel on {num_workers} CPU cores...")
    print("=" * 60)
    
    with multiprocessing.Pool(processes=num_workers) as pool:
        results = pool.map(_run_worker, config_dicts)
    
    print("\nAll runs complete!")
    
    summaries = []
    for r in results:
        summary = ExperimentSummary(
            generator=r["generator"],
            experiment_directory=Path(r["experiment_directory"]),
            overall_status=r["overall_status"],
            tests=[TestResult(**t) for t in r["tests"]]
        )
        summaries.append(summary)
    
    reporter = BatchReporter(summaries)
    batch_dir = Path("batch_results") / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    reporter.generate_md(batch_dir / "comparison.md")
    reporter.generate_json(batch_dir / "comparison.json")
    reporter.generate_html(batch_dir / "comparison.html")
    
    print(f"\n{'='*60}")
    print(f"Comparison report: {batch_dir}")
    print(f"  comparison.md   → Markdown table")
    print(f"  comparison.json → Structured data")
    print(f"  comparison.html → Interactive dashboard")


def main():
    parser = argparse.ArgumentParser(description="NIST STS Test Runner")
    parser.add_argument("--config", default="config.json", help="Single test config JSON")
    parser.add_argument("--batch", help="Batch comparison config JSON")
    parser.add_argument("--file", help="Quick test: input file path")
    parser.add_argument("--name", help="Quick test: generator name")
    parser.add_argument("--streams", type=int, help="Quick test: number of streams")
    parser.add_argument("--length", type=int, help="Quick test: stream length")
    args = parser.parse_args()
    
    if args.batch:
        run_batch(args.batch)
    elif args.file:
        if not args.name:
            args.name = Path(args.file).stem
        run_quick(args.file, args.name, args.streams, args.length)
    else:
        run_single(args.config)


if __name__ == "__main__":
    main()
