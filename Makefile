.PHONY: install dev-install test lint format clean build upload docs serve

# Default Python
PYTHON := python3
PIP := pip3

# Installation
install:
	$(PIP) install -e .

dev-install:
	$(PIP) install -e ".[dev]"
	playwright install

# Development
test:
	pytest tests/ -v --tb=short

lint:
	ruff check skt_ai_labs/
	black --check skt_ai_labs/

format:
	black skt_labs/ tests/
	ruff check --fix skt_ai_labs/

# Build & Distribution
build:
	$(PYTHON) -m build

upload:
	$(PYTHON) -m twine upload dist/*

# Documentation
docs:
	mkdocs serve

# Server
serve:
	uvicorn skt_ai_labs.api.server:app --reload --host 0.0.0.0 --port 8000

# CLI Examples
research:
	skt-adk research "Latest AI trends 2026"

chat:
	skt-adk chat "What is quantum computing?"

browse:
	skt-adk browse "Go to Hacker News and get top stories"

team:
	skt-adk team "Research latest AI developments"

# Cleanup
clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
