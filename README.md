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
│   ├── generators/
│   └── tests/
│
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

---

## In Progress

- Configurable STS runner
- Parameter configuration
- CSV exporter
- LaTeX exporter
- Improved parser
- Better experiment summaries

---

## Planned

- MATLAB integration
- FPGA bitstream support
- Verilog/VHDL workflow
- Batch experiment execution
- Statistical comparison tools
- Interactive dashboard

---

# Technologies

- Python 3
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
- CSV summaries *(coming soon)*
- LaTeX tables *(coming soon)*

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
