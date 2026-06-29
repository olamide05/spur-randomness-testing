import os
import subprocess

from click import command


from loader import load_and_process_bitstream
class NISTRunner:
    STS_PATH = "/mnt/c/Users/alimi/OneDrive/Desktop/spur-randomness-testing/spur-randomness-testing/sts/sts-2.1.2"

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

        

    def calculate_num_streams(self, total_bits, stream_length):
      if stream_length <= 0:
          raise ValueError("Stream length must be greater than 0.")

      num_streams = total_bits // stream_length

      if num_streams == 0:
          raise ValueError(
              f"Not enough bits. Need at least {stream_length} bits."
          )

      return num_streams

    def build_sts_answers(self, file_path, num_streams):
            return (
             f"0\n"
             f"{file_path}\n"
             f"1\n"
             f"0\n"
             f"{num_streams}\n"
             f"0\n"
    )
    def windows_to_wsl_path(self, path):
     if path.startswith("C:\\"):
         return path.replace("C:\\", "/mnt/c/").replace("\\", "/")
     return path
        


    def run(self, file_path, stream_length=1000):
        validation = self.validate_input(file_path)
        file_path = self.windows_to_wsl_path(file_path)

        assess_path=self.STS_PATH

        # validation = self.validate_input(file_path)
        total_bits = validation["total_bits"]
        # bitstream = validation["bitstream"]

        num_streams = self.calculate_num_streams(
            validation["total_bits"],
            stream_length
        )

        answers = self.build_sts_answers(
            file_path,
            num_streams
        )

        command = (
           f"cd {self.STS_PATH} && ./assess {stream_length}"
        )
        print(f"Running command: {command}")
        print(f"With answers: {answers}")
        process = subprocess.Popen(
    [
        "wsl",
        "-d",
        "Ubuntu",
        "bash",
        "-c",
        command
    ],
    stdin=subprocess.PIPE,
    text=True
)

        process.communicate(answers)


        return {
    "status": "completed",
    "return_code": process.returncode,
    "experiments_folder": self.STS_PATH + "/experiments"
}