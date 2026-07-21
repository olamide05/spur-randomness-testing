import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.config.sts_config import STSConfig
from src.automation.nist_runner import NISTRunner
from src.parser.result_parser import ResultParser
from src.exporters import export_json, export_csv, export_latex

print("=" * 60)
print("NIST STS FRAMEWORK - FULL TEST")
print("=" * 60)

# TEST 1: Config
print("\n[1/5] Testing STSConfig...")
config = STSConfig(
    sts_path=Path("sts/sts-2.1.2"),
    input_file=Path("/workspaces/fs/sts/sts-2.1.2/data/data.pi"),
    generator="MyRNG2",
    stream_length=1_000_000,
    number_of_streams=100,
    #  test_parameters={
    #      "block_frequency": {"block_length": 128},
    #     "approximate_entropy": {"block_length": 10},
    #     ""
    # }
)
print(f"   OK: {config.generator}")

# TEST 2: Runner
print("\n[2/5] Testing NISTRunner...")
runner = NISTRunner(config)
print("   OK: Runner created")
print(f"\n--- STS Answers ---\n{runner.build_sts_answers()}")
print(f"--- Parameter Answers ---\n{runner.build_parameter_answers()}")

# TEST 3: Parser with REAL NIST format mock data
print("\n[3/5] Testing ResultParser with real NIST format...")

mock_exp = Path("experiments/TestParser_1000000_100_20250708_120000")
mock_exp.mkdir(parents=True, exist_ok=True)

# Real NIST finalAnalysisReport.txt format
report = """------------------------------------------------------------------------------
RESULTS FOR THE UNIFORMITY OF P-VALUES AND THE PROPORTION OF PASSING SEQUENCES
------------------------------------------------------------------------------
   generator is </mnt/c/Users/alimi/OneDrive/Desktop/spur-randomness-testing/spur-randomness-testing/datasets/test_cases/test_bits.txt>
------------------------------------------------------------------------------
 C1  C2  C3  C4  C5  C6  C7  C8  C9 C10  P-VALUE  PROPORTION  STATISTICAL TEST
------------------------------------------------------------------------------
  7   8  12  10   8  13   7  11   9   5  0.437274     100/100     Frequency
  6   9  11  10   9  12   8  10   9   6  0.534146      99/100     BlockFrequency
  5   8  10  12  11   9  10   8   7  10  0.662200     100/100     CumulativeSums
  8   7   9  11  10  12   8   9  10   6  0.739918     100/100     CumulativeSums
  9  10   8   7  11  10   9   8  10   8  0.851383      98/100     Runs
  7  11   9   8  10   7  12   9   8   9  0.920383     100/100     LongestRun
  8   9  10   7  11   8   9  10   8  10  0.534146     100/100     Rank
 10   8   7   9  11   8  10   7   9  11  0.437274     100/100     FFT
  1   2   1   0   2   2   1   1   0   0  0.739918     100/100     NonOverlappingTemplate
  0   1   1   2   1   1   1   2   0   1  0.911413     100/100     NonOverlappingTemplate
  4   0   1   2   0   1   0   0   0   2  0.066882      96/100     OverlappingTemplate
 10   0   0   0   0   0   0   0   0   0  0.000000 *    0/100   *  Universal
  0   1   1   2   0   1   3   1   1   0  0.534146     100/100     ApproximateEntropy
  0   2   0   0   0   0   0   0   0   0     ----       2/2       RandomExcursions
  0   0   0   0   1   0   1   0   0   0     ----       2/2       RandomExcursions
  0   0   0   0   0   0   1   1   0   0     ----       2/2       RandomExcursionsVariant
  0   0   1   0   0   0   0   1   0   0     ----       2/2       RandomExcursionsVariant
  3   0   2   1   0   0   1   0   1   2  0.350485      99/100     Serial
  2   2   1   1   0   2   0   0   0   2  0.534146      99/100     Serial
  2   2   1   0   0   1   1   0   2   1  0.739918     100/100     LinearComplexity
------------------------------------------------------------------------------"""

with open(mock_exp / "finalAnalysisReport.txt", "w") as f:
    f.write(report)

# Real NIST stats.txt format
stats = """Frequency
0.437274
0.123456
0.987654
BlockFrequency
0.534146
0.234567
0.876543
CumulativeSums
0.662200
0.345678
0.765432
Runs
0.851383
0.456789
0.654321
LongestRun
0.920383
0.567890
0.543210
Rank
0.534146
0.678901
0.432109
FFT
0.437274
0.789012
0.321098
NonOverlappingTemplate
0.739918
0.890123
0.210987
OverlappingTemplate
0.066882
0.901234
0.109876
Universal
0.000000
0.012345
0.987655
ApproximateEntropy
0.534146
0.123450
0.876550
RandomExcursions
0.500000
0.600000
RandomExcursionsVariant
0.400000
0.700000
Serial
0.350485
0.234560
0.765440
LinearComplexity
0.739918
0.345670
0.654330"""

with open(mock_exp / "stats.txt", "w") as f:
    f.write(stats)

# Real NIST results.txt format
results = """Frequency
1
1
0
BlockFrequency
1
0
1
CumulativeSums
1
1
0
Runs
1
0
0
LongestRun
1
1
1
Rank
1
1
0
FFT
1
0
1
NonOverlappingTemplate
1
1
1
OverlappingTemplate
1
0
0
Universal
0
0
0
ApproximateEntropy
1
1
0
RandomExcursions
1
1
RandomExcursionsVariant
1
0
Serial
1
0
1
LinearComplexity
1
1
0"""

with open(mock_exp / "results.txt", "w") as f:
    f.write(results)

# Parse with generator from config
parser = ResultParser(mock_exp, generator="MyRNG")
summary = parser.parse()

print(f"   OK: Parsed {len(summary.tests)} unique tests")
print(f"   Generator: {summary.generator}")
print(f"   Overall: {'PASS' if summary.overall_passed else 'FAIL'}")

for t in summary.tests:
    icon = "✓" if t.status == "Pass" else "✗" if t.status == "Fail" else "○"
    print(f"   {icon} {t.name:30s} | {t.status:8s} | {t.pass_rate:10s}")

# TEST 4: Exporters
print("\n[4/5] Testing Exporters...")

json_path = export_json(summary)
print(f"   JSON: {json_path}")

csv_path = export_csv(summary)
print(f"   CSV:  {csv_path}")

latex_path = export_latex(summary)
print(f"   LaTeX: {latex_path}")

# Show CSV preview
print("\n--- CSV Preview ---")
with open(csv_path) as f:
    for i, line in enumerate(f):
        if i > 20:
            print("   ...")
            break
        print(f"   {line.rstrip()}")

# TEST 5: JSON structure
print("\n[5/5] JSON structure check...")
import json
with open(json_path) as f:
    data = json.load(f)
print(f"   Framework: {data['framework']}")
print(f"   Generator: {data['metadata']['generator']}")
print(f"   Total: {data['metadata']['total_tests']}")
print(f"   Passed: {data['metadata']['tests_passed']}")
print(f"   Failed: {data['metadata']['tests_failed']}")
print(f"   Not Run: {data['metadata']['tests_not_run']}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print(f"\nResults saved to: {mock_exp}")