import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.sts_config import STSConfig
from src.automation.nist_runner import NISTRunner
from src.parser.result_parser import ResultParser
from src.exporters import export_json, export_csv, export_latex, export_html


def main():
    parser = argparse.ArgumentParser(description="NIST STS Test Runner")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--file", help="Override input file")
    parser.add_argument("--generator", help="Override generator name")
    parser.add_argument("--streams", type=int, help="Override number of streams")
    args = parser.parse_args()

    config = STSConfig.from_json(args.config)

    if args.file:
        config.input_file = Path(args.file)
    if args.generator:
        config.generator = args.generator
    if args.streams:
        config.number_of_streams = args.streams

    file_size = config.input_file.stat().st_size
    bits = file_size * 8 if config.input_mode == 1 else file_size
    needed = config.stream_length * config.number_of_streams

    print(f"Generator: {config.generator}")
    print(f"File: {config.input_file.resolve()}")
    print(f"Streams: {config.number_of_streams} x {config.stream_length:,} bits")
    print(f"\nFile: {bits:,} bits | Needed: {needed:,} bits")

    if bits < needed:
        print(f"\nERROR: File too small. Need {needed:,} bits, have {bits:,}")
        sys.exit(1)

    print("\nRunning NIST STS...")
    runner = NISTRunner(config)
    exp_dir = runner.run()
    print(f"Done. Results: {exp_dir.resolve()}")

    parser = ResultParser(exp_dir, generator=config.generator)
    summary = parser.parse()

    status_icon = "PASS" if summary.overall_status == "pass" else "FAIL"
    print(f"\nOverall: {status_icon}")
    print(f"Tests: {len(summary.tests)}")

    for test in summary.tests:
        icon = "[OK]" if test.status == "pass" else "[XX]" if test.status == "fail" else "[--]"
        print(f"  {icon} {test.name:30s} {test.passed}/{test.total}")

    export_json(summary)
    export_csv(summary)
    export_latex(summary)
    html_path = export_html(summary)

    print(f"\nReports exported.")
    print(f"Dashboard: {html_path}")


if __name__ == "__main__":
    main()