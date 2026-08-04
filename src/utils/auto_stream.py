from pathlib import Path


def auto_calculate(file_path: Path, min_stream_length: int = 100000, max_streams: int = 100) -> tuple:
    """
    Auto-calculate optimal stream_length and number_of_streams
    based on file size and NIST recommendations.

    Returns: (stream_length, number_of_streams)
    """
    file_size = file_path.stat().st_size

    # Detect if ASCII or binary to calculate total bits
    with open(file_path, "rb") as f:
        sample = f.read(1000)
    text = sample.decode("ascii", errors="ignore")
    valid = set("01 \n\r\t")
    is_ascii = all(c in valid for c in text) and len(text) > 100

    total_bits = file_size if is_ascii else file_size * 8

    # NIST recommends stream_length >= 1,000,000 for reliable results
    # But 100,000 is the minimum that works

    # Strategy: use largest possible stream_length that allows at least 10 streams
    # but cap at 1,000,000 per stream

    if total_bits >= 10_000_000:
        # Large file: use 1M bits per stream
        stream_length = 1_000_000
    elif total_bits >= 1_000_000:
        # Medium file: use 100K bits per stream
        stream_length = 100_000
    else:
        # Small file: use whatever we can, minimum 1000
        stream_length = max(1000, total_bits // 10)

    number_of_streams = min(total_bits // stream_length, max_streams)

    # Ensure at least 1 stream
    if number_of_streams < 1:
        stream_length = total_bits
        number_of_streams = 1

    return stream_length, number_of_streams