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
    pkg_config_name: str | None = None
    family: str = "Other"
    std: str = "c++17"


@dataclass(frozen=True)
class SVExample:
    id: str
    title: str
    description: str
    generator_name: str
    core_source: str
    family: str = "Other"


def _cpp_generator_source(body: str) -> str:
    """Wrap a next_word() implementation in the WebUI generator contract."""
    return r'''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>

''' + body + r'''

// Contract: generator OUTPUT_PATH REQUESTED_BITS
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    char *end = nullptr;
    const unsigned long long requested_bits = std::strtoull(argv[2], &end, 10);
    if (end == argv[2] || *end != '\0') return 2;
    std::FILE *output = std::fopen(argv[1], "wb");
    if (!output) { std::perror("fopen"); return 1; }
    const char *format = std::getenv("SPUR_OUTPUT_FORMAT");
    if (format && std::strcmp(format, "ascii") == 0) {
        std::uint64_t ascii_word = 0;
        unsigned ascii_available = 0;
        for (unsigned long long i = 0; i < requested_bits; ++i) {
            if (ascii_available == 0) {
                ascii_word = next_word();
                ascii_available = 64;
            }
            std::fputc('0' + static_cast<int>((ascii_word >> 63) & 1U), output);
            ascii_word <<= 1;
            --ascii_available;
            if ((i + 1U) % 64U == 0U) std::fputc('\n', output);
        }
        return std::fclose(output) == 0 ? 0 : 1;
    }

    const unsigned long long requested_bytes = (requested_bits + 7U) / 8U;
    std::uint64_t word = 0;
    unsigned available = 0;
    for (unsigned long long i = 0; i < requested_bytes; ++i) {
        if (available == 0) { word = next_word(); available = 8; }
        unsigned char output_byte = static_cast<unsigned char>((word >> 56) & 0xffU);
        const unsigned trailing_bits = static_cast<unsigned>(requested_bits & 7U);
        if (trailing_bits != 0 && i + 1U == requested_bytes)
            output_byte &= static_cast<unsigned char>(0xffU << (8U - trailing_bits));
        if (std::fputc(output_byte, output) == EOF) {
            std::perror("fputc");
            std::fclose(output);
            return 1;
        }
        word <<= 8;
        --available;
    }
    return std::fclose(output) == 0 ? 0 : 1;
}
'''

PCG32_SOURCE = _cpp_generator_source(r'''// PCG-XSH-RR: a 64-bit LCG state with a permuted 32-bit output.
static std::uint64_t state = UINT64_C(0x853c49e6748fea9b);
static std::uint32_t pcg32() {
    const std::uint64_t old = state;
    state = old * UINT64_C(6364136223846793005) + UINT64_C(1442695040888963407);
    const std::uint32_t x = static_cast<std::uint32_t>(((old >> 18U) ^ old) >> 27U);
    const unsigned r = static_cast<unsigned>(old >> 59U);
    return (x >> r) | (x << ((-r) & 31U));
}
static std::uint64_t next_word() {
    return (static_cast<std::uint64_t>(pcg32()) << 32) | pcg32();
}
''')

SPLITMIX64_SOURCE = _cpp_generator_source(r'''// SplitMix64: Weyl addition followed by two multiplicative mixers.
static std::uint64_t state = UINT64_C(0x243f6a8885a308d3);
static std::uint64_t next_word() {
    std::uint64_t z = (state += UINT64_C(0x9e3779b97f4a7c15));
    z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
    return z ^ (z >> 31);
}
''')

MSWS_SOURCE = _cpp_generator_source(r'''// Middle-Square Weyl Sequence: multiply, add Weyl, rotate.
static std::uint64_t x = UINT64_C(0xb5ad4eceda1ce2a9), w = 0;
static constexpr std::uint64_t step = UINT64_C(0xb5ad4eceda1ce2a9);
static std::uint64_t next_word() {
    x *= x; x += (w += step); x = (x >> 32) | (x << 32);
    const std::uint64_t hi = x;
    x *= x; x += (w += step); x = (x >> 32) | (x << 32);
    return (hi & UINT64_C(0xffffffff00000000)) | (x >> 32);
}
''')

