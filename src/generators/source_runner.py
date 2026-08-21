"""Compile source-code generators and turn their output into STS inputs.

The source programs are intentionally given a very small, language-neutral
contract:

* C: ``generator OUTPUT_PATH REQUESTED_BITS``
* SystemVerilog: ``+OUTPUT=OUTPUT_PATH +BITS=REQUESTED_BITS``

Both generators may write either ASCII ``0``/``1`` data or packed binary data.
Diagnostics belong on stdout/stderr when the supplied output path is used.
For simple command-line C generators, stdout is also accepted as a fallback.
"""

from __future__ import annotations

import math
import os
import re
import resource
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_GENERATED_BYTES = 500 * 1024 * 1024
COMPILE_TIMEOUT_SECONDS = 120
RUN_TIMEOUT_SECONDS = 180
REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_TOOL_BIN = REPO_ROOT / ".tools" / "verilator" / "usr" / "bin"


C_TEMPLATE = r'''#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/*
 * Contract: generator OUTPUT_PATH REQUESTED_BITS
 * Write ASCII 0/1 characters to OUTPUT_PATH. The standard C library and
 * libm are available. Select "packed binary" in the UI if you use fwrite()
 * to emit bytes instead.
 */
static uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s OUTPUT_PATH REQUESTED_BITS\n", argv[0]);
        return 2;
    }

    errno = 0;
    char *end = NULL;
    unsigned long long requested_bits = strtoull(argv[2], &end, 10);
    if (errno || end == argv[2] || *end != '\0') {
        fprintf(stderr, "invalid bit count: %s\n", argv[2]);
        return 2;
    }

    FILE *output = fopen(argv[1], "wb");
    if (!output) {
        perror("fopen");
        return 1;
    }

    uint32_t state = UINT32_C(0x6d2b79f5);
    for (unsigned long long i = 0; i < requested_bits; ++i) {
        int bit = (int)(xorshift32(&state) & 1U);
        if (fputc('0' + bit, output) == EOF) {
            perror("fputc");
            fclose(output);
            return 1;
        }
        if ((i + 1U) % 64U == 0U) {
            fputc('\n', output);
        }
    }

    if (fclose(output) != 0) {
        perror("fclose");
        return 1;
    }
    return 0;
}
'''


SV_CORE_TEMPLATE = r'''module rng_core;
  logic [31:0] state = 32'h6d2b79f5;

  // A task keeps this starter compatible with both legacy and current
  // simulator packages; replace it with your own RTL interface as needed.
  task automatic next_bit(output logic value);
    state = state ^ (state << 13);
    state = state ^ (state >> 17);
    state = state ^ (state << 5);
    value = state[0];
  endtask
endmodule
'''


SV_TB_TEMPLATE = r'''module tb;
  rng_core dut();

  string output_path;
  longint unsigned requested_bits;
  integer output_file;
  logic value;

  initial begin
    if (!$value$plusargs("OUTPUT=%s", output_path))
      $fatal(1, "missing +OUTPUT=<path>");
    if (!$value$plusargs("BITS=%d", requested_bits))
      $fatal(1, "missing +BITS=<count>");

    output_file = $fopen(output_path, "wb");
    if (output_file == 0)
      $fatal(1, "could not open output file");

    for (longint unsigned i = 0; i < requested_bits; i++) begin
      dut.next_bit(value);
      $fwrite(output_file, "%0d", value);
      if ((i + 1) % 64 == 0)
        $fwrite(output_file, "\n");
    end

    $fclose(output_file);
    $finish;
  end
endmodule
'''


class GenerationError(RuntimeError):
    """A source generator could not be compiled, run, or validated."""


@dataclass(frozen=True)
class GeneratedBitstream:
    path: Path
    input_mode: int
    bit_count: int


def _tool(tool: Optional[str], env_name: str, candidates: Sequence[str]) -> str:
    requested = tool or os.environ.get(env_name)
    if requested:
        resolved = shutil.which(requested)
        if resolved:
            return resolved
        raise GenerationError(f"Required tool '{requested}' was not found on PATH.")
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        local_candidate = LOCAL_TOOL_BIN / candidate
        if local_candidate.is_file() and os.access(local_candidate, os.X_OK):
            return str(local_candidate)
    names = " or ".join(candidates)
    raise GenerationError(
        f"Required tool {names} was not found. Run 'bash scripts/setup.sh' first."
    )


