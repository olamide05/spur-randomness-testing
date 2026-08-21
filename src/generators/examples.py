"""Registry of example generators shown on the web UI's Examples tab.

To add your own library example: write a template using the same
`generator OUTPUT_PATH REQUESTED_BITS` contract as the C/C++ templates in
source_runner.py, append a LibraryExample entry to LIBRARY_EXAMPLES below with
the pkg-config name that reports the library as installed, and it will appear
automatically the next time that library's headers/pkg-config file are
present on this host -- no other code changes needed. `libsodium_randombytes`
below is a real, ready-to-run example of exactly this: it stays hidden until
`libsodium-dev` is installed.
"""

import functools
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class LibraryExample:
    id: str
    title: str
    description: str
    generator_name: str
    output_format: str
    source: str
    pkg_config_name: str
    std: str = "c++17"


@dataclass(frozen=True)
class SVExample:
    id: str
    title: str
    description: str
    generator_name: str
    core_source: str


OPENSSL_RAND_SOURCE = r'''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <openssl/rand.h>

// Contract: generator OUTPUT_PATH REQUESTED_BITS
// Uses OpenSSL's RAND_bytes() (a CSPRNG) and emits each bit as ASCII '0'/'1'.
int main(int argc, char **argv) {
    if (argc != 3) {
        std::fprintf(stderr, "usage: %s OUTPUT_PATH REQUESTED_BITS\n", argv[0]);
        return 2;
    }

    char *end = nullptr;
    unsigned long long requested_bits = std::strtoull(argv[2], &end, 10);
    if (end == argv[2] || *end != '\0') {
        std::fprintf(stderr, "invalid bit count: %s\n", argv[2]);
        return 2;
    }

    std::FILE *output = std::fopen(argv[1], "wb");
    if (!output) {
        std::perror("fopen");
        return 1;
    }

    const size_t chunk_bytes = 4096;
    unsigned char buffer[chunk_bytes];
    unsigned long long bits_written = 0;
    unsigned long long col = 0;
    while (bits_written < requested_bits) {
        if (RAND_bytes(buffer, chunk_bytes) != 1) {
            std::fprintf(stderr, "RAND_bytes failed\n");
            std::fclose(output);
            return 1;
        }
        for (size_t i = 0; i < chunk_bytes && bits_written < requested_bits; ++i) {
            for (int b = 7; b >= 0 && bits_written < requested_bits; --b) {
                int bit = (buffer[i] >> b) & 1;
                std::fputc('0' + bit, output);
                ++bits_written;
                if (++col % 64 == 0) std::fputc('\n', output);
            }
        }
    }

    if (std::fclose(output) != 0) {
        std::perror("fclose");
        return 1;
    }
    return 0;
}
'''


LIBSODIUM_RANDOMBYTES_SOURCE = r'''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <sodium.h>

// Contract: generator OUTPUT_PATH REQUESTED_BITS
// Uses libsodium's randombytes_buf() and emits each bit as ASCII '0'/'1'.
int main(int argc, char **argv) {
    if (argc != 3) {
        std::fprintf(stderr, "usage: %s OUTPUT_PATH REQUESTED_BITS\n", argv[0]);
        return 2;
    }
    if (sodium_init() < 0) {
        std::fprintf(stderr, "sodium_init failed\n");
        return 1;
    }

    char *end = nullptr;
    unsigned long long requested_bits = std::strtoull(argv[2], &end, 10);
    if (end == argv[2] || *end != '\0') {
        std::fprintf(stderr, "invalid bit count: %s\n", argv[2]);
        return 2;
    }

    std::FILE *output = std::fopen(argv[1], "wb");
    if (!output) {
        std::perror("fopen");
        return 1;
    }

    const size_t chunk_bytes = 4096;
    unsigned char buffer[chunk_bytes];
    unsigned long long bits_written = 0;
    unsigned long long col = 0;
    while (bits_written < requested_bits) {
        randombytes_buf(buffer, chunk_bytes);
        for (size_t i = 0; i < chunk_bytes && bits_written < requested_bits; ++i) {
            for (int b = 7; b >= 0 && bits_written < requested_bits; --b) {
                int bit = (buffer[i] >> b) & 1;
                std::fputc('0' + bit, output);
                ++bits_written;
                if (++col % 64 == 0) std::fputc('\n', output);
            }
        }
    }

    if (std::fclose(output) != 0) {
        std::perror("fclose");
        return 1;
    }
    return 0;
}
'''


