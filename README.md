# Hamilton Institute SPUR 2026

## Statistical Evaluation of XOR-Based Pseudo-Random Number Generators

> Research repository documenting the investigation of XOR-based pseudo-random number generators (PRNGs), statistical randomness testing, and lightweight cryptographic applications.

---

## About the Project

This repository contains the research, experiments, notes, and implementations developed during my participation in the **Hamilton Institute SPUR 2026 Research Programme**.

The project focuses on understanding how simple logical and arithmetic operations can generate complex and seemingly random behaviour. The primary objective is to evaluate the statistical quality of XOR-based pseudo-random number generators and determine their suitability for cryptographic and lightweight security applications.

The research combines concepts from:

* Statistical Analysis
* Cryptography
* Computer Arithmetic
* Boolean Logic
* Chaos and Dynamical Systems
* FPGA-Based Computing
* Lightweight Security Systems

---

## Research Questions

This project investigates questions such as:

* Can simple XOR-based systems generate statistically random behaviour?
* How can randomness be measured objectively?
* What causes dynamical degradation in pseudo-random systems?
* How do finite precision and computer arithmetic affect randomness?
* What statistical properties make a generator suitable for security applications?

---

## Methodology

The research follows a test-driven evaluation process:

### 1. Generator Implementation

* XORShift generators
* Additional PRNG architectures
* FPGA-generated data sets

### 2. Statistical Testing

* NIST SP 800-22
* Frequency Test
* Block Frequency Test
* Runs Test
* Additional NIST tests
* Diehard Test Suite
* Dieharder Test Suite

### 3. Analysis

* Statistical comparison
* Bias detection
* Pattern analysis
* Entropy evaluation
* Dynamical degradation investigation

### 4. Documentation

* Experiment reports
* Research notes
* Literature reviews
* Weekly progress updates

---

## Repository Structure

```text
.
├── docs/
├── experiments/
├── notes/
├── papers/
├── results/
├── src/
└── README.md
```

### docs/

Project plans, meeting notes, and progress tracking.

### experiments/

Individual experiment implementations and evaluations.

### notes/

Research notes, concepts, and learning logs.

### papers/

Paper summaries and literature review notes.

### results/

Generated datasets, statistical outputs, and experiment results.

### src/

Reusable code for generators and testing utilities.

---

## Current Progress

### Completed

* Initial literature review
* XORShift implementation
* Seed analysis experiments
* Frequency analysis experiments
* NIST SP 800-22 study (ongoing)

### In Progress

* Frequency Test implementation
* Runs Test study
* Statistical documentation framework

### Upcoming

* Full NIST test implementation
* Diehard and Dieharder testing
* FPGA data analysis
* Comparative evaluation of PRNG designs

---

## Technologies

* Python
* MATLAB (planned)
* Git/GitHub
* NIST Statistical Test Suite
* FPGA Toolchains (project dependent)

---

## Research Log

This repository is maintained as a research notebook. Experiments, observations, and conclusions are documented as the project progresses.

---

## Acknowledgements

Research conducted through the Hamilton Institute SPUR 2026 Programme under the supervision of Dr. Erivelton Nepomuceno and Arthur.
