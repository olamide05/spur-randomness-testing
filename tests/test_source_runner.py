from pathlib import Path
import shutil

import pytest

from src.generators.source_runner import (
    C_TEMPLATE,
    SV_CORE_TEMPLATE,
    SV_TB_TEMPLATE,
    GenerationError,
    generate_from_c,
    generate_from_systemverilog,
)


def test_c_template_generates_valid_ascii_stream(tmp_path):
    destination = tmp_path / "c-stream.txt"

    result = generate_from_c(C_TEMPLATE, destination, 257)

    assert result.path == destination
    assert result.input_mode == 0
    assert result.bit_count == 257
    assert set(destination.read_text().replace("\n", "")) <= {"0", "1"}


def test_c_stdout_is_supported_as_a_fallback(tmp_path):
    source = r'''
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    unsigned long long count = strtoull(argv[2], NULL, 10);
    for (unsigned long long i = 0; i < count; ++i) putchar((i & 1U) ? '1' : '0');
    return 0;
}
'''
    destination = tmp_path / "stdout-stream.txt"

    result = generate_from_c(source, destination, 64)

    assert result.bit_count == 64
    assert destination.read_text() == "01" * 32


def test_c_generator_rejects_non_bit_ascii(tmp_path):
    source = r'''
#include <stdio.h>
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    FILE *output = fopen(argv[1], "wb");
    fputs("0102", output);
    return fclose(output);
}
'''
    with pytest.raises(GenerationError, match="only 0, 1, and whitespace"):
        generate_from_c(source, tmp_path / "bad.txt", 4)


def test_c_generator_accepts_packed_binary(tmp_path):
    source = r'''
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    unsigned long long count = strtoull(argv[2], NULL, 10);
    FILE *output = fopen(argv[1], "wb");
    for (unsigned long long i = 0; i < (count + 7) / 8; ++i) fputc(0xa5, output);
    return fclose(output);
}
'''
    destination = tmp_path / "packed.bin"

    result = generate_from_c(
        source, destination, 257, output_format="binary"
    )

    assert result.input_mode == 1
    assert result.bit_count == 264
    assert destination.read_bytes() == b"\xa5" * 33


LOCAL_VERILATOR = Path(__file__).parents[1] / ".tools" / "verilator" / "usr" / "bin" / "verilator"


@pytest.mark.skipif(
    shutil.which("verilator") is None and not LOCAL_VERILATOR.is_file(),
    reason="Verilator is not installed",
)
def test_systemverilog_templates_generate_valid_ascii_stream(tmp_path):
    destination = tmp_path / "sv-stream.txt"

    result = generate_from_systemverilog(
        SV_CORE_TEMPLATE,
        SV_TB_TEMPLATE,
        "tb",
        destination,
        257,
    )

    assert result.path == destination
    assert result.input_mode == 0
    assert result.bit_count == 257
    assert set(destination.read_text().replace("\n", "")) <= {"0", "1"}
