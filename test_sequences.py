#!/usr/bin/env python3
"""Test if assess can write to experiments directories."""
import subprocess
import shutil
from pathlib import Path

sts_path = Path("sts/sts-2.1.2").resolve()
assess = sts_path / "assess"

# Don't delete existing experiments dir - just ensure subdirs exist
algo_dir = sts_path / "experiments" / "AlgorithmTesting"
if not algo_dir.exists():
    algo_dir.mkdir(parents=True)

for name in ["Frequency", "BlockFrequency", "CumulativeSums", "Runs",
             "LongestRun", "Rank", "FFT", "NonOverlappingTemplate",
             "OverlappingTemplate", "Universal", "ApproximateEntropy",
             "RandomExcursions", "RandomExcursionsVariant", "Serial", "LinearComplexity"]:
    d = algo_dir / name
    if not d.exists():
        d.mkdir()

# Clear old top-level results
for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
    p = sts_path / name
    if p.exists():
        p.unlink()

# Run with random data
inputs = [
    "0", "data/test_random.txt", "0", "1", "10",
    "128", "0", "9", "148", "0", "9", "0", "10", "0", "16", "0", "500", "0",
]

input_data = "\n".join(inputs) + "\n"

print("Running assess (preserving existing dirs)...")
result = subprocess.run(
    [str(assess), "100000"],
    input=input_data,
    capture_output=True,
    text=True,
    timeout=120,
    cwd=str(sts_path),
)

print(f"Return code: {result.returncode}")

# Check what files assess created
print("\nFiles in AlgorithmTesting:")
for d in sorted(algo_dir.iterdir()):
    files = list(d.iterdir())
    print(f"  {d.name}: {len(files)} files")

# Check report
report = sts_path / "finalAnalysisReport.txt"
if report.exists():
    print(f"\nReport exists! Size: {report.stat().st_size}")
    lines = report.read_text().splitlines()
    test_lines = [l for l in lines if any(t in l for t in ["Frequency", "BlockFrequency", "Runs", "Rank", "LongestRun", "Universal"])]
    print("Sample results:")
    for line in test_lines[:15]:
        print(f"  {line}")
else:
    print("\nNo report")
    print(f"Stdout (last 500): {result.stdout[-500:]}")