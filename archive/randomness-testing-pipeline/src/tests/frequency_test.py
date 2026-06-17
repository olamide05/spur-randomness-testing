from math import sqrt, erfc
def frequency_test(bitstream):
    total = len(bitstream)
    if total == 0:
        raise ValueError("Bitstream is empty.")
    ones = bitstream.count('1')
    zeros = bitstream.count('0')
    S = ones - zeros
    S_obs = abs(S) / sqrt(total)
    p_value = erfc(S_obs / sqrt(2))
    passed = p_value >= 0.01
    return {
    "n": total,
    "ones": ones,
    "zeros": zeros,
    "S": S,
    "S_obs": S_obs,
    "p_value": p_value,
    "passed": passed
}