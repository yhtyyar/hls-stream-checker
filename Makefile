.PHONY: install test lint clean build deploy

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	flake8 .
	black . --check
	isort . --check-only

format:
	black .
	isort .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

build:
	python setup.py sdist bdist_wheel

deploy:
	./deploy.sh
