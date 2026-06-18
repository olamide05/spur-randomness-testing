# Main Goal

Develop an automated framework for evaluating and comparing pseudo-random number generators (PRNGs) using the official NIST Statistical Test Suite (STS), while understanding how finite precision, computer arithmetic, and FPGA implementations affect randomness.

---

# First Stage – Learning the Fundamentals

Build a strong understanding of:

* PRNGs and randomness
* XOR-based generators
* Chaos theory and logistic maps
* Finite precision and rounding errors
* NIST SP 800-22 statistical tests
* How randomness is evaluated in research papers

At the same time, continue reading relevant papers and maintaining research notes.

---

# Second Stage – Understanding NIST Statistical Testing

The goal is to become confident in interpreting the NIST tests and their outputs.

This includes:

* Frequency Test
* Block Frequency Test
* Runs Test
* Rank Test
* FFT Test
* Approximate Entropy Test
* Linear Complexity Test
* Other NIST SP 800-22 tests

For each test I want to understand:

* What it measures
* Why it is important
* Typical failure modes
* Interpretation of p-values
* Interpretation of pass rates

---

# Third Stage – NIST STS Automation Framework

Develop an automated pipeline around the official NIST STS 2.1.2 implementation.

Pipeline:

MATLAB / Simulink Output
↓
Input Conversion
↓
NIST STS Execution
↓
Result Parsing
↓
JSON / PDF Report

Inputs:

* MATLAB workspace variables
* ASCII files containing binary sequences
* Future FPGA datasets

Features:

* Standard parameter configuration
* Custom parameter configuration
* Automated execution
* Automated report generation

---

# Fourth Stage – Dataset Analysis

Once datasets are available:

* Run NIST STS tests
* Compare multiple generators
* Analyse pass rates and p-values
* Identify patterns, weaknesses, or biases
* Document observations

Potential datasets:

* Logistic map generators
* XORShift generators
* FPGA-generated sequences
* Future QRNG datasets

---

# Fifth Stage – Finite Precision and Hardware Effects

Investigate how:

* Finite precision
* Rounding errors
* Floating-point arithmetic
* FPGA implementations

affect the statistical properties of generated sequences.

---

# Sixth Stage – Documentation and Reporting

Throughout the project:

* Maintain GitHub repository
* Maintain project architecture notes
* Maintain paper review notes
* Document experiments
* Track weekly progress
* Generate final reports

---

# Progress So Far

Completed:

* Read several project-related papers
* Implemented XORShift generator
* Studied Frequency Test and Runs Test
* Learned NIST SP 800-22 fundamentals
* Created project repository structure
* Built input conversion pipeline
* Built configuration management system
* Downloaded official NIST STS 2.1.2
* Compiled official NIST STS successfully using WSL
* Successfully executed STS and tested file input workflow

Current Focus:

* Understanding complete STS execution workflow
* Designing automation architecture
* Creating NIST execution wrapper
* Designing result parsing system

Next Steps:

* Run STS successfully on valid datasets
* Document all STS execution parameters
* Implement nist_runner.py
* Parse STS output automatically
* Generate JSON reports

---

# STS Execution Requirements

The official STS workflow requires:

1. Stream Length
2. Input Source
3. Test Selection
4. Test Parameters
5. Number of Bitstreams
6. Input Format (ASCII or Binary)

---

# Current Architecture

Input Converter
↓
Config Manager
↓
NIST Runner
↓
Result Parser
↓
Report Generator
