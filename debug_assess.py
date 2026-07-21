#!/usr/bin/env python3
"""Debug assess input sequence."""
import subprocess
import sys
from pathlib import Path

sts_path = Path("sts/sts-2.1.2")
assess = sts_path / "assess"

def test_sequence(name, inputs, stream_length=100000):
    """Test a specific input sequence."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print("Input:")
    for i, line in enumerate(inputs, 1):
        print(f"  {i}: {repr(line)}")

    input_data = "\n".join(inputs) + "\n"

    try:
        result = subprocess.run(
            [str(assess), str(stream_length)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(sts_path),
        )

        print(f"\nReturn code: {result.returncode}")
        print(f"Stdout (last 500 chars):")
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

        # Check if report was generated
        report = sts_path / "finalAnalysisReport.txt"
        if report.exists():
            content = report.read_text()
            lines = [l for l in content.splitlines() if "Frequency" in l or "BlockFrequency" in l]
            print(f"\nReport lines:")
            for line in lines[:3]:
                print(f"  {line}")

    except Exception as e:
        print(f"ERROR: {e}")


# Test 1: Minimal sequence (what manual run used)
test_sequence("Manual run sequence", [
    "0",                    # generator type
    "data/data.pi",         # file path
    "0",                    # don't run all tests? (or run all?)
    "1",                    # ???
    "10",                   # num streams
    "128",                  # block freq
    "0",                    # continue
    "9",                    # non-overlap template
    "148",                  # num templates
    "0",                    # continue
    "9",                    # overlap template
    "0",                    # continue
])

# Test 2: Try with run_all=1
test_sequence("Run all tests", [
    "0",
    "data/data.pi",
    "1",                    # run all tests
    "10",                   # num streams
    "0",                    # input mode (ASCII)
])

# Test 3: Different order
test_sequence("Streams before mode", [
    "0",
    "data/data.pi",
    "1",                    # run all
    "10",                   # streams
    "0",                    # ASCII mode
])

print("\n" + "="*60)
print("Check which test produced valid results (not all ------)")
print("="*60)