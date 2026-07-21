#!/usr/bin/env python3
"""Test assess with fresh experiments directory."""
import subprocess
import shutil
from pathlib import Path

sts_path = Path("sts/sts-2.1.2").resolve()
assess = sts_path / "assess"

# Remove old experiments directory completely
exp_dir = sts_path / "experiments" / "AlgorithmTesting"
if exp_dir.exists():
    print(f"Removing old: {exp_dir}")
    shutil.rmtree(exp_dir)

# Also remove old result files
for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
    p = sts_path / name
    if p.exists():
        p.unlink()

# Test sequence from manual run that worked
inputs = [
    "0", "data/data.pi", "0", "1", "10",
    "128", "0", "9", "148", "0", "9", "0", "10", "0", "16", "0", "500", "0",
]

input_data = "\n".join(inputs) + "\n"

print("Running assess with fresh directory...")
result = subprocess.run(
    [str(assess), "100000"],
    input=input_data,
    capture_output=True,
    text=True,
    timeout=120,
    cwd=str(sts_path),
)

print(f"Return code: {result.returncode}")
print(f"\nStdout (last 500 chars):")
print(result.stdout[-500:] if result.stdout else "EMPTY")

# Check report
report = sts_path / "finalAnalysisReport.txt"
if report.exists():
    print(f"\nReport exists! Size: {report.stat().st_size}")
    lines = report.read_text().splitlines()
    test_lines = [l for l in lines if any(t in l for t in ["Frequency", "BlockFrequency", "Runs", "Rank"])]
    print("\nSample results:")
    for line in test_lines[:8]:
        print(f"  {line}")
else:
    print("\nNo report generated")
    print(f"Stderr: {result.stderr[:500]}")