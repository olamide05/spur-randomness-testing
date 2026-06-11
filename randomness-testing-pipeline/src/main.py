from parsers.loader import load_bitstream, clean_bitstream, validate_bitstream, load_and_process_bitstream
from stats.basic_stats import stats
def main():
    filepath = 'sample_bitstream.txt'
    try:
        bitstream = load_and_process_bitstream(filepath)
        statistics = stats(bitstream)
        print(statistics)
    except Exception as e:
        print(f"Error processing bitstream: {e}")

if __name__ == "__main__":
    main()