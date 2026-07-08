from pathlib import Path
from typing import Union, Iterator


class BitstreamLoader:
    @staticmethod
    def load_binary(file_path: Path) -> bytes:
        with open(file_path, 'rb') as f:
            return f.read()

    @staticmethod
    def load_ascii(file_path: Path) -> str:
        with open(file_path, 'r', encoding='ascii') as f:
            content = f.read()
        return ''.join(c for c in content if c in '01')

    @staticmethod
    def bits_from_bytes(data: bytes) -> Iterator[int]:
        for byte in data:
            for i in range(7, -1, -1):
                yield (byte >> i) & 1

    @staticmethod
    def load(file_path: Path, input_mode: int = 0) -> Union[bytes, str]:
        if input_mode == 0:
            return BitstreamLoader.load_binary(file_path)
        return BitstreamLoader.load_ascii(file_path)

    @staticmethod
    def get_bit_count(file_path: Path, input_mode: int = 0) -> int:
        if input_mode == 0:
            return file_path.stat().st_size * 8
        return len(BitstreamLoader.load_ascii(file_path))