LOGISTIC_MAP_SOURCE = _cpp_generator_source(r'''// Coupled logistic maps. Digital chaos is finite-state and not cryptographic.
static double x = 0.3141592653589793, y = 0.2718281828459045;
static std::uint64_t next_word() {
    std::uint64_t out = 0;
    for (unsigned i = 0; i < 64; ++i) {
        const double nx = 3.99*x*(1.0-x), ny = 3.98*y*(1.0-y);
        x = 0.97*nx + 0.03*ny; y = 0.03*nx + 0.97*ny;
        out = (out << 1) | static_cast<std::uint64_t>(x > y);
    }
    return out;
}
''')

TENT_MAP_SOURCE = _cpp_generator_source(r'''// Coupled skew-tent maps with unequal parameters.
static double x = 0.123456789012345, y = 0.731234567890123;
static double tent(double v, double split) {
    return v < split ? v/split : (1.0-v)/(1.0-split);
}
static std::uint64_t next_word() {
    std::uint64_t out = 0;
    for (unsigned i = 0; i < 64; ++i) {
        const double nx = tent(x, 0.417), ny = tent(y, 0.683);
        x = std::fmod(nx + 0.03125*ny, 1.0);
        y = std::fmod(ny + 0.046875*nx, 1.0);
        out = (out << 1) | static_cast<std::uint64_t>(x + y >= 1.0);
    }
    return out;
}
''')

HENON_MAP_SOURCE = _cpp_generator_source(r'''// Henon attractor sampled through a threshold comparator.
static double x = 0.1, y = 0.3;
static std::uint64_t next_word() {
    std::uint64_t out = 0;
    for (unsigned i = 0; i < 64; ++i) {
        const double nx = 1.0 - 1.4*x*x + y;
        y = 0.3*x; x = nx;
        out = (out << 1) | static_cast<std::uint64_t>(x >= 0.0);
    }
    return out;
}
''')


OPENSSL_RAND_SOURCE = r'''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <openssl/rand.h>

// Contract: generator OUTPUT_PATH REQUESTED_BITS
// Writes ceil(REQUESTED_BITS / 8) bytes from OpenSSL RAND_bytes().
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    char *end = nullptr;
    const unsigned long long requested_bits = std::strtoull(argv[2], &end, 10);
    if (end == argv[2] || *end != '\0') return 2;
    std::FILE *output = std::fopen(argv[1], "wb");
    if (!output) { std::perror("fopen"); return 1; }

    const std::size_t chunk_bytes = 4096;
    unsigned char buffer[chunk_bytes];
    unsigned long long remaining = (requested_bits + 7U) / 8U;
    while (remaining != 0) {
        const std::size_t count = remaining < chunk_bytes
            ? static_cast<std::size_t>(remaining) : chunk_bytes;
        if (RAND_bytes(buffer, static_cast<int>(count)) != 1) {
            std::fprintf(stderr, "RAND_bytes failed\n");
            std::fclose(output);
            return 1;
        }
        const unsigned trailing_bits = static_cast<unsigned>(requested_bits & 7U);
        if (remaining == count && trailing_bits != 0)
            buffer[count - 1] &= static_cast<unsigned char>(0xffU << (8U - trailing_bits));
        if (std::fwrite(buffer, 1, count, output) != count) {
            std::perror("fwrite");
            std::fclose(output);
            return 1;
        }
        remaining -= count;
    }
    return std::fclose(output) == 0 ? 0 : 1;
}
'''


