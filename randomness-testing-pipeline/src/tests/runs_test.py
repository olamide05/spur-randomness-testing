def runs_test(bitstream):
    """
    Runs Test: This test checks for the number of runs (consecutive bits of the same value) in the bitstream. 
    The number of runs should be within a certain range for a random sequence.
    """

    
    n = len(bitstream)
    if n == 0:
        raise ValueError("Bitstream is empty.")

    # Count the number of runs
    runs = 1  # Start with one run
    for i in range(1, n):
        if bitstream[i] != bitstream[i - 1]:
            runs += 1

    # Calculate expected number of runs for a random sequence
    expected_runs = (n / 2) + 1

    # Check if the number of runs is within the expected range (±10% tolerance)
    lower_bound = expected_runs * 0.9
    upper_bound = expected_runs * 1.1

    return {
        "runs": runs,
        "expected_runs": expected_runs,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "is_within_range": lower_bound <= runs <= upper_bound
    }