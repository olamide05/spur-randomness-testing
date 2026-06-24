import os

from automation.loader import load_and_process_bitstream
class NISTRunner:

    def validate_input(self, file_path):
     if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"The file {file_path} does not exist."
        )
     bitstream = load_and_process_bitstream(file_path)
     if len(bitstream) == 0:
        raise ValueError(
            "The bitstream is empty."
        )
     return {
      "valid": True,
      "total_bits": len(bitstream),
      "bitstream": bitstream
     }

        

    def calculate_num_streams(self, file_path, stream_length):
        pass

    def build_sts_answers(self, file_path, num_streams):
        pass

    def run(self, file_path, stream_length=1000):
        pass