LIBSODIUM_RANDOMBYTES_SOURCE = r'''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <sodium.h>

// Contract: generator OUTPUT_PATH REQUESTED_BITS
// Writes ceil(REQUESTED_BITS / 8) bytes from libsodium randombytes_buf().
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    if (sodium_init() < 0) return 1;
    char *end = nullptr;
    const unsigned long long requested_bits = std::strtoull(argv[2], &end, 10);
    if (end == argv[2] || *end != '\0') return 2;
    std::FILE *output = std::fopen(argv[1], "wb");
    if (!output) { std::perror("fopen"); return 1; }

    const std::size_t chunk_bytes = 4096;
    unsigned char buffer[chunk_bytes];
    unsigned long long remaining = (requested_bits + 7U) / 8U;
    while (remaining != 0) {
        const std::size_t count = remaining < chunk_bytes
            ? static_cast<std::size_t>(remaining) : chunk_bytes;
        randombytes_buf(buffer, count);
        const unsigned trailing_bits = static_cast<unsigned>(requested_bits & 7U);
        if (remaining == count && trailing_bits != 0)
            buffer[count - 1] &= static_cast<unsigned char>(0xffU << (8U - trailing_bits));
        if (std::fwrite(buffer, 1, count, output) != count) {
            std::perror("fwrite");
            std::fclose(output);
            return 1;
        }
        remaining -= count;
    }
    return std::fclose(output) == 0 ? 0 : 1;
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


PCG32_SV_SOURCE = r'''module rng_core;
  logic [63:0] state = 64'h853c49e6748fea9b;
  logic [63:0] word = 0;
  int unsigned bits_left = 0;
  function automatic logic [31:0] rotr32(input logic [31:0] x, input int r);
    rotr32 = (x >> r) | (x << ((32-r) & 31));
  endfunction
  task automatic refill;
    logic [63:0] oldstate;
    logic [31:0] xorshifted;
    logic [31:0] first_word;
    int rot;
    begin
      oldstate = state;
      state = oldstate * 64'd6364136223846793005 + 64'd1442695040888963407;
      xorshifted = ((oldstate >> 18) ^ oldstate) >> 27;
      rot = oldstate >> 59;
      first_word = rotr32(xorshifted, rot);
      oldstate = state;
      state = oldstate * 64'd6364136223846793005 + 64'd1442695040888963407;
      xorshifted = ((oldstate >> 18) ^ oldstate) >> 27;
      rot = oldstate >> 59;
      word = {first_word, rotr32(xorshifted, rot)};
      bits_left = 64;
    end
  endtask
  task automatic next_bit(output logic value);
    begin
      if (bits_left == 0) refill();
      value = word[63]; word = word << 1; bits_left = bits_left - 1;
    end
  endtask
endmodule
'''

MSWS_SV_SOURCE = r'''module rng_core;
  logic [63:0] x = 64'hb5ad4eceda1ce2a9;
  logic [63:0] w = 0;
  logic [63:0] word = 0;
  int unsigned bits_left = 0;
  task automatic refill;
    begin
      x = x*x; w = w + 64'hb5ad4eceda1ce2a9; x = x+w;
      x = {x[31:0], x[63:32]};
      word = x; bits_left = 64;
    end
  endtask
  task automatic next_bit(output logic value);
    begin
      if (bits_left == 0) refill();
      value = word[63]; word = word << 1; bits_left = bits_left - 1;
    end
  endtask
