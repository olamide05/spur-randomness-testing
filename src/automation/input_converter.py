from loader import load_and_process_bitstream
class InputConverter:

    def __init__(self):
        pass

    def from_ascii_file(self, path):
     return load_and_process_bitstream(path)

    def from_matlab_variable(self, data):
        ...

    def to_nist_bitstream(self, data):
        ...
converter = InputConverter()

bitstream = converter.from_ascii_file(
    "datasets/test_cases/test1.txt"
)

print(bitstream)
print(type(bitstream))
print(len(bitstream))