import sys
from pathlib import Path

# Add the directory containing THIS file to Python path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# Now import
from src.config.sts_config import STSConfig
from src.automation.nist_runner import NISTRunner
from src.parser.result_parser import ResultParser
from src.exporters import export_json, export_csv, export_latex


# ========== TEST 1: Config ==========
print("=" * 50)
print("TEST 1: STSConfig")
print("=" * 50)

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
print(f"✓ Config: {config.generator}, {config.stream_length} bits, {config.number_of_streams} streams")


# ========== TEST 2: Validation ==========
print("\n" + "=" * 50)
print("TEST 2: Validation")
print("=" * 50)

from src.utils.validation import validate_input_file

result = validate_input_file(config.input_file, input_mode=1)
print(f"✓ Valid: {result.valid}, Bits: {result.bit_count}")


# ========== TEST 3: Runner (answers only) ==========
print("\n" + "=" * 50)
print("TEST 3: NISTRunner - Build Answers")
print("=" * 50)

runner = NISTRunner(config)
print("✓ Runner created")

sts_answers = runner.build_sts_answers()
print(f"\n--- STS Answers ---\n{sts_answers}")

param_answers = runner.build_parameter_answers()
print(f"--- Parameter Answers ---\n{param_answers}")


# ========== TEST 4: Parser (with mock data) ==========
print("\n" + "=" * 50)
print("TEST 4: ResultParser")
print("=" * 50)

mock_exp = Path("experiments/TestParser_1000000_100_20250707_120000")
mock_exp.mkdir(parents=True, exist_ok=True)

report = """RESULTS FOR THE UNIFORMITY OF P-VALUES AND THE PROPORTION OF PASSING SEQUENCES
-------------------------------------------------------------------------------
generator is MyRNG

C1  C2  C3  C4  C5  C6  C7  C8  C9 C10  P-VALUE  PROPORTION  STATISTICAL TEST
  7   8  12  10   8  13   7  11   9   5  0.437274     100/100     Frequency
  6   9  11  10   9  12   8  10   9   6  0.534146      99/100     BlockFrequency
"""

with open(mock_exp / "finalAnalysisReport.txt", "w") as f:
    f.write(report)

with open(mock_exp / "stats.txt", "w") as f:
    f.write("Frequency\n0.437274\n0.123456\nBlockFrequency\n0.534146\n0.234567\n")

with open(mock_exp / "results.txt", "w") as f:
    f.write("Frequency\n1\n1\n0\nBlockFrequency\n1\n0\n1\n")

parser = ResultParser(mock_exp)
summary = parser.parse()

print(f"✓ Parsed: {len(summary.tests)} tests")
print(f"  Generator: {summary.generator}")
print(f"  Overall: {'PASS' if summary.overall_passed else 'FAIL'}")
for t in summary.tests:
    print(f"  - {t.name}: passed={t.passed}, p={t.p_value:.4f}")


# ========== TEST 5: Exporters ==========
print("\n" + "=" * 50)
print("TEST 5: Exporters")
print("=" * 50)

json_path = export_json(summary)
print(f"✓ JSON: {json_path}")

csv_path = export_csv(summary)
print(f"✓ CSV: {csv_path}")

latex_path = export_latex(summary)
print(f"✓ LaTeX: {latex_path}")

print("\n--- CSV Content ---")
with open(csv_path) as f:
    print(f.read())


print("\n" + "=" * 50)
print("ALL TESTS PASSED ✓")
print("=" * 50)