XOSHIRO128SS_SV_SOURCE = r'''module rng_core;
  // xoshiro128** (Blackman & Vigna) -- a small, hardware-cheap upgrade over
  // plain xorshift/LFSR designs. Those fail the NIST Rank and Linear
  // Complexity tests because their raw state update is linear over GF(2);
  // the rotate+multiply output scramble below breaks that linearity in the
  // emitted bits while the state update itself stays a 3-op xorshift network.
  logic [31:0] s0 = 32'h9E3779B9;
  logic [31:0] s1 = 32'h6C078967;
  logic [31:0] s2 = 32'hBB67AE85;
  logic [31:0] s3 = 32'h3C6EF372;

  logic [31:0] word = 32'h0;
  int unsigned bits_left = 0;

  function automatic logic [31:0] rotl(input logic [31:0] x, input int k);
    rotl = (x << k) | (x >> (32 - k));
  endfunction

  task automatic advance;
    logic [31:0] result;
    logic [31:0] t;
    begin
      result = rotl(s1 * 5, 7) * 9;
      t = s1 << 9;

      s2 = s2 ^ s0;
      s3 = s3 ^ s1;
      s1 = s1 ^ s2;
      s0 = s0 ^ s3;

      s2 = s2 ^ t;
      s3 = rotl(s3, 11);

      word = result;
      bits_left = 32;
    end
  endtask

  task automatic next_bit(output logic value);
    begin
      if (bits_left == 0) advance();
      value = word[31];
      word = word << 1;
      bits_left = bits_left - 1;
    end
  endtask
endmodule
'''


LIBRARY_EXAMPLES = [
    LibraryExample(
        id="openssl_rand",
        title="OpenSSL RAND_bytes",
        description="A CSPRNG-backed generator using OpenSSL's RAND_bytes().",
        generator_name="openssl_rand",
        output_format="ascii",
        source=OPENSSL_RAND_SOURCE,
        pkg_config_name="libcrypto",
    ),
    LibraryExample(
        id="libsodium_randombytes",
        title="libsodium randombytes_buf",
        description="A CSPRNG-backed generator using libsodium's randombytes_buf().",
        generator_name="libsodium_randombytes",
        output_format="ascii",
        source=LIBSODIUM_RANDOMBYTES_SOURCE,
        pkg_config_name="libsodium",
    ),
]

SV_EXAMPLES = [
    SVExample(
        id="sv_xoshiro128ss",
        title="xoshiro128** (SystemVerilog)",
        description=(
            "A 128-bit-state PRNG designed to pass much harder statistical "
            "batteries than a plain LFSR or xorshift core."
        ),
        generator_name="sv_xoshiro128ss",
        core_source=XOSHIRO128SS_SV_SOURCE,
    ),
]


@functools.lru_cache(maxsize=None)
def _pkg_config_available(name: str) -> bool:
    try:
        return subprocess.run(
            ["pkg-config", "--exists", name],
            capture_output=True,
            timeout=5,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@functools.lru_cache(maxsize=None)
def _pkg_config_flags(name: str) -> tuple:
    try:
        result = subprocess.run(
            ["pkg-config", "--cflags", "--libs", name],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    return tuple(result.stdout.split())


def available_library_examples() -> list:
    """LIBRARY_EXAMPLES filtered to libraries actually installed on this host --
    the Examples tab and the C-panel's library dropdown both call this so an
    uninstalled library never appears in either place."""
    return [ex for ex in LIBRARY_EXAMPLES if _pkg_config_available(ex.pkg_config_name)]


def library_example_by_id(example_id: str):
    """Look up a library example by id, but only among currently-available
    ones -- the server never trusts a posted id beyond this lookup."""
    for example in available_library_examples():
        if example.id == example_id:
            return example
    return None


def extra_compile_flags(example: LibraryExample) -> tuple:
    """Compiler/linker flags for one library example, resolved server-side
    from pkg-config -- never taken from user input."""
    return _pkg_config_flags(example.pkg_config_name)


def sv_example_by_id(example_id: str):
    for example in SV_EXAMPLES:
        if example.id == example_id:
            return example
    return None