def _check_source(source: str, label: str) -> None:
    if not source.strip():
        raise GenerationError(f"{label} source is empty.")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise GenerationError(
            f"{label} source exceeds the {MAX_SOURCE_BYTES // (1024 * 1024)} MiB limit."
        )


def _tail(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - limit))
        return handle.read().decode("utf-8", errors="replace").strip()


def _terminate_process_group(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (AttributeError, ProcessLookupError):
        process.kill()


def _run_logged(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    stdout_path: Path,
    stderr_path: Path,
    env: Optional[dict[str, str]] = None,
) -> None:
    def apply_limits() -> None:
        # Source generators are user programs. Bound their CPU time, output
        # files, and crash dumps in addition to the parent-side wall timeout.
        def bounded_limit(kind: int, soft: int, hard: int) -> None:
            _, inherited_hard = resource.getrlimit(kind)
            if inherited_hard != resource.RLIM_INFINITY:
                hard = min(hard, inherited_hard)
                soft = min(soft, hard)
            resource.setrlimit(kind, (soft, hard))

        bounded_limit(resource.RLIMIT_CPU, timeout, timeout + 1)
        bounded_limit(
            resource.RLIMIT_FSIZE, MAX_GENERATED_BYTES, MAX_GENERATED_BYTES
        )
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                stdout=stdout,
                stderr=stderr,
                env=env,
                start_new_session=True,
                preexec_fn=apply_limits,
            )
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_process_group(process)
                process.wait()
                raise GenerationError(
                    f"Command timed out after {timeout} seconds: {Path(command[0]).name}"
                )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GenerationError(f"Could not run {Path(command[0]).name}: {exc}") from exc

    if return_code != 0:
        details = _tail(stderr_path) or _tail(stdout_path) or "no diagnostic output"
        raise GenerationError(
            f"{Path(command[0]).name} exited with status {return_code}:\n{details}"
        )


def _required_bytes(bit_count: int, output_format: str) -> int:
    if bit_count < 1:
        raise GenerationError("Requested bit count must be at least 1.")
    if output_format == "ascii":
        required = bit_count
    elif output_format == "binary":
        required = math.ceil(bit_count / 8)
    else:
        raise GenerationError("Output format must be 'ascii' or 'binary'.")
    if required > MAX_GENERATED_BYTES:
        raise GenerationError(
            "Requested generated bitstream exceeds the 500 MiB output limit."
        )
    return required


def _validate_ascii(path: Path, required_bits: int) -> int:
    count = 0
    offset = 0
    allowed_whitespace = b" \t\r\n"
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            for index, value in enumerate(chunk):
                if value in (ord("0"), ord("1")):
                    count += 1
                elif value not in allowed_whitespace:
                    shown = repr(bytes([value]))
                    raise GenerationError(
                        f"Generated ASCII stream contains {shown} at byte {offset + index}; "
                        "only 0, 1, and whitespace are allowed."
                    )
            offset += len(chunk)
    if count < required_bits:
        raise GenerationError(
            f"Generator produced {count:,} bits, but {required_bits:,} are required."
        )
    return count


def _validate_output(path: Path, required_bits: int, output_format: str) -> GeneratedBitstream:
    if not path.is_file() or path.stat().st_size == 0:
        raise GenerationError(
            "Generator did not create a bitstream. Use the OUTPUT_PATH/OUTPUT contract shown in the editor."
        )
    if path.stat().st_size > MAX_GENERATED_BYTES:
        raise GenerationError("Generated bitstream exceeds the 500 MiB output limit.")

    if output_format == "ascii":
        bit_count = _validate_ascii(path, required_bits)
        input_mode = 0
    else:
        bit_count = path.stat().st_size * 8
        if bit_count < required_bits:
            raise GenerationError(
                f"Generator produced {bit_count:,} packed bits, but {required_bits:,} are required."
            )
        input_mode = 1
    return GeneratedBitstream(path=path, input_mode=input_mode, bit_count=bit_count)


