# SPUR Randomness Testing Framework

A modular research framework for evaluating the statistical quality of random number generators using the **NIST SP 800-22 Statistical Test Suite (STS)**.

Developed as part of the **SPUR (Summer Programme for Undergraduate Research)** at **Maynooth University**.

---

## Overview

Random number generators (RNGs) are fundamental to cryptography, simulations, hardware design, embedded systems, and scientific computing. This project provides an automated framework for executing the NIST Statistical Test Suite, collecting results, and exporting them into structured formats for further analysis.

Rather than interacting with the STS command-line interface manually, this framework automates the complete workflow:

```
Bitstream
    │
    ▼
Configuration
    │
    ▼
NIST STS Runner
    │
    ▼
NIST SP 800-22
    │
    ▼
Result Parser
    │
    ▼
JSON / CSV / LaTeX Reports
```

---

# Getting Started (GitHub Codespaces)

This repository is preconfigured for **GitHub Codespaces** / Dev Containers.

1. Click **Code → Create codespace on main** (or on your branch).
2. Wait for the container to finish provisioning. On first start it automatically:
   - installs system build tools (`build-essential`, `gcc`, `make`) and Verilator,
   - installs the Python dependencies from `requirements.txt`,
   - downloads the NIST STS source if it is missing, then **builds** the
     `assess` binary from source (`scripts/setup_sts.sh`),
   - runs the automated test suite to verify the setup.

Once the codespace is ready:

```bash
make test
make serve
```

Port 5000 is forwarded automatically by Codespaces. Open the forwarded
**SPUR NIST Web UI** port after running `make serve`.

## Local setup

The same steps work on a Debian/Ubuntu Linux machine with Python 3.10+:

```bash
make install
```

`make install` calls the idempotent setup script, which uses `sudo` when
necessary to install GCC, Make, Verilator,
Python venv support, curl, and unzip. It then creates `.venv`, installs all
Python packages, builds STS, and runs the tests. The compiled `assess` binary
and object files are build artifacts; `scripts/setup_sts.sh` regenerates them.
If sudo is unavailable but the other dependencies already exist, Verilator can
instead be installed into the git-ignored `.tools/` directory with
`make install-local`; the Web UI detects it automatically.

Useful commands:

```bash
make help        # list commands
make install     # complete system setup + verification
make setup-sts   # rebuild only NIST STS
make test        # run all automated tests
make serve       # start the Web UI
```

## Web UI assessment inputs

Start the local UI and open `http://127.0.0.1:5000`:

```bash
make serve
```

The assessment form supports three input modes:

- **Bitstream files**: upload one file for a dashboard or several for a
  parallel comparison.
- **C generator**: edit C11 source in the browser or load a `.c` file into the
  syntax-highlighting editor. The executable receives
  `OUTPUT_PATH REQUESTED_BITS`, has the normal C library plus `libm`, and
  writes ASCII bits or packed binary to the supplied path.
- **SystemVerilog generator**: edit or load separate core and testbench `.sv`
  files with Verilog/SystemVerilog highlighting. Verilator builds the selected
  top module. The simulation receives `+OUTPUT=<path> +BITS=<count>` and writes
  the requested ASCII or packed stream.

The starter source in both editors implements these contracts and can be run
unchanged. Source and generated streams are retained under
`webui/uploads/generated/`, while rendered reports are retained under
`webui/uploads/reports/`. Both runtime directories are git-ignored.

> **Security:** C and SystemVerilog assessment modes compile and execute the
> submitted code on the host. Local setup binds to localhost; Codespaces uses
> its forwarded port, which should remain private. Time and output limits are
> applied, but this is not a sandbox for untrusted source code.

---

# Features

- Automated execution of NIST SP 800-22
- Configurable experiment settings
- Automatic Windows → WSL support
- Automatic stream validation
- Result parsing
- JSON report generation
- Modular architecture
- Ready for FPGA-generated bitstreams
- Extensible export system

---

# Project Structure

```
spur-randomness-testing/

├── Makefile                 # install, test, build, and serve entry points
├── scripts/
│   ├── setup.sh             # complete Debian/Ubuntu setup
│   ├── setup_sts.sh         # NIST STS download/build
│   └── setup_verilator_local.sh
│
├── webui/
│   ├── app.py               # Flask routes and assessment orchestration
│   ├── templates/           # Jinja page templates
│   └── static/              # styles, behavior, and vendored Ace editor
│
├── datasets/
│   ├── comparison/
│   ├── generated/
│   ├── fpga/
│   └── test_cases/
│
├── src/
│   ├── automation/
│   │   ├── loader.py
│   │   ├── nist_runner.py
│   │   ├── matlab_runner.py
│   │   └── result_parser.py
│   │
│   ├── config/
│   │   └── sts_config.py
│   │
│   └── generators/
│
├── tests/
├── results/
├── matlab/
├── sts/
│   └── sts-2.1.2/
│
└── README.md
```

---

# Current Progress

## Completed

- Literature review
- XORShift implementation
- Seed analysis experiments
- Frequency analysis
- Automated NIST STS execution
- Windows / WSL integration
- Bitstream validation
- Automatic stream calculation
- Automatic STS prompt generation
- Result parsing
- JSON export framework
- Web UI C11 bitstream generation
- Web UI SystemVerilog/Verilator bitstream generation
- Syntax-highlighted in-browser source editors

---

## In Progress

- Configurable STS runner
- Parameter configuration
- Improved parser
- Better experiment summaries

---

## Planned

- MATLAB integration
- FPGA bitstream support
- VHDL workflow
- Batch experiment execution
- Statistical comparison tools
- Interactive dashboard

---

# Technologies

- Python 3
- Flask
- Ace editor
- GCC / C11
- SystemVerilog / Verilator
- NIST SP 800-22
- Linux / WSL
- MATLAB
- JSON
- CSV
- LaTeX

---

# Example Usage

```python
from config.sts_config import STSConfig
from automation.nist_runner import NISTRunner

config = STSConfig(
    input_file="datasets/test_cases/test_bits.txt",
    stream_length=1000000,
    number_of_streams=10,
)

runner = NISTRunner(config)
result = runner.run()
```

---

# Output

The framework automatically generates structured experiment outputs including:

- JSON reports
- CSV summaries
- LaTeX tables

Example:

```
results/

sample_bitstream_results.json
report.csv
report.tex
```

---

# Research Goals

This project aims to provide a reusable framework for evaluating the statistical properties of software and hardware random number generators using standardized statistical testing.

Future work includes integrating FPGA-generated bitstreams, MATLAB simulations, and additional statistical test suites.

---

# Repository Status

🚧 Active Development

Current focus:

- Configurable STS execution
- Parameter automation
- Enhanced result parsing
- Export system

---

# Acknowledgements

- Maynooth University
- SPUR Programme
- NIST Statistical Test Suite (SP 800-22)

---

# License

This project is developed for research purposes as part of the SPUR programme.
