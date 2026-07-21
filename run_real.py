#!/usr/bin/env python3
"""Run NIST STS using config.json with auto file type detection."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.config.sts_config import STSConfig
from src.automation.nist_runner import NISTRunner
from src.parser.result_parser import ResultParser
from src.exporters import export_json, export_csv, export_latex
from src.exporters.html_exporter import export_html


def list_files():
    data_dir = Path("sts/sts-2.1.2/data").resolve()
    if not data_dir.exists():
        print("ERROR: NIST data directory not found")
        return
    for f in sorted(data_dir.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name:20s} ({size:,} bytes)")


def run(config_path: Path):
    config = STSConfig.from_json(config_path)
    info = config.get_file_info()

    print(f"Generator: {config.generator}")
    print(f"File: {config.input_file}")
    print(f"Detected: {info['mode_name']} ({info['total_bits']:,} bits)")
    print(f"Streams: {config.number_of_streams} x {config.stream_length:,} bits")
    print()

    needed = config.stream_length * config.number_of_streams
    print(f"Needed: {needed:,} bits")

    if info["total_bits"] < needed:
        config.number_of_streams = info["total_bits"] // config.stream_length
        if config.number_of_streams < 1:
            print("ERROR: Not enough data")
            sys.exit(1)
        print(f"Adjusted to {config.number_of_streams} streams")

    print("\nRunning NIST STS...")
    runner = NISTRunner(config)
    result = runner.run()

    if not result.success:
        print(f"FAILED: {result.stderr}")
        print(f"Stdout: {result.stdout[-500:]}")
        sys.exit(1)

    print(f"Done. Results: {result.experiment_directory}")

    summary = ResultParser(result.experiment_directory, generator=config.generator).parse()

    print(f"\nOverall: {'PASS' if summary.overall_passed else 'FAIL'}")
    print(f"Tests: {len(summary.tests)}")
    for t in summary.tests:
        icon = "OK" if t.status == "Pass" else "XX" if t.status == "Fail" else "--"
        print(f"  [{icon}] {t.name:30s} {t.pass_rate}")

    export_json(summary)
    export_csv(summary)
    export_latex(summary)
    html_path = export_html(summary)

    print(f"\nReports exported.")
    print(f"Dashboard: {html_path}")


def main():
    parser = argparse.ArgumentParser(description="Run NIST STS")
    parser.add_argument("--config", "-c", type=Path, default=Path("config.json"), help="Config JSON file")
    parser.add_argument("--list", action="store_true", help="List available NIST data files")
    args = parser.parse_args()

    if args.list:
        list_files()
        return

    if not args.config.exists():
        print(f"Config not found: {args.config}")
        sys.exit(1)

    run(args.config)


if __name__ == "__main__":
    main()