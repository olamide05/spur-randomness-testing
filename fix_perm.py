#!/usr/bin/env python3
"""Fix permissions for NIST STS experiments directory."""
import subprocess
import shutil
from pathlib import Path

sts_path = Path("sts/sts-2.1.2").resolve()
exp_dir = sts_path / "experiments"

print(f"Current owner of {exp_dir}:")
subprocess.run(["ls", "-la", str(exp_dir)])

# Fix ownership
print("\nFixing ownership...")
result = subprocess.run(
    ["sudo", "chown", "-R", "vscode:vscode", str(exp_dir)],
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print(f"sudo failed: {result.stderr}")
    print("Trying without sudo...")
    # Just recreate the directory
    if exp_dir.exists():
        shutil.rmtree(exp_dir)
    exp_dir.mkdir(parents=True)
    (exp_dir / "AlgorithmTesting").mkdir(exist_ok=True)
else:
    print("Ownership fixed!")

print(f"\nNew permissions:")
subprocess.run(["ls", "-la", str(exp_dir)])

# Now test assess
assess = sts_path / "assess"

# Clear old results
for name in ["finalAnalysisReport.txt", "stats.txt", "results.txt", "freq.txt"]:
    p = sts_path / name
    if p.exists():
        p.unlink()

algo_dir = exp_dir / "AlgorithmTesting"
if algo_dir.exists():
    shutil.rmtree(algo_dir)
algo_dir.mkdir(exist_ok=True)

inputs = [
    "0", "data/data.pi", "0", "1", "10",
    "128", "0", "9", "148", "0", "9", "0", "10", "0", "16", "0", "500", "0",
]

input_data = "\n".join(inputs) + "\n"

print("\nRunning assess...")
result = subprocess.run(
    [str(assess), "100000"],
    input=input_data,
    capture_output=True,
    text=True,
    timeout=120,
    cwd=str(sts_path),
)

print(f"Return code: {result.returncode}")

report = sts_path / "finalAnalysisReport.txt"
if report.exists():
    print(f"\nReport exists! Size: {report.stat().st_size}")
    lines = report.read_text().splitlines()
    test_lines = [l for l in lines if any(t in l for t in ["Frequency", "BlockFrequency", "Runs", "Rank"])]
    print("Sample results:")
    for line in test_lines[:8]:
        print(f"  {line}")
else:
    print("\nNo report")
    print(f"Stdout: {result.stdout[-400:]}")