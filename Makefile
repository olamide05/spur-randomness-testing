SHELL := /bin/bash
PYTHON := .venv/bin/python

.DEFAULT_GOAL := help

.PHONY: help install install-local setup-sts test check serve

help: ## Show the available development commands
	@awk 'BEGIN {FS = ":.*## "; printf "SPUR randomness framework\n\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install system/Python dependencies, build STS, and test
	bash scripts/setup.sh

install-local: ## Use a rootless local Verilator package, then set up and test
	bash scripts/setup_verilator_local.sh
	bash scripts/setup.sh --skip-system

setup-sts: ## Build or rebuild the NIST STS assess executable
	bash scripts/setup_sts.sh

test: ## Run the Python, C-generator, HDL-generator, and Web UI tests
	$(PYTHON) -m pytest -q

check: test ## Alias for the full automated checks

serve: ## Start the Web UI at http://127.0.0.1:5000
	$(PYTHON) webui/app.py
