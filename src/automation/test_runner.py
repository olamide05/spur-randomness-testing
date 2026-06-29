
from nist_runner import NISTRunner
runner = NISTRunner()
result = runner.run(
        r"C:\Users\alimi\OneDrive\Desktop\spur-randomness-testing\spur-randomness-testing\datasets\test_cases\test_bits.txt",
        stream_length=1000
    )

print(result)