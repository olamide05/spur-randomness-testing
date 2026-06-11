def total_bits(bitstream):
    return len(bitstream)
def count_ones(bitstream):
    return bitstream.count('1')
def count_zeros(bitstream):
    return bitstream.count('0')
def ones_percentage(bitstream, total, ones):
    # total = total_bits(bitstream)
    if total == 0:
        return 0
    return ones / total
def zeros_percentage(bitstream, total, zeros):
    # total = total_bits(bitstream)
    if total == 0:
        return 0
    return zeros / total
def bit_balance(bitstream, total, ones, zeros):
    # total = total_bits(bitstream)
    if total == 0:
        return 0
    return abs(ones_percentage(bitstream, total, ones) - zeros_percentage(bitstream, total, zeros))
def stats(bitstream):
    total = total_bits(bitstream)
    ones = count_ones(bitstream)
    zeros = count_zeros(bitstream)
    return {
        'total_bits': total,
        'count_ones': ones,
        'count_zeros': zeros,
        'ones_percentage': ones_percentage(bitstream, total, ones),
        'zeros_percentage': zeros_percentage(bitstream, total, zeros),
        'bit_balance': bit_balance(bitstream, total, ones, zeros)
    }
