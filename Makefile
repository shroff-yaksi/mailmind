.PHONY: help install test lint format clean run

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ -v --cov=mailmind --cov-report=term-missing --cov-report=html

lint:  ## Run linting checks
	flake8 mailmind.py testconnection.py tests/ --count --statistics

format:  ## Format code with black and isort
	black mailmind.py testconnection.py tests/
	isort mailmind.py testconnection.py tests/

format-check:  ## Check if code is formatted
	black --check mailmind.py testconnection.py tests/
	isort --check mailmind.py testconnection.py tests/

type-check:  ## Run type checking with mypy
	mypy mailmind.py --ignore-missing-imports

clean:  ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

run:  ## Run the application
	python mailmind.py

test-connection:  ## Test email and API connections
	python testconnection.py

all: format lint test  ## Run format, lint, and test