def _promote_output(
    generated_path: Path,
    stdout_path: Path,
    destination: Path,
    required_bits: int,
    output_format: str,
) -> GeneratedBitstream:
    source = generated_path
    if not source.exists() or source.stat().st_size == 0:
        source = stdout_path
    checked = _validate_output(source, required_bits, output_format)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return GeneratedBitstream(destination, checked.input_mode, checked.bit_count)


def generate_from_c(
    source: str,
    destination: Path,
    requested_bits: int,
    *,
    output_format: str = "ascii",
    compiler: Optional[str] = None,
) -> GeneratedBitstream:
    """Compile a C11 program and execute it using the generator contract."""

    _check_source(source, "C")
    _required_bytes(requested_bits, output_format)
    cc = _tool(compiler, "CC", ("cc", "gcc"))
    destination = Path(destination).resolve()

    with tempfile.TemporaryDirectory(prefix="spur_c_") as temp_name:
        work_dir = Path(temp_name)
        source_path = work_dir / "generator.c"
        executable = work_dir / "generator"
        generated_path = work_dir / "bitstream.out"
        compile_stdout = work_dir / "compile.stdout.log"
        compile_stderr = work_dir / "compile.stderr.log"
        run_stdout = work_dir / "run.stdout.log"
        run_stderr = work_dir / "run.stderr.log"
        source_path.write_text(source, encoding="utf-8")

        _run_logged(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", str(source_path), "-o", str(executable), "-lm"],
            cwd=work_dir,
            timeout=COMPILE_TIMEOUT_SECONDS,
            stdout_path=compile_stdout,
            stderr_path=compile_stderr,
        )
        _run_logged(
            [str(executable), str(generated_path), str(requested_bits)],
            cwd=work_dir,
            timeout=RUN_TIMEOUT_SECONDS,
            stdout_path=run_stdout,
            stderr_path=run_stderr,
        )
        return _promote_output(
            generated_path, run_stdout, destination, requested_bits, output_format
        )


def generate_from_cpp(
    source: str,
    destination: Path,
    requested_bits: int,
    *,
    output_format: str = "ascii",
    compiler: Optional[str] = None,
    std: str = "c++17",
    extra_flags: Sequence[str] = (),
) -> GeneratedBitstream:
    """Compile a C++ program and execute it using the generator contract.

    extra_flags must only ever come from server-side lookups (e.g. a
    pkg-config result for a known library id) -- never from raw user input,
    since they are passed straight to the compiler's argv.
    """

    _check_source(source, "C++")
    _required_bytes(requested_bits, output_format)
    cxx = _tool(compiler, "CXX", ("c++", "g++"))
    destination = Path(destination).resolve()

    with tempfile.TemporaryDirectory(prefix="spur_cpp_") as temp_name:
        work_dir = Path(temp_name)
        source_path = work_dir / "generator.cpp"
        executable = work_dir / "generator"
        generated_path = work_dir / "bitstream.out"
        compile_stdout = work_dir / "compile.stdout.log"
        compile_stderr = work_dir / "compile.stderr.log"
        run_stdout = work_dir / "run.stdout.log"
        run_stderr = work_dir / "run.stderr.log"
        source_path.write_text(source, encoding="utf-8")

        _run_logged(
            [cxx, f"-std={std}", "-O2", "-Wall", "-Wextra", str(source_path),
             "-o", str(executable), *extra_flags],
            cwd=work_dir,
            timeout=COMPILE_TIMEOUT_SECONDS,
            stdout_path=compile_stdout,
            stderr_path=compile_stderr,
        )
        _run_logged(
            [str(executable), str(generated_path), str(requested_bits)],
            cwd=work_dir,
            timeout=RUN_TIMEOUT_SECONDS,
            stdout_path=run_stdout,
            stderr_path=run_stderr,
        )
        return _promote_output(
            generated_path, run_stdout, destination, requested_bits, output_format
        )


