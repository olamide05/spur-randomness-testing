import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# 1. Config
from src.config.sts_config import STSConfig
config = STSConfig(
    sts_path=Path("sts/sts-2.1.2"),
    input_file=Path("datasets/test_cases/test_bits.txt"),
    generator="MyRNG",
    stream_length=1_000_000,
    number_of_streams=100,
    test_parameters={
        "block_frequency": {"block_length": 128},
        "approximate_entropy": {"block_length": 10},
    }
)
print("✅ STSConfig with parameters")

# 2. Runner
from src.automation.nist_runner import NISTRunner
runner = NISTRunner(config)
answers = runner.build_sts_answers()
params = runner.build_parameter_answers()
print("✅ NISTRunner consumes config")
print(f"   STS answers: {len(answers)} chars")
print(f"   Param answers: {len(params)} chars")

# 3. Parser + Exporters
from src.parser.result_parser import ResultParser
from src.exporters import export_json, export_csv, export_latex

# Create mock experiment
mock = Path("experiments/V1Verify_1000000_100_20250708_120000")
mock.mkdir(parents=True, exist_ok=True)
with open(mock / "finalAnalysisReport.txt", "w") as f:
    f.write("generator is TestRNG\n\nC1 C2 C3 C4 C5 C6 C7 C8 C9 C10 P-VALUE PROPORTION STATISTICAL TEST\n 7  8 12 10  8 13  7 11  9  5 0.437274    100/100    Frequency\n")
with open(mock / "stats.txt", "w") as f:
    f.write("Frequency\n0.437274\n0.123456\n")
with open(mock / "results.txt", "w") as f:
    f.write("Frequency\n1\n1\n0\n")

parser = ResultParser(mock)
summary = parser.parse()

# 4. Export all formats
export_json(summary)
export_csv(summary)
export_latex(summary)

print("✅ JSON exported")
print("✅ CSV exported")
print("✅ LaTeX exported")
print(f"\n📁 Results in: {mock}")
print("\n🎉 V1 FRAMEWORK COMPLETE")