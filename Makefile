PHONY: help
help:
	@echo "Available targets:"
	@echo "  setup       - Create virtual environment and install dependencies"
	@echo "  clean       - Remove virtual environment"
	@echo "  reinstall   - Clean and reinstall everything"
	@echo "  run         - Activate venv and run kairo CLI"
	@echo "  test        - Run tests with pytest"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  lint        - Run linters (black and isort)"
	@echo "  format      - Format code (black and isort)"

PHONY: setup
setup:
	@echo "Setting up virtual environment..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install poetry
	. venv/bin/activate && poetry install
	. venv/bin/activate && pip install -e .
	@echo "Setup complete. Activate with: source venv/bin/activate"

PHONY: clean
clean:
	@echo "Cleaning virtual environment..."
	rm -rf venv
	@echo "Cleaned successfully"

PHONY: reinstall
reinstall: clean setup

PHONY: test
test:
	@echo "Running tests..."
	. venv/bin/activate && python -m pytest tests/ -v --tb=short

PHONY: test-cov
test-cov:
	@echo "Running tests with coverage..."
	. venv/bin/activate && python -m pytest tests/ -v --cov=kairo --cov-report=term-missing

PHONY: lint
lint:
	@echo "Running linters..."
	. venv/bin/activate && black --check .
	. venv/bin/activate && isort --check .

PHONY: format
format:
	@echo "Formatting code..."
	. venv/bin/activate && black .
	. venv/bin/activate && isort .

PHONY: run
run:
	@echo "Activating virtual environment and running kairo..."
	. venv/bin/activate && kairo $(args)