def _verilator_major(verilator: str, work_dir: Path) -> int:
    try:
        result = subprocess.run(
            [verilator, "--version"],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GenerationError(f"Could not query Verilator version: {exc}") from exc
    match = re.search(r"Verilator\s+(\d+)", result.stdout + result.stderr)
    if result.returncode != 0 or not match:
        raise GenerationError("Could not determine the installed Verilator version.")
    return int(match.group(1))


def _legacy_harness(top_module: str) -> str:
    return f'''#include "V{top_module}.h"
#include "verilated.h"

static vluint64_t simulation_time = 0;
double sc_time_stamp() {{ return static_cast<double>(simulation_time); }}

int main(int argc, char **argv) {{
    Verilated::commandArgs(argc, argv);
    V{top_module} top;
    const vluint64_t iteration_limit = 100000000ULL;
    while (!Verilated::gotFinish() && simulation_time < iteration_limit) {{
        top.eval();
        ++simulation_time;
    }}
    top.final();
    if (!Verilated::gotFinish()) {{
        VL_PRINTF("Simulation stopped: testbench did not call $finish.\\n");
        return 3;
    }}
    return 0;
}}
'''


def generate_from_systemverilog(
    core_source: str,
    testbench_source: str,
    top_module: str,
    destination: Path,
    requested_bits: int,
    *,
    output_format: str = "ascii",
    verilator: Optional[str] = None,
    binary_destination: Optional[Path] = None,
) -> GeneratedBitstream:
    """Build and execute a SystemVerilog testbench with Verilator."""

    _check_source(core_source, "SystemVerilog core")
    _check_source(testbench_source, "SystemVerilog testbench")
    _required_bytes(requested_bits, output_format)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", top_module):
        raise GenerationError("Top module must be a valid SystemVerilog identifier.")

    verilator_bin = _tool(verilator, "VERILATOR", ("verilator",))
    destination = Path(destination).resolve()

    with tempfile.TemporaryDirectory(prefix="spur_sv_") as temp_name:
        work_dir = Path(temp_name)
        core_path = work_dir / "core.sv"
        testbench_path = work_dir / "testbench.sv"
        object_dir = work_dir / "obj_dir"
        generated_path = work_dir / "bitstream.out"
        compile_stdout = work_dir / "compile.stdout.log"
        compile_stderr = work_dir / "compile.stderr.log"
        run_stdout = work_dir / "run.stdout.log"
        run_stderr = work_dir / "run.stderr.log"
        core_path.write_text(core_source, encoding="utf-8")
        testbench_path.write_text(testbench_source, encoding="utf-8")

        major = _verilator_major(verilator_bin, work_dir)
        common = [
            verilator_bin,
            "-Wall",
            "-Wno-fatal",
            "--top-module",
            top_module,
            "--Mdir",
            str(object_dir),
        ]
        if major >= 5:
            executable = object_dir / f"V{top_module}"
            command = common + [
                "--binary",
                "--timing",
                str(core_path),
                str(testbench_path),
            ]
        else:
            harness_path = work_dir / "sim_main.cpp"
            harness_path.write_text(_legacy_harness(top_module), encoding="utf-8")
            executable = object_dir / f"V{top_module}"
            command = common + [
                "--cc",
                "--exe",
                "--build",
                str(core_path),
                str(testbench_path),
                str(harness_path),
            ]

        env = os.environ.copy()
        local_root = Path(verilator_bin).parent.parent
        if (local_root / "include" / "verilated.h").is_file():
            env.setdefault("VERILATOR_ROOT", str(local_root))
        _run_logged(
            command,
            cwd=work_dir,
            timeout=COMPILE_TIMEOUT_SECONDS,
            stdout_path=compile_stdout,
            stderr_path=compile_stderr,
            env=env,
        )
        _run_logged(
            [str(executable), f"+OUTPUT={generated_path}", f"+BITS={requested_bits}"],
            cwd=work_dir,
            timeout=RUN_TIMEOUT_SECONDS,
            stdout_path=run_stdout,
            stderr_path=run_stderr,
            env=env,
        )
        if binary_destination is not None:
            binary_destination = Path(binary_destination)
            binary_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(executable, binary_destination)
        return _promote_output(
            generated_path, run_stdout, destination, requested_bits, output_format
        )
