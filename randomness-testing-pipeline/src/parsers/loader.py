def load_bitstream(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        bitstream = f.read()
        
    return bitstream
def clean_bitstream(bitstream):
    # Remove any non-binary characters (if necessary)
    cleaned_bitstream = bitstream.replace('\n', '').replace(' ', '').replace('\t', '')  # Remove newlines, spaces, and tabs
    return cleaned_bitstream

def validate_bitstream(bitstream):
    # Check if the bitstream contains only '0' and '1'
    if all(char in '01' for char in bitstream):
        return True
    else:
        raise ValueError("Bitstream contains invalid characters. Only '0' and '1' are allowed.")
def load_and_process_bitstream(filepath):
    bitstream = load_bitstream(filepath)
    if not bitstream:
        raise ValueError("Bitstream is empty.")
    cleaned_bitstream = clean_bitstream(bitstream)
    if validate_bitstream(cleaned_bitstream):
        return cleaned_bitstream
    else:        raise ValueError("Invalid bitstream after cleaning.")
# print(load_and_process_bitstream('sample_bitstream.txt'))
