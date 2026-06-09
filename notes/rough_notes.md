# What I Have Learned So Far

## Project Overview

The project focuses on evaluating pseudo-random number generators (PRNGs) using statistical testing methods such as NIST SP 800-22.

The main goal is to determine whether generated sequences are sufficiently random for cryptographic and lightweight security applications.

 

## Randomness Testing

### NIST SP 800-22

NIST provides a collection of statistical tests used to evaluate randomness.

I have started learning:

* Frequency Test
* Block Frequency Test
* Runs Test

### Important Observation

Passing a single test does not prove that a sequence is random.

Different tests measure different properties of randomness.

 

## XOR-Based Generators

I implemented an XORShift generator in Python and performed basic frequency analysis.

The experiments involved:

* Generating sequences using different seeds
* Converting outputs to binary
* Counting 1s and 0s
* Comparing the proportions

This helped me understand the difference between balance and true randomness.

 

## Chaos and Randomness

A major theme across the papers is that simple mathematical systems can generate very complex behaviour.

Examples include:

* Logistic maps
* Chaotic systems
* Discrete chaos

These systems are often used to generate pseudo-random sequences.

 

## Finite Precision

One of the most important concepts I have encountered is finite precision.

Computers cannot represent real numbers exactly.

Because chaotic systems are extremely sensitive to small changes, rounding and numerical errors can significantly affect their behaviour.

 

## Dynamical Degradation

Due to finite precision, a chaotic system implemented on a computer may lose some of its chaotic properties over time.

This phenomenon is referred to as dynamical degradation.

Several papers focus on either:

* reducing this effect, or
* exploiting it as a source of randomness

 

## Galois Fields

I have started learning about Galois fields and their use in cryptography.

One of the key advantages is that computations are performed using exact finite arithmetic, which avoids many floating-point precision issues.

 

## FPGA Implementations

Many of the papers implement PRNGs on FPGA hardware.

Some recurring ideas include:

* XOR operations
* Shift operations
* Throughput optimisation
* Resource efficiency

I am currently building a better understanding of FPGA-related concepts and hardware constraints.
 

## Literature Review

Papers studied so far include:

* High-Throughput Pseudo-Random Number Generators Over Discrete Chaos
* A Reliable Chaos-Based Cryptography Using Galois Field
* Image Encryption Based on the Pseudo-Orbits from 1D Chaotic Map
* Minimal Digital Chaotic System
* The Dangers of Rounding Errors for Simulations and Analysis of Nonlinear Circuits and Systems

 

## Current Focus

My current goals are:

* Develop a deeper understanding of NIST statistical testing
* Build a literature comparison matrix
* Organise notes and experiments on GitHub
* Prepare for analysing datasets provided by the research group

 

## Questions

* What would a successful outcome of the project look like by the end of SPUR?
ans : file from arthur and if heb could use a routine that he could use after im gne 
* Which statistical test suites should I prioritise after NIST SP 800-22? ent entropy  crypto analysis 
* Will my work focus mainly on analysing datasets, implementing generators, or both?
* Are there any additional papers or topics I should focus on during the first few weeks?
