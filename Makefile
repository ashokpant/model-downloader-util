.PHONY: install upgrade test clean

install:
	uv sync

upgrade:
	uv sync --upgrade

test:
	uv run pytest

clean:
	rm -rf .venv dist build __pycache__ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
