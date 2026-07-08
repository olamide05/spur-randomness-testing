from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    valid: bool
    bit_count: int = 0
    message: str = ""

    def __bool__(self):
        return self.valid


def validate_binary_file(file_path: Path) -> ValidationResult:
    if not file_path.exists():
        return ValidationResult(False, 0, f"File not found: {file_path}")
    if not file_path.is_file():
        return ValidationResult(False, 0, f"Not a file: {file_path}")
    
    size = file_path.stat().st_size
    if size == 0:
        return ValidationResult(False, 0, "File is empty")
    
    try:
        with open(file_path, 'rb') as f:
            if not f.read(1):
                return ValidationResult(False, 0, "Could not read file")
    except (IOError, OSError) as e:
        return ValidationResult(False, 0, f"Read error: {e}")
    
    bits = size * 8
    return ValidationResult(True, bits, f"Valid: {size} bytes ({bits} bits)")


def validate_ascii_file(file_path: Path) -> ValidationResult:
    if not file_path.exists():
        return ValidationResult(False, 0, f"File not found: {file_path}")
    if not file_path.is_file():
        return ValidationResult(False, 0, f"Not a file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='ascii') as f:
            content = f.read()
    except UnicodeDecodeError:
        return ValidationResult(False, 0, "Not valid ASCII")
    except (IOError, OSError) as e:
        return ValidationResult(False, 0, f"Read error: {e}")
    
    if not content:
        return ValidationResult(False, 0, "File is empty")
    
    bit_count = 0
    invalid = []
    for i, c in enumerate(content):
        if c in '01':
            bit_count += 1
        elif c not in ' \n\r\t':
            invalid.append(i)
    
    if invalid:
        return ValidationResult(False, 0, f"Invalid chars at: {invalid[:5]}")
    
    if bit_count == 0:
        return ValidationResult(False, 0, "No valid bits")
    
    return ValidationResult(True, bit_count, f"Valid: {bit_count} bits")


def validate_input_file(file_path: Path, input_mode: int = 0) -> ValidationResult:
    if input_mode == 0:
        return validate_binary_file(file_path)
    return validate_ascii_file(file_path)


def calculate_num_streams(bit_count: int, stream_length: int) -> int:
    if stream_length <= 0:
        raise ValueError("stream_length must be positive")
    return bit_count // stream_length