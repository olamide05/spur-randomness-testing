from pathlib import Path
import shutil

import pytest

from src.generators.examples import (
    LIBRARY_EXAMPLES,
    PCG32_SOURCE,
    SV_EXAMPLES,
    available_library_examples,
    extra_compile_flags,
)
from src.generators.source_runner import (
    SV_TB_TEMPLATE,
    generate_from_cpp,
    generate_from_systemverilog,
)


def test_catalog_contains_arithmetic_and_chaos_for_both_languages():
    cpp_families = {example.family for example in LIBRARY_EXAMPLES}
    sv_families = {example.family for example in SV_EXAMPLES}

    assert {"Arithmetic", "Chaos"} <= cpp_families
    assert {"Arithmetic", "Chaos"} <= sv_families
    assert len(LIBRARY_EXAMPLES) >= 8
    assert len(SV_EXAMPLES) >= 5


@pytest.mark.parametrize(
    "example",
    available_library_examples(),
    ids=lambda example: example.id,
)
def test_builtin_cpp_example_generates_bits(example, tmp_path):
    result = generate_from_cpp(
        example.source,
        tmp_path / f"{example.id}.bin",
        257,
        output_format=example.output_format,
        std=example.std,
        extra_flags=extra_compile_flags(example),
    )

    assert example.output_format == "binary"
    assert result.input_mode == 1
    assert result.bit_count == 264
    assert result.path.stat().st_size == 33
    assert result.path.read_bytes()[-1] & 0x7f == 0


def test_builtin_cpp_example_still_supports_ascii_selection(tmp_path):
    destination = tmp_path / "pcg32.txt"

    result = generate_from_cpp(
        PCG32_SOURCE, destination, 257, output_format="ascii"
    )

    bits = "".join(destination.read_text().split())
    assert result.input_mode == 0
    assert result.bit_count == 257
    assert len(bits) == 257
    assert set(bits) <= {"0", "1"}


LOCAL_VERILATOR = (
    Path(__file__).parents[1] / ".tools" / "verilator" / "usr" / "bin" / "verilator"
)


@pytest.mark.skipif(
    shutil.which("verilator") is None and not LOCAL_VERILATOR.is_file(),
    reason="Verilator is not installed",
)
@pytest.mark.parametrize("example", SV_EXAMPLES, ids=lambda example: example.id)
def test_systemverilog_example_generates_bits(example, tmp_path):
    result = generate_from_systemverilog(
        example.core_source,
        SV_TB_TEMPLATE,
        "tb",
        tmp_path / f"{example.id}.bin",
        257,
    )

    assert result.input_mode == 1
    assert result.bit_count == 264
    assert result.path.stat().st_size == 33
    assert result.path.read_bytes()[-1] & 0x7f == 0


def test_builtin_examples_are_always_available():
    visible_ids = {example.id for example in available_library_examples()}
    builtin_ids = {
        example.id for example in LIBRARY_EXAMPLES
        if example.pkg_config_name is None
    }
    assert builtin_ids <= visible_ids
