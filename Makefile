.PHONY: build test format lint clean run help

VENV = venv_vibe_attribute
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

help:
	@echo "Available targets:"
	@echo "  make build   - Install dependencies"
	@echo "  make test    - Run tests"
	@echo "  make format  - Format code with ruff"
	@echo "  make lint    - Lint with ruff and mypy"
	@echo "  make clean   - Remove build artifacts"
	@echo "  make run     - Run the CLI tool (example: make run ARGS='image.png')"

build: $(VENV)
	$(PIP) install -e ".[dev]"

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

test: build
	$(PYTHON) -m pytest tests/ -v --cov=attribute --cov-report=term-missing

format: build
	$(PYTHON) -m ruff format attribute/ tests/
	$(PYTHON) -m ruff check --fix attribute/ tests/

lint: build
	$(PYTHON) -m ruff check attribute/ tests/
	$(PYTHON) -m mypy attribute/

clean:
	rm -rf $(VENV)
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

run: build
	$(PYTHON) -m attribute.cli $(ARGS)

