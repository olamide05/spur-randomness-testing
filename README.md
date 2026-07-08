# Randomness Testing Framework

> Automated framework for evaluating random number generators using the official NIST Statistical Test Suite (STS).

---

## Overview

This project is part of my SPUR (Summer Programme for Undergraduate Research) at Maynooth University.

The objective is to build an automation framework around the official NIST Statistical Test Suite (STS 2.1.2) for evaluating pseudo-random number generators (PRNGs), chaotic random number generators, MATLAB simulations, and FPGA-generated bitstreams.

Instead of manually running the NIST suite, this framework automates the entire workflow from input validation to report generation.

---

# Features

## Current

- Official NIST STS integration
- Automatic input validation
- Automatic bitstream processing
- Automatic stream calculation
- Windows → WSL execution
- STS automation pipeline
- Modular project architecture

## In Progress

- Result parser
- JSON report generation
- MATLAB integration
- Configurable STS parameters

## Planned

- PDF reports
- Batch testing
- FPGA dataset analysis
- MATLAB workspace support
- Statistical visualisations
- Hardware randomness evaluation

---

# Architecture

```
           MATLAB
              │
              │
      ASCII Bitstream
              │
              ▼
     Input Validation
              │
              ▼
   Stream Calculations
              │
              ▼
  Windows → WSL Adapter
              │
              ▼
 Official NIST STS 2.1.2
              │
              ▼
      Result Parser
              │
              ▼
      JSON / PDF Report
```

---

# Project Structure

```
.
├── archive/
├── datasets/
│   ├── comparison/
│   ├── fpga/
│   ├── generated/
│   └── test_cases/
├── docs/
├── experiments/
├── matlab/
├── notes/
├── results/
├── src/
│   ├── automation/
│   ├── generators/
│   └── tests/
└── sts/
```

---

# Technologies

- Python
- C
- MATLAB
- WSL (Ubuntu)
- Git

Future Technologies

- Verilog
- VHDL
- FPGA
- Simulink

---

# Development Roadmap

## Phase 1

- Repository architecture
- Literature review
- NIST STS setup
- Initial automation

## Phase 2

- Automated execution
- Result parser
- JSON reports

## Phase 3

- MATLAB integration
- Configurable testing
- Batch processing

## Phase 4

- FPGA support
- Verilog/VHDL integration
- Comparative randomness analysis

## Phase 5

- Research experiments
- Performance benchmarking
- Publication-quality reporting

---

# Current Status

Current Version

**v0.1.0**

Current Focus

- Complete result parser
- Generate JSON reports
- MATLAB integration
- Demonstrate end-to-end automated testing

---

# References

- NIST SP 800-22 Rev.1a
- NIST Statistical Test Suite (STS) 2.1.2