endmodule
'''

LOGISTIC_SV_SOURCE = r'''module rng_core;
  // Q0.32 fixed-point logistic maps: x[n+1] = 4*x[n]*(1-x[n]).
  logic [31:0] x = 32'h3243f6a9;
  logic [31:0] y = 32'h8a308d31;
  task automatic next_bit(output logic value);
    logic [63:0] px;
    logic [63:0] py;
    begin
      px = x * (64'h0000000100000000 - x);
      py = y * (64'h0000000100000000 - y);
      x = px[61:30] ^ {y[15:0], y[31:16]};
      y = py[61:30] ^ {x[7:0], x[31:8]};
      value = x[31] ^ y[30];
    end
  endtask
endmodule
'''

TENT_SV_SOURCE = r'''module rng_core;
  // Two coupled Q0.32 tent maps with cross-coupling against short cycles.
  logic [31:0] x = 32'h1f9add37;
  logic [31:0] y = 32'hbb67ae85;
  task automatic next_bit(output logic value);
    logic [31:0] tx;
    logic [31:0] ty;
    begin
      tx = x[31] ? ~(x << 1) : (x << 1);
      ty = y[31] ? ~(y << 1) : (y << 1);
      x = tx + {y[4:0], y[31:5]};
      y = ty + {x[6:0], x[31:7]};
      value = x[29] ^ y[31];
    end
  endtask
endmodule
'''


LIBRARY_EXAMPLES = [
    LibraryExample("pcg32", "PCG32 (XSH-RR)", "A compact permuted congruential generator with 64-bit state.", "pcg32", "binary", PCG32_SOURCE, family="Arithmetic"),
    LibraryExample("splitmix64", "SplitMix64", "A fast Weyl-sequence generator with strong 64-bit arithmetic mixing.", "splitmix64", "binary", SPLITMIX64_SOURCE, family="Arithmetic"),
    LibraryExample("msws", "Middle-Square Weyl Sequence", "A modern middle-square generator rescued from zero cycles by a Weyl sequence.", "msws", "binary", MSWS_SOURCE, family="Arithmetic"),
    LibraryExample("coupled_logistic", "Coupled logistic maps", "Two floating-point logistic maps coupled before threshold extraction.", "coupled_logistic", "binary", LOGISTIC_MAP_SOURCE, family="Chaos"),
    LibraryExample("coupled_tent", "Coupled skew-tent maps", "Unequal skew-tent maps with cross-coupling and comparator extraction.", "coupled_tent", "binary", TENT_MAP_SOURCE, family="Chaos"),
    LibraryExample("henon_map", "Henon map", "The classic two-dimensional Henon attractor sampled into a bitstream.", "henon_map", "binary", HENON_MAP_SOURCE, family="Chaos"),
    LibraryExample(
        id="openssl_rand",
        title="OpenSSL RAND_bytes",
        description="A CSPRNG-backed generator using OpenSSL's RAND_bytes().",
        generator_name="openssl_rand",
        output_format="binary",
        source=OPENSSL_RAND_SOURCE,
        pkg_config_name="libcrypto",
        family="Cryptographic",
    ),
    LibraryExample(
        id="libsodium_randombytes",
        title="libsodium randombytes_buf",
        description="A CSPRNG-backed generator using libsodium's randombytes_buf().",
        generator_name="libsodium_randombytes",
        output_format="binary",
        source=LIBSODIUM_RANDOMBYTES_SOURCE,
        pkg_config_name="libsodium",
        family="Cryptographic",
    ),
]

SV_EXAMPLES = [
    SVExample("sv_pcg32", "PCG32 (SystemVerilog)", "A hardware form of the permuted congruential generator.", "sv_pcg32", PCG32_SV_SOURCE, "Arithmetic"),
    SVExample("sv_msws", "Middle-Square Weyl (SystemVerilog)", "A 64-bit multiply-add-rotate arithmetic generator.", "sv_msws", MSWS_SV_SOURCE, "Arithmetic"),
    SVExample("sv_logistic", "Fixed-point logistic maps (SystemVerilog)", "Coupled Q0.32 logistic maps with cross-state perturbation.", "sv_logistic", LOGISTIC_SV_SOURCE, "Chaos"),
    SVExample("sv_tent", "Fixed-point tent maps (SystemVerilog)", "Coupled Q0.32 tent maps designed for straightforward RTL experiments.", "sv_tent", TENT_SV_SOURCE, "Chaos"),
    SVExample(
        id="sv_xoshiro128ss",
        title="xoshiro128** (SystemVerilog)",
        description=(
            "A 128-bit-state PRNG designed to pass much harder statistical "
            "batteries than a plain LFSR or xorshift core."
        ),
        generator_name="sv_xoshiro128ss",
        core_source=XOSHIRO128SS_SV_SOURCE,
        family="Arithmetic",
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
    return [
        ex for ex in LIBRARY_EXAMPLES
        if ex.pkg_config_name is None or _pkg_config_available(ex.pkg_config_name)
    ]


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
    if example.pkg_config_name is None:
        return ()
    return _pkg_config_flags(example.pkg_config_name)


def sv_example_by_id(example_id: str):
    for example in SV_EXAMPLES:
        if example.id == example_id:
            return example
    return None
