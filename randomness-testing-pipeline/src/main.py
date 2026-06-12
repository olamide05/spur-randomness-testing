from parsers.loader import load_bitstream, clean_bitstream, validate_bitstream, load_and_process_bitstream
from stats.basic_stats import stats
from tests.frequency_test import frequency_test
def main():
    filepath = 'sample_bitstream.txt'
    try:
        bitstream = load_and_process_bitstream(filepath)
        statistics = stats(bitstream)
        frequency_result = frequency_test(bitstream)
        print(statistics)
        print(frequency_result)
        
    except Exception as e:
        print(f"Error processing bitstream: {e}")

if __name__ == "__main__":
    main()