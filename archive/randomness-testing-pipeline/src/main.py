import json

from parsers.loader import load_bitstream, clean_bitstream, validate_bitstream, load_and_process_bitstream
from stats.basic_stats import stats
from tests.runs_test import runs_test
from tests.frequency_test import frequency_test
def main():
    filepath = 'sample_bitstream.txt'
    try:
        bitstream = load_and_process_bitstream(filepath)
        statistics = stats(bitstream)
        frequency_result = frequency_test(bitstream)
        runs_result = runs_test(bitstream)
        # print(statistics)
        # print(frequency_result)
        # print(runs_result)
        name = f"results/{filepath.split('.')[0]}_results.json"
        with open(name, "w", encoding="utf-8") as file:
            json.dump({
                "name": name,
                "statistics": statistics,
                "frequency_result": frequency_result,
                "runs_test_result": runs_result
            }, file, indent=4, ensure_ascii=False)
            print(f"Dataset Loaded Successfully and Results Saved to JSON File: {name}")
    except Exception as e:
        print(f"Error processing bitstream: {e}")

if __name__ == "__main__":
    main()